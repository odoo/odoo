# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    def generate_email(self, res_ids, fields):
        """ Method overridden in order to add an attachment containing the ISR
        to the draft message when opening the 'send by mail' wizard on an invoice.
        This attachment generation will only occur if all the required data are
        present on the invoice. Otherwise, no ISR attachment will be created, and
        the mail will only contain the invoice (as defined in the mother method).
        """
        result = super(MailTemplate, self).generate_email(res_ids, fields)
        if self.model != 'account.move':
            return result

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        for record in self.env[self.model].browse(res_ids):
            if record.l10n_ch_isr_valid:
                # We add an attachment containing the ISR
                report_name = 'ISR-' + self._render_field('report_name', record.ids, compute_lang=True)[record.id] + '.pdf'

                pdf = self.env.ref('l10n_ch.l10n_ch_isr_report').render_qweb_pdf(record.ids)[0]
                pdf = base64.b64encode(pdf)

                record_dict = multi_mode and result[record.id] or result
                attachments_list = record_dict.get('attachments', False)
                if attachments_list:
                    attachments_list.append((report_name, pdf))
                else:
                    record_dict['attachments'] = [(report_name, pdf)]
        return result
