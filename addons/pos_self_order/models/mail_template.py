from odoo import _, api, models

class MailTemplate(models.Model):
    _name = 'mail.template'
    _inherit = ['mail.template', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('id', 'in', [preset['mail_template_id'] for preset in data['pos.preset']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id']
