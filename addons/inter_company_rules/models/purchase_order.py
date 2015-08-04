# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import Warning


class purchase_order(models.Model):

    _inherit = "purchase.order"

    auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False)
    auto_sale_order_id = fields.Many2one('sale.order', string='Source Sale Order', readonly=True, copy=False)

    @api.multi
    def wkf_confirm_order(self):
        """ Generate inter company sale order base on conditions."""
        res = super(purchase_order, self).wkf_confirm_order()
        for order in self:
            # get the company from partner then trigger action of intercompany relation
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.so_from_po and (not order.auto_generated):
                order.inter_company_create_sale_order(company_rec)
        return res


    @api.one
    def inter_company_create_sale_order(self, company):
        """ Create a Sale Order from the current PO (self)
            Note : In this method, reading the current PO is done as sudo, and the creation of the derived
            SO as intercompany_user, minimizing the access right required for the trigger user.
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        SaleOrder = self.env['sale.order']
        company_partner = self.company_id.partner_id

        # find user for creating and validation SO/PO from partner company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise Warning(_('Provide at least one user for inter company relation for % ') % company.name)
        # check intercompany user access rights
        if not SaleOrder.sudo(intercompany_uid).check_access_rights('create', raise_exception=False):
            raise Warning(_("Inter company user of company %s doesn't have enough access rights") % company.name)

        # check pricelist currency should be same with SO/PO document
        if self.pricelist_id.currency_id.id != company_partner.property_product_pricelist.currency_id.id:
            raise Warning(_('You cannot create SO from PO because sale price list currency is different than purchase price list currency.'))

        # create the SO and generate its lines from the PO lines
        SaleOrderLine = self.env['sale.order.line']
        # read it as sudo, because inter-compagny user can not have the access right on PO
        sale_order_data = self.sudo()._prepare_sale_order_data(self.name, company_partner, company, self.dest_address_id and self.dest_address_id.id or False)
        sale_order = SaleOrder.sudo(intercompany_uid).create(sale_order_data[0])
        for line in self.order_line:
            so_line_vals = self.sudo()._prepare_sale_order_line_data(line, company, sale_order.id)
            SaleOrderLine.sudo(intercompany_uid).create(so_line_vals)

        # write vendor reference field on PO
        if not self.partner_ref:
            self.partner_ref = sale_order.name

        #Validation of sale order
        if company.auto_validation:
            sale_order.sudo(intercompany_uid).signal_workflow('order_confirm')

    @api.one
    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        """ Generate the Sale Order values from the PO
            :param name : the origin client reference
            :rtype name : string
            :param partner : the partner reprenseting the company
            :rtype partner : res.partner record
            :param company : the company of the created SO
            :rtype company : res.company record
            :param direct_delivery_address : the address of the SO
            :rtype direct_delivery_address : res.partner record
        """
        partner_addr = partner.sudo().address_get(['invoice', 'delivery', 'contact'])
        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/',
            'company_id': company.id,
            'client_order_ref': name,
            'partner_id': partner.id,
            'pricelist_id': partner.property_product_pricelist.id,
            'partner_invoice_id': partner_addr['invoice'],
            'date_order': self.date_order,
            'fiscal_position_id': partner.property_account_position_id.id,
            'user_id': False,
            'auto_generated': True,
            'auto_purchase_order_id': self.id,
            'partner_shipping_id': direct_delivery_address or partner_addr['delivery']
        }

    @api.model
    def _prepare_sale_order_line_data(self, line, company, sale_id):
        """ Generate the Sale Order Line values from the PO line
            :param line : the origin Purchase Order Line
            :rtype line : purchase.order.line record
            :param company : the company of the created SO
            :rtype company : res.company record
            :param sale_id : the id of the SO
        """
        # it may not affected because of parallel company relation
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
