# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    l10n_in_ewaybill_id = fields.One2many('l10n.in.ewaybill', 'picking_id', string='Ewaybill')

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref('l10n_in_ewaybill_stock.l10n_in_ewaybill_form_action')._get_action_dict()

    def action_l10n_in_ewaybill_create(self):
        self.ensure_one()
        if (
            product_with_no_hsn := self.move_ids.mapped('product_id').filtered(
                lambda product: not product.l10n_in_hsn_code
            )
        ):
            raise UserError(_("Please set HSN code in below products: \n%s", '\n'.join(
                [product.name for product in product_with_no_hsn]
            )))
        if self.l10n_in_ewaybill_id:
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
        action['res_id'] = self.l10n_in_ewaybill_id.id
        return action
