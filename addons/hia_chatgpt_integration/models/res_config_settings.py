from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def _get_default_chatgpt_model(self):
        return self.env.ref('hia_chatgpt_integration.chatgpt_model_gpt_3_5_turbo').id

    def _get_default_chatgpt_tempreture(self):
        return self.env.ref('hia_chatgpt_integration.chatgpt_tempreture_6').id

    openapi_api_key = fields.Char(string="API Key", help="Provide the API key here", config_parameter="hia_chatgpt_integration.openapi_api_key", required=True)
    chatgpt_model_id = fields.Many2one('chatgpt.model', 'ChatGPT Model', ondelete='cascade', default=_get_default_chatgpt_model,  config_parameter="hia_chatgpt_integration.chatgpt_model_id")
    tempreture_id = fields.Many2one('chatgpt.tempreture', 'ChatGPT Tempreture', ondelete='cascade', default=_get_default_chatgpt_tempreture, config_parameter="hia_chatgpt_integration.tempreture_id")