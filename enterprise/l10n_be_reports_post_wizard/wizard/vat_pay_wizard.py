# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, models, fields, _


class VATPayWizard(models.TransientModel):
    _name = 'l10n_be.vat.pay.wizard'
    _description = "Payment instructions for VAT"

    move_id = fields.Many2one(comodel_name='account.move')
    company_currency_id = fields.Many2one(related='move_id.company_currency_id')
    amount = fields.Monetary(currency_field='company_currency_id')
    partner_bank_id = fields.Many2one(comodel_name='res.partner.bank', compute='_compute_partner_bank_id')
    acc_number = fields.Char(string="IBAN", related='partner_bank_id.acc_number')
    partner_id = fields.Many2one(comodel_name='res.partner', related='partner_bank_id.partner_id')
    communication = fields.Char(compute='_compute_communication')
    qr_code = fields.Html(compute='_compute_qr_code')

    @api.depends('move_id')
    def _compute_communication(self):
        ''' Taken from https://finances.belgium.be/fr/communication-structuree
        '''
        for wizard in self:
            vat = (self.move_id.company_id.vat or self.env.company.vat or '').replace("BE", "")
            communication = ''
            if len(vat) == 10:
                number = int(vat)
                suffix = f"{number % 97 or 97:02}"
                communication = f"+++{vat[:3]}/{vat[3:7]}/{vat[7:]}{suffix}+++"
            wizard.communication = communication

    @api.depends('move_id')
    def _compute_partner_bank_id(self):
        fps_account = self.env.ref('l10n_be_reports_post_wizard.fps_vat_current_account', raise_if_not_found=False)
        self.partner_bank_id = fps_account or False

    @api.depends('move_id', 'communication', 'amount')
    def _compute_qr_code(self):
        for wizard in self:
            qr_html = False
            if wizard.partner_bank_id and wizard.amount and wizard.communication:
                b64_qr = wizard.partner_bank_id.build_qr_code_base64(
                    amount=wizard.amount,
                    free_communication=wizard.communication,
                    structured_communication=wizard.communication,
                    currency=wizard.company_currency_id or self.env.company.currency_id,
                    debtor_partner=wizard.partner_id,
                )
                if b64_qr:
                    txt = _('Scan me with your banking app.')
                    qr_html = Markup("""
                        <div class="text-center">
                            <img src="{b64_qr}"/>
                            <p><strong>{txt}</strong></p>
                        </div>
                    """).format(b64_qr=b64_qr, txt=txt)
            wizard.qr_code = qr_html

    def mark_paid(self):
        activity = self.move_id.activity_ids.filtered(lambda a: a.activity_type_id == self.env.ref('account_reports.mail_activity_type_tax_report_to_pay'))
        activity.action_done()
        return {'type': 'ir.actions.client', 'tag': 'soft_reload'}
