# -*- coding: utf-8 -*-
from openerp import api, fields, models, _, SUPERUSER_ID
from openerp.exceptions import Warning


class res_company(models.Model):

    _inherit = 'res.company'

    so_from_po = fields.Boolean(string="Create Sale Orders when buying to this company",
        help="Generate a Sale Order when a Purchase Order with this company as supplier is created.\n The intercompany user must at least be Sale User.")
    po_from_so = fields.Boolean(string="Create Purchase Orders when selling to this company",
        help="Generate a Purchase Order when a Sale Order with this company as customer is created.\n The intercompany user must at least be Purchase User.")
    auto_generate_invoices = fields.Boolean(string="Create Invoices/Refunds when encoding invoices/refunds made to this company",
        help="Generate Customer/Supplier Invoices (and refunds) when encoding invoices (or refunds) made to this company.\n e.g: Generate a Customer Invoice when a Supplier Invoice with this company as supplier is created.")
    auto_validation = fields.Boolean(string="Sale/Purchase Orders Auto Validation",
        help="When a Sale Order or a Purchase Order is created by a multi company rule for this company, it will automatically validate it")
    intercompany_user_id = fields.Many2one("res.users", string="Inter Company User", default=SUPERUSER_ID,
        help="Responsible user for creation of documents triggered by intercompany rules.")
    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse For Purchase Orders",
        help="Default value to set on Purchase Orders that will be created based on Sale Orders made to this company")

    @api.model
    def _find_company_from_partner(self, partner_id):
        company = self.sudo().search([('partner_id', '=', partner_id)], limit=1)
        return company or False

    @api.one
    @api.constrains('po_from_so', 'so_from_po', 'auto_generate_invoices')
    def _check_intercompany_missmatch_selection(self):
        if (self.po_from_so or self.so_from_po) and self.auto_generate_invoices:
            raise Warning(_('''You cannot select to create invoices based on other invoices
                    simultaneously with another option ('Create Sale Orders when buying to this
                    company' or 'Create Purchase Orders when selling to this company')!'''))

