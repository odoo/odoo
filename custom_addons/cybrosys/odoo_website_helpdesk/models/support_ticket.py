# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Arshad Ali Pottengal (<https://www.cybrosys.com>)
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
################################################################################
from odoo import fields, models


class SupportTicket(models.Model):
    """Creating onetoMany model"""
    _name = 'support.ticket'
    _description = 'Support Tickets'

    subject = fields.Char(string='Subject', help='Subject of the merged '
                                                 'tickets.')
    display_name = fields.Char(string='Display Name',
                               help='Display name of the merged tickets.')
    description = fields.Char(string='Description',
                              help='Description of the tickets.')
    support_ticket_id = fields.Many2one('merge.ticket',
                                        string='Support Tickets',
                                        help='Support tickets')
    merged_ticket = fields.Integer(string='Merged Ticket ID',
                                   help='Storing merged ticket id')
