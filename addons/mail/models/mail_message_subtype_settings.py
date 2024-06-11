from odoo import fields, models


class MailMessageSubtypeSettings(models.Model):
    _name = 'mail.message.subtype.settings'
    _description = 'Message subtype settings'
    _rec_name = 'partner_id'

    res_model_id = fields.Many2one(
        'ir.model', string='Model', required=True, ondelete='cascade', index=True)
    partner_id = fields.Many2one(
        'res.partner', string='Related Partner', index=True, ondelete='cascade', required=True)
    subtype_ids = fields.Many2many(
        'mail.message.subtype', string='Subtype',
        help="Message subtypes followed, meaning subtypes that will be pushed onto the user's Wall.")

    def set_mail_message_subtype_settings(self, partner_id, thread_model, subtype_ids):
        res_model_id = self.env["ir.model"]._get_id(thread_model)
        record = self.search([
            ("res_model_id", "=", res_model_id),
            ("partner_id", "=", partner_id),
        ])
        if not record:
            record = self.create({
                "res_model_id": res_model_id,
                "partner_id": partner_id,
            })
        record.subtype_ids = subtype_ids
        return True
