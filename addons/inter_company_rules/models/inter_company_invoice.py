from openerp import models, fields, api, _
from openerp.exceptions import Warning

class account_invoice(models.Model):
    _inherit = 'account.invoice'

    auto_generated = fields.Boolean(string='Auto Generated Document', copy=False)
    auto_invoice_id = fields.Many2one('account.invoice', string='Source Invoice',
        readonly=True, copy=False)

    @api.multi
    def invoice_validate(self):
        """
        Validated invoice generate cross invoice base on company rules.
        """
        for invoice in self:
            #do not consider invoices that have already been auto-generated, nor the invoices that were already validated in the past
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if company and company.auto_generate_invoices and not invoice.auto_generated:
                if invoice.type == 'out_invoice':
                    invoice.action_create_invoice(company, 'in_invoice', 'purchase')
                elif invoice.type == 'in_invoice':
                    invoice.action_create_invoice(company, 'out_invoice', 'sale')
                elif invoice.type == 'out_refund':
                    invoice.action_create_invoice(company, 'in_refund', 'purchase_refund')
                elif invoice.type == 'in_refund':
                    invoice.action_create_invoice(company, 'out_refund', 'sale_refund')
        return super(account_invoice, self).invoice_validate()

    @api.one
    def action_create_invoice(self, company, inv_type, journal_type):
        #Find user for creating the invoice from company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise Warning(_('Provide one user for intercompany relation for % ') % company.name)

        ctx = self._context.copy()
        ctx['force_company'] = company.id
        this_company_partner = self.company_id.partner_id
        inv_lines = []
        for line in self.invoice_line:
            #To find lot of data from product onchanges because its already avail method in core.
            product_uom = line.product_id.uom_id and line.product_id.uom_id.id or False
            line_data = line.with_context(ctx).sudo(intercompany_uid).product_id_change(line.product_id.id,
                                                product_uom, qty=line.quantity, name='', type=inv_type, 
                                                partner_id=this_company_partner.id, 
                                                fposition_id=this_company_partner.property_account_position.id, company_id=company.id)
            inv_line_data = self._prepare_inv_line(line_data, line)
            inv_line_id = line.with_context(ctx).sudo(intercompany_uid).create(inv_line_data)
            inv_lines.append(inv_line_id.id)
        #create invoice
        invoice_vals = self.with_context(ctx).sudo(intercompany_uid)._prepare_inv(inv_lines, inv_type, journal_type, company)[0]
        return self.with_context(ctx).sudo(intercompany_uid).create(invoice_vals)

    @api.model
    def _prepare_inv_line(self, line_data, line):
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

    @api.one
    def _prepare_inv(self, inv_lines, inv_type, jrnl_type, company):
        """ Generate invoice dictionary """
        #To find journal.
        journal = self.env['account.journal'].search([('type', '=', jrnl_type), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise Warning(_('Please define %s journal for this company: "%s" (id:%d).') % (jrnl_type, company.name, company.id))

        #To find periods of supplier company.
        ctx = self._context.copy()
        ctx['company_id'] = company.id
        period_ids = self.env['account.period'].with_context(ctx).find(self.date_invoice)
        #To find account,payment term,fiscal position,bank.
        partner_data = self.onchange_partner_id(inv_type, self.company_id.partner_id.id, company_id=company.id)

        return {
            'name': self.name,
            'origin': self.company_id.name + _(' Invoice: ') + str(self.number),
            'type': inv_type,
            'date_invoice': self.date_invoice,
            'reference': self.reference,
            'account_id': partner_data['value'].get('account_id', False),
            'partner_id': self.company_id.partner_id.id,
            'journal_id': journal.id,
            'invoice_line': [(6, 0, inv_lines)],
            'currency_id': self.currency_id and self.currency_id.id,
            'fiscal_position': partner_data['value'].get('fiscal_position', False),
            'payment_term': partner_data['value'].get('payment_term', False),
            'company_id': company.id,
            'period_id': period_ids and period_ids[0].id or False,
            'partner_bank_id': partner_data['value'].get('partner_bank_id', False),
            'auto_generated': True,
            'auto_invoice_id': self.id,
        }
