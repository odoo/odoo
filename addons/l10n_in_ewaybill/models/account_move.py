from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_in_ewaybill_id = fields.One2many("l10n.in.ewaybill", 'account_move_id', string="E-Waybill", readonly=True)
    l10n_in_ewaybill_name = fields.Char(compute="_compute_l10n_in_ewaybill_details")
    l10n_in_ewaybill_exipry_date = fields.Datetime(compute="_compute_l10n_in_ewaybill_details")

    def _get_l10n_in_seller_buyer_party(self):
        res = super()._get_l10n_in_seller_buyer_party()
        if self.is_purchase_document(include_receipts=True):
            res = {
                "seller_details":  self.partner_id,
                "dispatch_details": self.partner_shipping_id or self.partner_id,
                "buyer_details": self.company_id.partner_id,
                "ship_to_details": self._l10n_in_get_warehouse_address() or self.company_id.partner_id,
            }
        return res

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref('l10n_in_ewaybill.l10n_in_ewaybill_form_action')._get_action_dict()

    def action_l10n_in_ewaybill_create(self):
        self.ensure_one()
        if self.l10n_in_ewaybill_id:
            raise UserError(_("Ewaybill already created for this move."))
        action = self._get_l10n_in_ewaybill_form_action()
        action['context'] = {'default_account_move_id': self.id}
        return action

    def action_open_l10n_in_ewaybill(self):
        self.ensure_one()
        action = self._get_l10n_in_ewaybill_form_action()
        action['res_id'] = self.l10n_in_ewaybill_id.id
        return action

    @api.depends('l10n_in_ewaybill_id.state')
    def _compute_l10n_in_ewaybill_details(self):
        for move in self:
            if move.country_code == 'IN' and move.l10n_in_ewaybill_id.state == 'generated':
                move.l10n_in_ewaybill_name = move.l10n_in_ewaybill_id.name
                move.l10n_in_ewaybill_exipry_date = move.l10n_in_ewaybill_id.ewaybill_expiry_date
            else:
                move.l10n_in_ewaybill_name = False
                move.l10n_in_ewaybill_exipry_date = False
