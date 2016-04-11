#!/usr/bin/env python
from odoo.osv import fields as f1
import functools
import htmlentitydefs
import itertools
import logging
import operator
import psycopg2
import re
from email.utils import parseaddr
from ast import literal_eval

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv.orm import browse_record
from odoo.tools import mute_logger

# Validation Library https://pypi.python.org/pypi/validate_email/1.1
from .validate_email import validate_email

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


class MergePartnerLine(models.TransientModel):
    _name = 'base.partner.merge.line'
    _order = 'min_id'

    wizard_id = fields.Many2one('base.partner.merge.automatic.wizard', string='Wizard')
    min_id = fields.Integer(string='MinID')
    aggr_ids = fields.Char(string='Ids', required=True)


class MergePartnerAutomatic(models.TransientModel):
    """
        The idea behind this wizard is to create a list of potential partners to
        merge. We use two objects, the first one is the wizard for the end-user.
        And the second will contain the partner list to merge.
    """
    _name = 'base.partner.merge.automatic.wizard'

    # Group by
    group_by_email = fields.Boolean(string='Email')
    group_by_name = fields.Boolean(string='Name')
    group_by_is_company = fields.Boolean(string='Is Company')
    group_by_vat = fields.Boolean(string='VAT')
    group_by_parent_id = fields.Boolean(string='Parent Company')

    state = fields.Selection([('option', 'Option'),
                                   ('selection', 'Selection'),
                                   ('finished', 'Finished')], readonly=True, required=True, default='option')
    number_group = fields.Integer(string="Group of Contacts", readonly=True)
    current_line_id = fields.Many2one('base.partner.merge.line', string='Current Line')
    line_ids = fields.One2many('base.partner.merge.line', 'wizard_id', string='Lines')
    partner_ids = fields.Many2many('res.partner', string='Contacts')
    dst_partner_id = fields.Many2one('res.partner', string='Destination Contact')

    exclude_contact = fields.Boolean(string='A user associated to the contact')
    exclude_journal_item = fields.Boolean(string='Journal Items associated to the contact')
    maximum_group = fields.Integer(string="Maximum of Group of Contacts")

    @api.model
    def default_get(self, fields):
        res = super(MergePartnerAutomatic, self).default_get(fields)
        active_ids = self.env.context.get('active_ids')
        if self.env.context.get('active_model') == 'res.partner' and active_ids:
            res['state'] = 'selection'
            res['partner_ids'] = active_ids
            res['dst_partner_id'] = self._get_ordered_partner(active_ids)[-1].id
        return res

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
        return self.env.cr.execute(q, (table,))

    @api.model
    def _update_foreign_keys(self, src_partners, dst_partner):
        _logger.debug('_update_foreign_keys for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))
        cr = self.env.cr
        # find the many2one relation to a partner
        Partner = self.env['res.partner']
        self.get_fk_on('res_partner')
        # ignore two tables

        for table, column in cr.fetchall():
            if 'base_partner_merge_' in table:
                continue
            partner_ids = tuple(map(int, src_partners))

            query = "SELECT column_name FROM information_schema.columns WHERE table_name LIKE '%s'" % (table)
            cr.execute(query, ())
            columns = []
            for data in cr.fetchall():
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
                    cr.execute(query, (dst_partner.id, partner_id, dst_partner.id))
            else:
                try:
                    with mute_logger('openerp.sql_db'), cr.savepoint():
                        query = 'UPDATE "%(table)s" SET %(column)s = %%s WHERE %(column)s IN %%s' % query_dic
                        cr.execute(query, (dst_partner.id, partner_ids,))

                        if column == Partner._parent_name and table == 'res_partner':
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
                            cr.execute(query, (dst_partner.id,))
                except psycopg2.Error:
                    # updating fails, most likely due to a violated unique constraint
                    # keeping record with nonexistent partner_id is useless, better delete it
                    query = 'DELETE FROM %(table)s WHERE %(column)s = %%s' % query_dic
                    cr.execute(query, (partner_id,))

    @api.model
    def _update_reference_fields(self, src_partners, dst_partner):
        _logger.debug('_update_reference_fields for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        def update_records(model, src, field_model='model', field_id='res_id'):
            if self.env.registry.get(model) is None:
                return
            domain = [(field_model, '=', 'res.partner'), (field_id, '=', src.id)]
            proxy_model = self.env[model].sudo().search(domain)
            try:
                with mute_logger('openerp.sql_db'), self.env.cr.savepoint():
                    return proxy_model.sudo().write({field_id: dst_partner.id})
            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent partner_id is useless, better delete it
                return proxy_model.sudo().unlink()

        update_records = functools.partial(update_records)

        for partner in src_partners:
            update_records('calendar', src=partner, field_model='model_id.model')
            update_records('ir.attachment', src=partner, field_model='res_model')
            update_records('mail.followers', src=partner, field_model='res_model')
            update_records('mail.message', src=partner)
            update_records('marketing.campaign.workitem', src=partner, field_model='object_id.model')
            update_records('ir.model.data', src=partner)

        domain = [('ttype', '=', 'reference')]
        for record in self.env['ir.model.fields'].sudo().search(domain):
            try:
                ProxyModel = self.env[record.model]
                field = ProxyModel._fields[record.name]
            except KeyError:
                # unknown model or field => skip
                continue

            if field.compute is not None:
                continue

            for partner in src_partners:
                domain = [
                    (record.name, '=', 'res.partner,%d' % partner.id)
                ]
                model_res = ProxyModel.sudo().search(domain)
                values = {
                    record.name: 'res.partner,%d' % dst_partner.id,
                }
                model_res.sudo().write(values)

    @api.model
    def _update_values(self, src_partners, dst_partner):
        _logger.debug('_update_values for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        fields = dst_partner._fields

        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item

        values = dict()
        for name, field in fields.iteritems():
            if field.type not in ('many2many', 'one2many') and field.compute is None:
                for item in itertools.chain(src_partners, [dst_partner]):
                    if item[name]:
                        values[name] = write_serializer(name, item[name])

        values.pop('id', None)
        parent_id = values.pop('parent_id', None)
        dst_partner.write(values)
        if parent_id and parent_id != dst_partner.id:
            try:
                dst_partner.write({'parent_id': parent_id})
            except ValidationError:
                _logger.info('Skip recursive partner hierarchies for parent_id %s of partner: %s', parent_id, dst_partner.id)

    @api.model
    @mute_logger('openerp.osv.expression', 'openerp.models')
    def _merge(self, partner_ids, dst_partner=None):
        Partner = childs = self.env['res.partner']
        partners = Partner.browse(partner_ids).exists()
        if len(partners) < 2:
            return

        if len(partners) > 3:
            raise UserError(_("For safety reasons, you cannot merge more than 3 contacts together. You can re-open the wizard several times if needed."))

        for partner in partners:
            childs |= (Partner.search([('id', 'child_of', [partner.id])]) - partner)
        if partners & childs:
            raise UserError(_("You cannot merge a contact with one of his parent."))

        if SUPERUSER_ID != self.env.uid and len(partners.mapped('email')) > 1:
            raise UserError(_("All contacts must have the same email. Only the Administrator can merge contacts with different emails."))

        if dst_partner and dst_partner in partners:
            src_partners = partners.filtered(lambda p: p != dst_partner)
        else:
            ordered_partners = self._get_ordered_partner(partners.ids)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)

        if SUPERUSER_ID != self.env.uid and self._model_is_installed('account.move.line') and \
                self.env['account.move.line'].sudo().search([('partner_id', 'in', src_partners.ids)]):
            raise UserError(_("Only the destination contact may be linked to existing Journal Items. Please ask the Administrator if you need to merge several contacts linked to existing Journal Items."))

        call_it = lambda function: function(src_partners, dst_partner)

        call_it(self._update_foreign_keys)
        call_it(self._update_reference_fields)
        call_it(self._update_values)

        _logger.info('(uid = %s) merged the partners %r with %s', self.env.uid, list(map(operator.attrgetter('id'), src_partners)), dst_partner.id)
        dst_partner.message_post(body='%s %s' % (_("Merged with the following partners:"), ", ".join('%s<%s>(ID %s)' % (p.name, p.email or 'n/a', p.id) for p in src_partners)))

        src_partners.unlink()

    @api.model
    def clean_emails(self):
        """
        Clean the email address of the partner, if there is an email field with
        a mimum of two addresses, the system will create a new partner, with the
        information of the previous one and will copy the new cleaned email into
        the email field.
        """
        context = dict(self.env.context)
        fields = self.env['ir.model.fields'].search([('model', '=', 'res.partner'),
                                                 ('ttype', 'like', '%2many')])
        reset_fields = dict((field.name, []) for field in fields)
  
        context['active_test'] = False
        Partner = self.env['res.partner'].with_context(context)
        partners = Partner.search([])
  
        fields = ['name', 'var' 'partner_id' 'is_company', 'email']
        partners_dict = partners.read(fields)
  
        partners_dict.sort(key=operator.itemgetter('id'))
        partners_len = len(partners_dict)
  
        _logger.info('partner_len: %r', partners_len)
  
        for idx, partner in enumerate(partners_dict):
            if not partner['email']:
                continue
  
            percent = (idx / float(partners_len)) * 100.0
            _logger.info('idx: %r', idx)
            _logger.info('percent: %r', percent)
            try:
                emails = sanitize_email(partner['email'])
                head, tail = emails[:1], emails[1:]
                email = head[0] if head else False
  
                Partner.browse(partner['id']).write({'email': email})
  
                for email in tail:
                    values = dict(reset_fields, email=email)
                    Partner.browse(partner['id']).copy(values)
  
            except Exception:
                _logger.exception("There is a problem with this partner: %r", partner)
                raise
        return True

    @api.multi
    def close_cb(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
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

    @api.model
    def _compute_selected_groupby(self):
        group_by_str = 'group_by_'
        group_by_len = len(group_by_str)

        fields = [
            key[group_by_len:]
            for key in self._fields.keys()
            if key.startswith(group_by_str)
        ]

        groups = [
            field
            for field in fields
            if getattr(self, '%s%s' % (group_by_str, field), False)
        ]

        if not groups:
            raise UserError(_("You have to specify a filter for your selection"))

        return groups

    @api.multi
    def next_cb(self):
        """
        Don't compute any thing
        """
        self.ensure_one()
        self.with_context(active_test=False).current_line_id.unlink()
        return self.with_context(active_test=False)._next_screen()

    @api.model
    def _get_ordered_partner(self, partner_ids):
        partners = self.env['res.partner'].search([('id', 'in', partner_ids)])
        return sorted(sorted(partners, key=operator.attrgetter(
            'create_date'), reverse=True), key=operator.attrgetter('active'), reverse=True)

    def _next_screen(self):
        self.ensure_one()
        self.invalidate_cache()
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

    @api.model
    def _model_is_installed(self, model):
        return self.env['ir.model'].search_count([('model', '=', model)]) > 0

    @api.model
    def _partner_use_in(self, aggr_ids, models):
        """
        Check if there is no occurence of this group of partner in the selected
        model
        """
        for model, field in models.iteritems():
            if self.env[model].search_count([(field, 'in', aggr_ids)]):
                return True
        return False

    def compute_models(self):
        """
        Compute the different models needed by the system if you want to exclude
        some partners.
        """
        self.ensure_one()

        models = {}
        if self.exclude_contact:
            models['res.users'] = 'partner_id'

        if self._model_is_installed('account.move.line') and self.exclude_journal_item:
            models['account.move.line'] = 'partner_id'

        return models

    def _process_query(self, query):
        """
        Execute the select request and write the result in this wizard
        """
        self.ensure_one()
        BasePartnerMergeLine = self.env['base.partner.merge.line']
        models = self.compute_models()
        self.env.cr.execute(query)

        counter = 0
        for min_id, aggr_ids in self.env.cr.fetchall():
            if models and self._partner_use_in(aggr_ids, models):
                continue
            values = {
                'wizard_id': self.id,
                'min_id': min_id,
                'aggr_ids': aggr_ids,
            }

            BasePartnerMergeLine.create(values)
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
        self.ensure_one()
        groups = self._compute_selected_groupby()
        query = self._generate_query(groups, self.maximum_group)
        self.with_context(active_test=False)._process_query(query)
        return self.with_context(active_test=False)._next_screen()

    @api.multi
    def automatic_process_cb(self):
        self.ensure_one()

        self.start_process_cb()
        self.invalidate_cache()

        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(partner_ids)
            line.unlink()
            self.env.cr.commit()

        self.state = 'finished'
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def parent_migration_process_cb(self):
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

        self.with_context(active_test=False)._process_query(query)

        for line in self.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self.with_context(active_test=False)._merge(partner_ids)
            line.unlink()
            self.env.cr.commit()

        self.state = 'finished'

        self.env.cr.execute("""
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
        self.ensure_one()
        self.parent_migration_process_cb()

        list_merge = [
            {'group_by_vat': True, 'group_by_email': True, 'group_by_name': True},
        ]

        for merge_value in list_merge:
            self.create(merge_value).automatic_process_cb()

        self.env.cr.execute("""
            UPDATE
                res_partner
            SET
                is_company = NULL
            WHERE
                parent_id IS NOT NULL AND
                is_company IS NOT NULL
        """)

        return self._next_screen()

    @api.multi
    def merge_cb(self):
        self.ensure_one()

        partner_ids = set(map(int, self.partner_ids))
        if not partner_ids:
            self.state = 'finished'
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }

        self.with_context(active_test=False)._merge(partner_ids, self.dst_partner_id)

        self.current_line_id.unlink()

        return self.with_context(active_test=False)._next_screen()

    def auto_set_parent_id(self):
        self.ensure_one()
        cr = self.env.cr

        # select partner who have one least invoice
        partner_treated = ['@gmail.com']
        cr.execute("""  SELECT p.id, p.email
                        FROM res_partner as p 
                        LEFT JOIN account_invoice as a 
                        ON p.id = a.partner_id AND a.state in ('open','paid')
                        WHERE p.grade_id is NOT NULL
                        GROUP BY p.id
                        ORDER BY COUNT(a.id) DESC
                """)
        re_email = re.compile(r".*@")
        for id, email in cr.fetchall():
            # check email domain
            email = re_email.sub("@", email or "")
            if not email or email in partner_treated:
                continue
            partner_treated.append(email)

            # don't update the partners if they are more of one who have invoice
            cr.execute("""  SELECT *
                            FROM res_partner as p
                            WHERE p.id != %s AND p.email LIKE %s AND
                                EXISTS (SELECT * FROM account_invoice as a WHERE p.id = a.partner_id AND a.state in ('open','paid'))
                    """, (id, '%' + email))

            if len(cr.fetchall()) > 1:
                _logger.info("%s MORE OF ONE COMPANY", email)
                continue

            # to display changed values
            cr.execute("""  SELECT id,email
                            FROM res_partner
                            WHERE parent_id != %s AND id != %s AND email LIKE %s
                    """, (id, id, '%' + email))
            _logger.info("%r", cr.fetchall())

            # upgrade
            cr.execute("""  UPDATE res_partner
                            SET parent_id = %s
                            WHERE id != %s AND email LIKE %s
                    """, (id, id, '%' + email))
        return False
