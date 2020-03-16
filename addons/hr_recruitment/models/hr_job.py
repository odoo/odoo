# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json	
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from odoo import api, fields, models, _
from odoo.osv import expression
from odoo.release import version	
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF	
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang	
import random		
import ast

class Job(models.Model):
    _name = "hr.job"
    _inherit = ["mail.alias.mixin", "hr.job"]
    _order = "state desc, name asc"

    @api.model
    def _default_address_id(self):
        return self.env.company.partner_id

    def _get_default_favorite_user_ids(self):
        return [(6, 0, [self.env.uid])]

    address_id = fields.Many2one(
        'res.partner', "Job Location", default=_default_address_id,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Address where employees are working")
    application_ids = fields.One2many('hr.applicant', 'job_id', "Applications")
    application_count = fields.Integer(compute='_compute_application_count', string="Application Count")
    new_application_count = fields.Integer(
        compute='_compute_new_application_count', string="New Application",
        help="Number of applications that are new in the flow (typically at first step of the flow)")
    manager_id = fields.Many2one(
        'hr.employee', related='department_id.manager_id', string="Department Manager",
        readonly=True, store=True)
    user_id = fields.Many2one('res.users', "Responsible", tracking=True)
    hr_responsible_id = fields.Many2one(
        'res.users', "HR Responsible", tracking=True,
        help="Person responsible of validating the employee's contracts.")
    document_ids = fields.One2many('ir.attachment', compute='_compute_document_ids', string="Documents")
    documents_count = fields.Integer(compute='_compute_document_ids', string="Document Count")
    alias_id = fields.Many2one(
        'mail.alias', "Alias", ondelete="restrict", required=True,
        help="Email alias for this job position. New emails will automatically create new applicants for this job position.")
    color = fields.Integer("Color Index",default=0)
    is_favorite = fields.Boolean(compute='_compute_is_favorite', inverse='_inverse_is_favorite')
    favorite_user_ids = fields.Many2many('res.users', 'job_favorite_user_rel', 'job_id', 'user_id', default=_get_default_favorite_user_ids)

    def _compute_is_favorite(self):
        for job in self:
            job.is_favorite = self.env.user in job.favorite_user_ids

    def _inverse_is_favorite(self):
        unfavorited_jobs = favorited_jobs = self.env['hr.job']
        for job in self:
            if self.env.user in job.favorite_user_ids:
                unfavorited_jobs |= job
            else:
                favorited_jobs |= job
        favorited_jobs.write({'favorite_user_ids': [(4, self.env.uid)]})
        unfavorited_jobs.write({'favorite_user_ids': [(3, self.env.uid)]})

    def _compute_document_ids(self):
        applicants = self.mapped('application_ids').filtered(lambda self: not self.emp_id)
        app_to_job = dict((applicant.id, applicant.job_id.id) for applicant in applicants)
        attachments = self.env['ir.attachment'].search([
            '|',
            '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids),
            '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicants.ids)])
        result = dict.fromkeys(self.ids, self.env['ir.attachment'])
        for attachment in attachments:
            if attachment.res_model == 'hr.applicant':
                result[app_to_job[attachment.res_id]] |= attachment
            else:
                result[attachment.res_id] |= attachment

        for job in self:
            job.document_ids = result[job.id]
            job.documents_count = len(job.document_ids)

    def _compute_application_count(self):
        read_group_result = self.env['hr.applicant'].read_group([('job_id', 'in', self.ids)], ['job_id'], ['job_id'])
        result = dict((data['job_id'][0], data['job_id_count']) for data in read_group_result)
        for job in self:
            job.application_count = result.get(job.id, 0)

    def action_view_job(self):
        return {
            'name': _('Job Position'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.job',
            'res_id': self.id,
        }
    def action_hr_job_sources_func(self):
        return{
            'name':_('Job Position'),
            'type':'ir.actions.act_window',
            'res_model':'hr.recruitment.source',
            'view_mode':'tree',
            'domain':'[("job_id","=",active_id)]',
            'context':'{"default_job_id": active_id,"default_source_id":6}',
        }
    def _get_first_stage(self):
        self.ensure_one()
        return self.env['hr.recruitment.stage'].search([
            '|',
            ('job_ids', '=', False),
            ('job_ids', '=', self.id)], order='sequence asc', limit=1)

    def _compute_new_application_count(self):
        for job in self:
            job.new_application_count = self.env["hr.applicant"].search_count(
                [("job_id", "=", job.id), ("stage_id", "=", job._get_first_stage().id)]
            )

    def get_alias_model_name(self, vals):
        return 'hr.applicant'

    def get_alias_values(self):
        values = super(Job, self).get_alias_values()
        values['alias_defaults'] = {
            'job_id': self.id,
            'department_id': self.department_id.id,
            'company_id': self.department_id.company_id.id if self.department_id else self.company_id.id
        }
        return values

    @api.model
    def create(self, vals):
        vals['favorite_user_ids'] = vals.get('favorite_user_ids', []) + [(4, self.env.uid)]
        res = super(Job, self).create(vals)
        new_source = self.env['hr.recruitment.source'].create({
            'source_id': 6,
            'job_id': res.id
        })
        return res

    def _creation_subtype(self):
        return self.env.ref('hr_recruitment.mt_job_new')

    def action_get_attachment_tree_view(self):
        action = self.env.ref('base.action_attachment').read()[0]
        action['context'] = {
            'default_res_model': self._name,
            'default_res_id': self.ids[0]
        }
        action['search_view_id'] = (self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').id, )
        action['domain'] = ['|', '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', self.ids), '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.mapped('application_ids').ids)]
        return action

    def close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    def edit_dialog(self):
        form_view = self.env.ref('hr.view_hr_job_form')
        return {
            'name': _('Job'),
            'res_model': 'hr.job',
            'res_id': self.id,
            'views': [(form_view.id, 'form'),],
            'type': 'ir.actions.act_window',
            'target': 'inline'
        }
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')
    def _kanban_dashboard_graph(self):
        for job in self:
                job.kanban_dashboard_graph = json.dumps(job.get_line_graph_datas())

    def get_line_graph_datas(self):

        locale = get_lang(self.env).code
        def build_graph_data(date, amount):
            #display date in locale format
            name = format_date(date, 'd LLLL Y', locale=locale)
            short_name = format_date(date, 'd MMM', locale=locale)
            return {'x':short_name,'y': amount, 'name':name}

        self.ensure_one()
        today = datetime.today()
        Applications = self.env['hr.applicant']
        data = []
        is_sample_data=False
        color='#875A7B'
        for i in range(7, 0,-1):
            current_date_upperbound = today + timedelta(days=-i)#Use of upper and lowerbound to get Applicant with date_open equal to lowerbound date who looks like YYYY-MM-DD after strftime by testing between upper and lowerbound we get them all even if date_open is in datetime format with hours and minutes
            current_date_lowerbound = today + timedelta(days=-(i+1))
            amount_applications = Applications.search([('job_id', '=',self.id),'&',('date_open','>',current_date_lowerbound.strftime(DF)),('date_open','<=',current_date_upperbound.strftime(DF))])
            data_item = build_graph_data(current_date_upperbound, len(amount_applications))
            data.append(data_item)

        return [{'values': data, 'title': '', 'key': 'Applications Count', 'area': True, 'color': color, 'is_sample_data': is_sample_data}]
