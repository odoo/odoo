# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from markupsafe import Markup


class L10nAuSTPSubmit(models.TransientModel):
    _name = "l10n_au.stp.submit"
    _description = "Submit STP Report"

    l10n_au_stp_id = fields.Many2one(
        'l10n_au.stp', string='STP Report', required=True)
    stp_terms = fields.Boolean(
        string="I have read and accepted the T&C above, and "
        "I authorise Odoo to send compliant payroll data to the ATO on my behalf.",
        default=False)
    terms_header = fields.Html(compute="_compute_terms")
    terms = fields.Html(compute="_compute_terms")

    @api.depends('l10n_au_stp_id')
    def _compute_terms(self):
        self.terms_header = Markup("<strong>A pay run cannot be reverted for corrections once filed through STP. Please read the following terms and conditions before proceeding.</strong>")
        for rec in self:
            company = self.l10n_au_stp_id.company_id
            company.ensure_one()
            terms = Markup("""
<ul>
    <li class="p-2">
        <b>{company_name}</b> authorised me, <b>{user_name}</b>, to submit confidential payroll information to the ATO via STP.
    </p>
    <li class="p-2">
        I fully understand the information to be submitted to the ATO, and I am aware of the company's payroll
        obligations. All payslips have been thoroughly reviewed, and I confirm that all data is true and correct.
    </p>
    <li class="p-2">
        I have read, understood and accepted the
        <a href="https://www.sbr.gov.au/sbr-products-register/sbr-end-user-agreement" target="_blank">
            SBR end user agreement.
        </a>
    </li>
    <li class="p-2">
        I understand that while Odoo is a tool that can be used for Australian companies to be compliant with
        STP Phase 2 and SuperStream obligations, Odoo AU Pty Ltd does not provide agent services nor business advice.
        <b>{company_name}</b> remains responsible for correctly entering, reviewing and validating payroll and superannuation-related data.
    </li>
</ul>
            """).format(company_name=rec.l10n_au_stp_id.company_id.name, user_name=rec.env.user.name)
            rec.terms = terms

    def action_submit(self):
        if not self.stp_terms:
            raise ValidationError(_("You need to accept the terms and conditions to submit the STP report."))
        self.l10n_au_stp_id.submit()

        self.l10n_au_stp_id.message_post(body=self._fields['stp_terms'].string + "\n" + self.terms)
        return {'type': 'ir.actions.act_window_close'}
