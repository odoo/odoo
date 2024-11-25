# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime, timedelta
from hashlib import sha256
from json import dumps

from odoo import models, api, fields
from odoo.fields import Datetime
from odoo.tools.translate import _, _lt
from odoo.exceptions import UserError


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


ORDER_FIELDS = ['date_order', 'user_id', 'lines', 'payment_ids', 'pricelist_id', 'partner_id', 'session_id', 'pos_reference', 'sale_journal', 'fiscal_position_id']
LINE_FIELDS = ['notice', 'product_id', 'qty', 'price_unit', 'discount', 'tax_ids', 'tax_ids_after_fiscal_position']
ERR_MSG = _lt('According to the French law, you cannot modify a %s. Forbidden fields: %s.')

MAX_HASH_VERSION = 2

class pos_order(models.Model):
    _inherit = 'pos.order'

    l10n_fr_hash = fields.Char(string="Inalteralbility Hash", readonly=True, copy=False)
    l10n_fr_secure_sequence_number = fields.Integer(string="Inalteralbility No Gap Sequence #", readonly=True, copy=False, index=True)
    l10n_fr_string_to_hash = fields.Char(compute='_compute_string_to_hash', readonly=True, store=False)

    def _get_new_hash(self, secure_seq_number):
        """ Returns the hash to write on pos orders when they get posted"""
        self.ensure_one()
        #get the only one exact previous order in the securisation sequence
        prev_order = self.search([('state', 'in', ['paid', 'done', 'invoiced']),
                                 ('company_id', '=', self.company_id.id),
                                 ('l10n_fr_secure_sequence_number', '!=', 0),
                                 ('l10n_fr_secure_sequence_number', '=', int(secure_seq_number) - 1)])
        if prev_order and len(prev_order) != 1:
            raise UserError(
               _('An error occurred when computing the inalterability. Impossible to get the unique previous posted point of sale order.'))

        #build and return the hash
        return self._compute_hash(prev_order.l10n_fr_hash if prev_order else u'')

    def _compute_hash(self, previous_hash):
        """ Computes the hash of the browse_record given as self, based on the hash
        of the previous record in the company's securisation sequence given as parameter"""
        self.ensure_one()
        hash_string = sha256((previous_hash + self.l10n_fr_string_to_hash).encode('utf-8'))
        return hash_string.hexdigest()
    
    def _l10n_fr_get_integrity_hash_fields(self):
        # Use the new hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return ORDER_FIELDS
        elif hash_version == MAX_HASH_VERSION:
            # https://bofip.impots.gouv.fr/bofip/10691-PGP.html/identifiant=BOI-TVA-DECLA-30-10-30-20210519
            return ['date_order', 'config_id', 'pos_reference', 'amount_tax', 'amount_total', 'amount_paid']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def _l10n_fr_get_integrity_hash_fields_and_subfields(self):
        return self._l10n_fr_get_integrity_hash_fields() + \
            [f'line_ids.{subfield}' for subfield in self.line_ids._l10n_fr_get_integrity_hash_fields()] + \
            [f'payment_ids.{subfield}' for subfield in self.payment_ids._l10n_fr_get_integrity_hash_fields()]

    @api.depends(lambda self: self._l10n_fr_get_integrity_hash_fields_and_subfields())
    @api.depends_context('hash_version')
    def _compute_string_to_hash(self):
        def _getattrstring(obj, field_str):
            field_value = obj[field_str]
            if obj._fields[field_str].type == 'many2one':
                field_value = field_value.id
            if obj._fields[field_str].type in ['many2many', 'one2many']:
                # there no 'many2many', 'one2many' fields with hash version 2
                field_value = field_value.sorted().ids
            return str(field_value)

        for order in self:
            values = {}
            for field in self._l10n_fr_get_integrity_hash_fields():
                values[field] = _getattrstring(order, field)

            for line in order.lines:
                for field in line._l10n_fr_get_integrity_hash_fields():
                    k = 'line_%d_%s' % (line.id, field)
                    values[k] = _getattrstring(line, field)

            for payment in order.payment_ids:
                for field in payment._l10n_fr_get_integrity_hash_fields():
                    k = 'payment_%d_%s' % (payment.id, field)
                    values[k] = _getattrstring(payment, field)

            #make the json serialization canonical
            #  (https://tools.ietf.org/html/draft-staykov-hu-json-canonical-form-00)
            order.l10n_fr_string_to_hash = dumps(values, sort_keys=True,
                                                ensure_ascii=True, indent=None,
                                                separators=(',',':'))

    def write(self, vals):
        has_been_posted = False
        for order in self:
            if order.company_id._is_accounting_unalterable():
                # write the hash and the secure_sequence_number when posting or invoicing an pos.order
                if vals.get('state') in ['paid', 'done', 'invoiced']:
                    has_been_posted = True

                # restrict the operation in case we are trying to write a forbidden field
                if (order.state in ['paid', 'done', 'invoiced'] and set(vals).intersection(self._l10n_fr_get_integrity_hash_fields())):
                    raise UserError(_('According to the French law, you cannot modify a point of sale order. Forbidden fields: %s.') % ', '.join(self._l10n_fr_get_integrity_hash_fields()))
                # restrict the operation in case we are trying to overwrite existing hash
                if (order.l10n_fr_hash and 'l10n_fr_hash' in vals) or (order.l10n_fr_secure_sequence_number and 'l10n_fr_secure_sequence_number' in vals):
                    raise UserError(_('You cannot overwrite the values ensuring the inalterability of the point of sale.'))
        res = super(pos_order, self).write(vals)
        # write the hash and the secure_sequence_number when posting or invoicing a pos order
        if has_been_posted:
            for order in self.filtered(lambda o: o.company_id._is_accounting_unalterable() and
                                                not (o.l10n_fr_secure_sequence_number or o.l10n_fr_hash)):
                new_number = order.company_id.l10n_fr_pos_cert_sequence_id.next_by_id()
                vals_hashing = {'l10n_fr_secure_sequence_number': new_number,
                                'l10n_fr_hash': order._get_new_hash(new_number)}
                res |= super(pos_order, order).write(vals_hashing)
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_except_pos_so(self):
        for order in self:
            if order.company_id._is_accounting_unalterable():
                raise UserError(_("According to French law, you cannot delete a point of sale order."))

    def _export_for_ui(self, order):
        res = super()._export_for_ui(order)
        res['l10n_fr_hash'] = order.l10n_fr_hash
        return res

