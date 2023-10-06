from odoo import api, models


class BaseModel(models.AbstractModel):
    _inherit = 'base'

    @api.model
    def _marketing_card_allowed_field_paths(self) -> list[str]:
        """List of fields allowed to be accessed in template rendering."""
        allowed_fields_dict = {
            'res.partner': [
                'display_name', 'name',
                'email', 'mobile', 'phone',
                'country_id', 'country_id.display_name', 'country_id.name',
                'image_128', 'image_256', 'image_512', 'image_1024',
            ],

        }
        allowed_fields_dict['event.track'] = [
            'display_name', 'name',
            'event_id', 'event_id.name', 'event_id.display_name',
            'image', 'partner_id',
            'location_id', 'location_id.name', 'location_id.display_name',
            'date', 'date_end',
            'event_id', 'event_id.name', 'event_id.display_name'
        ] + [f'partner_id.{partner_path}' for partner_path in allowed_fields_dict['res.partner']]
        allowed_fields_dict['event.booth'] = [
            'display_name', 'name',
            'event_id', 'event_id.name', 'event_id.display_name', 'event_id.address_inline',
            'event_id.date_begin', 'event_id.date_end', 'event_id.date_tz',
            'contact_name', 'contact_email', 'contact_phone',
            'sponsor_name', 'sponsor_email', 'sponsor_mobile', 'sponsor_phone', 'sponsor_subtitle', 'sponsor_image_512',
        ]
        return allowed_fields_dict.get(self._name, [])
