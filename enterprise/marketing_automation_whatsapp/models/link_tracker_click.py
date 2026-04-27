from odoo import api, fields, models


class LinkTrackerClick(models.Model):
    _inherit = "link.tracker.click"

    whatsapp_message_id = fields.Many2one('whatsapp.message', string='Whatsapp Message', ondelete="set null")

    def _prepare_click_values_from_route(self, **route_values):
        click_values = super()._prepare_click_values_from_route(**route_values)

        if 'campaign_id' not in click_values and 'whatsapp_message_id' in route_values:
            wa_msg = self.env['whatsapp.message'].browse(route_values['whatsapp_message_id'])
            utm_campaign = wa_msg.marketing_trace_ids.activity_id.campaign_id.utm_campaign_id
            if utm_campaign:
                click_values['campaign_id'] = utm_campaign.id
        return click_values

    @api.model
    def add_click(self, code, **route_values):
        click = super().add_click(code, **route_values)

        if click and click.whatsapp_message_id:
            click.whatsapp_message_id.set_clicked()

        return click
