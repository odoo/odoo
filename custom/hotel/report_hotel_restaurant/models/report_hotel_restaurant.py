# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportHotelRestaurantStatus(models.Model):
    _name = "report.hotel.restaurant.status"
    _description = "Booking By State"
    _auto = False

    reservation_id = fields.Char('Booking No', size=64, readonly=True)
    nbr = fields.Integer('Reservatioorder_datan', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('done', 'Done')], 'State', size=16,
                             readonly=True)

    def init(self):
        """
        This method is for initialization for report hotel restaurant
        status Module.
        @param self: The object pointer
        @param cr: database cursor
        """
        self.env.cr.execute("""
            create or replace view report_hotel_restaurant_status as (
                select
                    min(c.id) as id,
                    c.reservation_id,
                    c.state,
                    count(*) as nbr
                from
                    hotel_restaurant_reservation c
                group by c.state,c.reservation_id
            )""")
