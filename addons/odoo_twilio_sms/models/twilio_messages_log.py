from odoo import api, fields, models


class TwilioMessageLog(models.Model):
    _name = 'twilio.message.log'
    _rec_name = 'res_model'

    account_sid = fields.Char(string="Account SID")
    body = fields.Char(string="Body")
    date_sent = fields.Datetime(string="Date Sent")
    direction = fields.Char(string="Direction")
    error_code = fields.Char(string="Error Code")
    error_message = fields.Char(string="Error Message")
    from_phone = fields.Char(string="From")
    to_phone = fields.Char(string="To")
    messaging_service_sid = fields.Char(string="Message Service Id")
    sid = fields.Char(string="Sid")
    uri = fields.Char(string="URI")
    status = fields.Char(string="Status")
    res_model = fields.Char(string="Res Model")
    res_id = fields.Char(string="Res ID")
    is_reply_message = fields.Boolean(string="Is Reply Message", default=False)
    company_id = fields.Many2one("res.company","Company")
    user_id = fields.Many2one("res.users", "User")
    res_name = fields.Char("Res Name")
