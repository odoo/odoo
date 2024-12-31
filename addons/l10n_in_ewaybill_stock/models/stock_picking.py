# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_in_ewaybill_ids = fields.One2many('l10n.in.ewaybill', 'picking_id', string="Ewaybill")
    l10n_in_ewaybill_name = fields.Char(
        "Indian Ewaybill Number",
        compute='_compute_l10n_in_ewaybill_details'
    )

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref('l10n_in_ewaybill.l10n_in_ewaybill_form_action')._get_action_dict()

    def action_l10n_in_ewaybill_create(self):
        self.ensure_one()
        if product_with_no_hsn := self.move_ids.product_id.filtered(lambda p: not p.l10n_in_hsn_code):
            raise UserError(
                _("Please set HSN code in below products: \n%s", '\n'.join(product_with_no_hsn.mapped('name'))))
        if self.l10n_in_ewaybill_ids:
            raise UserError(_("Ewaybill already created for this picking."))
        action = self._get_l10n_in_ewaybill_form_action()
        ewaybill = self.env['l10n.in.ewaybill'].create({
            'picking_id': self.id,
            'type_id': self.env.ref('l10n_in_ewaybill_stock.type_delivery_challan_sub_others').id,
        })
        action['res_id'] = ewaybill.id
        return action

    def action_open_l10n_in_ewaybill(self):
        self.ensure_one()
        action = self._get_l10n_in_ewaybill_form_action()
        action['res_id'] = self.l10n_in_ewaybill_ids and self.l10n_in_ewaybill_ids[0].id
        return action

    @api.depends('l10n_in_ewaybill_ids.state')
    def _compute_l10n_in_ewaybill_details(self):
        for picking in self:
            ewaybill = picking.l10n_in_ewaybill_ids and picking.l10n_in_ewaybill_ids[0]
            if (
                picking.country_code == 'IN'
                and ewaybill.state in ['challan', 'generated']
            ):
                picking.l10n_in_ewaybill_name = ewaybill.name
            else:
                picking.l10n_in_ewaybill_name = False
