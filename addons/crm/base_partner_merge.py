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
from openerp.exceptions import ValidationError
from openerp.tools import mute_logger

# Validation Library https://pypi.python.org/pypi/validate_email/1.1
from .validate_email import validate_email

import openerp
from openerp.osv import osv, orm
from openerp.osv import fields
from openerp.osv.orm import browse_record
from openerp.tools.translate import _
from openerp.exceptions import UserError

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


class ResPartner(osv.Model):
    _inherit = 'res.partner'

    _columns = {
        'id': fields.integer('Id', readonly=True),
        'create_date': fields.datetime('Create Date', readonly=True),
    }

class MergePartnerLine(osv.TransientModel):
    _name = 'base.partner.merge.line'

    _columns = {
        'wizard_id': fields.many2one('base.partner.merge.automatic.wizard',
                                     'Wizard'),
        'min_id': fields.integer('MinID'),
        'aggr_ids': fields.char('Ids', required=True),
    }

    _order = 'min_id asc'


class MergePartnerAutomatic(osv.TransientModel):
    """
        The idea behind this wizard is to create a list of potential partners to
        merge. We use two objects, the first one is the wizard for the end-user.
        And the second will contain the partner list to merge.
    """
    _name = 'base.partner.merge.automatic.wizard'

    _columns = {
        # Group by
        'group_by_email': fields.boolean('Email'),
        'group_by_name': fields.boolean('Name'),
        'group_by_is_company': fields.boolean('Is Company'),
        'group_by_vat': fields.boolean('VAT'),
        'group_by_parent_id': fields.boolean('Parent Company'),

        'state': fields.selection([('option', 'Option'),
                                   ('selection', 'Selection'),
                                   ('finished', 'Finished')],
                                  'State',
                                  readonly=True,
                                  required=True),
        'number_group': fields.integer("Group of Contacts", readonly=True),
        'current_line_id': fields.many2one('base.partner.merge.line', 'Current Line'),
        'line_ids': fields.one2many('base.partner.merge.line', 'wizard_id', 'Lines'),
        'partner_ids': fields.many2many('res.partner', string='Contacts'),
        'dst_partner_id': fields.many2one('res.partner', string='Destination Contact'),

        'exclude_contact': fields.boolean('A user associated to the contact'),
        'exclude_journal_item': fields.boolean('Journal Items associated to the contact'),
        'maximum_group': fields.integer("Maximum of Group of Contacts"),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(MergePartnerAutomatic, self).default_get(cr, uid, fields, context)
        if context.get('active_model') == 'res.partner' and context.get('active_ids'):
            partner_ids = context['active_ids']
            res['state'] = 'selection'
            res['partner_ids'] = partner_ids
            res['dst_partner_id'] = self._get_ordered_partner(cr, uid, partner_ids, context=context)[-1].id
        return res

    _defaults = {
        'state': 'option'
    }

    def get_fk_on(self, cr, table):
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
        return cr.execute(q, (table,))

    def _update_foreign_keys(self, cr, uid, src_partners, dst_partner, context=None):
        _logger.debug('_update_foreign_keys for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        # find the many2one relation to a partner
        proxy = self.pool.get('res.partner')
        self.get_fk_on(cr, 'res_partner')

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
                            cr.execute(query, (dst_partner.id,))
                except psycopg2.Error:
                    # updating fails, most likely due to a violated unique constraint
                    # keeping record with nonexistent partner_id is useless, better delete it
                    query = 'DELETE FROM %(table)s WHERE %(column)s = %%s' % query_dic
                    cr.execute(query, (partner_id,))

    def _update_reference_fields(self, cr, uid, src_partners, dst_partner, context=None):
        _logger.debug('_update_reference_fields for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))

        def update_records(model, src, field_model='model', field_id='res_id', context=None):
            proxy = self.pool.get(model)
            if proxy is None:
                return
            domain = [(field_model, '=', 'res.partner'), (field_id, '=', src.id)]
            ids = proxy.search(cr, openerp.SUPERUSER_ID, domain, context=context)
            try:
                with mute_logger('openerp.sql_db'), cr.savepoint():
                    return proxy.write(cr, openerp.SUPERUSER_ID, ids, {field_id: dst_partner.id}, context=context)
            except psycopg2.Error:
                # updating fails, most likely due to a violated unique constraint
                # keeping record with nonexistent partner_id is useless, better delete it
                return proxy.unlink(cr, openerp.SUPERUSER_ID, ids, context=context)

        update_records = functools.partial(update_records, context=context)

        for partner in src_partners:
            update_records('calendar', src=partner, field_model='model_id.model')
            update_records('ir.attachment', src=partner, field_model='res_model')
            update_records('mail.followers', src=partner, field_model='res_model')
            update_records('mail.message', src=partner)
            update_records('marketing.campaign.workitem', src=partner, field_model='object_id.model')
            update_records('ir.model.data', src=partner)

        proxy = self.pool['ir.model.fields']
        domain = [('ttype', '=', 'reference')]
        record_ids = proxy.search(cr, openerp.SUPERUSER_ID, domain, context=context)

        for record in proxy.browse(cr, openerp.SUPERUSER_ID, record_ids, context=context):
            try:
                proxy_model = self.pool[record.model]
                column = proxy_model._columns[record.name]
            except KeyError:
                # unknown model or field => skip
                continue

            if isinstance(column, fields.function):
                continue

            for partner in src_partners:
                domain = [
                    (record.name, '=', 'res.partner,%d' % partner.id)
                ]
                model_ids = proxy_model.search(cr, openerp.SUPERUSER_ID, domain, context=context)
                values = {
                    record.name: 'res.partner,%d' % dst_partner.id,
                }
                proxy_model.write(cr, openerp.SUPERUSER_ID, model_ids, values, context=context)

    def _update_values(self, cr, uid, src_partners, dst_partner, context=None):
        _logger.debug('_update_values for dst_partner: %s for src_partners: %r', dst_partner.id, list(map(operator.attrgetter('id'), src_partners)))
        columns = dst_partner.fields_get().keys()
        def write_serializer(column, item):
            if isinstance(item, browse_record):
                return item.id
            else:
                return item

        values = dict()
        for column in columns:
            field = dst_partner._fields[column]
            if field.type not in ('many2many', 'one2many') and field.compute is None:
                for item in itertools.chain(src_partners, [dst_partner]):
                    if item[column]:
                        values[column] = write_serializer(column, item[column])

        values.pop('id', None)
        parent_id = values.pop('parent_id', None)
        dst_partner.write(values)
        if parent_id and parent_id != dst_partner.id:
            try:
                dst_partner.write({'parent_id': parent_id})
            except ValidationError:
                _logger.info('Skip recursive partner hierarchies for parent_id %s of partner: %s', parent_id, dst_partner.id)

    @mute_logger('openerp.osv.expression', 'openerp.models')
    def _merge(self, cr, uid, partner_ids, dst_partner=None, context=None):
        proxy = self.pool.get('res.partner')

        partner_ids = proxy.exists(cr, uid, list(partner_ids), context=context)
        if len(partner_ids) < 2:
            return

        if len(partner_ids) > 3:
            raise UserError(_("For safety reasons, you cannot merge more than 3 contacts together. You can re-open the wizard several times if needed."))

        child_ids = set()
        for partner_id in partner_ids:
            child_ids = child_ids.union(set(proxy.search(cr, uid, [('id', 'child_of', [partner_id])])) - set([partner_id]))
        if set(partner_ids).intersection(child_ids):
            raise UserError(_("You cannot merge a contact with one of his parent."))

        if openerp.SUPERUSER_ID != uid and len(set(partner.email for partner in proxy.browse(cr, uid, partner_ids, context=context))) > 1:
            raise UserError(_("All contacts must have the same email. Only the Administrator can merge contacts with different emails."))

        if dst_partner and dst_partner.id in partner_ids:
            src_partners = proxy.browse(cr, uid, [id for id in partner_ids if id != dst_partner.id], context=context)
        else:
            ordered_partners = self._get_ordered_partner(cr, uid, partner_ids, context)
            dst_partner = ordered_partners[-1]
            src_partners = ordered_partners[:-1]
        _logger.info("dst_partner: %s", dst_partner.id)

        if openerp.SUPERUSER_ID != uid and self._model_is_installed(cr, uid, 'account.move.line', context=context) and \
                self.pool.get('account.move.line').search(cr, openerp.SUPERUSER_ID, [('partner_id', 'in', [partner.id for partner in src_partners])], context=context):
            raise UserError(_("Only the destination contact may be linked to existing Journal Items. Please ask the Administrator if you need to merge several contacts linked to existing Journal Items."))

        call_it = lambda function: function(cr, uid, src_partners, dst_partner,
                                            context=context)

        call_it(self._update_foreign_keys)
        call_it(self._update_reference_fields)
        call_it(self._update_values)

        _logger.info('(uid = %s) merged the partners %r with %s', uid, list(map(operator.attrgetter('id'), src_partners)), dst_partner.id)
        dst_partner.message_post(body='%s %s'%(_("Merged with the following partners:"), ", ".join('%s<%s>(ID %s)' % (p.name, p.email or 'n/a', p.id) for p in src_partners)))
        
        for partner in src_partners:
            partner.unlink()

    def clean_emails(self, cr, uid, context=None):
        """
        Clean the email address of the partner, if there is an email field with
        a mimum of two addresses, the system will create a new partner, with the
        information of the previous one and will copy the new cleaned email into
        the email field.
        """
        context = dict(context or {})

        proxy_model = self.pool['ir.model.fields']
        field_ids = proxy_model.search(cr, uid, [('model', '=', 'res.partner'),
                                                 ('ttype', 'like', '%2many')],
                                       context=context)
        fields = proxy_model.read(cr, uid, field_ids, context=context)
        reset_fields = dict((field['name'], []) for field in fields)

        proxy_partner = self.pool['res.partner']
        context['active_test'] = False
        ids = proxy_partner.search(cr, uid, [], context=context)

        fields = ['name', 'var' 'partner_id' 'is_company', 'email']
        partners = proxy_partner.read(cr, uid, ids, fields, context=context)

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

                proxy_partner.write(cr, uid, [partner['id']],
                                    {'email': email}, context=context)

                for email in tail:
                    values = dict(reset_fields, email=email)
                    proxy_partner.copy(cr, uid, partner['id'], values,
                                       context=context)

            except Exception:
                _logger.exception("There is a problem with this partner: %r", partner)
                raise
        return True

    def close_cb(self, cr, uid, ids, context=None):
        return {'type': 'ir.actions.act_window_close'}

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

    def _compute_selected_groupby(self, this):
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
            if getattr(this, '%s%s' % (group_by_str, field), False)
        ]

        if not groups:
            raise UserError(_("You have to specify a filter for your selection"))

        return groups

    def next_cb(self, cr, uid, ids, context=None):
        """
        Don't compute any thing
        """
        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)
        if this.current_line_id:
            this.current_line_id.unlink()
        return self._next_screen(cr, uid, this, context)

    def _get_ordered_partner(self, cr, uid, partner_ids, context=None):
        partners = self.pool.get('res.partner').browse(cr, uid, list(partner_ids), context=context)
        ordered_partners = sorted(sorted(partners,
                            key=operator.attrgetter('create_date'), reverse=True),
                                key=operator.attrgetter('active'), reverse=True)
        return ordered_partners

    def _next_screen(self, cr, uid, this, context=None):
        this.refresh()
        values = {}
        if this.line_ids:
            # in this case, we try to find the next record.
            current_line = this.line_ids[0]
            current_partner_ids = literal_eval(current_line.aggr_ids)
            values.update({
                'current_line_id': current_line.id,
                'partner_ids': [(6, 0, current_partner_ids)],
                'dst_partner_id': self._get_ordered_partner(cr, uid, current_partner_ids, context)[-1].id,
                'state': 'selection',
            })
        else:
            values.update({
                'current_line_id': False,
                'partner_ids': [],
                'state': 'finished',
            })

        this.write(values)

        return {
            'type': 'ir.actions.act_window',
            'res_model': this._name,
            'res_id': this.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _model_is_installed(self, cr, uid, model, context=None):
        proxy = self.pool.get('ir.model')
        domain = [('model', '=', model)]
        return proxy.search_count(cr, uid, domain, context=context) > 0

    def _partner_use_in(self, cr, uid, aggr_ids, models, context=None):
        """
        Check if there is no occurence of this group of partner in the selected
        model
        """
        for model, field in models.iteritems():
            proxy = self.pool.get(model)
            domain = [(field, 'in', aggr_ids)]
            if proxy.search_count(cr, uid, domain, context=context):
                return True
        return False

    def compute_models(self, cr, uid, ids, context=None):
        """
        Compute the different models needed by the system if you want to exclude
        some partners.
        """
        assert is_integer_list(ids)

        this = self.browse(cr, uid, ids[0], context=context)

        models = {}
        if this.exclude_contact:
            models['res.users'] = 'partner_id'

        if self._model_is_installed(cr, uid, 'account.move.line', context=context) and this.exclude_journal_item:
            models['account.move.line'] = 'partner_id'

        return models

    def _process_query(self, cr, uid, ids, query, context=None):
        """
        Execute the select request and write the result in this wizard
        """
        proxy = self.pool.get('base.partner.merge.line')
        this = self.browse(cr, uid, ids[0], context=context)
        models = self.compute_models(cr, uid, ids, context=context)
        cr.execute(query)

        counter = 0
        for min_id, aggr_ids in cr.fetchall():
            if models and self._partner_use_in(cr, uid, aggr_ids, models, context=context):
                continue
            values = {
                'wizard_id': this.id,
                'min_id': min_id,
                'aggr_ids': aggr_ids,
            }
            # To ensure that the used partners are accessible by the user
            partner_ids = self.pool['res.partner'].search(cr, uid, [('id', 'in', aggr_ids)], context=context)
            if len(partner_ids) >= 2:
                values['aggr_ids'] = partner_ids
                proxy.create(cr, uid, values, context=context)
                counter += 1

        values = {
            'state': 'selection',
            'number_group': counter,
        }

        this.write(values)

        _logger.info("counter: %s", counter)

    def start_process_cb(self, cr, uid, ids, context=None):
        """
        Start the process.
        * Compute the selected groups (with duplication)
        * If the user has selected the 'exclude_XXX' fields, avoid the partners.
        """
        assert is_integer_list(ids)

        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)
        groups = self._compute_selected_groupby(this)
        query = self._generate_query(groups, this.maximum_group)
        self._process_query(cr, uid, ids, query, context=context)

        return self._next_screen(cr, uid, this, context)

    def automatic_process_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)
        this = self.browse(cr, uid, ids[0], context=context)
        this.start_process_cb()
        this.refresh()

        for line in this.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(cr, uid, partner_ids, context=context)
            line.unlink()
            cr.commit()

        this.write({'state': 'finished'})
        return {
            'type': 'ir.actions.act_window',
            'res_model': this._name,
            'res_id': this.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def parent_migration_process_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)

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

        self._process_query(cr, uid, ids, query, context=context)

        for line in this.line_ids:
            partner_ids = literal_eval(line.aggr_ids)
            self._merge(cr, uid, partner_ids, context=context)
            line.unlink()
            cr.commit()

        this.write({'state': 'finished'})

        cr.execute("""
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
            'res_model': this._name,
            'res_id': this.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def update_all_process_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

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

        this = self.browse(cr, uid, ids[0], context=context)

        self.parent_migration_process_cb(cr, uid, ids, context=None)

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
            id = self.create(cr, uid, merge_value, context=context)
            self.automatic_process_cb(cr, uid, [id], context=context)

        cr.execute("""
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

        return self._next_screen(cr, uid, this, context)

    def merge_cb(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

        context = dict(context or {}, active_test=False)
        this = self.browse(cr, uid, ids[0], context=context)

        partner_ids = set(map(int, this.partner_ids))
        if not partner_ids:
            this.write({'state': 'finished'})
            return {
                'type': 'ir.actions.act_window',
                'res_model': this._name,
                'res_id': this.id,
                'view_mode': 'form',
                'target': 'new',
            }

        self._merge(cr, uid, partner_ids, this.dst_partner_id, context=context)

        if this.current_line_id:
            this.current_line_id.unlink()

        return self._next_screen(cr, uid, this, context)

    def auto_set_parent_id(self, cr, uid, ids, context=None):
        assert is_integer_list(ids)

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
