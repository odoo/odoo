# -*- coding: utf-8 -*-
################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2026-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: Cybrosys Technologies (<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (AGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (AGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (AGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
################################################################################
from odoo import fields, models


class CampaignSmartButton(models.Model):
    """Extends the UTM Campaign model with a Smart Button to calculate and
    display the Win Loss Ratio."""
    _inherit = 'utm.campaign'

    total_ratio = fields.Float(compute='_compute_ratio',
                               help="Total lead ratio")

    def get_ratio(self):
        """Open the Win Loss Ratio window upon clicking the Smart Button.
       Returns:
           dict: A dictionary specifying the action to be taken upon button
           click."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Win Loss Ratio',
            'view_mode': 'kanban',
            'res_model': 'crm.lead',
            'domain': [['user_id', '=', self.env.uid], "|",
                       "&", ["active", "=", True], ["probability", '=', 100],
                       "&", ["active", "=", False], ["probability", '=', 0]
                       ],
            'context': "{'create': False,'records_draggable': False}"
        }

    def _compute_ratio(self):
        """Compute the Win Loss Ratio based on CRM lead statistics."""
        total_won = self.env['crm.lead'].search_count(
            [('active', '=', True), ('probability', '=', 100),
             ('user_id', '=', self.env.uid)])
        total_lose = self.env['crm.lead'].search_count(
            [('active', '=', False), ('probability', '=', 0),
             ('user_id', '=', self.env.uid)])

        if total_lose == 0:
            ratio = 0
        else:
            ratio = round(total_won / total_lose, 2)
        self.total_ratio = ratio
