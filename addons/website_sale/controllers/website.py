# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.exceptions import ValidationError
from odoo.http import request, route

from odoo.addons.base.models.ir_qweb_fields import nl2br_enclose
from odoo.addons.website.controllers import main
from odoo.addons.website.controllers.form import WebsiteForm


class WebsiteSaleForm(WebsiteForm):

    @route('/website/form/shop.sale.order', type='http', auth="public", methods=['POST'], website=True)
    def website_form_saleorder(self, **kwargs):
        model_record = request.env.ref('sale.model_sale_order')
        try:
            data = self.extract_data(model_record, kwargs)
        except ValidationError as e:
            return json.dumps({'error_fields': e.args[0]})

        order = request.website.sale_get_order()
        if not order:
            return json.dumps({'error': "No order found; please add a product to your cart."})

        if data['record']:
            order.write(data['record'])

        if data['custom']:
            order._message_log(
                body=nl2br_enclose(data['custom'], 'p'),
                message_type='comment',
            )

        if data['attachments']:
            self.insert_attachment(model_record, order.id, data['attachments'])

        return json.dumps({'id': order.id})


class Website(main.Website):

    def _login_redirect(self, uid, redirect=None):
        # If we are logging in, clear the current pricelist to be able to find
        # the pricelist that corresponds to the user afterwards.
        request.session.pop('website_sale_current_pl', None)
        request.session.pop('website_sale_selected_pl_id', None)
        return super()._login_redirect(uid, redirect=redirect)

    @route()
    def autocomplete(self, search_type=None, term=None, order=None, limit=5, max_nb_chars=999, options=None):
        options = options or {}
        if 'display_currency' not in options:
            options['display_currency'] = request.website.currency_id
        return super().autocomplete(search_type, term, order, limit, max_nb_chars, options)

    @route()
    def theme_customize_data(self, is_view_data, enable=None, disable=None, reset_view_arch=False):
        super().theme_customize_data(is_view_data, enable, disable, reset_view_arch)
        if any(key in enable or key in disable for key in ['website_sale.products_list_view', 'website_sale.add_grid_or_list_option']):
            request.session.pop('website_sale_shop_layout_mode', None)

    @route()
    def get_current_currency(self, **kwargs):
        return {
            'id': request.website.currency_id.id,
            'symbol': request.website.currency_id.symbol,
            'position': request.website.currency_id.position,
        }

    @route()
    def change_lang(self, lang, **kwargs):
        order_sudo = request.website.sale_get_order()
        request.env.add_to_compute(
            order_sudo.order_line._fields['name'],
            order_sudo.order_line.with_context(lang=lang),
        )
        return super().change_lang(lang, **kwargs)
