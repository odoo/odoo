from openerp import models, fields, api, _
from openerp.exceptions import Warning
from openerp import SUPERUSER_ID

class res_company(models.Model):
    _inherit = 'res.company'

    so_from_po = fields.Boolean(string='Create Sale Orders when buying to this company', 
        help='Generate a Sale Order when a Purchase Order with this company as supplier is created.')
    po_from_so = fields.Boolean(string='Create Purchase Orders when selling to this company',
        help='Generate a Purchase Order when a Sale Order with this company as customer is created.')
    auto_generate_invoices = fields.Boolean(string='Create Invoices/Refunds when encoding invoices/refunds made to this company',
        help='''Generate Customer/Supplier Invoices (and refunds) when encoding 
            invoices (or refunds) made to this company.\n e.g: Generate a Customer Invoice when 
            a Supplier Invoice with this company as supplier is created.''')
    auto_validation = fields.Boolean(string='Sale/Purchase Orders Auto Validation', 
        help='''When a Sale Order or a Purchase Order is created by a multi company 
            rule for this company, it will automatically validate it''')
    intercompany_user_id = fields.Many2one('res.users', string='Inter Company User', default= SUPERUSER_ID,
        help='Responsible user for creation of documents triggered by intercompany rules.')
    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse For Purchase Orders',
        help='''Default value to set on Purchase Orders that will be 
            created based on Sale Orders made to this company''')

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

class sale_order(models.Model):
    _inherit = "sale.order"

    auto_generated = fields.Boolean(string='Auto Generated Sale Order', copy=False)
    auto_po_id = fields.Many2one('purchase.order', string='Source Purchase Order',
        readonly=True, copy=False)

    @api.multi
    def action_button_confirm(self):
        """ Also generate inter company purchase order base on conditions."""
        res = super(sale_order, self).action_button_confirm()
        for order in self:
            #If company_id not found, return to normal behavior
            if not order.company_id:
                continue

            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.po_from_so and (not order.auto_generated):
                order.action_create_po(company_rec)
        return res

    @api.model
    def _po_line_vals(self, line, company_partner, date_order, purchase_id, company):
        """ @return : Purchase Line values dictionary """

        #price on PO line should be line - discount
        price = line.price_unit - (line.price_unit * (line.discount / 100))

        #Computing Default taxes of lines. It may not affect because of parallel company relation
        taxes = line.tax_id
        if line.product_id:
            taxes = line.product_id.supplier_taxes_id

        #Fetch taxes by company not by inter-company user
        company_taxes = [tax_rec.id for tax_rec in taxes if tax_rec.company_id.id == company.id]

        return {
            'name': line.name,
            'order_id': purchase_id,
            'product_qty': line.product_uom_qty,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
            'price_unit': price or 0.0,
            'company_id': line.order_id.company_id.id,
            'date_planned': line.order_id.commitment_date or date_order,
            'taxes_id': [(6, 0, company_taxes)],
        }

    @api.one
    def _po_vals(self, company, this_company_partner):
        """ @return : Purchase values dictionary """
        #To find location and warehouse,pick warehouse from company object
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
        if not warehouse:
            raise Warning(_('Configure correct warehouse for company(%s) from Menu: Settings/companies/companies' % (company.name)))

        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'partner_id': this_company_partner.id,
            'location_id': warehouse.lot_stock_id.id,
            'pricelist_id': this_company_partner.property_product_pricelist_purchase.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position': this_company_partner.property_account_position or False,
            'payment_term_id': this_company_partner.property_supplier_payment_term.id or False,
            'auto_generated': True,
            'auto_so_id': self.id,
            'partner_ref': self.name,
            'dest_address_id': self.partner_shipping_id and self.partner_shipping_id.id or False,
        }

    @api.one
    def action_create_po(self, company):
        """ Intercompany Purchase Order trigger when sale order confirm"""

        purchase_obj = self.env['purchase.order']
        this_company_partner = self.company_id and self.company_id.partner_id or False
        if not company or not this_company_partner.id:
            return

        #Find user for creating and validating SO/PO from company
        update_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not update_uid:
            raise Warning(_('Provide one user for intercompany relation for % ') % company.name)

        if not purchase_obj.sudo(update_uid).check_access_rights('create', raise_exception=False):
            raise Warning(_("Inter company user of company %s doesn't have enough access rights") % company.name)

        #Check pricelist currency should be same with SO/PO document
        if self.pricelist_id.currency_id.id != this_company_partner.property_product_pricelist_purchase.currency_id.id:
            raise Warning(_('You cannot create PO from SO because purchase pricelist currency is different than sale pricelist currency.'))

        #create the PO
        po_vals = self.sudo(update_uid)._po_vals(company, this_company_partner)
        purchase = purchase_obj.sudo(update_uid).create(po_vals[0])
        for line in self.order_line:
            po_line_vals = self.sudo(update_uid)._po_line_vals(line, this_company_partner, self.date_order, purchase.id, company)
            self.env['purchase.order.line'].sudo(update_uid).create(po_line_vals)

        #write customer reference field on SO
        if not self.client_order_ref:
            self.client_order_ref = purchase.name

        #auto-validate the purchase order if needed
        if company.auto_validation:
            purchase.sudo(update_uid).signal_workflow('purchase_confirm')


