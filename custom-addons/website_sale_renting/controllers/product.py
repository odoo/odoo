# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request
from odoo import fields, http

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleRenting(WebsiteSale):

    @http.route()
    def cart_update(self, *args, start_date=None, end_date=None, **kw):
        """ Override to parse to datetime optional pickup and return dates.
        """
        start_date = fields.Datetime.to_datetime(start_date)
        end_date = fields.Datetime.to_datetime(end_date)
        return super().cart_update(*args, start_date=start_date, end_date=end_date, **kw)

    @http.route()
    def cart_update_json(self, *args, start_date=None, end_date=None, **kwargs):
        """ Override to parse to datetime optional pickup and return dates.
        """
        start_date = fields.Datetime.to_datetime(start_date)
        end_date = fields.Datetime.to_datetime(end_date)
        return super().cart_update_json(
            *args, start_date=start_date, end_date=end_date, **kwargs
        )

    @http.route(
        '/rental/product/constraints', type='json', auth="public", methods=['POST'], website=True
    )
    def renting_product_constraints(self):
        """ Return rental product constraints.

        Constraints are the days of the week where no pickup nor return can be processed and the
        minimal time of a rental.

        :rtype: dict
        """
        weekdays = request.env.company._get_renting_forbidden_days()
        return {
            'renting_unavailabity_days': {day: day in weekdays for day in range(1, 8)},
            'renting_minimal_time': {
                'duration': request.env.company.renting_minimal_time_duration,
                'unit': request.env.company.renting_minimal_time_unit,
            },
        }
