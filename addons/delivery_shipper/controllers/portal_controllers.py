from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.http import request, route


class CustomCustomerPortal(CustomerPortal):

    def _get_mandatory_fields(self):
        mandatory_fields = super()._get_mandatory_fields()
        return mandatory_fields + ['city_id', 'district_id', 'area_id']

    @route('/get_areas', type='json', auth='user', csrf=False)
    def get_areas(self, district_id):
        areas = request.env['area'].sudo().search_read(
            [('district_id', '=', int(district_id))], ['id', 'name']
        )
        return areas

    @route(['/my/account'], type='http', auth='user', website=True)
    def account(self, redirect=None, **post):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        values.update({
            'error': {},
            'error_message': [],
        })

        if post and request.httprequest.method == 'POST':
            if not partner.can_edit_vat():
                post['country_id'] = str(partner.country_id.id)

            error, error_message = self.details_form_validate(post)
            values.update({'error': error, 'error_message': error_message})
            values.update(post)
            if not error:
                values = {key: post[key] for key in self._get_mandatory_fields()}
                values.update({key: post[key] for key in self._get_optional_fields() if key in post})
                for field in set(['country_id', 'state_id', 'city_id', 'district_id', 'area_id']) & set(values.keys()):
                    try:
                        values[field] = int(values[field])
                    except:
                        values[field] = False
                values.update({'zip': values.pop('zipcode', '')})
                self.on_account_update(values, partner)
                partner.sudo().write(values)
                if redirect:
                    return request.redirect(redirect)
                return request.redirect('/my/home')

        countries = request.env['res.country'].sudo().search([])
        states = request.env['res.country.state'].sudo().search([])
        cities = request.env['res.city'].sudo().search([])
        districts = request.env['district'].sudo().search([])
        areas = []

        values.update({
            'partner': partner,
            'countries': countries,
            'cities': cities,
            'states': states,
            'districts': districts,
            'areas': areas,
            'has_check_vat': hasattr(request.env['res.partner'], 'check_vat'),
            'partner_can_edit_vat': partner.can_edit_vat(),
            'redirect': redirect,
            'page_name': 'my_details',
        })

        response = request.render("portal.portal_my_details", values)
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
        return response
