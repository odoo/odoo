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
from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    """Inheriting the res config settings model"""
    _inherit = 'res.config.settings'

    show_create_task = fields.Boolean(string="Create Tasks",
                                      config_parameter='odoo_website_helpdesk.show_create_task',
                                      help='Enable this option to allow users'
                                           'to create tasks directly from the '
                                           'helpdesk module. When activated, users '
                                           'will have the ability to generate and '
                                           'assign tasks as part of their workflow '
                                           'within the helpdesk interface.')
    show_category = fields.Boolean(string="Category",
                                   config_parameter='odoo_website_helpdesk.show_category',
                                   help='Enable this option to display the '
                                        'category field in the helpdesk tickets. '
                                        'This can be useful for organizing and '
                                        'filtering tickets based on their category.',
                                   implied_group='odoo_website_helpdesk.group_show_category')
    product_website = fields.Boolean(string="Product On Website",
                                     config_parameter='odoo_website_helpdesk.product_website',
                                     help='Product on website')
    auto_close_ticket = fields.Boolean(string="Auto Close Ticket",
                                       config_parameter='odoo_website_helpdesk.auto_close_ticket',
                                       help='Auto Close ticket')
    no_of_days = fields.Integer(string="No Of Days",
                                config_parameter='odoo_website_helpdesk.no_of_days',
                                help='No of Days')
    closed_stage_id = fields.Many2one(
        'ticket.stage', string='Closing stage',
        help='Closing Stage of the ticket.',
        config_parameter='odoo_website_helpdesk.closed_stage_id')

    reply_template_id = fields.Many2one('mail.template',
                                        domain="[('model', '=', 'ticket.helpdesk')]",
                                        config_parameter='odoo_website_helpdesk.reply_template_id',
                                        help='Reply Template of the helpdesk'
                                             ' ticket.')
    helpdesk_menu_show = fields.Boolean('Helpdesk Menu',
                                        config_parameter=
                                        'odoo_website_helpdesk.helpdesk_menu_show',
                                        help='Helpdesk menu')

    def set_values(self):
        """Override to handle category group assignment"""
        super(ResConfigSettings, self).set_values()
        # Handle show_category group assignment
        group_category = self.env.ref('odoo_website_helpdesk.group_show_category', raise_if_not_found=False)
        if group_category:
            if self.show_category:
                # Add current user to the category group
                group_category.write({'user_ids': [(4, self.env.user.id)]})
            else:
                # Remove current user from the category group
                group_category.write({'user_ids': [(3, self.env.user.id)]})

    @api.onchange('closed_stage_id')
    def _onchange_closed_stage_id(self):
        """Closing stage function"""
        if self.closed_stage_id:
            stage = self.closed_stage_id.id
            in_stage = self.env['ticket.stage'].search([('id', '=', stage)])
            not_in_stage = self.env['ticket.stage'].search(
                [('id', '!=', stage)])
            in_stage.closing_stage = True
            for each in not_in_stage:
                each.closing_stage = False