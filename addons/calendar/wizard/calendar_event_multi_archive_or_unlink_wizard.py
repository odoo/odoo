from odoo import fields, models


class CalendarEventMultiArchiveOrUnlinkWizard(models.TransientModel):
    _name = 'calendar.event.multi.archive.or.unlink.wizard'
    _description = 'Calendar Event Multi Archive Or Unlink Wizard'

    def _default_archive_or_unlink_wizard_ids(self):
        event_ids = self.env.context.get('active_model') == 'calendar.event' and self.env.context.get('active_ids') or []
        return [fields.Command.create({'calendar_event_id': event_id}) for event_id in event_ids]

    archive_or_unlink_wizard_ids = fields.One2many('calendar.event.archive.or.unlink.wizard', 'multi_archive_or_unlink_wizard_id', default=_default_archive_or_unlink_wizard_ids)
    is_user_admin = fields.Boolean(compute="_compute_is_user_admin")
    requested_action = fields.Selection([('archive', 'archive'), ('unlink', 'delete')], default='archive', required=True)

    def _compute_is_user_admin(self):
        for wizard in self:
            wizard.is_user_admin = self.env.user._is_admin()

    def action_archive(self):
        self.archive_or_unlink_wizard_ids.calendar_event_id.with_context(disable_auto_send_cancellation_emails=True).write({'active': False})
        return self.env.context.get('next_action')

    def action_unlink(self):
        self.archive_or_unlink_wizard_ids.calendar_event_id._action_unlink()
        return self.env.context.get('next_action')

    def action_send_mails(self):
        now = fields.Datetime.now()
        self.env['mail.mail'].sudo().create([
            wizard._prepare_mail_values() for wizard in self.archive_or_unlink_wizard_ids
            if wizard.calendar_event_id.partner_ids != self.env.user.partner_id
               and wizard.calendar_event_id.start > now
               and not wizard.calendar_event_id.is_draft
        ]).send_after_commit()

    def action_send_mails_and_archive(self):
        self.action_send_mails()
        return self.action_archive()

    def action_send_mails_and_unlink(self):
        self.action_send_mails()
        return self.action_unlink()
