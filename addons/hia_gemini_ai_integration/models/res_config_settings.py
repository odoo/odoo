from odoo import models,api, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    def _get_default_gemini_model(self):
        return self.env.ref('hia_gemini_ai_integration.gemini-pro-vision').id

    gemini_api_key = fields.Char(
        string="Gemini API key",
        help="Provide Gemini API Key here",
        config_parameter="hia_gemini_ai_integration.gemini_api_key",
        
    )
    
    gemini_model_id = fields.Many2one(
        'gemini.model',
        'Gemini Model',
        ondelete='cascade',
        default=_get_default_gemini_model,
        config_parameter="hia_gemini_ai_integration.gemini_model"
    )

    model_support = fields.Char(
        string="Model Support",
        compute="_compute_model_support",
        help="""Description of the selected Gemini model based on the model ID:
        - gemini-pro: Only Text
        - gemini-pro-vision: Image and Text Both Expected
        - gemini-1-5-pro: Image or Text Expected
        - gemini-1-5-flash: Image or Text Expected""")

    @api.depends('gemini_model_id')
    def _compute_model_support(self):
        for record in self:
            if record.gemini_model_id.id == 1:
                record.model_support = "Only Text"
            elif record.gemini_model_id.id == 2:
                record.model_support = "Image and Text Both Expect"
            elif record.gemini_model_id.id == 3:
                record.model_support = "Image or Text Expect"
            elif record.gemini_model_id.id == 4:
                record.model_support = "Image or Text Expect"
            else:
                record.model_support = "Unknown Model"