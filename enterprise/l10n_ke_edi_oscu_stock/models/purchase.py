# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    l10n_ke_customs_import_ids = fields.One2many('l10n_ke_edi.customs.import', 'purchase_id')

    def action_view_l10n_ke_edi_customs_import(self):
        self.ensure_one()
        result = self.env['ir.actions.act_window']._for_xml_id('l10n_ke_edi_oscu_stock.action_l10n_ke_edi_oscu_customs_import')
        if len(self.l10n_ke_customs_import_ids) > 1:
            result['domain'] = [('id', 'in', self.l10n_ke_customs_import_ids.ids)]
        elif len(self.l10n_ke_customs_import_ids) == 1:
            result['views'] = [(self.env.ref('l10n_ke_edi_oscu_stock.l10n_ke_edi_customs_import_view_branch_form', False).id, 'form')]
            result['res_id'] = self.l10n_ke_customs_import_ids.id
        else:
            result = None
        return result

    def _l10n_ke_check_import(self, imp):
        """ Custom imports may be approved if the total quantity of custom imports
            for a product on a purchase is equal to the received quantity for that product. """
        self.ensure_one()
        if imp.product_id:
            quantity_details = self._l10n_ke_import_quantity_details(products=imp.product_id)
            return quantity_details[imp.product_id]['received_quantity'] == quantity_details[imp.product_id]['import_expected_quantity']

        return False

    def _l10n_ke_import_quantity_details(self, products=None):
        """
            Returns a dictionary of the quantities by product on the purchase order and its associated imports.
            :param products: (optional) a recordset of products to get quantities for
        """

        quantities = defaultdict(lambda: {
            'import_expected_quantity': 0,
            'import_rejected_quantity': 0,
            'purchase_quantity': 0,
            'received_quantity': 0,
        })
        for imp in self.l10n_ke_customs_import_ids:
            product = imp.product_id
            if not product.uom_id or products and product not in products:
                continue

            import_quantity = imp.uom_id._compute_quantity(imp.quantity, product.uom_id)
            if imp.state == '4':
                quantities[product]['import_rejected_quantity'] += import_quantity
            else:
                quantities[product]['import_expected_quantity'] += import_quantity

        for line in self.order_line.filtered(lambda line: line.product_id in quantities):
            quantities[line.product_id]['purchase_quantity'] += line.product_uom_qty
            quantities[line.product_id]['received_quantity'] += line.product_uom._compute_quantity(
                line.qty_received, line.product_id.uom_id,
            )

        return dict(quantities)


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # Calculate the Purchase Order Line
    @api.depends('order_id', 'name')
    def _compute_display_name(self):
        ke_pol = self.filtered(lambda pol: pol.company_id.country_code == 'KE')
        super(PurchaseOrderLine, self - ke_pol)._compute_display_name()
        for pol in ke_pol:
            pol.display_name = f"{pol.order_id.name} {pol.name}"
