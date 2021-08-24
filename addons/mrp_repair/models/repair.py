# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Repair(models.Model):
    _inherit = 'repair.order'

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.action_explode()
        return res

    def write(self, vals):
        res = super().write(vals)
        self.action_explode()
        return res

    def action_explode(self):
        lines_to_unlink_ids = set()
        line_vals_list = []
        for op in self.operations:
            bom = self.env['mrp.bom'].sudo()._bom_find(op.product_id, company_id=op.company_id.id, bom_type='phantom')[op.product_id]
            if not bom:
                continue
            factor = op.product_uom._compute_quantity(op.product_uom_qty, bom.product_uom_id) / bom.product_qty
            _boms, lines = bom.sudo().explode(op.product_id, factor, picking_type=bom.picking_type_id)
            for bom_line, line_data in lines:
                if bom_line.product_id.type != 'service':
                    line_vals_list.append(op._prepare_phantom_line_vals(bom_line, line_data['qty']))
            lines_to_unlink_ids.add(op.id)

        self.env['repair.line'].browse(lines_to_unlink_ids).sudo().unlink()
        if line_vals_list:
            self.env['repair.line'].create(line_vals_list)


class RepairLine(models.Model):
    _inherit = 'repair.line'

    def _prepare_phantom_line_vals(self, bom_line, qty):
        self.ensure_one()
        product = bom_line.product_id
        uom = bom_line.product_uom_id
        partner = self.repair_id.partner_id
        price = self.repair_id.pricelist_id.get_product_price(product, qty, partner, uom_id=uom.id)
        tax = self.env['account.tax']
        if partner:
            partner_invoice = self.repair_id.partner_invoice_id or partner
            fpos = self.env['account.fiscal.position'].get_fiscal_position(partner_invoice.id, delivery_id=self.repair_id.address_id.id)
            taxes = self.product_id.taxes_id.filtered(lambda x: x.company_id == self.repair_id.company_id)
            tax = fpos.map_tax(taxes)
        return {
            'name': self.name,
            'repair_id': self.repair_id.id,
            'type': self.type,
            'product_id': product.id,
            'price_unit': price,
            'tax_id': [(4, t.id) for t in tax],
            'product_uom_qty': qty,
            'product_uom': uom.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'state': 'draft',
        }
