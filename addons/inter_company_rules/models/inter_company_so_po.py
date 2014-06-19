
from openerp.osv import osv
from openerp.osv import fields
from openerp.tools.translate import _
from openerp import SUPERUSER_ID

class res_company(osv.osv):
    _inherit = 'res.company'

    _columns = {
        'so_from_po': fields.boolean("Create Sale Orders when buying to this company", help='Generate a Sale Order when a Purchase Order with this company as supplier is created.'),
        'po_from_so': fields.boolean("Create Purchase Orders when selling to this company", help='Generate a Purchase Order when a Sale Order with this company as customer is created.'),
        'auto_generate_invoices': fields.boolean("Create Invoices/Refunds when encoding invoices/refunds made to this company", help="Generate Customer/Supplier Invoices (and refunds) when encoding invoices (or refunds) made to this company.\n e.g: Generate a Customer Invoice when a Supplier Invoice with this company as supplier is created."),
        'auto_validation': fields.boolean('Sale/Purchase Orders Auto Validation', help="When a Sale Order or a Purchase Order is created by a multi company rule for this company, it will automatically validate it"),
        'intercompany_user_id': fields.many2one('res.users', 'Inter Company User', help="Responsible user for creation of documents triggered by intercompany rules."),
        'warehouse_id': fields.many2one('stock.warehouse', 'Warehouse For Purchase Orders', help="Default value to set on Purchase Orders that will be created based on Sale Orders made to this company")
    }

    _defaults = {
        'intercompany_user_id': SUPERUSER_ID,
    }

    def _find_company_from_partner(self, cr, uid, partner_id, context=None):
        """ @Return : company_id"""
        company_ids = self.search(cr, SUPERUSER_ID, [('partner_id', '=', partner_id)], context=context)
        if company_ids:
            return self.browse(cr, SUPERUSER_ID, company_ids[0], context=context)

    def _check_intercompany_missmatch_selection(self, cr, uid, ids, context=None):
        for company in self.browse(cr, uid, ids, context=context):
            if (company.po_from_so or company.so_from_po) and company.auto_generate_invoices:
                raise osv.except_osv(_('Invalid Action!'), _("You cannot select to create invoices based on other invoices simultaneously with another option ('Create Sale Orders when buying to this company' or 'Create Purchase Orders when selling to this company')!"))
        return True

    _constraints = [
        (_check_intercompany_missmatch_selection, 'Invalid Action: Cannot Select group selection for intercompany', []),
    ]

