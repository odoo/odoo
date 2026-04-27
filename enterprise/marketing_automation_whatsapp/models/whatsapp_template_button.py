from odoo import models, fields


class WhatsAppTemplateButton(models.Model):
    _inherit = 'whatsapp.template.button'

    url_type = fields.Selection(selection_add=[
        ('tracked', 'Tracked'),
    ])

    def _filter_dynamic_buttons(self):
        """
        'tracked' button type is similar to dynamic one, therefore every time
        we retrieve 'dynamic' buttons we should also do the same for 'tracked' ones.
        """
        super_urls = super()._filter_dynamic_buttons()
        tracked_urls = self.filtered(lambda button: button.button_type == 'url' and button.url_type == 'tracked')
        return super_urls + tracked_urls
