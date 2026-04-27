# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields


def _convert_rental_dates(kwargs):
    kwargs.update({
        'start_date': fields.Datetime.to_datetime(kwargs.get('start_date')),
        'end_date': fields.Datetime.to_datetime(kwargs.get('end_date')),
    })