class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(self._l10n_fr_get_integrity_hash_fields()):
            if any(l.company_id._is_accounting_unalterable() and l.order_id.state in ['paid', 'done', 'invoiced'] for l in self):
                raise UserError(_('According to the French law, you cannot modify a point of sale order line. Forbidden fields: %s.') % ', '.join(self._l10n_fr_get_integrity_hash_fields()))
        return super().write(vals)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_pos_so(self):
        for line in self:
            if line.order_id.company_id._is_accounting_unalterable():
                raise UserError(_("According to French law, you cannot delete a point of sale order line."))

    def _l10n_fr_get_integrity_hash_fields(self):
        # Use the new hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return LINE_FIELDS
        elif hash_version == MAX_HASH_VERSION:
            # https://bofip.impots.gouv.fr/bofip/10691-PGP.html/identifiant=BOI-TVA-DECLA-30-10-30-20210519
            return ['notice', 'qty', 'price_unit', 'discount', 'full_product_name', 'price_subtotal', 'price_subtotal_incl']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

class PosPayment(models.Model):
    _inherit = "pos.payment"

    def _l10n_fr_get_integrity_hash_fields(self):
        # Use the new hash version by default, but keep the old one for backward compatibility when generating the integrity report.
        hash_version = self._context.get('hash_version', MAX_HASH_VERSION)
        if hash_version == 1:
            return []
        elif hash_version == MAX_HASH_VERSION:
            # https://bofip.impots.gouv.fr/bofip/10691-PGP.html/identifiant=BOI-TVA-DECLA-30-10-30-20210519
            return ['payment_method_id', 'amount', 'payment_date']
        raise NotImplementedError(f"hash_version={hash_version} doesn't exist")

    def write(self, vals):
        # restrict the operation in case we are trying to write a forbidden field
        if set(vals).intersection(self._l10n_fr_get_integrity_hash_fields()):
            if any(p.company_id._is_accounting_unalterable() and p.pos_order_id.state in ['paid', 'done', 'invoiced'] for p in self):
                raise UserError(_('According to the French law, you cannot modify a point of sale order line. Forbidden fields: %s.') % ', '.join(self._l10n_fr_get_integrity_hash_fields()))
        return super().write(vals)

    @api.ondelete(at_uninstall=True)
    def _unlink_except_pos_so(self):
        for payment in self:
            if payment.pos_order_id.company_id._is_accounting_unalterable():
                raise UserError(_("According to French law, you cannot delete a point of sale payment."))
