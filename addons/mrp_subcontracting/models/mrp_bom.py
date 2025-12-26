# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.fields import Domain


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    type = fields.Selection(selection_add=[
        ('subcontract', 'Subcontracting')
    ], ondelete={'subcontract': lambda recs: recs.write({'type': 'normal', 'active': False})})
    subcontractor_ids = fields.Many2many('res.partner', 'mrp_bom_subcontractor', string='Subcontractors', check_company=True)

    def _bom_subcontract_find(self, product, picking_type=None, company_id=False, bom_type='subcontract', subcontractor=False):
        domain = self._bom_find_domain(product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        if subcontractor:
            domain &= Domain('subcontractor_ids', 'parent_of', subcontractor.ids)
            return self.search(domain, order='sequence, product_id, id', limit=1)
        else:
            return self.env['mrp.bom']

    @api.constrains('operation_ids', 'byproduct_ids', 'type')
    def _check_subcontracting_no_operation(self):
        if self.filtered_domain([('type', '=', 'subcontract'), '|', ('operation_ids', '!=', False), ('byproduct_ids', '!=', False)]):
            raise ValidationError(_('You can not set a Bill of Material with operations or by-product line as subcontracting.'))

    def _compute_bom_cost(self, product, boms_to_recompute=False):
        """ Add the price of the subcontracting supplier if it exists with the bom configuration.
        """
        cost = super()._compute_bom_cost(product, boms_to_recompute)
        if self.type == 'subcontract':
            company = self.company_id or self.env.company
            seller = product.with_company(company)._select_seller(
                quantity=self.product_qty,
                uom_id=self.uom_id,
                params={'subcontractor_ids': self.subcontractor_ids}
            )
            if seller:
                seller_price = seller.currency_id._convert(seller.price, company.currency_id, company)
                cost += seller.uom_id._compute_price(seller_price, self.product_tmpl_id.uom_id)
        return cost
