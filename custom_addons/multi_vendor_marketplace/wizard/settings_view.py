# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2024-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
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


class SettingsView(models.Model):
    """Set the settings for the seller payment  based on some parameters"""
    _name = 'settings.view'
    _description = "Settings View"

    commission = fields.Float(readonly=True, string="Commission",
                              help='Commission for sellers')
    amt_limit = fields.Integer(readonly=True, string="Amount Limit",
                               help='Amount Limit')
    minimum_gap = fields.Integer(readonly=True, help='Minimum gap for request',
                                 string="Minimum Gap For Request")
