# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, modules, _


class ResPartner(models.Model):
    _inherit = "res.partner"

    date_localization = fields.Date(string='Geolocation Updated On')
    should_be_geolocalized = fields.Boolean(
        compute='_compute_should_be_geolocalized', store=True, readonly=False, default=False,
        help='Indicates whether the partner\'s address has changed, so we should geolocalize them from their new address.')

    @api.depends(lambda self: self._display_address_depends())
    def _compute_should_be_geolocalized(self):
        for partner in self:
            partner.should_be_geolocalized = partner.should_be_geolocalized or bool(partner._is_geolocalized())

    def _is_geolocalized(self):
        self.ensure_one()
        return super()._is_geolocalized() and not self.should_be_geolocalized

    @api.model
    def _geo_localize(self, street='', zip='', city='', state='', country=''):
        geo_obj = self.env['base.geocoder']
        search = geo_obj.geo_query_address(street=street, zip=zip, city=city, state=state, country=country)
        result = geo_obj.geo_find(search, force_country=country)
        if result is None:
            search = geo_obj.geo_query_address(city=city, state=state, country=country)
            result = geo_obj.geo_find(search, force_country=country)
        return result

    def geo_localize(self):
        # We need country names in English below
        if not self.env.context.get('force_geo_localize') and (
            self.env.context.get('import_file')
            or modules.module.current_test
            or not self.env.registry.ready
            or self.env.context.get('install_demo')
        ):
            return False
        partners_not_geo_localized = self.env['res.partner']
        for partner in self.with_context(lang='en_US'):
            result = partner._geo_localize(
                partner.street,
                partner.zip,
                partner.city,
                partner.state_id.name,
                partner.country_id.name,
            )

            if result:
                partner.write({
                    'partner_latitude': result[0],
                    'partner_longitude': result[1],
                    'date_localization': fields.Date.context_today(partner),
                    'should_be_geolocalized': False,
                })
            else:
                partners_not_geo_localized |= partner
        if partners_not_geo_localized and not self.env.context.get('cron_id'):
            self.env.user._bus_send("simple_notification", {
                'type': 'danger',
                'title': _("Warning"),
                'message': _('No match found for %(partner_names)s address(es).',
                             partner_names=', '.join(partners_not_geo_localized.mapped('display_name')))
            })
        return True

    def write(self, vals):
        res = super().write(vals)
        if (
            (vals.keys() & self._display_address_depends())
            and self.filtered('should_be_geolocalized')
            and (geo_localize_cron := self.env.ref('base_geolocalize.ir_cron_geolocalize_required_partners', raise_if_not_found=False))
        ):
            geo_localize_cron._trigger()
        return res

    def _cron_geolocalize(self, batch_size=20):
        domain = [('should_be_geolocalized', '=', True)]
        partners_to_geolocalize = self.search(domain, limit=batch_size)
        remaining = len(partners_to_geolocalize) if len(partners_to_geolocalize) < batch_size else self.search_count(domain)
        self.env['ir.cron']._commit_progress(remaining=remaining)
        for partner in partners_to_geolocalize:
            partner.geo_localize()
            self.env['ir.cron']._commit_progress(1)
