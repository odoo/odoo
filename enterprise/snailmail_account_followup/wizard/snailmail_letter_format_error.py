from odoo import _, models


class SnailmailLetterFormatError(models.TransientModel):
    _inherit = 'snailmail.letter.format.error'

    def _resend_letters(self, letters_to_resend):
        # The follow-up report can not be regenerated correctly because it requires special
        # follow-up specific `options` that are lost after the initial PDF generation for the letter.
        # We cancel the letters and display an error notification instead indicating that the followup
        # has to be done again manually.
        followup_report = self.env.ref('account_followup.action_report_followup')
        followup_letters = letters_to_resend.filtered(lambda l: l.report_template == followup_report)

        super()._resend_letters(letters_to_resend - followup_letters)

        if followup_letters:
            followup_letters.cancel()
            self.env['bus.bus']._sendone(self.env.user.partner_id, 'simple_notification', {
                'type': 'danger',
                'message': _("Payment reminders / follow-ups can not be updated and resent this way. They have to be sent again in the same way as they were originally sent."),
            })
