# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import Warning


class sale_order(models.Model):

    _inherit = "sale.order"

    auto_generated = fields.Boolean(string='Auto Generated Sale Order', copy=False)
    auto_purchase_order_id = fields.Many2one('purchase.order', string='Source Purchase Order', readonly=True, copy=False)

    @api.multi
    def action_button_confirm(self):
        """ Generate inter company purchase order based on conditions """
        res = super(sale_order, self).action_button_confirm()
        for order in self:
            if not order.company_id: # if company_id not found, return to normal behavior
                continue
            # if company allow to create a Purchase Order from Sale Order, then do it !
            company = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company and company.po_from_so and (not order.auto_generated):
                order.inter_company_create_purchase_order(company)
        return res

    @api.one
    def inter_company_create_purchase_order(self, company):
        """ Create a Purchase Order from the current SO (self)
            Note : In this method, reading the current SO is done as sudo, and the creation of the derived
            PO as intercompany_user, minimizing the access right required for the trigger user
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        PurchaseOrder = self.env['purchase.order']
        company_partner = self.company_id and self.company_id.partner_id or False
        if not company or not company_partner.id:
            return

        # find user for creating and validating SO/PO from company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise Warning(_('Provide one user for intercompany relation for % ') % company.name)
        # check intercompany user access rights
        if not PurchaseOrder.sudo(intercompany_uid).check_access_rights('create', raise_exception=False):
            raise Warning(_("Inter company user of company %s doesn't have enough access rights") % company.name)

        # check pricelist currency should be same with SO/PO document
        if self.pricelist_id.currency_id.id != company_partner.property_product_pricelist_purchase.currency_id.id:
            raise Warning(_('You cannot create PO from SO because purchase pricelist currency is different than sale pricelist currency.'))

        # create the PO and generate its lines from the SO
        PurchaseOrderLine = self.env['purchase.order.line']
        # read it as sudo, because inter-compagny user can not have the access right on PO
        po_vals = self.sudo()._prepare_purchase_order_data(company, company_partner)
        purchase_order = PurchaseOrder.sudo(intercompany_uid).create(po_vals[0])
        for line in self.order_line:
            po_line_vals = self.sudo()._prepare_purchase_order_line_data(line, self.date_order, purchase_order.id, company)
            PurchaseOrderLine.sudo(intercompany_uid).create(po_line_vals)

        # write customer reference field on SO
        if not self.client_order_ref:
            self.client_order_ref = purchase_order.name

        # auto-validate the purchase order if needed
        if company.auto_validation:
            purchase_order.sudo(intercompany_uid).signal_workflow('purchase_confirm')

    @api.one
    def _prepare_purchase_order_data(self, company, company_partner):
        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the SO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        # find location and warehouse, pick warehouse from company object
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
        if not warehouse:
            raise Warning(_('Configure correct warehouse for company(%s) from Menu: Settings/companies/companies' % (company.name)))

        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'partner_id': company_partner.id,
            'location_id': warehouse.lot_stock_id.id,
            'pricelist_id': company_partner.property_product_pricelist_purchase.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position': company_partner.property_account_position or False,
            'payment_term_id': company_partner.property_supplier_payment_term.id or False,
            'auto_generated': True,
            'auto_sale_order_id': self.id,
            'partner_ref': self.name,
            'dest_address_id': self.partner_shipping_id and self.partner_shipping_id.id or False,
        }

    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, purchase_id, company):
        """ Generate purchase order line values, from the SO line
            :param so_line : origin SO line
            :rtype so_line : sale.order.line record
            :param date_order : the date of the orgin SO
            :param purchase_id : the id of the purchase order
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        # price on PO so_line should be so_line - discount
        price = so_line.price_unit - (so_line.price_unit * (so_line.discount / 100))

        # computing Default taxes of so_line. It may not affect because of parallel company relation
        taxes = so_line.tax_id
        if so_line.product_id:
            taxes = so_line.product_id.supplier_taxes_id

        # fetch taxes by company not by inter-company user
        company_taxes = [tax_rec.id for tax_rec in taxes if tax_rec.company_id.id == company.id]
        return {
            'name': so_line.name,
            'order_id': purchase_id,
            'product_qty': so_line.product_uom_qty,
            'product_id': so_line.product_id and so_line.product_id.id or False,
            'product_uom': so_line.product_id and so_line.product_id.uom_po_id.id or so_line.product_uom.id,
            'price_unit': price or 0.0,
            'company_id': so_line.order_id.company_id.id,
            'date_planned': so_line.order_id.commitment_date or date_order,
            'taxes_id': [(6, 0, company_taxes)],
        }
