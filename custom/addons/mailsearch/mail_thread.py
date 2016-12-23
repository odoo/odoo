from openerp import models, fields, api, tools, _

class search_mail_thread(models.Model):
    _description = "message search"
    _inherit = 'mail.thread'
    _name = 'mail.thread'

    message_search = fields.Html(string="search message html", related='message_ids.body', select=True)