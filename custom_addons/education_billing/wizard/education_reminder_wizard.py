# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class EducationReminderWizard(models.TransientModel):
    _name = 'education.reminder.wizard'
    _description = 'Wizard Kirim Reminder Tagihan'

    school_id = fields.Many2one(
        'education.school',
        string='Sekolah / Kampus',
        required=True
    )
    class_id = fields.Many2one(
        'education.class',
        string='Kelas (Opsional)',
        domain="[('school_id', '=', school_id)]"
    )
    bill_ids = fields.Many2many(
        'education.bill',
        string='Daftar Tagihan yang Diingatkan'
    )
    reminder_channel = fields.Selection([
        ('chatter', 'Internal Chatter & Email Log'),
        ('whatsapp', 'Kompilasi Link WhatsApp'),
    ], string='Metode Reminder', default='chatter', required=True)

    @api.onchange('school_id', 'class_id')
    def _onchange_filter_bills(self):
        domain = [
            ('state', 'in', ('unpaid', 'waiting_verification', 'rejected')),
        ]
        if self.school_id:
            domain.append(('school_id', '=', self.school_id.id))
        if self.class_id:
            domain.append(('class_id', '=', self.class_id.id))
        self.bill_ids = self.env['education.bill'].search(domain)

    def action_send_reminders(self):
        self.ensure_one()
        if not self.bill_ids:
            raise UserError(_('Tidak ada tagihan yang dipilih untuk dikirimkan reminder.'))

        count = 0
        for bill in self.bill_ids:
            if self.reminder_channel == 'chatter':
                bill.action_send_email_reminder()
                count += 1
            elif self.reminder_channel == 'whatsapp':
                # Update stats & log
                bill.write({
                    'reminder_count': bill.reminder_count + 1,
                    'last_reminder_date': fields.Datetime.now(),
                })
                parent = bill.parent_id
                phone = parent.get_clean_whatsapp_number() if parent else ''
                bill.message_post(body=_("Reminder disiapkan untuk nomor WhatsApp Orang Tua: %s") % (phone or '-'))
                count += 1

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Reminder Berhasil Diproses'),
                'message': _('Reminder telah dikirimkan untuk %d tagihan.') % count,
                'sticky': False,
                'type': 'success',
            }
        }
