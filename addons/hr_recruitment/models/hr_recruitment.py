# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, SUPERUSER_ID
from odoo.tools.translate import _
from odoo.exceptions import UserError

AVAILABLE_PRIORITIES = [
    ('0', 'Normal'),
    ('1', 'Good'),
    ('2', 'Very Good'),
    ('3', 'Excellent')
]


class RecruitmentSource(models.Model):
    _name = "hr.recruitment.source"
    _description = "Source of Applicants"
    _inherits = {"utm.source": "source_id"}

    source_id = fields.Many2one('utm.source', "Source", ondelete='cascade', required=True)
    email = fields.Char(related='alias_id.display_name', string="Email", readonly=True)
    job_id = fields.Many2one('hr.job', "Job ID")
    alias_id = fields.Many2one('mail.alias', "Alias ID")

    @api.multi
    def create_alias(self):
        campaign = self.env.ref('hr_recruitment.utm_campaign_job')
        medium = self.env.ref('utm.utm_medium_email')
        for source in self:
            vals = {
                'alias_parent_thread_id': source.job_id.id,
                'alias_name': "%s+%s" % (source.job_id.alias_name or source.job_id.name, source.name),
                'alias_defaults': {
                    'job_id': source.job_id.id,
                    'campaign_id': campaign.id,
                    'medium_id': medium.id,
                    'source_id': source.source_id.id,
                },
            }
            source.alias_id = self.with_context(alias_model_name='hr.applicant', alias_parent_model_name='hr.job').env['mail.alias'].create(vals)
            source.name = source.source_id.name


class RecruitmentStage(models.Model):
    _name = "hr.recruitment.stage"
    _description = "Recruitment Stages"
    _order = 'sequence'

    name = fields.Char("Stage name", required=True, translate=True)
    sequence = fields.Integer(
        "Sequence", default=10,
        help="Gives the sequence order when displaying a list of stages.")
    job_id = fields.Many2one('hr.job', string='Job Specific',
                             ondelete='cascade',
                             help='Specific job that uses this stage. Other jobs will not use this stage.')
    requirements = fields.Text("Requirements")
    template_id = fields.Many2one(
        'mail.template', "Automated Email",
        help="If set, a message is posted on the applicant using the template when the applicant is set to the stage.")
    fold = fields.Boolean(
        "Folded in Recruitment Pipe",
        help="This stage is folded in the kanban view when there are no records in that stage to display.")
    legend_blocked = fields.Char(
        'Red Kanban Label', default=lambda self: _('Blocked'), translate=True, required=True)
    legend_done = fields.Char(
        'Green Kanban Label', default=lambda self: _('Ready for Next Stage'), translate=True, required=True)
    legend_normal = fields.Char(
        'Grey Kanban Label', default=lambda self: _('In Progress'), translate=True, required=True)

    @api.model
    def default_get(self, fields):
        if self._context and self._context.get('default_job_id') and not self._context.get('hr_recruitment_stage_mono', False):
            context = dict(self._context)
            context.pop('default_job_id')
            self = self.with_context(context)
        return super(RecruitmentStage, self).default_get(fields)


class RecruitmentDegree(models.Model):
    _name = "hr.recruitment.degree"
    _description = "Applicant Degree"
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of Recruitment must be unique!')
    ]

    name = fields.Char("Degree", required=True, translate=True)
    sequence = fields.Integer("Sequence", default=1, help="Gives the sequence order when displaying a list of degrees.")


