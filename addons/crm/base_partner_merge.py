#!/usr/bin/env python
from __future__ import absolute_import
from email.utils import parseaddr
import functools
import htmlentitydefs
import itertools
import logging
import operator
import psycopg2
import re
from ast import literal_eval
from openerp.tools import mute_logger

# Validation Library https://pypi.python.org/pypi/validate_email/1.1
from .validate_email import validate_email

import openerp
# from openerp.osv import osv, orm
# from openerp.osv import fields
from openerp import models, fields, api, _
from openerp.osv.orm import browse_record
from openerp.tools.translate import _

pattern = re.compile("&(\w+?);")

_logger = logging.getLogger('base.partner.merge')


# http://www.php2python.com/wiki/function.html-entity-decode/
def html_entity_decode_char(m, defs=htmlentitydefs.entitydefs):
    try:
        return defs[m.group(1)]
    except KeyError:
        return m.group(0)


def html_entity_decode(string):
    return pattern.sub(html_entity_decode_char, string)


def sanitize_email(email):
    assert isinstance(email, basestring) and email

    result = re.subn(r';|/|:', ',',
                     html_entity_decode(email or ''))[0].split(',')

    emails = [parseaddr(email)[1]
              for item in result
              for email in item.split()]

    return [email.lower()
            for email in emails
            if validate_email(email)]


def is_integer_list(ids):
    return all(isinstance(i, (int, long)) for i in ids)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    id = fields.Integer('Id', readonly=True)
    create_date = fields.Datetime('Create Date', readonly=True)


class MergePartnerLine(models.TransientModel):
    _name = 'base.partner.merge.line'

    wizard_id = fields.Many2one('base.partner.merge.automatic.wizard',
                                 'Wizard')
    min_id = fields.Integer('MinID')
    aggr_ids = fields.Char('Ids', required=True)

    _order = 'min_id asc'

