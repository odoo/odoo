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
        if lines_with_no_tax := self.move_ids.filtered(lambda line: not line.ewaybill_tax_ids):
            raise UserError(_("Please set Tax on below products: \n%s", '\n'.join(
                [product.name for product in lines_with_no_tax.mapped('product_id')]
            )))
        if self.l10n_in_ewaybill_id:
            raise UserError(_("Ewaybill already created for this picking."))
        action = self._get_l10n_in_ewaybill_form_action()
        action['context'] = {'default_picking_id': self.id}
        return action

    def action_open_l10n_in_ewaybill(self):
        self.ensure_one()
        action = self._get_l10n_in_ewaybill_form_action()
        action['res_id'] = self.l10n_in_ewaybill_id.id
        return action