class Applicant(models.Model):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "priority desc, id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'utm.mixin']

    def _default_stage_id(self):
        if self._context.get('default_job_id'):
            ids = self.env['hr.recruitment.stage'].search([
                '|',
                ('job_id', '=', False),
                ('job_id', '=', self._context['default_job_id']),
                ('fold', '=', False)
            ], order='sequence asc', limit=1).ids
            if ids:
                return ids[0]
        return False

    def _default_company_id(self):
        company_id = False
        if self._context.get('default_department_id'):
            department = self.env['hr.department'].browse(self._context['default_department_id'])
            company_id = department.company_id.id
        if not company_id:
            company_id = self.env['res.company']._company_default_get('hr.applicant')
        return company_id

    name = fields.Char("Subject / Application Name", required=True)
    active = fields.Boolean("Active", default=True, help="If the active field is set to false, it will allow you to hide the case without removing it.")
    description = fields.Text("Description")
    email_from = fields.Char("Email", size=128, help="These people will receive email.")
    email_cc = fields.Text("Watchers Emails", size=252,
                           help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma")
    probability = fields.Float("Probability")
    partner_id = fields.Many2one('res.partner', "Contact")
    create_date = fields.Datetime("Creation Date", readonly=True, index=True)
    stage_id = fields.Many2one('hr.recruitment.stage', 'Stage', ondelete='restrict', track_visibility='onchange',
                               domain="['|', ('job_id', '=', False), ('job_id', '=', job_id)]",
                               copy=False, index=True,
                               group_expand='_read_group_stage_ids',
                               default=_default_stage_id)
    last_stage_id = fields.Many2one('hr.recruitment.stage', "Last Stage",
                                    help="Stage of the applicant before being in the current stage. Used for lost cases analysis.")
    categ_ids = fields.Many2many('hr.applicant.category', string="Tags")
    company_id = fields.Many2one('res.company', "Company", default=_default_company_id)
    user_id = fields.Many2one('res.users', "Responsible", track_visibility="onchange", default=lambda self: self.env.uid)
    date_closed = fields.Datetime("Closed", readonly=True, index=True)
    date_open = fields.Datetime("Assigned", readonly=True, index=True)
    date_last_stage_update = fields.Datetime("Last Stage Update", index=True, default=fields.Datetime.now)
    priority = fields.Selection(AVAILABLE_PRIORITIES, "Appreciation", default='0')
    job_id = fields.Many2one('hr.job', "Applied Job")
    salary_proposed_extra = fields.Char("Proposed Salary Extra", help="Salary Proposed by the Organisation, extra advantages")
    salary_expected_extra = fields.Char("Expected Salary Extra", help="Salary Expected by Applicant, extra advantages")
    salary_proposed = fields.Float("Proposed Salary", group_operator="avg", help="Salary Proposed by the Organisation")
    salary_expected = fields.Float("Expected Salary", group_operator="avg", help="Salary Expected by Applicant")
    availability = fields.Date("Availability", help="The date at which the applicant will be available to start working")
    partner_name = fields.Char("Applicant's Name")
    partner_phone = fields.Char("Phone", size=32)
    partner_mobile = fields.Char("Mobile", size=32)
    type_id = fields.Many2one('hr.recruitment.degree', "Degree")
    department_id = fields.Many2one('hr.department', "Department")
    reference = fields.Char("Referred By")
    day_open = fields.Float(compute='_compute_day', string="Days to Open")
    day_close = fields.Float(compute='_compute_day', string="Days to Close")
    delay_close = fields.Float(compute="_compute_day", string='Delay to Close', readonly=True, group_operator="avg", help="Number of days to close", store=True)
    color = fields.Integer("Color Index", default=0)
    emp_id = fields.Many2one('hr.employee', string="Employee", track_visibility="onchange", help="Employee linked to the applicant.")
    user_email = fields.Char(related='user_id.email', type="char", string="User Email", readonly=True)
    attachment_number = fields.Integer(compute='_get_attachment_number', string="Number of Attachments")
    employee_name = fields.Char(related='emp_id.name', string="Employee Name", readonly=False)
    attachment_ids = fields.One2many('ir.attachment', 'res_id', domain=[('res_model', '=', 'hr.applicant')], string='Attachments')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        copy=False, default='normal', required=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked', readonly=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid', readonly=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing', readonly=False)
    

    @api.depends('date_open', 'date_closed')
    @api.one
    def _compute_day(self):
        if self.date_open:
            date_create = self.create_date
            date_open = self.date_open
            self.day_open = (date_open - date_create).total_seconds() / (24.0 * 3600)

        if self.date_closed:
            date_create = self.create_date
            date_closed = self.date_closed
            self.day_close = (date_closed - date_create).total_seconds() / (24.0 * 3600)
            self.delay_close = self.day_close - self.day_open

    @api.multi
    def _get_attachment_number(self):
        read_group_res = self.env['ir.attachment'].read_group(
            [('res_model', '=', 'hr.applicant'), ('res_id', 'in', self.ids)],
            ['res_id'], ['res_id'])
        attach_data = dict((res['res_id'], res['res_id_count']) for res in read_group_res)
        for record in self:
            record.attachment_number = attach_data.get(record.id, 0)

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # retrieve job_id from the context and write the domain: ids + contextual columns (job or default)
        job_id = self._context.get('default_job_id')
        search_domain = [('job_id', '=', False)]
        if job_id:
            search_domain = ['|', ('job_id', '=', job_id)] + search_domain
        if stages:
            search_domain = ['|', ('id', 'in', stages.ids)] + search_domain

        stage_ids = stages._search(search_domain, order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    @api.onchange('job_id')
    def onchange_job_id(self):
        vals = self._onchange_job_id_internal(self.job_id.id)
        self.department_id = vals['value']['department_id']
        self.user_id = vals['value']['user_id']
        self.stage_id = vals['value']['stage_id']

    def _onchange_job_id_internal(self, job_id):
        department_id = False
        user_id = False
        stage_id = self.stage_id.id or self._context.get('default_stage_id')
        if job_id:
            job = self.env['hr.job'].browse(job_id)
            department_id = job.department_id.id
            user_id = job.user_id.id
            if not stage_id:
                stage_ids = self.env['hr.recruitment.stage'].search([
                    '|',
                    ('job_id', '=', False),
                    ('job_id', '=', job.id),
                    ('fold', '=', False)
                ], order='sequence asc', limit=1).ids
                stage_id = stage_ids[0] if stage_ids else False

        return {'value': {
            'department_id': department_id,
            'user_id': user_id,
            'stage_id': stage_id
        }}

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        self.partner_phone = self.partner_id.phone
        self.partner_mobile = self.partner_id.mobile
        self.email_from = self.partner_id.email

    @api.onchange('stage_id')
    def onchange_stage_id(self):
        vals = self._onchange_stage_id_internal(self.stage_id.id)
        if vals['value'].get('date_closed'):
            self.date_closed = vals['value']['date_closed']

    def _onchange_stage_id_internal(self, stage_id):
        if not stage_id:
            return {'value': {}}
        stage = self.env['hr.recruitment.stage'].browse(stage_id)
        if stage.fold:
            return {'value': {'date_closed': fields.datetime.now()}}
        return {'value': {'date_closed': False}}

    @api.model
    def create(self, vals):
        if vals.get('department_id') and not self._context.get('default_department_id'):
            self = self.with_context(default_department_id=vals.get('department_id'))
        if vals.get('job_id') or self._context.get('default_job_id'):
            job_id = vals.get('job_id') or self._context.get('default_job_id')
            for key, value in self._onchange_job_id_internal(job_id)['value'].items():
                if key not in vals:
                    vals[key] = value
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        if 'stage_id' in vals:
            vals.update(self._onchange_stage_id_internal(vals.get('stage_id'))['value'])
        return super(Applicant, self.with_context(mail_create_nolog=True)).create(vals)

    @api.multi
    def write(self, vals):
        # user_id change: update date_open
        if vals.get('user_id'):
            vals['date_open'] = fields.Datetime.now()
        # stage_id: track last stage before update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.Datetime.now()
            vals.update(self._onchange_stage_id_internal(vals.get('stage_id'))['value'])
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
            for applicant in self:
                vals['last_stage_id'] = applicant.stage_id.id
                res = super(Applicant, self).write(vals)
        else:
            res = super(Applicant, self).write(vals)
        return res

    @api.model
    def get_empty_list_help(self, help):
        return super(Applicant, self.with_context(empty_list_help_model='hr.job',
                                                  empty_list_help_id=self.env.context.get('default_job_id'),
                                                  empty_list_help_document_name=_("job applicant"))).get_empty_list_help(help)

    @api.multi
    def action_get_created_employee(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window'].for_xml_id('hr', 'open_view_employee_list')
        action['res_id'] = self.mapped('emp_id').ids[0]
        return action

    @api.multi
    def action_makeMeeting(self):
        """ This opens Meeting's calendar view to schedule meeting on current applicant
            @return: Dictionary value for created Meeting view
        """
        self.ensure_one()
        partners = self.partner_id | self.user_id.partner_id | self.department_id.manager_id.user_id.partner_id

        category = self.env.ref('hr_recruitment.categ_meet_interview')
        res = self.env['ir.actions.act_window'].for_xml_id('calendar', 'action_calendar_event')
        res['context'] = {
            'search_default_partner_ids': self.partner_id.name,
            'default_partner_ids': partners.ids,
            'default_user_id': self.env.uid,
            'default_name': self.name,
            'default_categ_ids': category and [category.id] or False,
        }
        return res

    @api.multi
    def action_get_attachment_tree_view(self):
        attachment_action = self.env.ref('base.action_attachment')
        action = attachment_action.read()[0]
        action['context'] = {'default_res_model': self._name, 'default_res_id': self.ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', self.ids)])
        action['search_view_id'] = (self.env.ref('hr_recruitment.ir_attachment_view_search_inherit_hr_recruitment').id, )
        return action

    @api.multi
    def _track_template(self, tracking):
        res = super(Applicant, self)._track_template(tracking)
        applicant = self[0]
        changes, dummy = tracking[applicant.id]
        if 'stage_id' in changes and applicant.stage_id.template_id:
            res['stage_id'] = (applicant.stage_id.template_id, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data'].xmlid_to_res_id('mail.mt_note'),
                'notif_layout': 'mail.mail_notification_light'
            })
        return res

    @api.multi
    def _track_subtype(self, init_values):
        record = self[0]
        if 'emp_id' in init_values and record.emp_id and record.emp_id.active:
            return 'hr_recruitment.mt_applicant_hired'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence <= 1:
            return 'hr_recruitment.mt_applicant_new'
        elif 'stage_id' in init_values and record.stage_id and record.stage_id.sequence > 1:
            return 'hr_recruitment.mt_applicant_stage_changed'
        return super(Applicant, self)._track_subtype(init_values)

    @api.multi
    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Override to set alias of applicants to their job definition if any. """
        aliases = self.mapped('job_id')._notify_get_reply_to(default=default, records=None, company=company, doc_names=None)
        res = {app.id: aliases.get(app.job_id.id) for app in self}
        leftover = self.filtered(lambda rec: not rec.job_id)
        if leftover:
            res.update(super(Applicant, leftover)._notify_get_reply_to(default=default, records=None, company=company, doc_names=doc_names))
        return res

    @api.multi
    def message_get_suggested_recipients(self):
        recipients = super(Applicant, self).message_get_suggested_recipients()
        for applicant in self:
            if applicant.partner_id:
                applicant._message_add_suggested_recipient(recipients, partner=applicant.partner_id, reason=_('Contact'))
            elif applicant.email_from:
                applicant._message_add_suggested_recipient(recipients, email=applicant.email_from, reason=_('Contact Email'))
        return recipients

    @api.model
    def message_new(self, msg, custom_values=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        # remove default author when going through the mail gateway. Indeed we
        # do not want to explicitly set user_id to False; however we do not
        # want the gateway user to be responsible if no other responsible is
        # found.
        self = self.with_context(default_user_id=False)
        val = msg.get('from').split('<')[0]
        defaults = {
            'name': msg.get('subject') or _("No Subject"),
            'partner_name': val,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        if custom_values:
            defaults.update(custom_values)
        return super(Applicant, self).message_new(msg, custom_values=defaults)

    def _message_post_after_hook(self, message, *args, **kwargs):
        if self.email_from and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.email_from)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('email_from', '=', new_partner.email),
                    ('stage_id.fold', '=', False)]).write({'partner_id': new_partner.id})
        return super(Applicant, self)._message_post_after_hook(message, *args, **kwargs)

    @api.multi
    def create_employee_from_applicant(self):
        """ Create an hr.employee from the hr.applicants """
        employee = False
        for applicant in self:
            contact_name = False
            if applicant.partner_id:
                address_id = applicant.partner_id.address_get(['contact'])['contact']
                contact_name = applicant.partner_id.name_get()[0][1]
            else :
                new_partner_id = self.env['res.partner'].create({
                    'is_company': False,
                    'name': applicant.partner_name,
                    'email': applicant.email_from,
                    'phone': applicant.partner_phone,
                    'mobile': applicant.partner_mobile
                })
                address_id = new_partner_id.address_get(['contact'])['contact']
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1})
                employee = self.env['hr.employee'].create({
                    'name': applicant.partner_name or contact_name,
                    'job_id': applicant.job_id.id,
                    'address_home_id': address_id,
                    'department_id': applicant.department_id.id or False,
                    'address_id': applicant.company_id and applicant.company_id.partner_id
                            and applicant.company_id.partner_id.id or False,
                    'work_email': applicant.department_id and applicant.department_id.company_id
                            and applicant.department_id.company_id.email or False,
                    'work_phone': applicant.department_id and applicant.department_id.company_id
                            and applicant.department_id.company_id.phone or False})
                applicant.write({'emp_id': employee.id})
                applicant.job_id.message_post(
                    body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                    subtype="hr_recruitment.mt_job_applicant_hired")
            else:
                raise UserError(_('You must define an Applied Job and a Contact Name for this applicant.'))

        employee_action = self.env.ref('hr.open_view_employee_list')
        dict_act_window = employee_action.read([])[0]
        dict_act_window['context'] = {'form_view_initial_mode': 'edit'}
        dict_act_window['res_id'] = employee.id
        return dict_act_window

    @api.multi
    def archive_applicant(self):
        self.write({'active': False})

    @api.multi
    def reset_applicant(self):
        """ Reinsert the applicant into the recruitment pipe in the first stage"""
        default_stage_id = self._default_stage_id()
        self.write({'active': True, 'stage_id': default_stage_id})


class ApplicantCategory(models.Model):
    _name = "hr.applicant.category"
    _description = "Category of applicant"

    name = fields.Char("Name", required=True)
    color = fields.Integer(string='Color Index', default=10)

    _sql_constraints = [
            ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]