class MergePartnerAutomatic(models.TransientModel):
    """
        The idea behind this wizard is to create a list of potential partners to
        merge. We use two objects, the first one is the wizard for the end-user.
        And the second will contain the partner list to merge.
    """
    _name = 'base.partner.merge.automatic.wizard'

    group_by_email = fields.Boolean('Email')
    group_by_name = fields.Boolean('Name')
    group_by_is_company = fields.Boolean('Is Company')
    group_by_vat = fields.Boolean('VAT')
    group_by_parent_id = fields.Boolean('Parent Company')

    state = fields.Selection([('option', 'Option'),
                               ('selection', 'Selection'),
                               ('finished', 'Finished')],
                              'State',
                              readonly=True,
                              required=True,
                              default='option')
    number_group = fields.Integer("Group of Contacts", readonly=True)
    current_line_id = fields.Many2one('base.partner.merge.line', 'Current Line')
    line_ids = fields.One2many('base.partner.merge.line', 'wizard_id', 'Lines')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    dst_partner_id = fields.Many2one('res.partner', string='Destination Contact')

    exclude_contact = fields.Boolean('A user associated to the contact')
    exclude_journal_item = fields.Boolean('Journal Items associated to the contact')
    maximum_group = fields.Integer("Maximum of Group of Contacts")

    @api.model
    def default_get(self, fields):
        res = super(MergePartnerAutomatic, self).default_get(fields)
        if self._context.get('active_model') == 'res.partner' and self._context.get('active_ids'):
            partner_ids = self._context['active_ids']
            res['state'] = 'selection'
            res['partner_ids'] = partner_ids
            res['dst_partner_id'] = self._get_ordered_partner(partner_ids)[-1].id
        return res

    _defaults = {
        'state': 'option'
    }

    @api.multi
    def get_fk_on(self, table):
        q = """  SELECT cl1.relname as table,
                        att1.attname as column
                   FROM pg_constraint as con, pg_class as cl1, pg_class as cl2,
                        pg_attribute as att1, pg_attribute as att2
                  WHERE con.conrelid = cl1.oid
                    AND con.confrelid = cl2.oid
                    AND array_lower(con.conkey, 1) = 1
                    AND con.conkey[1] = att1.attnum
                    AND att1.attrelid = cl1.oid
                    AND cl2.relname = %s
                    AND att2.attname = 'id'
                    AND array_lower(con.confkey, 1) = 1
                    AND con.confkey[1] = att2.attnum
                    AND att2.attrelid = cl2.oid
                    AND con.contype = 'f'
        """
        return self._cr.execute(q, (table,))

    @api.multi
    def _update_foreign_keys(self, src_partners, dst_partner):
        _logger.debug('_update_foreign_keys for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        # find the many2one relation to a partner
        proxy = self.pool['res.partner']
        self.get_fk_on('res_partner')
        # ignore two tables
        for table, column in self._cr.fetchall():
            if 'base_partner_merge_' in table:
                continue
            partner_ids = tuple(map(int, src_partners))
            query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE '%s'" % (table)
            self._cr.execute(query, ())
            columns = []
            for data in self._cr.fetchall():
                if data[0] != column:
                    columns.append(data[0])

            query_dic = {
                'table': table,
                'column': column,
                'value': columns[0],
            }
            if len(columns) <= 1:
                # unique key treated
                query = """
                    UPDATE "%(table)s" as ___tu
                    SET %(column)s = %%s
                    WHERE
                        %(column)s = %%s AND
                        NOT EXISTS (
                            SELECT 1
                            FROM "%(table)s" as ___tw
                            WHERE
                                %(column)s = %%s AND
                                ___tu.%(value)s = ___tw.%(value)s
                        )""" % query_dic
                for partner_id in partner_ids:
                    self._cr.execute(query, (dst_partner.id, partner_id, dst_partner.id))
            else:
                try:
                    with mute_logger('openerp.sql_db'), self._cr.savepoint():
                        query = 'UPDATE "%(table)s" SET %(column)s = %%s WHERE %(column)s IN %%s' % query_dic
                        self._cr.execute(query, (dst_partner.id, partner_ids,))
                        if column == proxy._parent_name and table == 'res_partner':
                            query = """
                                WITH RECURSIVE cycle(id, parent_id) AS (
                                        SELECT id, parent_id FROM res_partner
                                    UNION
                                        SELECT  cycle.id, res_partner.parent_id
                                        FROM    res_partner, cycle
                                        WHERE   res_partner.id = cycle.parent_id AND
                                                cycle.id != cycle.parent_id
                                )
                                SELECT id FROM cycle WHERE id = parent_id AND id = %s
                            """
                            self._cr.execute(query, (dst_partner.id,))
                except psycopg2.Error:
                    # updating fails, most likely due to a violated unique constraint
                    # keeping record with nonexistent partner_id is useless, better delete it
                    query = 'DELETE FROM %(table)s WHERE %(column)s = %%s' % query_dic
                    self._cr.execute(query, (partner_id,))

    @api.multi
    def _update_reference_fields(self, src_partners, dst_partner):
        _logger.debug('_update_reference_fields for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        def update_records(model, src, field_model='model', field_id='res_id'):
            proxy = self.pool.get(model)
            if proxy is None:
                return
            domain = [(field_model, '=', 'res.partner'), (field_id, '=', src.id)]
            ids = proxy.search(self._cr, openerp.SUPERUSER_ID, domain, context=self._context)
            try:
                with mute_logger('openerp.sql_db'), self._cr.savepoint():
                    return proxy.write(self._cr, openerp.SUPERUSER_ID, ids, {field_id: dst_partner.id}, context=self._context)
            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent partner_id is useless, better delete it
                return proxy.unlink(self._cr, openerp.SUPERUSER_ID, ids, context=self._context)
        update_records = functools.partial(update_records)

        for partner in src_partners:
            update_records('calendar', src=partner, field_model='model_id.model')
            update_records('ir.attachment', src=partner, field_model='res_model')
            update_records('mail.followers', src=partner, field_model='res_model')
            update_records('mail.message', src=partner)
            update_records('marketing.campaign.workitem', src=partner, field_model='object_id.model')
            update_records('ir.model.data', src=partner)

        proxy = self.pool['ir.model.fields']
        domain = [('ttype', '=', 'reference')]
        record_ids = proxy.search(self._cr, openerp.SUPERUSER_ID, domain, context=self._context)

        for record in proxy.browse(self._cr, openerp.SUPERUSER_ID, record_ids, context=self._context):
            try:
                proxy_model = self.pool[record.model]
                field_type = proxy_model._columns[record.name].__class__._type
            except KeyError:
                # unknown model or field => skip
                continue
            if field_type == 'function':
                continue
            for partner in src_partners:
                domain = [
                    (record.name, '=', 'res.partner,%d' % partner.id)
                ]
                model_ids = proxy_model.search(self._cr, openerp.SUPERUSER_ID, domain, context=self._context)
                values = {
                    record.name: 'res.partner,%d' % dst_partner.id,
                }
                proxy_model.write(self._cr, openerp.SUPERUSER_ID, model_ids, values, context=self._context)

    @api.multi
    def _update_values(self, src_partners, dst_partner):
        _logger.debug('_update_values for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))
        columns = dst_partner._columns
        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item
        values = dict()
        for column, field in columns.iteritems():
            if field._type not in ('many2many', 'one2many') and not isinstance(field, models.NewId):
                for item in itertools.chain(src_partners, dst_partner):
                    
                    if item[column]:
                        values[column] = write_serializer(column, item[column])
        values.pop('id', None)
        parent_id = values.pop('parent_id', None)
        dst_partner.write(values)
        if parent_id and parent_id != dst_partner.id:
            try:
                dst_partner.write({'parent_id': parent_id})
            except (osv.except_osv, orm.except_orm):
                _logger.info('Skip recursive partner hierarchies for parent_id %s of partner: %s', parent_id, dst_partner.id)

    @api.multi
    @mute_logger('openerp.osv.expression', 'openerp.models')
    def _merge(self, partner_ids, dst_partner=None):
        proxy = self.pool['res.partner']
        partner_ids = proxy.exists(self._cr, self._uid, list(partner_ids), context=self._context)
        if len(partner_ids) < 2:
            return
        if len(partner_ids) > 3:
            raise osv.except_osv(_('Error'), _("For safety reasons, you cannot merge more than 3 contacts together. You can re-open the wizard several times if needed."))
        if openerp.SUPERUSER_ID != self._uid and len(set(partner.email for partner in partner_ids)) > 1:
            raise osv.except_osv(_('Error'), _("All contacts must have the same email. Only the Administrator can merge contacts with different emails."))
        if dst_partner and dst_partner.id in partner_ids:
            src_partners = proxy.browse(self._cr, self._uid, [id for id in partner_ids if id != dst_partner.id], context=self._context)
        else:
            ordered_partners = self._get_ordered_partner(partner_ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)
        if openerp.SUPERUSER_ID != self._uid and self._model_is_installed('account.move.line') and \
                self.pool['account.move.line'].search(self._cr, openerp.SUPERUSER_ID, [('partner_id', 'in', [partner.id for partner in src_partners])], context=self._context):
            raise osv.except_osv(_('Error'), _("Only the destination contact may be linked to existing Journal Items. Please ask the Administrator if you need to merge several contacts linked to existing Journal Items."))

        call_it = lambda function: function(src_partners, dst_partner)
        call_it(self._update_foreign_keys)
        call_it(self._update_reference_fields)
        call_it(self._update_values)

        _logger.info('(uid = %s) merged the partners %r with %s', self._uid, list(map(operator.attrgetter('id'), src_partners)), dst_partner.id)
        dst_partner.message_post(body='%s %s'%(_("Merged with the following partners:"), ", ".join('%s<%s>(ID %s)' % (p.name, p.email or 'n/a', p.id) for p in src_partners)))
        for partner in src_partners:
            partner.unlink()

#TODO: need to check
    @api.multi
    def clean_emails(self):
        """
        Clean the email address of the partner, if there is an email field with
        a mimum of two addresses, the system will create a new partner, with the
        information of the previous one and will copy the new cleaned email into
        the email field.
        """
        proxy_model = self.pool['ir.model.fields']
        fields = proxy_model.search_read(self._cr, self._uid, 
            [('model', '=', 'res.partner'),('ttype', 'like', '%2many')],context=self._context)
        reset_fields = dict((field['name'], []) for field in fields)
        proxy_partner = self.pool['res.partner']
        self = self.with_context(active_test=False)
        partners = proxy_partner.search_read(cr, uid, [], context=self._context)
        fields = ['name', 'var' 'partner_id' 'is_company', 'email']
        partners.sort(key=operator.itemgetter('id'))
        partners_len = len(partners)
        _logger.info('partner_len: %r', partners_len)

        for idx, partner in enumerate(partners):
            if not partner['email']:
                continue
            percent = (idx / float(partners_len)) * 100.0
            _logger.info('idx: %r', idx)
            _logger.info('percent: %r', percent)
            try:
                emails = sanitize_email(partner['email'])
                head, tail = emails[:1], emails[1:]
                email = head[0] if head else False
                proxy_partner.write(self._cr, self._uid, [partner['id']],
                                    {'email': email}, context=self._context)
                for email in tail:
                    values = dict(reset_fields, email=email)
                    proxy_partner.copy(self._cr, self._uid, partner['id'], values,
                                       context=self._context)
            except Exception:
                _logger.exception("There is a problem with this partner: %r", partner)
                raise
        return True

    @api.multi
    def close_cb(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def _generate_query(self, fields, maximum_group=100):
        sql_fields = []
        for field in fields:
            if field in ['email', 'name']:
                sql_fields.append('lower(%s)' % field)
            elif field in ['vat']:
                sql_fields.append("replace(%s, ' ', '')" % field)
            else:
                sql_fields.append(field)
        group_fields = ', '.join(sql_fields)
        filters = []
        for field in fields:
            if field in ['email', 'name', 'vat']:
                filters.append((field, 'IS NOT', 'NULL'))
        criteria = ' AND '.join('%s %s %s' % (field, operator, value)
                                for field, operator, value in filters)

        text = [
            "SELECT min(id), array_agg(id)",
            "FROM res_partner",
        ]

        if criteria:
            text.append('WHERE %s' % criteria)

        text.extend([
            "GROUP BY %s" % group_fields,
            "HAVING COUNT(*) >= 2",
            "ORDER BY min(id)",
        ])

        if maximum_group:
            text.extend([
                "LIMIT %s" % maximum_group,
            ])
        
        
        return ' '.join(text)

    @api.multi
    def _compute_selected_groupby(self):
        group_by_str = 'group_by_'
        group_by_len = len(group_by_str)
        fields = [
            key[group_by_len:]
            for key in self._columns.keys()
            if key.startswith(group_by_str)
        ]
        groups = [
            field
            for field in fields
            if getattr(self, '%s%s' % (group_by_str, field), False)
        ]
        if not groups:
            raise osv.except_osv(_('Error'),
                                 _("You have to specify a filter for your selection"))
        return groups

    @api.multi
    def next_cb(self):
        """
        Don't compute any thing
        """
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._next_screen()

    @api.multi
    def _get_ordered_partner(self, partner_ids):
        partners = self.pool['res.partner'].browse(self._cr, self._uid, list(partner_ids), context=self._context)
        ordered_partners = sorted(sorted(partners,
                            key=operator.attrgetter('create_date'), reverse=True),
                                key=operator.attrgetter('active'), reverse=True)
        return ordered_partners

    @api.multi
    def _next_screen(self):
        self.refresh()
        values = {}
        if self.line_ids:
            # in this case, we try to find the next record.
            current_line = self.line_ids[0]
            current_partner_ids = literal_eval(current_line.aggr_ids)
            values.update({
                'current_line_id': current_line.id,
                'partner_ids': [(6, 0, current_partner_ids)],
                'dst_partner_id': self._get_ordered_partner(current_partner_ids)[-1].id,
                'state': 'selection',
            })
        else:
            values.update({
                'current_line_id': False,
                'partner_ids': [],
                'state': 'finished',
            })

        self.write(values)
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def _model_is_installed(self, model):
        proxy = self.pool['ir.model']
        domain = [('model', '=', model)]
        return proxy.search_count(self._cr, self._uid, domain, context=self._context) > 0

    @api.multi
    def _partner_use_in(self, aggr_ids, models):
        """
        Check if there is no occurence of this group of partner in the selected
        model
        """
        for model, field in models.iteritems():
            proxy = self.pool[model]
            domain = [(field, 'in', aggr_ids)]
            if proxy.search_count(self._cr, self._uid, domain, context=self._context):
                return True
        return False

    @api.multi
    def compute_models(self):
        """
        Compute the different models needed by the system if you want to exclude
        some partners.
        """
        models = {}
        if self.exclude_contact:
            models['res.users'] = 'partner_id'

        if self._model_is_installed('account.move.line') and self.exclude_journal_item:
            models['account.move.line'] = 'partner_id'

        return models

    @api.multi
    def _process_query(self, query):
        """
        Execute the select request and write the result in this wizard
        """
        proxy = self.env['base.partner.merge.line']
        models = self.compute_models()
        self._cr.execute(query)
        counter = 0
        for min_id, aggr_ids in self._cr.fetchall():
            if models and self._partner_use_in(aggr_ids, models):
                continue
            values = {
                'wizard_id': self.id,
                'min_id': min_id,
                'aggr_ids': aggr_ids,
            }

            proxy.create(values)
            counter += 1

        values = {
            'state': 'selection',
            'number_group': counter,
        }
        self.write(values)
        _logger.info("counter: %s", counter)
        
    @api.multi
    def start_process_cb(self):
        """
        Start the process.
        * Compute the selected groups (with duplication)
        * If the user has selected the 'exclude_XXX' fields, avoid the partners.
        """
        self = self.with_context(active_test=False)
        groups = self._compute_selected_groupby()
        query = self._generate_query(groups, self[0].maximum_group)
        self._process_query(query)
        return self._next_screen()

    @api.multi
    def automatic_process_cb(self):
        
        self.start_process_cb()
        self.refresh()
        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(partner_ids)
            line.unlink()
            self._cr.commit()
        self.write({'state': 'finished'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def parent_migration_process_cb(self):
        self = self.with_context(active_test=False)
        query = """
            SELECT
                min(p1.id),
                array_agg(DISTINCT p1.id)
            FROM
                res_partner as p1
            INNER join
                res_partner as p2
            ON
                p1.email = p2.email AND
                p1.name = p2.name AND
                (p1.parent_id = p2.id OR p1.id = p2.parent_id)
            WHERE
                p2.id IS NOT NULL
            GROUP BY
                p1.email,
                p1.name,
                CASE WHEN p1.parent_id = p2.id THEN p2.id
                    ELSE p1.id
                END
            HAVING COUNT(*) >= 2
            ORDER BY
                min(p1.id)
        """
        self._process_query(query)
        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(partner_ids)
            line.unlink()
            self._cr.commit()
        self.write({'state': 'finished'})
        self._cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL,
                parent_id = NULL
            WHERE
                parent_id = id
        """)
        
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    @api.multi
    def update_all_process_cb(self):
        # WITH RECURSIVE cycle(id, parent_id) AS (
        #     SELECT id, parent_id FROM res_partner
        #   UNION
        #     SELECT  cycle.id, res_partner.parent_id
        #     FROM    res_partner, cycle
        #     WHERE   res_partner.id = cycle.parent_id AND
        #             cycle.id != cycle.parent_id
        # )
        # UPDATE  res_partner
        # SET     parent_id = NULL
        # WHERE   id in (SELECT id FROM cycle WHERE id = parent_id);

        self.parent_migration_process_cb()
        list_merge = [
            {'group_by_vat': True, 'group_by_email': True, 'group_by_name': True},
            # {'group_by_name': True, 'group_by_is_company': True, 'group_by_parent_id': True},
            # {'group_by_email': True, 'group_by_is_company': True, 'group_by_parent_id': True},
            # {'group_by_name': True, 'group_by_vat': True, 'group_by_is_company': True, 'exclude_journal_item': True},
            # {'group_by_email': True, 'group_by_vat': True, 'group_by_is_company': True, 'exclude_journal_item': True},
            # {'group_by_email': True, 'group_by_is_company': True, 'exclude_contact': True, 'exclude_journal_item': True},
            # {'group_by_name': True, 'group_by_is_company': True, 'exclude_contact': True, 'exclude_journal_item': True}
        ]

        for merge_value in list_merge:
            rec = self.create(merge_value)
            rec.automatic_process_cb()

        self._cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL
            WHERE
                parent_id IS NOT NULL AND
                is_company IS NOT NULL
        """)

        # cr.execute("""
        #     UPDATE
        #         res_partner as p1
        #     SET
        #         is_company = NULL,
        #         parent_id = (
        #             SELECT  p2.id
        #             FROM    res_partner as p2
        #             WHERE   p2.email = p1.email AND
        #                     p2.parent_id != p2.id
        #             LIMIT 1
        #         )
        #     WHERE
        #         p1.parent_id = p1.id
        # """)
        return self._next_screen()

    @api.multi
    def merge_cb(self):
        self = self.with_context(active_test=False)
        partner_ids = set(map(int, self.partner_ids))
        if not partner_ids:
            self.write({'state': 'finished'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        self._merge(partner_ids)
        if self.current_line_id:
            self.current_line_id.unlink()
        return self._next_screen()

    @api.multi
    def auto_set_parent_id(self):
        # select partner who have one least invoice
        partner_treated = ['@gmail.com']
        self._cr.execute("""  SELECT p.id, p.email
                        FROM res_partner as p 
                        LEFT JOIN account_invoice as a 
                        ON p.id = a.partner_id AND a.state in ('open','paid')
                        WHERE p.grade_id is NOT NULL
                        GROUP BY p.id
                        ORDER BY COUNT(a.id) DESC
                """)
        re_email = re.compile(r".*@")
        for id, email in self._cr.fetchall():
            # check email domain
            email = re_email.sub("@", email or "")
            if not email or email in partner_treated:
                continue
            partner_treated.append(email)
            # don't update the partners if they are more of one who have invoice
            self._cr.execute("""  SELECT *
                            FROM res_partner as p
                            WHERE p.id != %s AND p.email LIKE '%%%s' AND
                                EXISTS (SELECT * FROM account_invoice as a WHERE p.id = a.partner_id AND a.state in ('open','paid'))
                    """ % (id, email))

            if len(self._cr.fetchall()) > 1:
                _logger.info("%s MORE OF ONE COMPANY", email)
                continue

            # to display changed values
            self._.execute("""  SELECT id,email
                            FROM res_partner
                            WHERE parent_id != %s AND id != %s AND email LIKE '%%%s'
                    """ % (id, id, email))
            _logger.info("%r", self._cr.fetchall())
            # upgrade
            self._cr.execute("""  UPDATE res_partner
                            SET parent_id = %s
                            WHERE id != %s AND email LIKE '%%%s'
                    """ % (id, id, email))
        return False