class purchase_order(models.Model):
    _inherit = "purchase.order"

    auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False)
    auto_so_id = fields.Many2one('sale.order', string='Source Sale Order', readonly=True, copy=False)

    @api.multi
    def wkf_confirm_order(self):
        """ Also generate inter company sale order base on conditions."""

        res = super(purchase_order, self).wkf_confirm_order()
        for order in self:
            #get the company from partner then trigger action of intercompany relation.
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.so_from_po and (not order.auto_generated):
                order.action_create_so(company_rec)
        return res

    @api.model
    def _so_line_vals(self, line, partner, company, sale_id):
        #It may not affected because of parallel company relation
        price = line.price_unit or 0.0
        taxes = line.taxes_id
        if line.product_id:
            taxes = line.product_id.taxes_id
        company_taxes = [tax_rec.id for tax_rec in taxes if tax_rec.company_id.id == company.id]

        return {
            'name': line.product_id and line.product_id.name or line.name,
            'order_id': sale_id,
            'product_uom_qty': line.product_qty,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': price,
            'delay': line.product_id and line.product_id.sale_delay or 0.0,
            'company_id': company.id,
            'tax_id': [(6, 0, company_taxes)],
        }

    @api.one
    def _so_vals(self, name, partner, company, direct_delivery_address):
        partner_addr = partner.sudo().address_get(['default', 'invoice', 'delivery', 'contact'])
        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/',
            'company_id': company.id,
            'client_order_ref': name,
            'partner_id': partner.id,
            'pricelist_id': partner.property_product_pricelist.id,
            'partner_invoice_id': partner_addr['invoice'],
            'date_order': self.date_order,
            'fiscal_position': partner.property_account_position and partner.property_account_position.id or False,
            'user_id': False,
            'auto_generated': True,
            'auto_po_id': self.id,
            'partner_shipping_id': direct_delivery_address or partner_addr['delivery']
        }

    @api.one
    def action_create_so(self, company):
        sale_obj = self.env['sale.order']
        #To find user for creating and validation SO/PO from partner company
        update_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not update_uid:
            raise Warning(_('Provide at least one user for inter company relation for % ') % company.name)

        if not sale_obj.sudo(update_uid).check_access_rights('create', raise_exception=False):
            raise Warning(_("Inter company user of company %s doesn't have enough access rights") % company.name)

        #Check pricelist currency should be same with SO/PO document
        if self.pricelist_id.currency_id.id != self.company_id.partner_id.property_product_pricelist.currency_id.id:
            raise Warning(_('You cannot create SO from PO because sale price list currency is different than purchase price list currency.'))

        #create the SO
        so_vals = self.sudo(update_uid)._so_vals(self.name, self.company_id.partner_id, 
                                company, self.dest_address_id and self.dest_address_id.id or False)
        sale = sale_obj.sudo(update_uid).create(so_vals[0])
        for line in self.order_line:
            so_line_vals = self.sudo(update_uid)._so_line_vals(line, self.company_id.partner_id, company, sale.id)
            self.env['sale.order.line'].sudo(update_uid).create(so_line_vals)

        #write supplier reference field on PO
        if not self.partner_ref:
            self.partner_ref = self.name

        #Validation of sale order
        if company.auto_validation:
            sale.sudo(update_uid).signal_workflow('order_confirm')

