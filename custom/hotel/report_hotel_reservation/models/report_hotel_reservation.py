# -*- coding: utf-8 -*-
# See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ReportHotelReservationStatus(models.Model):

    _name = "report.hotel.reservation.status"
    _description = "Booking By State"
    _auto = False

    reservation_no = fields.Char('Booking No', size=64, readonly=True)
    nbr = fields.Integer('Booking', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirm'),
                              ('done', 'Done')], 'State', size=16,
                             readonly=True)

    def init(self):
        """
        This method is for initialization for report hotel reservation
        status Module.
        @param self: The object pointer
        @param cr: database cursor
        """
        self.env.cr.execute("""
            create or replace view report_hotel_reservation_status as (
                select
                    min(c.id) as id,
                    c.reservation_no,
                    c.state,
                    count(*) as nbr
                from
                    hotel_reservation c
                group by c.state,c.reservation_no
            )""")
