# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.modules.module import get_resource_path
import base64

class AccountTourUploadBill(models.TransientModel):
    _name = 'account.tour.upload.bill'
    _description = 'Account tour upload bill'
    _inherits = {'mail.compose.message': 'composer_id'}

    composer_id = fields.Many2one('mail.compose.message', string='Composer', required=True, ondelete='cascade')

    selection = fields.Selection(
        selection=lambda self: self._selection_values(),
        default="sample"
    )

    sample_bill_preview = fields.Binary(
        readonly=True,
        compute='_compute_sample_bill_image'
    )

    def _selection_values(self):
        journal_alias = self.env['account.journal'] \
            .search([('type', '=', 'purchase'), ('company_id', '=', self.env.company.id)], limit=1)

        return [('sample', _('Try a sample vendor bill')),
                ('upload', _('Upload your own bill')),
                ('email', _('Or send a bill to %s@%s', journal_alias.alias_name, journal_alias.alias_domain))]

    def _compute_sample_bill_image(self):
        """ Retrieve sample bill with facturx to speed up onboarding """
        try:
            path = get_resource_path('account_edi_facturx', 'data/files', 'Invoice.pdf')
            self.sample_bill_preview = base64.b64encode(open(path, 'rb').read()) if path else False
        except (IOError, OSError):
            self.sample_bill_preview = False
        return

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
        purchase_journal = self.env['account.journal'].search([('type', '=', 'purchase')], limit=1)
        if self.selection == 'upload':
            return purchase_journal.with_context(default_journal_id=purchase_journal.id, default_move_type='in_invoice').create_invoice_from_attachment(attachment_ids=self.attachment_ids.ids)
        elif self.selection == 'sample':
            attachment = self.env['ir.attachment'].create({
                'type': 'binary',
                'name': 'INV/2020/0011.pdf',
                'res_model': 'mail.compose.message',
                'datas': self.sample_bill_preview,
            })
            bill = purchase_journal.with_context(default_journal_id=purchase_journal.id, default_move_type='in_invoice').create_invoice_from_attachment(attachment.ids)
            if self.selection == 'sample':
                bill.write({
                    'partner_id': self.env.ref('base.main_partner').id,
                    'ref': 'INV/2020/0011'
                })
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
