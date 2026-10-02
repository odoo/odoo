# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import fields, models


class SaleReport(models.Model):
    """This class is for displaying margin information in pivot view of
    sales."""
    _inherit = 'sale.report'

    margin_sale = fields.Float(string='Margin Total', help='Displays margin '
                                                           'in sales')

    def _select_sale(self):
        """Method to view field in pivot view of sale report."""
        return super(SaleReport, self)._select_sale() + \
            ", SUM(l.margin_amount_sale / CASE COALESCE(s.currency_rate, " \
            "0) WHEN 0 THEN 1.0 ELSE s.currency_rate END) AS margin_sale"
