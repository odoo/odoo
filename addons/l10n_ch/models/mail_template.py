# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo import api, models


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.multi
    def generate_email(self, res_ids, fields=None):
        """ Method overridden in order to add an attachment containing the ISR
        to the draft message when opening the 'send by mail' wizard on an invoice.
        This attachment generation will only occur if all the required data are
        present on the invoice. Otherwise, no ISR attachment will be created, and
        the mail will only contain the invoice (as defined in the mother method).
        """
        rslt = super(MailTemplate, self).generate_email(res_ids, fields)

        multi_mode = True
        if isinstance(res_ids, int):
            res_ids = [res_ids]
            multi_mode = False

        res_ids_to_templates = self.get_email_template(res_ids)
        for res_id in res_ids:
            related_model = self.env[self.model_id.model].browse(res_id)

            if related_model._name == 'account.move' and related_model.l10n_ch_isr_valid:
                #We add an attachment containing the ISR
                template = res_ids_to_templates[res_id]
                report_name = 'ISR-' + self._render_template(template.report_name, template.model, res_id) + '.pdf'

                pdf = self.env.ref('l10n_ch.l10n_ch_isr_report').render_qweb_pdf([res_id])[0]
                pdf = base64.b64encode(pdf)

                attachments_list = multi_mode and rslt[res_id].get('attachments', False) or rslt.get('attachments', False)
                if attachments_list:
                    attachments_list.append((report_name, pdf))
                else:
                    rslt[res_id]['attachments'] = [(report_name, pdf)]
        return rslt
