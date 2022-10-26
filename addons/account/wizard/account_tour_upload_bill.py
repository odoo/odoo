# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _, Command, tools
import base64
from datetime import timedelta


class AccountTourUploadBill(models.TransientModel):
    _name = 'account.tour.upload.bill'
    _description = 'Account tour upload bill'

    attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        relation='account_tour_upload_bill_ir_attachments_rel',
        string='Attachments')

    selection = fields.Selection(
        selection=lambda self: self._selection_values(),
        default="sample"
    )

    preview_invoice = fields.Html(
        compute="_compute_preview_invoice",
        string="Invoice Preview",
        translate=True,
    )

    def _compute_preview_invoice(self):
        invoice_date = fields.Date.today() - timedelta(days=12)
        addr = [x for x in [
            self.env.company.street,
            self.env.company.street2,
            ' '.join([x for x in [self.env.company.state_id.name, self.env.company.zip] if x]),
            self.env.company.country_id.name,
        ] if x]
        ref = 'INV/%s/0001' % invoice_date.strftime('%Y/%m')
        html = self.env['ir.qweb']._render('account.bill_preview', {
            'company_name': self.env.company.name,
            'company_street_address': addr,
            'invoice_name': 'Invoice ' + ref,
            'invoice_ref': ref,
            'invoice_date': invoice_date,
            'invoice_due_date': invoice_date + timedelta(days=30),
        })
        for record in self:
            record.preview_invoice = html

    def _selection_values(self):
        journal_alias = self.env['account.journal'] \
            .search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)

        values = [('sample', _('Try a sample vendor bill')), ('upload', _('Upload your own bill'))]
        if journal_alias.alias_name and journal_alias.alias_domain:
            values.append(('email', _('Or send a bill to %s@%s', journal_alias.alias_name, journal_alias.alias_domain)))
        return values

    def _action_list_view_bill(self, bill_ids=[]):
        context = dict(self._context)
        context['default_move_type'] = 'in_invoice'
        return {
            'name': _('Generated Documents'),
            'domain': [('id', 'in', bill_ids)],
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [[False, "tree"], [False, "form"]],
            'type': 'ir.actions.act_window',
            'context': context
        }

    def apply(self):
        if self._context.get('active_model') == 'account.journal' and self._context.get('active_ids'):
            purchase_journal = self.env['account.journal'].browse(self._context['active_ids'])
        else:
            purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)

        if self.selection == 'upload':
            return purchase_journal.with_context(default_journal_id=purchase_journal.id, default_move_type='in_invoice').create_document_from_attachment(attachment_ids=self.attachment_ids.ids)
        elif self.selection == 'sample':
            invoice_date = fields.Date.today() - timedelta(days=12)
            partner = self.env['res.partner'].search([('name', '=', 'Deco Addict')], limit=1)
            if not partner:
                partner = self.env['res.partner'].create({
                    'name': 'Deco Addict',
                    'is_company': True,
                })
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': partner.id,
                'ref': 'INV/%s/0001' % invoice_date.strftime('%Y/%m'),
                'invoice_date': invoice_date,
                'invoice_date_due': invoice_date + timedelta(days=30),
                'journal_id': purchase_journal.id,
                'invoice_line_ids': [
                    Command.create({
                        'name': "[FURN_8999] Three-Seat Sofa",
                        'quantity': 5,
                        'price_unit': 1500,
                    }),
                    Command.create({
                        'name': "[FURN_8220] Four Person Desk",
                        'quantity': 5,
                        'price_unit': 2350,
                    })
                ],
            })
            # In case of test environment, don't create the pdf
            if tools.config['test_enable'] or tools.config['test_file']:
                bill.with_context(no_new_invoice=True).message_post()
            else:
                bodies = self.env['ir.actions.report']._prepare_html(self.preview_invoice)[0]
                content = self.env['ir.actions.report']._run_wkhtmltopdf(bodies)
                attachment = self.env['ir.attachment'].create({
                    'type': 'binary',
                    'name': 'INV-%s-0001.pdf' % invoice_date.strftime('%Y-%m'),
                    'res_model': 'mail.compose.message',
                    'datas': base64.encodebytes(content),
                })
                bill.with_context(no_new_invoice=True).message_post(attachment_ids=[attachment.id])

            return self._action_list_view_bill(bill.ids)
        else:
            email_alias = '%s@%s' % (purchase_journal.alias_name, purchase_journal.alias_domain)
            new_wizard = self.env['account.tour.upload.bill.email.confirm'].create({'email_alias': email_alias})
            view_id = self.env.ref('account.account_tour_upload_bill_email_confirm').id

            return {
                'type': 'ir.actions.act_window',
                'name': _('Confirm'),
                'view_mode': 'form',
                'res_model': 'account.tour.upload.bill.email.confirm',
                'target': 'new',
                'res_id': new_wizard.id,
                'views': [[view_id, 'form']],
            }


class AccountTourUploadBillEmailConfirm(models.TransientModel):
    _name = 'account.tour.upload.bill.email.confirm'
    _description = 'Account tour upload bill email confirm'

    email_alias = fields.Char(readonly=True)

    def apply(self):
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        bill_ids = self.env['account.move'].search([('journal_id', '=', purchase_journal.id)]).ids
        return self.env['account.tour.upload.bill']._action_list_view_bill(bill_ids)
