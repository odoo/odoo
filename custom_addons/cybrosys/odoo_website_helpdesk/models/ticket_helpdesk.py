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
import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

PRIORITIES = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
]
RATING = [
    ('0', 'Very Low'),
    ('1', 'Low'),
    ('2', 'Normal'),
    ('3', 'High'),
    ('4', 'Very High'),
    ('5', 'Extreme High')
]


class TicketHelpDesk(models.Model):
    """Help_ticket model"""
    _name = 'ticket.helpdesk'
    _description = 'Helpdesk Ticket'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _default_show_create_task(self):
        """Task creation"""
        return self.env['ir.config_parameter'].sudo().get_param(
            'odoo_website_helpdesk.show_create_task')

    def _default_show_category(self):
        """Show category default"""
        return self.env['ir.config_parameter'].sudo().get_param(
            'odoo_website_helpdesk.show_category')

    name = fields.Char('Name', default=lambda self: self.env['ir.sequence'].
                       next_by_code('ticket.helpdesk') or _('New'),
                       help='Ticket Name')
    customer_id = fields.Many2one('res.partner',
                                  string='Customer Name',
                                  help='Customer Name')
    customer_name = fields.Char('Customer Name', help='Customer Name')
    subject = fields.Text('Subject', required=True,
                          help='Subject of the Ticket')
    description = fields.Text('Description', required=True,
                              help='Description')
    email = fields.Char('Email', help='Email')
    phone = fields.Char('Phone', help='Contact Number')
    team_id = fields.Many2one('team.helpdesk', string='Helpdesk Team',
                              help='Helpdesk Team Name')
    product_ids = fields.Many2many('product.template',
                                   string='Product',
                                   help='Product Name')
    project_id = fields.Many2one('project.project',
                                 string='Project',
                                 readonly=False,
                                 related='team_id.project_id',
                                 store=True,
                                 help='Project Name')
    priority = fields.Selection(PRIORITIES, default='1', help='Priority of the'
                                                              ' Ticket')
    stage_id = fields.Many2one('ticket.stage', string='Stage',
                               tracking=True,
                               group_expand='_read_group_stage_ids',
                               help='Stages')
    user_id = fields.Many2one('res.users',
                              default=lambda self: self.env.user,
                              check_company=True,
                              index=True, tracking=True,
                              help='Login User', string='User')
    cost = fields.Float('Cost per hour', help='Cost Per Unit')
    service_product_id = fields.Many2one('product.product',
                                         string='Service Product',
                                         help='Service Product',
                                         domain=[
                                             ('type', '=', 'service')])
    create_date = fields.Datetime('Creation Date', help='Created date')
    start_date = fields.Datetime('Start Date', help='Start Date')
    end_date = fields.Datetime('End Date', help='End Date')
    public_ticket = fields.Boolean(string="Public Ticket",
                                   help='Public Ticket')
    invoice_ids = fields.Many2many('account.move',
                                   string='Invoices',
                                   help='Invoicing id'
                                   )
    task_ids = fields.Many2many('project.task',
                                string='Tasks',
                                help='Task id')
    color = fields.Integer(string="Color", help='Color')
    replied_date = fields.Datetime('Replied date', help='Replied Date')
    last_update_date = fields.Datetime('Last Update Date',
                                       help='Last Update Date')
    ticket_type_id = fields.Many2one('helpdesk.type',
                                     string='Ticket Type', help='Ticket Type')
    team_head_id = fields.Many2one('res.users', string='Team Leader',
                                   compute='_compute_team_head_id',
                                   help='Team Leader Name', store = True)
    assigned_user_id = fields.Many2one('res.users', string='Assigned User',
                                       domain=lambda self: [('group_ids', 'in',
                                                             self.env.ref(
                                                                 'odoo_website_helpdesk.helpdesk_user').id)],
                                       help='Assigned User Name')
    category_id = fields.Many2one('helpdesk.category', string='Category',
                                  help='Category')
    tags_ids = fields.Many2many('helpdesk.tag', help='Tags', string='Tags')
    assign_user = fields.Boolean(default=False, help='Assign User',
                                 string='Assign User')
    attachment_ids = fields.One2many('ir.attachment', 'res_id',
                                     help='Attachment Line',
                                     string='Attachments')
    merge_ticket_invisible = fields.Boolean(string='Merge Ticket',
                                            help='Merge Ticket Invisible or '
                                                 'Not', default=False)
    merge_count = fields.Integer(string='Merge Count', help='Merged Tickets '
                                                            'Count')
    active = fields.Boolean(default=True, help='Active', string='Active')

    show_create_task = fields.Boolean(string="Show Create Task",
                                      help='Show created task or not',
                                      default=_default_show_create_task,
                                      compute='_compute_show_create_task')
    create_task = fields.Boolean(string="Create Task", readonly=False,
                                 help='Create task or not',
                                 related='team_id.create_task', store=True)
    billable = fields.Boolean(string="Billable", default=False,
                              help='Is billable or not', )
    show_category = fields.Boolean(default=_default_show_category,
                                   string="Show Category",
                                   help='Show category or not',
                                   compute='_compute_show_category')
    customer_rating = fields.Selection(RATING, default='0', readonly=True)
    review = fields.Char('Review', readonly=True, help='Ticket review')
    kanban_state = fields.Selection([
        ('normal', 'Ready'),
        ('done', 'In Progress'),
        ('blocked', 'Blocked'), ], default='normal')

    @api.onchange('team_id', 'team_head_id')
    def _onchange_team_id(self):
        """Changing the team leader when selecting the team"""
        li = self.team_id.member_ids.mapped(id)
        return {'domain': {'assigned_user_id': [('id', 'in', li)]}}

    @api.depends('team_id')
    def _compute_team_head_id(self):
        """Compute the team head function"""
        self.team_head_id = self.team_id.team_lead_id.id

    @api.onchange('stage_id')
    def _onchange_stage_id(self):
        """Sending mail to the user function"""
        rec_id = self._origin.id
        data = self.env['ticket.helpdesk'].search([('id', '=', rec_id)])
        data.last_update_date = fields.Datetime.now()
        if self.stage_id.starting_stage:
            data.start_date = fields.Datetime.now()
        if self.stage_id.closing_stage or self.stage_id.cancel_stage:
            data.end_date = fields.Datetime.now()
        if self.stage_id.template_id:
            mail_template = self.stage_id.template_id
            mail_template.send_mail(self._origin.id, force_send=True)

    def assign_to_teamleader(self):
        """Assigning team leader function"""
        if self.team_id:
            self.team_head_id = self.team_id.team_lead_id.id
            mail_template = self.env.ref(
                'odoo_website_helpdesk.odoo_website_helpdesk_assign')
            mail_template.sudo().write({
                'email_to': self.team_head_id.email,
                'subject': self.name
            })
            mail_template.sudo().send_mail(self.id, force_send=True)
        else:
            raise ValidationError("Please choose a Helpdesk Team")

    def _compute_show_category(self):
        """Compute show category"""
        show_category = self._default_show_category()
        for rec in self:
            rec.show_category = show_category

    def _compute_show_create_task(self):
        """Compute the created task"""
        show_create_task = self._default_show_create_task()
        for record in self:
            record.show_create_task = show_create_task

    def auto_close_ticket(self):
        """Automatically closing the ticket"""
        auto_close = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_website_helpdesk.auto_close_ticket')
        if auto_close:
            no_of_days = self.env['ir.config_parameter'].sudo().get_param(
                'odoo_website_helpdesk.no_of_days')
            records = self.env['ticket.helpdesk'].search([])
            for rec in records:
                days = (fields.Datetime.today() - rec.create_date).days
                if days >= int(no_of_days):
                    close_stage_id = self.env['ticket.stage'].search(
                        [('closing_stage', '=', True)])
                    if close_stage_id:
                        rec.stage_id = close_stage_id

    def default_stage_id(self):
        """Method to return the default stage"""
        return self.env['ticket.stage'].search(
            [('name', '=', 'Draft')], limit=1).id

    def _read_group_stage_ids(self, stages, domain):
        """
        return the stages to stage_ids
        """
        stage_ids = self.env['ticket.stage'].search([])
        return stage_ids

    @api.model_create_multi
    def create(self, vals_list):
        """Create function"""
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'ticket.helpdesk')
        return super(TicketHelpDesk, self).create(vals_list)

    def write(self, vals):
        """Write function"""
        result = super(TicketHelpDesk, self).write(vals)
        return result

    def action_create_invoice(self):
        """Create Invoice based on the ticket"""
        tasks = self.env['project.task'].search(
            [('project_id', '=', self.project_id.id),
             ('ticket_id', '=', self.id)]).filtered(
            lambda line: not line.ticket_billed)
        if not tasks:
            raise UserError('No Tasks to Bill')
        total = sum(x.effective_hours for x in tasks if
                     x.effective_hours > 0 and not x.some_flag)
        invoice_no = self.env['ir.sequence'].next_by_code(
            'ticket.invoice')
        self.env['account.move'].create([
            {
                'name': invoice_no,
                'move_type': 'out_invoice',
                'partner_id': self.customer_id.id,
                'ticket_id': self.id,
                'date': fields.Date.today(),
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': [(0, 0,
                                      {
                                          'product_id': self.service_product_id.id,
                                          'name': self.service_product_id.name,
                                          'quantity': total,
                                          'product_uom_id': self.service_product_id.uom_id.id,
                                          'price_unit': self.cost,
                                          'account_id': self.service_product_id.categ_id.property_account_income_categ_id.id,
                                      })],
            }, ])
        for task in tasks:
            task.ticket_billed = True
        return {
            'effect': {
                'fadeout': 'medium',
                'message': 'Billed Successfully!',
                'type': 'rainbow_man',
            }
        }

    def action_create_tasks(self):
        """Task creation"""
        task_id = self.env['project.task'].create({
            'name': self.name + '-' + self.subject,
            'project_id': self.project_id.id,
            'company_id': self.env.company.id,
            'ticket_id': self.id,
        })
        self.write({
            'task_ids': [(4, task_id.id)]
        })
        return {
            'name': 'Tasks',
            'res_model': 'project.task',
            'view_id': False,
            'res_id': task_id.id,
            'view_mode': 'form',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def action_open_tasks(self):
        """View the Created task """
        return {
            'name': 'Tasks',
            'domain': [('ticket_id', '=', self.id)],
            'res_model': 'project.task',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
        }

    def action_open_invoices(self):
        """View the Created invoice"""
        return {
            'name': 'Invoice',
            'domain': [('ticket_id', '=', self.id)],
            'res_model': 'account.move',
            'view_id': False,
            'view_mode': 'list,form',
            'type': 'ir.actions.act_window',
        }

    def action_open_merged_tickets(self):
        """Open the merged tickets list view"""
        ticket_ids = self.env['support.ticket'].search(
            [('merged_ticket', '=', self.id)])
        helpdesk_ticket_ids = ticket_ids.mapped('display_name')
        help_ticket_records = self.env['ticket.helpdesk'].search(
            [('name', 'in', helpdesk_ticket_ids)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Helpdesk Ticket',
            'view_mode': 'list,form',
            'res_model': 'ticket.helpdesk',
            'domain': [('id', 'in', help_ticket_records.ids)],
            'context': self.env.context,
        }

    def action_send_reply(self):
        """Action to sent reply button"""
        template_id = self.env['ir.config_parameter'].sudo().get_param(
            'odoo_website_helpdesk.reply_template_id'
        )
        template_id = self.env['mail.template'].browse(int(template_id))
        if template_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'mail',
                'res_model': 'mail.compose.message',
                'view_mode': 'form',
                'target': 'new',
                'views': [[False, 'form']],
                'context': {
                    'default_model': 'ticket.helpdesk',
                    'default_res_ids': self.ids,
                    'default_template_id': template_id.id
                }
            }
        return {
            'type': 'ir.actions.act_window',
            'name': 'mail',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'target': 'new',
            'views': [[False, 'form']],
            'context': {
                'default_model': 'ticket.helpdesk',
                'default_res_ids': self.ids,
            }
        }
