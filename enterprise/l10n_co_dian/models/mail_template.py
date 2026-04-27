from odoo import models, api


class MailTemplate(models.Model):
    _inherit = 'mail.template'

    @api.model
    def _create_dian_mail_templates(self):
        """ This function is needed to create the DIAN mail templates because `copy_data` is overridden
        in mail, ignoring the default name passed when calling `copy`.
        """
        dian_subject = (
            "{{ object.company_id.partner_id._get_vat_without_verification_code() }};"
            "{{ object.company_id.name }};{{ object.name }};{{ (object.l10n_co_edi_type or '').rjust(2, '0') }};"
            "{{ object.company_id.partner_id.l10n_co_edi_commercial_name }}"
        )

        invoice_template = self.env.ref('account.email_template_edi_invoice', raise_if_not_found=False)
        if invoice_template:
            invoice_dian_template = invoice_template.copy({"subject": dian_subject})
            invoice_dian_template.name = "Invoice (DIAN): Sending"
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': "l10n_co_dian.email_template_edi_invoice",
                'record': invoice_dian_template,
                'noupdate': True,
            }])

        credit_note_template = self.env.ref('account.email_template_edi_credit_note', raise_if_not_found=False)
        if credit_note_template:
            credit_note_dian_template = credit_note_template.copy({"subject": dian_subject})
            credit_note_dian_template.name = "Credit Note (DIAN): Sending"
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': "l10n_co_dian.email_template_edi_credit_note",
                'record': credit_note_dian_template,
                'noupdate': True,
            }])
