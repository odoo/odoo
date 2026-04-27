from odoo import models, _


class WebsiteSnippetFilter(models.Model):
    _inherit = 'website.snippet.filter'

    def _get_hardcoded_sample(self, model):
        if model._name != 'appointment.type':
            return super()._get_hardcoded_sample(model)

        return [{
            'message_intro': _("A first step in joining our team as a technical consultant."),
            'name': _('Candidate Interview'),
        }, {
            'name': _('Online Cooking Lesson'),
        }, {
            'name': _('Tennis Court'),
        }]
