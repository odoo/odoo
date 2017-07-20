# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    @api.multi
    @api.onchange('template_id')
    def onchange_template_id_wrapper(self):
        '''Add automatically the EDI documents if checked in the config.
        '''
        super(MailComposeMessage, self).onchange_template_id_wrapper()
        country_id = self.env.user.company_id.country_id
        if self.model == 'account.invoice' and country_id == self.env.ref('base.be'):
            invoice_id = self.env[self.model].browse(self.res_id)
            attachment_id = self.env['ir.attachment'].search([
                    ('datas_fname', '=', invoice_id.l10n_be_edi_attachment_name()),
                    ('res_model', '=', self.model),
                    ('res_id', '=', invoice_id.id)
            ], limit=1)
            if attachment_id and attachment_id not in self.attachment_ids:
                self.attachment_ids += attachment_id
