from odoo import fields, models


class WebsiteLLMs(models.TransientModel):
    _name = 'website.llms'
    _description = "LLMs.txt Editor"
    _inherit = ['website.multi.mixin']

    content = fields.Text(related='website_id.llms_txt', readonly=False)

    def action_save(self):
        return {'type': 'ir.actions.act_window_close'}
