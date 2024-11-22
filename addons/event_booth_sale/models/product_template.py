from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    service_tracking = fields.Selection(selection_add=[
        ('event_booth', 'Event Booth'),
    ], ondelete={'event_booth': 'set default'})

    def _prepare_service_tracking_tooltip(self):
        if self.service_tracking == 'event_booth':
            return _("Mark the selected Booth as Unavailable.")
        return super()._prepare_service_tracking_tooltip()

    @api.onchange('service_tracking')
    def _onchange_type_event_booth(self):
        if self.service_tracking == 'event_booth':
            self.invoice_policy = 'order'

    def _service_tracking_blacklist(self):
        return super()._service_tracking_blacklist() + ['event_booth']

    @api.constrains('service_tracking')
    def _check_service_tracking_for_event_booths(self):
        """ Prevent changing the service_tracking field if the product template or any of its variants
        is linked to an Event Booth Category.
        """
        if product_variants_not_event_booth := self.product_variant_ids.filtered(lambda p: p.service_tracking != 'event_booth'):
            linked_booth_category = self.env['event.booth.category'].sudo().search([
                ('product_id', 'in', product_variants_not_event_booth.ids)
            ], limit=1)
            if linked_booth_category:
                raise ValidationError(
                    _(
                        'The "service_tracking" for the product template, %(product_template_name)s cannot be changed because '
                        'one of its variants is assigned to the Event Booth Category, %(event_booth_category_name)s. '
                        'The service_tracking must remain "Event Booth".',
                        product_template_name=linked_booth_category.product_id.name,
                        event_booth_category_name=linked_booth_category.name,
                    )
                )