class sale_order(osv.osv):
    _inherit = "sale.order"
    _columns = {
        'auto_generated': fields.boolean('Auto Generated Sale Order'),
        'auto_po_id': fields.many2one('purchase.order', 'Source Purchase Order', readonly=True),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'auto_po_id': False, 'auto_generated': False})
        return super(sale_order, self).copy(cr, uid, id, default=default, context=context)

    def action_button_confirm(self, cr, uid, ids, context=None):
        """ Overwrite method also generate intercompany purchase order base on conditions."""
        company_obj = self.pool.get('res.company')

        res = super(sale_order, self).action_button_confirm(cr, uid, ids, context=context)

        for order in self.browse(cr, uid, ids, context=context):
            #If company_id not found, return to normal behavior
            if not order.company_id:
                continue
            #Total check for intersale relation.
            self._check_amount_total(cr, uid, order.id, context=context)

            company_rec = company_obj._find_company_from_partner(cr, uid, order.partner_id.id, context=context)
            if company_rec and company_rec.po_from_so and (not order.auto_generated):
                self.action_create_po(cr, uid, ids, order.id, company_rec, context=context)
        return res

    def _po_line_vals(self, cr, uid, line, company_partner, date_order, purchase_id, company, context=None):
        """ @ return : Purchase Line values dictionary """
        line_obj = self.pool.get('purchase.order.line')
        tax_obj = self.pool.get('account.tax')

        #price on PO line should be line - discount
        price = line.price_unit - (line.price_unit * (line.discount / 100))

        #Computing Default taxes of lines. It may not affect because of parallel company relation
        taxes_ids = [x.id for x in line.tax_id]
        if line.product_id:
            onchange_lines = line_obj.onchange_product_id(cr, uid, [], False, line.product_id and line.product_id.id or False, line.product_uom_qty, line.product_id and line.product_id.uom_po_id.id or False, company_partner.id, context=context)
            if onchange_lines.get('value') and onchange_lines['value'].get('taxes_id'):
                taxes_ids = onchange_lines['value']['taxes_id']
        #Fetch taxes by company not by inter-company user
        cmpny_wise_taxes = []
        for tx_rec in tax_obj.browse(cr, SUPERUSER_ID, taxes_ids, context=context):
            if tx_rec.company_id.id == company.id:
                cmpny_wise_taxes.append(tx_rec.id)

        return {
                'name': line.name,
                'order_id': purchase_id,
                'product_qty': line.product_uom_qty,
                'product_id': line.product_id and line.product_id.id or False,
                'product_uom': line.product_id and line.product_id.uom_po_id.id or line.product_uom.id,
                'price_unit': price or 0.0,
                'company_id': line.order_id.company_id.id,
                'date_planned': line.order_id.commitment_date or date_order,
                'taxes_id': [(6, 0, cmpny_wise_taxes)],
        }

    def _po_vals(self, cr, uid, sale, company, this_company_partner, context=None):
        """ @ return : Purchase values dictionary """
        context = context or {}
        seq_obj = self.pool.get('ir.sequence')
        warehouse_obj = self.pool.get('stock.warehouse')

        #To find location and warehouse,pick warehouse from company object
        warehouse_id = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id.id or False
        if not warehouse_id:
            raise osv.except_osv(_('Invalid Action!'), _('Configure correct warehouse for company(%s) from Menu: Settings/companies/companies' % (company.name)))
        location_id = warehouse_obj.browse(cr, SUPERUSER_ID, warehouse_id, context=context).lot_stock_id.id
        pricelist_id = this_company_partner.property_product_pricelist_purchase.id
        return {
                'name': seq_obj.get(cr, SUPERUSER_ID, 'purchase.order'),
                'origin': sale.name,
                'partner_id': this_company_partner.id,
                'location_id': location_id,
                'pricelist_id': pricelist_id,
                'date_order': sale.date_order,
                'company_id': company.id,
                'fiscal_position': this_company_partner.property_account_position or False,
                'payment_term_id': this_company_partner.property_supplier_payment_term.id or False,
                'auto_generated': True,
                'auto_so_id': sale.id,
                'partner_ref': sale.name,
                'dest_address_id': sale.partner_shipping_id and sale.partner_shipping_id.id or False,
        }

    def action_create_po(self, cr, uid, ids, sale_id, company, context=None):
        """ Intercompany Purchase Order trigger when sale order confirm"""
        if context is None:
            context = {}

        purchase_obj = self.pool.get('purchase.order')
        purchaseline_obj = self.pool.get('purchase.order.line')

        sale = self.browse(cr, SUPERUSER_ID, sale_id, context=context)
        this_company_partner = sale.company_id and sale.company_id.partner_id or False
        if not company or not this_company_partner.id:
            return

        #Find user for creating and validating SO/PO from company
        update_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not update_uid:
            raise osv.except_osv(_('Warning!'), _('Provide one user for intercompany relation for % ') % company.name)

        if not purchase_obj.check_access_rights(cr, update_uid, 'create', raise_exception=False):
            raise osv.except_osv(_('Access Rights!'), _("Inter company user of company %s doesn't have enough access rights") % company.name)

        #Check pricelist currency should be same with SO/PO document
        if sale.pricelist_id.currency_id.id != this_company_partner.property_product_pricelist_purchase.currency_id.id:
            raise osv.except_osv(_('Different Currency!'), _('You cannot create PO from SO because purchase pricelist currency is different than sale pricelist currency.'))

        #create the PO
        po_vals = self._po_vals(cr, update_uid, sale, company, this_company_partner, context=context)
        purchase_id = purchase_obj.create(cr, update_uid, po_vals, context=context)
        for line in sale.order_line:
            po_line_vals = self._po_line_vals(cr, update_uid, line, this_company_partner, sale.date_order, purchase_id, company, context=context)
            purchaseline_obj.create(cr, update_uid, po_line_vals, context=context)

        #write customer reference field on SO
        if not sale.client_order_ref:
            self.write(cr, uid, sale.id, {'client_order_ref': purchase_obj.browse(cr, SUPERUSER_ID, purchase_id).name}, context=context)

        #auto-validate the purchase order if needed
        if company.auto_validation:
            purchase_obj.signal_purchase_confirm(cr, update_uid, [purchase_id])
        return True

    def _check_amount_total(self, cr, uid, sale_id, context=None):
        """ Check If total amount missmatch then raise the warning."""
        context = context or {}
        purchase_obj = self.pool.get('purchase.order')
        sale = self.browse(cr, SUPERUSER_ID, sale_id, context=context)
        #Total check for intersale relation.
        if sale.auto_po_id:
            amount_total = purchase_obj.browse(cr, SUPERUSER_ID, sale.auto_po_id.id, context=context).amount_total
            if sale.amount_total != amount_total:
                raise osv.except_osv(_('Total Mismatch!'), _('You cannot confirm this SO because its total amount does not match the total amount of the PO it is coming from.'))
        return True

