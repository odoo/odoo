from odoo import models


class SnailmailLetter(models.Model):
    _inherit = 'snailmail.letter'

    def _generate_report_pdf(self, report):
        followup_report = self.env.ref('account_followup.action_report_followup', raise_if_not_found=False)
        if not followup_report or report != followup_report:
            return super()._generate_report_pdf(report)
        partner = self.env['res.partner'].browse(self.res_id)
        options = self.env.context.get('followup_options')
        return partner.with_context(snailmail_layout=not self.cover)._get_followup_report_pdf(options)
