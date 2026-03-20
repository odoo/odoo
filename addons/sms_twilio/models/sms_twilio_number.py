from odoo import models, fields


class SmsTwilioNumber(models.Model):
    _name = 'sms.twilio.number'
    _description = 'Twilio Number'
    _order = 'sequence, id'

    company_id = fields.Many2one(
        'res.company', string='Company',
        required=True, ondelete='cascade', index='btree',
        default=lambda self: self.env.company)
    sequence = fields.Integer(default=1)
    number = fields.Char(string='Twilio Number', required=True)
    country_id = fields.Many2one("res.country", string='Country', required=True)
    country_code = fields.Char(related='country_id.code', string='Country Code')

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{record.number} ({record.country_id.name})"
