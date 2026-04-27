from odoo import api, fields, models, _
from odoo.exceptions import UserError


class sale_order(models.Model):

    _inherit = "sale.order"

    auto_generated = fields.Boolean(string='Auto Generated Sales Order', copy=False)
    auto_purchase_order_id = fields.Many2one('purchase.order', string='Source Purchase Order', readonly=True, copy=False)

    def _action_confirm(self):
        """ Generate inter company purchase order based on conditions """
        res = super(sale_order, self)._action_confirm()
        for order in self:
            if not order.company_id: # if company_id not found, return to normal behavior
                continue
            # if company allow to create a Purchase Order from Sales Order, then do it!
            company = self.env['res.company']._find_company_from_partner(order.partner_id.id)
            if company and company.intercompany_generate_purchase_orders and not order.auto_generated:
                order.with_user(company.intercompany_user_id).with_context(default_company_id=company.id).with_company(company).inter_company_create_purchase_order(company)
        return res

    def inter_company_create_purchase_order(self, company):
        """ Create a Purchase Order from the current SO (self)
            Note : In this method, reading the current SO is done as sudo, and the creation of the derived
            PO as intercompany_user, minimizing the access right required for the trigger user
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        for rec in self:
            if not company or not rec.company_id.partner_id:
                continue

            # find user for creating and validating SO/PO from company
            intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
            if not intercompany_uid:
                raise UserError(_('Provide one user for intercompany relation for %(name)s '), name=company.name)
            # check intercompany user access rights
            if not self.env['purchase.order'].with_user(intercompany_uid).has_access('create'):
                raise UserError(_("Inter company user of company %s doesn't have enough access rights", company.name))

            company_partner = rec.company_id.partner_id.with_user(intercompany_uid)
            # create the PO and generate its lines from the SO
            # read it as sudo, because inter-compagny user can not have the access right on PO
            po_vals = rec.sudo()._prepare_purchase_order_data(company, company_partner)
            for line in rec.order_line.sudo():
                po_vals['order_line'] += [(0, 0, rec._prepare_purchase_order_line_data(line, rec.date_order, company))]
            purchase_order = self.env['purchase.order'].create(po_vals)
            msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=self.name, company=rec.company_id.name)
            purchase_order.message_post(body=msg)

            # write customer reference field on SO
            if not rec.client_order_ref:
                rec.client_order_ref = purchase_order.name

            # auto-validate the purchase order if needed
            if company.intercompany_document_state == 'posted':
                purchase_order.with_user(intercompany_uid).button_confirm()

    def _prepare_purchase_order_data(self, company, company_partner):
        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the SO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        self.ensure_one()

        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'partner_id': company_partner.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': self.env['account.fiscal.position']._get_fiscal_position(company_partner).id,
            'payment_term_id': company_partner.property_supplier_payment_term_id.id,
            'auto_generated': True,
            'auto_sale_order_id': self.id,
            'partner_ref': self.name,
            'currency_id': self.currency_id.id,
            'order_line': [],
        }

    @api.model
    def _prepare_purchase_order_line_data(self, so_line, date_order, company):
        """ Generate purchase order line values, from the SO line
            :param so_line : origin SO line
            :rtype so_line : sale.order.line record
            :param date_order : the date of the orgin SO
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        # price on PO so_line should be so_line - discount
        price = so_line.price_unit or 0.0
        quantity = so_line.product_id and so_line.product_uom._compute_quantity(so_line.product_uom_qty, so_line.product_id.uom_po_id) or so_line.product_uom_qty
        price = so_line.product_id and so_line.product_uom._compute_price(price, so_line.product_id.uom_po_id) or price
        return {
            'name': so_line.name,
            'product_qty': quantity,
            'product_id': so_line.product_id and so_line.product_id.id or False,
            'product_uom': so_line.product_id and so_line.product_id.uom_po_id.id or so_line.product_uom.id,
            'price_unit': price or 0.0,
            'discount': so_line.discount or 0.0,
            'company_id': company.id,
            'date_planned': so_line.order_id.commitment_date or so_line.order_id.expected_date or date_order,
            'display_type': so_line.display_type,
        }
