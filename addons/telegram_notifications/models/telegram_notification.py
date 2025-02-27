from odoo import models, fields

class TelegramNotification(models.Model):
    _inherit = 'mail.message'

    def _notify_by_telegram(self):
        """Send notification via Telegram instead of email."""
        bot = self.env['telegram.bot'].search([], limit=1)
        if bot:
            for recipient in self.partner_ids:
                chat_id = recipient.telegram_chat_id
                if chat_id:
                    bot.send_telegram_message(chat_id, self.body)