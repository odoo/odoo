
from openerp.osv import osv, fields
from openerp.tools.translate import _

class account_invoice(osv.osv):
    _inherit = 'account.invoice'

    _columns = {
        'auto_generated': fields.boolean('Auto Generated Document'),
        'auto_invoice_id': fields.many2one('account.invoice', 'Source Invoice', readonly=True),
    }

    def copy(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        default.update({'auto_invoice_id': False, 'auto_generated': False})
        return super(account_invoice, self).copy(cr, uid, id, default=default, context=context)

    def invoice_validate(self, cr, uid, ids, context=None):
        """
        Validated invoice generate cross invoice base on company rules.
        """
        company_obj = self.pool.get('res.company')
        for invoice in self.browse(cr, uid, ids, context=context):
            #do not consider invoices that have already been auto-generated, nor the invoices that were already validated in the past
            company = company_obj._find_company_from_partner(cr, uid, invoice.partner_id.id, context=context)
            if company and company.auto_generate_invoices and not invoice.auto_generated:
                if invoice.type == 'out_invoice':
                    self.action_create_invoice(cr, uid, invoice, company, 'in_invoice', 'purchase', context=context)
                elif invoice.type == 'in_invoice':
                    self.action_create_invoice(cr, uid, invoice, company, 'out_invoice', 'sale', context=context)
                elif invoice.type == 'out_refund':
                    self.action_create_invoice(cr, uid, invoice, company, 'in_refund', 'purchase_refund', context=context)
                elif invoice.type == 'in_refund':
                    self.action_create_invoice(cr, uid, invoice, company, 'out_refund', 'sale_refund', context=context)
        return super(account_invoice, self).invoice_validate(cr, uid, ids, context=context)

    def action_create_invoice(self, cr, uid, invoice, company, inv_type, journal_type, context=None):
        if context is None:
            context = {}
        inv_obj = self.pool.get('account.invoice')
        inv_line_obj = self.pool.get('account.invoice.line')

        #Find user for creating the invoice from company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise osv.except_osv(_('Warning!'), _('Provide one user for intercompany relation for % ') % company.name)

        #
        ctx = context.copy()
        ctx['force_company'] = company.id
        this_company_partner = invoice.company_id.partner_id
        inv_lines = []
        for line in invoice.invoice_line:
            #To find lot of data from product onchanges because its already avail method in core.
            product_uom = line.product_id.uom_id and line.product_id.uom_id.id or False
            line_data = inv_line_obj.product_id_change(cr, intercompany_uid, [line.id], line.product_id.id, product_uom, qty=line.quantity, name='', type=inv_type, partner_id=this_company_partner.id, fposition_id=this_company_partner.property_account_position.id, context=ctx, company_id=company.id)
            inv_line_data = self._prepare_inv_line(cr, uid, line_data, line, context=ctx)
            inv_line_id = inv_line_obj.create(cr, intercompany_uid, inv_line_data, context=ctx)
            inv_lines.append(inv_line_id)

        #create invoice
        invoice_vals = self._prepare_inv(cr, intercompany_uid, invoice, inv_lines, inv_type, journal_type, company, context=ctx)
        return inv_obj.create(cr, intercompany_uid, invoice_vals, context=ctx)

    def _prepare_inv_line(self, cr, uid, line_data, line, context=None):
        """ Generate invoice line dictionary"""
        vals = {
            'name': line.name,
            'price_unit': line.price_unit,
            'quantity': line.quantity,
            'discount': line.discount,
            'product_id': line.product_id.id or False,
            'uos_id': line.uos_id.id or False,
            'sequence': line.sequence,
            'invoice_line_tax_id': [(6, 0, line_data['value'].get('invoice_line_tax_id', []))],
            'account_analytic_id': line.account_analytic_id.id or False,
        }
        if line_data['value'].get('account_id', False):
            vals['account_id'] = line_data['value']['account_id']
        return vals

    def _prepare_inv(self, cr, uid, invoice, inv_lines, inv_type, jrnl_type, company, context=None):
        """ Generate invoice dictionary """
        context = context or {}
        journal_obj = self.pool.get('account.journal')
        period_obj = self.pool.get('account.period')

        #To find journal.
        journal_ids = journal_obj.search(cr, uid, [('type', '=', jrnl_type), ('company_id', '=', company.id)], limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define %s journal for this company: "%s" (id:%d).') % (jrnl_type, company.name, company.id))
        #To find periods of supplier company.
        ctx = context.copy()
        ctx.update(company_id=company.id)
        period_ids = period_obj.find(cr, uid, invoice.date_invoice, context=ctx)
        #To find account,payment term,fiscal position,bank.
        partner_data = self.onchange_partner_id(cr, uid, [invoice.id], inv_type, invoice.company_id.partner_id.id, company_id=company.id)

        return {
                'name': invoice.name,
                'origin': invoice.company_id.name + _(' Invoice: ') + str(invoice.number),
                'type': inv_type,
                'date_invoice': invoice.date_invoice,
                'reference': invoice.reference,
                'account_id': partner_data['value'].get('account_id', False),
                'partner_id': invoice.company_id.partner_id.id,
                'journal_id': journal_ids[0],
                'invoice_line': [(6, 0, inv_lines)],
                'currency_id': invoice.currency_id and invoice.currency_id.id,
                'fiscal_position': partner_data['value'].get('fiscal_position', False),
                'payment_term': partner_data['value'].get('payment_term', False),
                'company_id': company.id,
                'period_id': period_ids and period_ids[0] or False,
                'partner_bank_id': partner_data['value'].get('partner_bank_id', False),
                'auto_generated': True,
                'auto_invoice_id': invoice.id,
        }
