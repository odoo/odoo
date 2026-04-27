from odoo import api, fields, models, _
from odoo.exceptions import UserError


class purchase_order(models.Model):

    _inherit = "purchase.order"

    auto_generated = fields.Boolean(string='Auto Generated Purchase Order', copy=False)
    auto_sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', readonly=True, copy=False)

    def button_approve(self, force=False):
        """ Generate inter company sales order base on conditions."""
        res = super(purchase_order, self).button_approve(force=force)
        for order in self:
            # get the company from partner then trigger action of intercompany relation
            company_rec = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company_rec and company_rec.intercompany_generate_sales_orders and not order.auto_generated:
                order.with_user(company_rec.intercompany_user_id).with_context(default_company_id=company_rec.id).with_company(company_rec).inter_company_create_sale_order(company_rec)
        return res

    def inter_company_create_sale_order(self, company):
        """ Create a Sales Order from the current PO (self)
            Note : In this method, reading the current PO is done as sudo, and the creation of the derived
            SO as intercompany_user, minimizing the access right required for the trigger user.
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        # find user for creating and validation SO/PO from partner company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise UserError(_(
                'Provide at least one user for inter company relation for %(name)s',
                name=company.name,
            ))
        # check intercompany user access rights
        if not self.env['sale.order'].has_access('create'):
            raise UserError(_(
                "Inter company user of company %(name)s doesn't have enough access rights",
                name=company.name,
            ))

        for rec in self:
            # check pricelist currency should be same with SO/PO document
            company_partner = rec.company_id.partner_id.with_user(intercompany_uid)
            if company_partner.property_product_pricelist and \
               rec.currency_id.id != company_partner.property_product_pricelist.currency_id.id:
                raise UserError(_(
                    'You cannot create SO from PO because sale price list currency is different '
                    'than purchase price list currency.\n'
                    'The currency of the SO is obtained from the pricelist of the company partner.\n\n'
                    '(SO currency: %(so_currency)s, Pricelist: %(pricelist)s, Partner: %(partner)s (ID: %(id)s))',
                    so_currency=rec.currency_id.name,
                    pricelist=company_partner.property_product_pricelist.display_name,
                    partner=company_partner.display_name,
                    id=company_partner.id,
                ))

            # create the SO and generate its lines from the PO lines
            # read it as sudo, because inter-compagny user can not have the access right on PO
            sale_order_data = rec.sudo()._prepare_sale_order_data(rec.name, company_partner, company, rec.dest_address_id.id or False)

            # lines are browse as sudo to access all data required to be copied on SO line (mainly for company dependent field like taxes)
            for line in rec.order_line.sudo():
                sale_order_data['order_line'] += [(0, 0, rec._prepare_sale_order_line_data(line, company))]
            sale_order = self.env['sale.order'].with_context(
                allowed_company_ids=company.ids,
                in_rental_app=False,  # avoid creating rental orders if PO is accessed via Rental
            ).with_user(intercompany_uid).create(sale_order_data)
            msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=self.name, company=rec.company_id.name)
            sale_order.message_post(body=msg)

            # write vendor reference field on PO
            if not rec.partner_ref:
                rec.partner_ref = sale_order.name

            #Validation of sales order
            if company.intercompany_document_state == 'posted':
                sale_order.with_user(intercompany_uid).action_confirm()

    def _prepare_sale_order_data(self, name, partner, company, direct_delivery_address):
        """ Generate the Sales Order values from the PO
            :param name : the origin client reference
            :rtype name : string
            :param partner : the partner reprenseting the company
            :rtype partner : res.partner record
            :param company : the company of the created SO
            :rtype company : res.company record
            :param direct_delivery_address : the address of the SO
            :rtype direct_delivery_address : res.partner record
        """
        self.ensure_one()
        partner_addr = partner.sudo().address_get(['invoice', 'delivery', 'contact'])

        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('sale.order') or '/',
            'company_id': company.id,
            'client_order_ref': name,
            'partner_id': partner.id,
            'pricelist_id': partner.property_product_pricelist.id,
            'partner_invoice_id': partner_addr['invoice'],
            'date_order': self.date_order,
            'fiscal_position_id': self.env['account.fiscal.position']._get_fiscal_position(partner).id,
            'payment_term_id': partner.property_payment_term_id.id,
            'user_id': False,
            'auto_generated': True,
            'auto_purchase_order_id': self.id,
            'partner_shipping_id': direct_delivery_address or partner_addr['delivery'],
            'commitment_date': self.date_planned,
            'order_line': [],
        }

    @api.model
    def _prepare_sale_order_line_data(self, line, company):
        """ Generate the Sales Order Line values from the PO line
            :param line : the origin Purchase Order Line
            :rtype line : purchase.order.line record
            :param company : the company of the created SO
            :rtype company : res.company record
        """
        # it may not affected because of parallel company relation
        price = line.price_unit or 0.0
        quantity = line.product_id and line.product_uom._compute_quantity(line.product_qty, line.product_id.uom_id) or line.product_qty
        price = line.product_id and line.product_uom._compute_price(price, line.product_id.uom_id) or price
        return {
            'name': line.name,
            'product_uom_qty': quantity,
            'product_id': line.product_id and line.product_id.id or False,
            'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
            'price_unit': price,
            'discount': line.discount or 0.0,
            'company_id': company.id,
            'display_type': line.display_type,
        }
