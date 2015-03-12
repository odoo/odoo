# -*- coding: utf-8 -*-
from openerp import api, fields, models, _
from openerp.exceptions import Warning


class account_invoice(models.Model):

    _inherit = 'account.invoice'

    auto_generated = fields.Boolean(string='Auto Generated Document', copy=False, default=False)
    auto_invoice_id = fields.Many2one('account.invoice', string='Source Invoice', readonly=True, copy=False)

    @api.multi
    def invoice_validate(self):
        """ Validated invoice generate cross invoice base on company rules """
        for invoice in self:
            # do not consider invoices that have already been auto-generated, nor the invoices that were already validated in the past
            company = self.env['res.company']._find_company_from_partner(invoice.partner_id.id)
            if company and company.auto_generate_invoices and not invoice.auto_generated:
                if invoice.type == 'out_invoice':
                    invoice.inter_company_create_invoice(company, 'in_invoice', 'purchase')
                elif invoice.type == 'in_invoice':
                    invoice.inter_company_create_invoice(company, 'out_invoice', 'sale')
                elif invoice.type == 'out_refund':
                    invoice.inter_company_create_invoice(company, 'in_refund', 'purchase_refund')
                elif invoice.type == 'in_refund':
                    invoice.inter_company_create_invoice(company, 'out_refund', 'sale_refund')
        return super(account_invoice, self).invoice_validate()

    @api.one
    def inter_company_create_invoice(self, company, inv_type, journal_type):
        """ create an invoice for the given company : it wil copy the invoice lines in the new
            invoice. The intercompany user is the author of the new invoice.
            :param company : the company of the created invoice
            :rtype company : res.company record
            :param inv_type : the type of the invoice ('in_refund', 'out_refund', 'in_invoice', ...)
            :rtype inv_type : string
            :param journal_type : the type of the journal to register the invoice
            :rtype journal_type : string
        """
        # find user for creating the invoice from company
        intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
        if not intercompany_uid:
            raise Warning(_('Provide one user for intercompany relation for % ') % company.name)

        context = self._context.copy()
        context['force_company'] = company.id
        origin_partner_id = self.company_id.partner_id
        invoice_line_ids = []
        for line in self.invoice_line:
            # get invoice line data from product onchange
            product_uom_id = line.product_id.uom_id and line.product_id.uom_id.id or False
            line_data = line.with_context(context).sudo().product_id_change(line.product_id.id,
                                                product_uom_id,
                                                qty=line.quantity,
                                                name='',
                                                type=inv_type,
                                                partner_id=origin_partner_id.id,
                                                fposition_id=origin_partner_id.property_account_position.id,
                                                company_id=company.id)
            # create invoice line, as the intercompany user
            inv_line_data = self.sudo()._prepare_invoice_line_data(line_data, line)
            inv_line_id = line.with_context(context).sudo(intercompany_uid).create(inv_line_data)
            invoice_line_ids.append(inv_line_id.id)
        # create invoice, as the intercompany user
        invoice_vals = self.with_context(context).sudo()._prepare_invoice_data(invoice_line_ids, inv_type, journal_type, company)[0]
        return self.with_context(context).sudo(intercompany_uid).create(invoice_vals)

    @api.one
    def _prepare_invoice_data(self, invoice_line_ids, inv_type, journal_type, company):
        """ Generate invoice values
            :param invoice_line_ids : the ids of the invoice lines
            :rtype invoice_line_ids : array of integer
            :param inv_type : the type of the invoice to prepare the values
            :param journal_type : type of the journal to register the invoice_line_ids
            :rtype journal_type : string
            :rtype company : res.company record
        """
        # find the correct journal
        journal = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', company.id)], limit=1)
        if not journal:
            raise Warning(_('Please define %s journal for this company: "%s" (id:%d).') % (journal_type, company.name, company.id))

        # find periods of supplier company
        context = self._context.copy()
        context['company_id'] = company.id
        period_ids = self.env['account.period'].with_context(context).find(self.date_invoice)

        # find account, payment term, fiscal position, bank.
        partner_data = self.onchange_partner_id(inv_type, self.company_id.partner_id.id, company_id=company.id)
        return {
            'name': self.name,
            #TODO : not sure !!
            'origin': self.company_id.name + _(' Invoice: ') + str(self.number),
            'type': inv_type,
            'date_invoice': self.date_invoice,
            'reference': self.reference,
            'account_id': partner_data['value'].get('account_id', False),
            'partner_id': self.company_id.partner_id.id,
            'journal_id': journal.id,
            'invoice_line': [(6, 0, invoice_line_ids)],
            'currency_id': self.currency_id and self.currency_id.id,
            'fiscal_position': partner_data['value'].get('fiscal_position', False),
            'payment_term': partner_data['value'].get('payment_term', False),
            'company_id': company.id,
            'period_id': period_ids and period_ids[0].id or False,
            'partner_bank_id': partner_data['value'].get('partner_bank_id', False),
            'auto_generated': True,
            'auto_invoice_id': self.id,
        }

    @api.model
    def _prepare_invoice_line_data(self, line_data, line):
        """ Generate invoice line values
            :param line_data : dict of invoice line data
            :rtype line_data : dict
            :param line : the invoice line object
            :rtype line : account.invoice.line record
        """
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
        if line_data['value'].get('account_id'):
            vals['account_id'] = line_data['value']['account_id']
        return vals
