# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command, _, api, fields, models
from odoo.exceptions import ValidationError


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    online_payment_provider_ids = fields.Many2many('payment.provider', string="Allowed Providers", domain="[('is_published', '=', True)]")
    has_an_online_payment_provider = fields.Boolean(compute='_compute_has_an_online_payment_provider', readonly=True)
    type = fields.Selection(
        selection_add=[('online', 'Online')],
        ondelete={"online": "cascade"},
    )

    @api.model
    def _load_pos_data_read(self, records, config):
        read_records = super()._load_pos_data_read(records, config)

        for record in read_records:
            if record['type'] != 'online':
                continue

            pm = self.env['pos.payment.method'].browse(record['id']).exists()
            providers = pm._get_online_payment_providers().mapped('code') if pm else []
            record['_customer_required'] = bool(set(providers) & set(self._get_customer_required_providers_code()))
        return read_records

    def _get_online_payment_providers(self, pos_config_id=False, error_if_invalid=True):
        self.ensure_one()
        providers_sudo = self.sudo().online_payment_provider_ids
        if not providers_sudo:  # Empty = all published providers
            providers_sudo = self.sudo().env['payment.provider'].search([('is_published', '=', True)])

        if not pos_config_id:
            return providers_sudo

        config_currency = self.sudo().env['pos.config'].browse(pos_config_id).currency_id
        valid_providers = providers_sudo.filtered(lambda p: not p.journal_id.currency_id or p.journal_id.currency_id == config_currency)
        if error_if_invalid and len(providers_sudo) != len(valid_providers):
            raise ValidationError(_("All payment providers configured for an online payment method must use the same currency as the Sales Journal, or the company currency if that is not set, of the POS config."))
        return valid_providers

    @api.depends('type', 'online_payment_provider_ids')
    def _compute_has_an_online_payment_provider(self):
        for pm in self:
            if pm.type == 'online':
                pm.has_an_online_payment_provider = bool(pm._get_online_payment_providers())
            else:
                pm.has_an_online_payment_provider = False

    @api.constrains('config_ids', 'type')
    def _check_pos_config_online_payment(self):
        """ Check that each POS config has at most one online payment method,"""
        for pm in self.filtered(lambda p: p.type == 'online'):
            for config in pm.config_ids:
                other_online_pms = config.payment_method_ids.filtered(lambda other_pm: other_pm.type == 'online' and other_pm.id != pm.id)
                if other_online_pms:
                    raise ValidationError(_("The %s already has one online payment.", config.name))

    def _is_write_forbidden(self, fields):
        return super()._is_write_forbidden(fields - {'online_payment_provider_ids'})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('type', '') == 'online':
                self._force_online_payment_values(vals)
        return super().create(vals_list)

    def write(self, vals):
        if 'type' in vals and vals['type'] == 'online':
            self._force_online_payment_values(vals)
            return super().write(vals)

        opm = self.filtered(lambda p: p.type == 'online')
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

        disabled_fields_name = ('receivable_account_id', 'outstanding_account_id', 'journal_id', 'payment_provider', 'qr_code_method')
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

    def _get_provider_selection(self):
        if len(self) == 1 and self.type == 'online':
            return []
        return super()._get_provider_selection()

    @api.model
    def _get_or_create_online_payment_method(self, company_id, pos_config_id):
        """ Get the first online payment method compatible with the provided pos.config.
            If there isn't any, try to find an existing one in the same company and return it without adding the pos.config to it.
            If there is not, create a new one for the company and return it without adding the pos.config to it.
        """
        # Parameters are ids instead of a pos.config record because this method can be called from a web controller or internally
        payment_method_id = self.env['pos.payment.method'].search([('type', '=', 'online'), ('company_id', '=', company_id), ('config_ids', 'in', pos_config_id)], limit=1).exists()
        if not payment_method_id:
            payment_method_id = self.env['pos.payment.method'].search([('type', '=', 'online'), ('company_id', '=', company_id)], limit=1).exists()
            if not payment_method_id:
                payment_method_id = self.env['pos.payment.method'].create({
                    'name': _('Online Payment'),
                    'type': 'online',
                    'company_id': company_id,
                    'sequence': 3,
                })
                if not payment_method_id:
                    raise ValidationError(_(
                        "Could not create an online payment method (company_id=%(company_id)d, pos_config_id=%(pos_config_id)d)",
                        company_id=company_id,
                        pos_config_id=pos_config_id,
                    ))
        return payment_method_id

    @api.onchange('type')
    def _onchange_type(self):
        """Reset method to hide widget `pos_payment_provider_cards` in form view."""
        self.payment_method_type = 'none'

    def _get_customer_required_providers_code(self):
        return ['aps', 'flutterwave']

    def _create_online_payment_line_transfer(self, session):
        """
        Since online payments are created in another account receivable than
        the PoS one, we need to create a transfer journal entry to link them.

        The online payment creates:
          - Debit: Payment provider receivable (destination_account_id)
          - Credit: Outstanding account

        We create a transfer entry:
          - Debit: POS receivable
          - Credit: Payment provider receivable

        This allows reconciliation with the POS session invoice payment_term lines.
        """
        self.ensure_one()
        pos_receivable = session._get_receivable_account()
        online_orders = session.order_ids.filtered_domain([
            ('payment_ids.payment_method_id', '=', self.id),
        ])

        total_amount = sum(pay.amount for pay in online_orders.payment_ids)
        account_payment = online_orders.payment_ids.online_account_payment_id
        ref = _(
            "Transfer Online payment %(account_name)s => %(pos_receivable_name)s",
            account_name=account_payment.destination_account_id.name,
            pos_receivable_name=pos_receivable.name,
        )
        transfer_move = self.env["account.move"].sudo().create({
            "move_type": "entry",
            "journal_id": session.config_id.journal_id.id,
            "ref": ref,
            "line_ids": [
                Command.create({
                    "account_id": pos_receivable.id,
                    "debit": 0,
                    "credit": total_amount,
                    "name": _("POS Receivable Transfer"),
                    "partner_id": account_payment.partner_id.id,
                }),
                Command.create({
                    "account_id": account_payment.destination_account_id.id,
                    "debit": total_amount,
                    "credit": 0,
                    "name": _("Online Payment Transfer"),
                    "partner_id": account_payment.partner_id.id,
                }),
            ],
        })

        transfer_move._post()
        return transfer_move.line_ids.filtered(
            lambda line: line.account_id == pos_receivable,
        )

    def _create_payment_line(self, session, amount, account=None, message=None, partner=None):
        if self.type == 'online':
            return self._create_online_payment_line_transfer(session)
        return super()._create_payment_line(session, amount, account, message, partner)
