# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    is_online_payment = fields.Boolean(string="Online Payment", help="Use this payment method for online payments (payments made on a web page with online payment providers)", default=False)
    online_payment_provider_ids = fields.Many2many('payment.provider', string="Allowed Providers", domain="[('is_published', '=', True), ('state', 'in', ['enabled', 'test'])]")
    has_an_online_payment_provider = fields.Boolean(compute='_compute_has_an_online_payment_provider', readonly=True)
    type = fields.Selection(selection_add=[('online', 'Online')])

    @api.model
    def _load_pos_data_fields(self, config):
        params = super()._load_pos_data_fields(config)
        params += ['is_online_payment']
        return params

    @api.depends('is_online_payment')
    def _compute_type(self):
        opm = self.filtered('is_online_payment')
        if opm:
            opm.type = 'online'

        super(PosPaymentMethod, self - opm)._compute_type()

    def _get_online_payment_providers(self, pos_config_id=False, error_if_invalid=True):
        self.ensure_one()
        providers_sudo = self.sudo().online_payment_provider_ids
        if not providers_sudo: # Empty = all published providers
            providers_sudo = self.sudo().env['payment.provider'].search([('is_published', '=', True), ('state', 'in', ['enabled', 'test'])])

        if not pos_config_id:
            return providers_sudo

        config_currency = self.sudo().env['pos.config'].browse(pos_config_id).currency_id
        valid_providers = providers_sudo.filtered(lambda p: not p.journal_id.currency_id or p.journal_id.currency_id == config_currency)
        if error_if_invalid and len(providers_sudo) != len(valid_providers):
            raise ValidationError(_("All payment providers configured for an online payment method must use the same currency as the Sales Journal, or the company currency if that is not set, of the POS config."))
        return valid_providers

    @api.depends('is_online_payment', 'online_payment_provider_ids')
    def _compute_has_an_online_payment_provider(self):
        for pm in self:
            if pm.is_online_payment:
                pm.has_an_online_payment_provider = bool(pm._get_online_payment_providers())
            else:
                pm.has_an_online_payment_provider = False

    def _is_write_forbidden(self, fields):
        return super(PosPaymentMethod, self)._is_write_forbidden(fields - {'online_payment_provider_ids'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('is_online_payment', False):
                self._force_online_payment_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'is_online_payment' in vals:
            if vals['is_online_payment']:
                self._force_online_payment_values(vals)
            return super().write(vals)

        opm = self.filtered('is_online_payment')
        not_opm = self - opm

        res = True
        if opm:
            forced_vals = vals.copy()
            self._force_online_payment_values(forced_vals, True)
            res = super(PosPaymentMethod, opm).write(forced_vals) and res
        if not_opm:
            res = super(PosPaymentMethod, not_opm).write(vals) and res

        return res

    @staticmethod
    def _force_online_payment_values(vals, if_present=False):
        if 'type' in vals:
            vals['type'] = 'online'

        disabled_fields_name = ('split_transactions', 'receivable_account_id', 'outstanding_account_id', 'journal_id', 'is_cash_count', 'use_payment_terminal', 'qr_code_method')
        if if_present:
            for name in disabled_fields_name:
                if name in vals:
                    vals[name] = False
            if 'payment_method_type' in vals:
                vals['payment_method_type'] = 'none'
        else:
            for name in disabled_fields_name:
                vals[name] = False
            vals['payment_method_type'] = 'none'

    def _get_payment_terminal_selection(self):
        return super(PosPaymentMethod, self)._get_payment_terminal_selection() if not self.is_online_payment else []

    @api.depends('type')
    def _compute_hide_use_payment_terminal(self):
        opm = self.filtered(lambda pm: pm.type == 'online')
        if opm:
            opm.hide_use_payment_terminal = True
        super(PosPaymentMethod, self - opm)._compute_hide_use_payment_terminal()

    @api.model
    def _get_or_create_online_payment_method(self, company_id, pos_config_id):
        """ Get the first online payment method compatible with the provided pos.config.
            If there isn't any, try to find an existing one in the same company and return it without adding the pos.config to it.
            If there is not, create a new one for the company and return it without adding the pos.config to it.
        """
        # Parameters are ids instead of a pos.config record because this method can be called from a web controller or internally
        payment_method_id = self.env['pos.payment.method'].search([('is_online_payment', '=', True), ('company_id', '=', company_id), ('config_ids', 'in', pos_config_id)], limit=1).exists()
        if not payment_method_id:
            payment_method_id = self.env['pos.payment.method'].search([('is_online_payment', '=', True), ('company_id', '=', company_id)], limit=1).exists()
            if not payment_method_id:
                payment_method_id = self.env['pos.payment.method'].create({
                    'name': _('Online Payment'),
                    'is_online_payment': True,
                    'company_id': company_id,
                })
                if not payment_method_id:
                    raise ValidationError(_(
                        "Could not create an online payment method (company_id=%(company_id)d, pos_config_id=%(pos_config_id)d)",
                        company_id=company_id,
                        pos_config_id=pos_config_id,
                    ))
        return payment_method_id

    @api.onchange('is_online_payment')
    def _onchange_is_online_payment(self):
        """Reset method to hide widget `pos_payment_provider_cards` in form view."""
        self.payment_method_type = 'none'
