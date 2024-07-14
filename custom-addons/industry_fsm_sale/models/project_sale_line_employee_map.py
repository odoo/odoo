# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProjectProductEmployeeMap(models.Model):
    _inherit = 'project.sale.line.employee.map'

    timesheet_product_id = fields.Many2one(
        'product.product', string='Service',
        check_company=True,
        domain="""[
            ('detailed_type', '=', 'service'),
            ('invoice_policy', '=', 'delivery'),
            ('service_type', '=', 'timesheet'),
        ]""")
    price_unit = fields.Float(readonly=False)

    @api.depends('partner_id')
    def _compute_sale_line_id(self):
        fsm_mappings = self.filtered(lambda map_entry: map_entry.project_id.is_fsm)
        if fsm_mappings:
            # Remove the trigger on _compute_price_unit method
            # Because in fsm projects the SOL is not shown and set in employee mappings.
            # That is why, we need to remove the trigger to allow the user to edit the price unit if it is needed for him.
            price_unit_field = self._fields['price_unit']
            currency_id_field = self._fields['currency_id']
            self.env.remove_to_compute(price_unit_field, fsm_mappings)
            self.env.remove_to_compute(currency_id_field, fsm_mappings)
        super(ProjectProductEmployeeMap, self - fsm_mappings)._compute_sale_line_id()

    @api.depends('sale_line_id.price_unit', 'timesheet_product_id')
    def _compute_price_unit(self):
        mappings_with_product_and_no_sol = self.filtered(lambda mapping: not mapping.sale_line_id and mapping.timesheet_product_id)
        for line in mappings_with_product_and_no_sol:
            line.price_unit = line.timesheet_product_id.lst_price
        super(ProjectProductEmployeeMap, self - mappings_with_product_and_no_sol)._compute_price_unit()

    @api.depends('sale_line_id.price_unit', 'timesheet_product_id')
    def _compute_currency_id(self):
        fsm_project_mappings = self.filtered(lambda mapping: mapping.project_id.is_fsm)
        for mapping in fsm_project_mappings:
            mapping.currency_id = mapping.timesheet_product_id.currency_id if mapping.timesheet_product_id else False
        super(ProjectProductEmployeeMap, self - fsm_project_mappings)._compute_currency_id()