sale_order()

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _columns = {
        'auto_generated': fields.boolean('Auto Generated Purchase Order'),
        'auto_so_id': fields.many2one('sale.order', 'Source Sale Order', readonly=True)
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'auto_so_id': False, 'auto_generated': False})
        return super(purchase_order, self).copy(cr, uid, id, default=default, context=context)

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        """ Overwrite method also generate intercompany sale order base on conditions."""
        company_obj = self.pool.get('res.company')

        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context=context)
        for order in self.browse(cr, uid, ids, context):
            #Price check for intersale relation.
            self._check_amount_total(cr, uid, order.id, context=context)

            #get the company from partner then trigger action of intercompany relation.
            company_rec = company_obj._find_company_from_partner(cr, uid, order.partner_id.id, context=context)
            if company_rec and company_rec.so_from_po and (not order.auto_generated):
                self.action_create_so(cr, uid, order.id, company_rec, context=context)
        return res

    def _so_line_vals(self, cr, uid, line, partner, company, sale_id, context=None):
        """ @ return : Sale Line values dictionary """
        context = context or {}
        saleline_obj = self.pool.get('sale.order.line')
        tax_obj = self.pool.get('account.tax')

        #It may not affected because of parallel company relation
        taxes_ids = [x.id for x in line.taxes_id]
        price = line.price_unit or 0.0
        if line.product_id:
            soline_onchange = saleline_obj.product_id_change(cr, uid, [], False, line.product_id.id, qty=line.product_qty,
            uom=line.product_id.uom_id.id, partner_id=partner.id, context=context)
            if soline_onchange.get('value') and soline_onchange['value'].get('tax_id'):
                taxes_ids = soline_onchange['value']['tax_id']

        #Fetch taxes by company not by inter-company user
        cmpny_wise_taxes = []
        for tx_rec in tax_obj.browse(cr, SUPERUSER_ID, taxes_ids, context=context):
            if tx_rec.company_id.id == company.id:
                cmpny_wise_taxes.append(tx_rec.id)

        return {
                'name': line.product_id and line.product_id.name or line.name,
                'order_id': sale_id,
                'product_uom_qty': line.product_qty,
                'product_id': line.product_id and line.product_id.id or False,
                'product_uom': line.product_id and line.product_id.uom_id.id or line.product_uom.id,
                'price_unit': price,
                'delay': line.product_id and line.product_id.sale_delay or 0.0,
                'company_id': company.id,
                'tax_id': [(6, 0, cmpny_wise_taxes)],
        }

    def _so_vals(self, cr, uid, name, purchase_id, partner, company, direct_delivery_address, context=None):
        """ @ return : Sale values dictionary """
        context = context or {}
        seq_obj = self.pool.get('ir.sequence')
        partner_obj = self.pool.get('res.partner')
        partner_addr = partner_obj.address_get(cr, SUPERUSER_ID, [partner.id], ['default', 'invoice', 'delivery', 'contact'])
        pricelist_id = partner.property_product_pricelist.id
        fpos = partner.property_account_position and partner.property_account_position.id or False
        #Not good but browse here for compatible code
        return {
                'name': seq_obj.get(cr, SUPERUSER_ID, 'sale.order') or '/',
                'company_id': company.id,
                'client_order_ref': name,
                'partner_id': partner.id,
                'pricelist_id': pricelist_id,
                'partner_invoice_id': partner_addr['invoice'],
                'date_order': fields.date.context_today(self, cr, uid, context=context),
                'fiscal_position': fpos,
                'user_id': False,
                'auto_generated': True,
                'auto_po_id': purchase_id,
                'partner_shipping_id': direct_delivery_address or partner_addr['delivery']
        }

    def action_create_so(self, cr, uid, order_id, company, context=None):
        if context is None:
            context = {}

        sale_obj = self.pool.get('sale.order')
        saleline_obj = self.pool.get('sale.order.line')

        pur = self.browse(cr, SUPERUSER_ID, order_id)
        this_company_partner = pur.company_id.partner_id

        #To find user for creating and validation SO/PO from partner company
        update_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not update_uid:
            raise osv.except_osv(_('Warning!'), _('Provide atleast one user for intercompany relation for % ') % company.name)

        if not sale_obj.check_access_rights(cr, update_uid, 'create', raise_exception=False):
            raise osv.except_osv(_('Access Rights!'), _("Inter company user of company %s doesn't have enough access rights") % company.name)

        #Check pricelist currency should be same with SO/PO document
        if pur.pricelist_id.currency_id.id != this_company_partner.property_product_pricelist.currency_id.id:
            raise osv.except_osv(_('Different Currency!'), _('You cannot create SO from PO because sale pricelist currency is different than purchase pricelist currency.'))

        #create the SO
        direct_delivery_address = pur.dest_address_id and pur.dest_address_id.id or False
        so_vals = self._so_vals(cr, update_uid, pur.name, pur.id, this_company_partner, company, direct_delivery_address, context=context)
        sale_id = sale_obj.create(cr, update_uid, so_vals, context=context)
        for line in pur.order_line:
            so_line_vals = self._so_line_vals(cr, update_uid, line, this_company_partner, company, sale_id, context=context)
            saleline_obj.create(cr, update_uid, so_line_vals, context=context)

        #write supplier reference field on PO
        if not pur.partner_ref:
            self.write(cr, uid, pur.id, {'partner_ref': sale_obj.browse(cr, SUPERUSER_ID, sale_id).name}, context=context)

        #Validation of sale order
        if company.auto_validation:
            sale_obj.signal_order_confirm(cr, update_uid, [sale_id])
        return True

    def _check_amount_total(self, cr, uid, purchase_id, context=None):
        """ Check If total amount missmatch then raise the warning."""
        context = context or {}
        sale_obj = self.pool.get('sale.order')
        purchase = self.browse(cr, SUPERUSER_ID, purchase_id, context=context)
        #Total check for intersale relation.
        if purchase.auto_so_id:
            amount_total = sale_obj.browse(cr, SUPERUSER_ID, purchase.auto_so_id.id, context=context).amount_total
            if purchase.amount_total != amount_total:
                raise osv.except_osv(_('Total Mismatch!'), _('You cannot confirm this PO because its total amount does not match the total amount of the SO is it coming from.'))
        return True

purchase_order()
