# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from hashlib import sha256
from json import dumps, loads
import logging
from collections import defaultdict

from odoo import models, api, fields, release, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class pos_config(models.Model):
    _inherit = 'pos.config'

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id:
                raise UserError(_("You have to set a country in your company setting."))
            if config.company_id._is_accounting_unalterable():
                if config.current_session_id:
                    config.current_session_id._check_session_timing()
        return super(pos_config, self).open_ui()

    def _config_sequence_implementation(self):
        return 'no_gap' if self.env.company._is_accounting_unalterable() else super()._config_sequence_implementation()


class pos_session(models.Model):
    _inherit = 'pos.session'

    def _check_session_timing(self):
        self.ensure_one()
        return True

    def open_frontend_cb(self):
        sessions_to_check = self.filtered(lambda s: s.config_id.company_id._is_accounting_unalterable())
        sessions_to_check.filtered(lambda s: s.state == 'opening_control').start_at = fields.Datetime.now()
        for session in sessions_to_check:
            session._check_session_timing()
        return super(pos_session, self).open_frontend_cb()


ORDER_FIELDS_BEFORE_17_4 = ['date_order', 'user_id', 'lines', 'payment_ids', 'pricelist_id', 'session_id', 'pos_reference', 'sale_journal', 'fiscal_position_id', 'partner_id']
ORDER_FIELDS_FROM_17_4 = ['date_order', 'user_id', 'lines', 'payment_ids', 'pricelist_id', 'session_id', 'pos_reference', 'sale_journal', 'fiscal_position_id', 'pos_version']
LINE_FIELDS = ['notice', 'product_id', 'qty', 'price_unit', 'discount', 'tax_ids', 'tax_ids_after_fiscal_position']


class pos_order(models.Model):
    _inherit = 'pos.order'

    l10n_fr_hash = fields.Char(string="Inalteralbility Hash", readonly=True, copy=False)
    l10n_fr_secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)
    previous_order_id = fields.Many2one('pos.order', string='Previous Order', readonly=True, compute='_compute_previous_order', store=True, copy=False)
    pos_version = fields.Char(help="Version of Odoo that created the order", readonly=True, copy=False)

    @api.depends('l10n_fr_secure_sequence_number')
    def _compute_previous_order(self):
        orders_by_company = defaultdict(list)
        for order in self.filtered(lambda o: o.l10n_fr_secure_sequence_number):
            orders_by_company[order.company_id.id].append(order)

        for company_id, orders in orders_by_company.items():
            prev_seq = [o.l10n_fr_secure_sequence_number - 1 for o in orders]
            prev_orders = self.search([
                ('state', 'in', ['paid', 'done', 'invoiced']),
                ('company_id', '=', company_id),
                ('l10n_fr_secure_sequence_number', 'in', prev_seq),
            ])
            prev_map = defaultdict(list)
            for po in prev_orders:
                prev_map[po.l10n_fr_secure_sequence_number].append(po)

            for order in orders:
                match = prev_map.get(order.l10n_fr_secure_sequence_number - 1, [])
                if len(match) > 1:
                    raise UserError(_('An error occurred when computing the inalterability. Impossible to get the unique previous posted point of sale order.'))
                order.previous_order_id = match[0] if match else False

    def _get_new_hash(self):
        """ Returns the hash to write on pos orders when they get posted"""
        self.ensure_one()
        # build and return the hash
        computed_hash = self._compute_hash(self.previous_order_id.l10n_fr_hash if self.previous_order_id else '')
        _logger.info(
            'Computed hash for order ID %s: %s \n String to hash: %s \n Previous hash: %s',
            self.id,
            computed_hash,
            dumps(loads(self.l10n_fr_string_to_hash), indent=2),
            self.previous_order_id.l10n_fr_hash
        )
        return computed_hash

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256((previous_hash + self.l10n_fr_string_to_hash).encode('utf-8'))
        return hash_string.hexdigest()

    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_str].type in ['many2many', 'one2many']:
                field_value = field_value.sorted().ids
            return str(field_value)

        for order in self:
            values = {}
            if order.pos_version:
                order_fields = ORDER_FIELDS_FROM_17_4
            else:
                order_fields = ORDER_FIELDS_BEFORE_17_4
            for field in order_fields:
                values[field] = _getattrstring(order, field)

            for line in order.lines:
                for field in LINE_FIELDS:
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)
            #make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            order.l10n_fr_string_to_hash = dumps(values, sort_keys=True,
                                                ensure_ascii=True, indent=None,
                                                separators=(',',':'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['pos_version'] = release.version
        return super().create(vals_list)

    def write(self, vals):
        has_been_posted = False
        for order in self:
            if order.company_id._is_accounting_unalterable():
                # write the hash and the secure_sequence_number when posting or invoicing an pos.order
                if vals.get('state') in ['paid', 'done', 'invoiced']:
                    has_been_posted = True

                # restrict the operation in case we are trying to write a forbidden field
                if order.pos_version:
                    ORDER_FIELDS = ORDER_FIELDS_FROM_17_4
                else:
                    ORDER_FIELDS = ORDER_FIELDS_BEFORE_17_4
                if (order.state in ['paid', 'done', 'invoiced'] and set(vals).intersection(ORDER_FIELDS)):
                    raise UserError(_('According to the French law, you cannot modify a point of sale order. Forbidden fields: %s.') % ', '.join(ORDER_FIELDS))
                # restrict the operation in case we are trying to overwrite existing hash
                if (order.l10n_fr_hash and 'l10n_fr_hash' in vals) or (order.l10n_fr_secure_sequence_number and 'l10n_fr_secure_sequence_number' in vals):
                    raise UserError(_('You cannot overwrite the values ensuring the inalterability of the point of sale.'))
        res = super(pos_order, self).write(vals)
        # write the hash and the secure_sequence_number when posting or invoicing a pos order
        if has_been_posted:
            for order in self.filtered(lambda o: o.company_id._is_accounting_unalterable() and
                                                not (o.l10n_fr_secure_sequence_number or o.l10n_fr_hash)):
                new_number = order.company_id.l10n_fr_pos_cert_sequence_id.next_by_id()
                res |= super(pos_order, order).write({'l10n_fr_secure_sequence_number': new_number})
                res |= super(pos_order, order).write({'l10n_fr_hash': order._get_new_hash()})
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_pos_so(self):
        for order in self:
            if order.company_id._is_accounting_unalterable():
                raise UserError(_("According to French law, you cannot delete a point of sale order."))

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(LINE_FIELDS):
            if any(l.company_id._is_accounting_unalterable() and l.order_id.state in ['done', 'invoiced'] for l in self):
                raise UserError(_('According to the French law, you cannot modify a point of sale order line. Forbidden fields: %s.') % ', '.join(LINE_FIELDS))
        return super(PosOrderLine, self).write(vals)
