from odoo import fields, models


class WebsiteLLMs(models.TransientModel):
    _name = 'website.llms'
    _description = 'LLMs.txt Editor'

    content = fields.Text(default=lambda s: s.env['website'].get_current_website().llms_txt)

    def action_save(self):
        website = self.env['website'].get_current_website()
        website.llms_txt = self.content
        return {'type': 'ir.actions.act_window_close'}
