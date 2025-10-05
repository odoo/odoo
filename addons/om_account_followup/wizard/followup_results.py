from odoo import api, fields, models, _


class FollowupSendingResults(models.TransientModel):
    _name = 'followup.sending.results'
    _description = 'Results from the sending of the different letters and emails'

    def do_report(self):
        return self.env.context.get('report_data')

    def do_done(self):
        return {}

    def _get_description(self):
        return self.env.context.get('description')

    def _get_need_printing(self):
        return self.env.context.get('needprinting')

    description = fields.Html("Description", readonly=True, default=_get_description)
    needprinting = fields.Boolean("Needs Printing", default=_get_need_printing)
