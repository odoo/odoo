from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    kw_api_token_length = fields.Integer(
        string='Token length', config_parameter='kw_api.kw_api_token_length',
        default=40, )
    kw_api_token_prefix = fields.Char(
        string='Token prefix', config_parameter='kw_api.kw_api_token_prefix',
        default='access_token_')
    kw_api_token_expire_hours = fields.Integer(
        string='Token expire after (hours)', default=24,
        config_parameter='kw_api.kw_api_token_expire_hours', )
    kw_api_refresh_token_expire_hours = fields.Integer(
        string='Refresh token expire after (hours)', default=720,
        config_parameter='kw_api.kw_api_refresh_token_expire_hours', )
    kw_api_first_page_number = fields.Integer(
        string='First page number', default=0,
        config_parameter='kw_api.kw_api_first_page_number', )
    kw_api_ensure_ascii = fields.Boolean(
        string='API JSON ensure_ascii',
        config_parameter='kw_api.kw_api_ensure_ascii', )
    kw_api_update_lang_from_header = fields.Boolean(
        string='Update lang from header',
        config_parameter='kw_api.kw_api_update_lang_from_header', )
    kw_api_update_lang_param_name = fields.Char(
        string='Language (locale) param name', default='Accept-Language',
        config_parameter='kw_api.kw_api_update_lang_param_name', )
    kw_api_one_token_per_user = fields.Boolean(
        string='One token per user',
        config_parameter='kw_api.kw_api_one_token_per_user', )
    kw_api_user_result_wrapper = fields.Boolean(
        string='Use result wrapper',
        config_parameter='kw_api.kw_api_user_result_wrapper', )
    kw_api_use_false_if_empty = fields.Boolean(
        string='Use False if empty',
        config_parameter='kw_api.kw_api_use_false_if_empty', )
    kw_api_key_attachment_required = fields.Boolean(
        string='Api-Key Attachment Required',
        config_parameter='kw_api.kw_api_key_attachment_required', )
    kw_api_is_log_enabled = fields.Boolean(
        string='Use API log',
        config_parameter='kw_api.kw_api_is_log_enabled', )
    kw_api_log_storage_days = fields.Integer(
        default=1, string='API log storage days',
        config_parameter='kw_api.kw_api_log_storage_days', )
    kw_api_text_log_limit = fields.Integer(
        default=100, string='Limit for log text fields, Kb',
        config_parameter='kw_api.kw_api_text_log_limit',
        help='If data bigger then limit, it will stored to file', )
