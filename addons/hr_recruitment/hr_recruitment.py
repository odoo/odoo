# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from datetime import datetime

from openerp import SUPERUSER_ID
from openerp.osv import fields, osv
from openerp.tools.translate import _


AVAILABLE_PRIORITIES = [
    ('0', 'Bad'),
    ('1', 'Below Average'),
    ('2', 'Average'),
    ('3', 'Good'),
    ('4', 'Excellent')
]

class hr_recruitment_source(osv.osv):
    """ Sources of HR Recruitment """
    _name = "hr.recruitment.source"
    _description = "Source of Applicants"
    _columns = {
        'name': fields.char('Source Name', required=True, translate=True),
    }

class hr_recruitment_stage(osv.osv):
    """ Stage of HR Recruitment """
    _name = "hr.recruitment.stage"
    _description = "Stage of Recruitment"
    _order = 'sequence'
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of stages."),
        'department_id':fields.many2one('hr.department', 'Specific to a Department', help="Stages of the recruitment process may be different per department. If this stage is common to all departments, keep this field empty."),
        'requirements': fields.text('Requirements'),
        'template_id': fields.many2one('email.template', 'Use template', help="If set, a message is posted on the applicant using the template when the applicant is set to the stage."),
        'fold': fields.boolean('Folded in Kanban View',
                               help='This stage is folded in the kanban view when'
                               'there are no records in that stage to display.'),
    }
    _defaults = {
        'sequence': 1,
    }

class hr_recruitment_degree(osv.osv):
    """ Degree of HR Recruitment """
    _name = "hr.recruitment.degree"
    _description = "Degree of Recruitment"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of degrees."),
    }
    _defaults = {
        'sequence': 1,
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of Recruitment must be unique!')
    ]

class hr_applicant(osv.Model):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']

    _track = {
        'stage_id': {
            # this is only an heuristics; depending on your particular stage configuration it may not match all 'new' stages
            'hr_recruitment.mt_applicant_new': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence <= 1,
            'hr_recruitment.mt_applicant_stage_changed': lambda self, cr, uid, obj, ctx=None: obj.stage_id and obj.stage_id.sequence > 1,
        },
    }
    _mail_mass_mailing = _('Applicants')

    def _get_default_department_id(self, cr, uid, context=None):
        """ Gives default department by checking if present in the context """
        return (self._resolve_department_id_from_context(cr, uid, context=context) or False)

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        department_id = self._get_default_department_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], department_id, [('fold', '=', False)], context=context)

    def _resolve_department_id_from_context(self, cr, uid, context=None):
        """ Returns ID of department based on the value of 'default_department_id'
            context key, or None if it cannot be resolved to a single
            department.
        """
        if context is None:
            context = {}
        if type(context.get('default_department_id')) in (int, long):
            return context.get('default_department_id')
        if isinstance(context.get('default_department_id'), basestring):
            department_name = context['default_department_id']
            department_ids = self.pool.get('hr.department').name_search(cr, uid, name=department_name, context=context)
            if len(department_ids) == 1:
                return int(department_ids[0][0])
        return None

    def _get_default_company_id(self, cr, uid, department_id=None, context=None):
        company_id = False
        if department_id:
            department = self.pool['hr.department'].browse(cr,  uid, department_id, context=context)
            company_id = department.company_id.id if department and department.company_id else False
        if not company_id:
            company_id = self.pool['res.company']._company_default_get(cr, uid, 'hr.applicant', context=context)
        return company_id            

    def _read_group_stage_ids(self, cr, uid, ids, domain, read_group_order=None, access_rights_uid=None, context=None):
        access_rights_uid = access_rights_uid or uid
        stage_obj = self.pool.get('hr.recruitment.stage')
        order = stage_obj._order
        # lame hack to allow reverting search, should just work in the trivial case
        if read_group_order == 'stage_id desc':
            order = "%s desc" % order
        # retrieve section_id from the context and write the domain
        # - ('id', 'in', 'ids'): add columns that should be present
        # - OR ('department_id', '=', False), ('fold', '=', False): add default columns that are not folded
        # - OR ('department_id', 'in', department_id), ('fold', '=', False) if department_id: add department columns that are not folded
        department_id = self._resolve_department_id_from_context(cr, uid, context=context)
        search_domain = []
        if department_id:
            search_domain += ['|', ('department_id', '=', department_id)]
        search_domain += ['|', ('id', 'in', ids), ('department_id', '=', False)]
        stage_ids = stage_obj._search(cr, uid, search_domain, order=order, access_rights_uid=access_rights_uid, context=context)
        result = stage_obj.name_get(cr, access_rights_uid, stage_ids, context=context)
        # restore order of the search
        result.sort(lambda x,y: cmp(stage_ids.index(x[0]), stage_ids.index(y[0])))

        fold = {}
        for stage in stage_obj.browse(cr, access_rights_uid, stage_ids, context=context):
            fold[stage.id] = stage.fold or False
        return result, fold

    def _compute_day(self, cr, uid, ids, fields, args, context=None):
        """
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Openday’s IDs
        @return: difference between current date and log date
        @param context: A standard dictionary for contextual values
        """
        res = {}
        for issue in self.browse(cr, uid, ids, context=context):
            for field in fields:
                res[issue.id] = {}
                duration = 0
                ans = False
                hours = 0

                if field in ['day_open']:
                    if issue.date_open:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_open = datetime.strptime(issue.date_open, "%Y-%m-%d %H:%M:%S")
                        ans = date_open - date_create

                elif field in ['day_close']:
                    if issue.date_closed:
                        date_create = datetime.strptime(issue.create_date, "%Y-%m-%d %H:%M:%S")
                        date_close = datetime.strptime(issue.date_closed, "%Y-%m-%d %H:%M:%S")
                        ans = date_close - date_create
                if ans:
                    duration = float(ans.days)
                    res[issue.id][field] = abs(float(duration))
        return res

    def _get_attachment_number(self, cr, uid, ids, fields, args, context=None):
        res = dict.fromkeys(ids, 0)
        for app_id in ids:
            res[app_id] = self.pool['ir.attachment'].search_count(cr, uid, [('res_model', '=', 'hr.applicant'), ('res_id', '=', app_id)], context=context)
        return res

    _columns = {
        'name': fields.char('Subject / Application Name', required=True),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the case without removing it."),
        'description': fields.text('Description'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'probability': fields.float('Probability'),
        'partner_id': fields.many2one('res.partner', 'Contact'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage', track_visibility='onchange',
                        domain="['|', ('department_id', '=', department_id), ('department_id', '=', False)]"),
        'last_stage_id': fields.many2one('hr.recruitment.stage', 'Last Stage',
                                         help='Stage of the applicant before being in the current stage. Used for lost cases analysis.'),
        'categ_ids': fields.many2many('hr.applicant_category', string='Tags'),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
        'date_closed': fields.datetime('Closed', readonly=True, select=True),
        'date_open': fields.datetime('Assigned', readonly=True, select=True),
        'date_last_stage_update': fields.datetime('Last Stage Update', select=True),
        'date_action': fields.date('Next Action Date'),
        'title_action': fields.char('Next Action', size=64),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed_extra': fields.char('Proposed Salary Extra', help="Salary Proposed by the Organisation, extra advantages"),
        'salary_expected_extra': fields.char('Expected Salary Extra', help="Salary Expected by Applicant, extra advantages"),
        'salary_proposed': fields.float('Proposed Salary', help="Salary Proposed by the Organisation"),
        'salary_expected': fields.float('Expected Salary', help="Salary Expected by Applicant"),
        'availability': fields.integer('Availability', help="The number of days in which the applicant will be available to start working"),
        'partner_name': fields.char("Applicant's Name"),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'type_id': fields.many2one('hr.recruitment.degree', 'Degree'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'survey': fields.related('job_id', 'survey_id', type='many2one', relation='survey.survey', string='Survey'),
        'response_id': fields.many2one('survey.user_input', "Response", ondelete='set null', oldname="response"),
        'reference': fields.char('Referred By'),
        'source_id': fields.many2one('hr.recruitment.source', 'Source'),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'color': fields.integer('Color Index'),
        'emp_id': fields.many2one('hr.employee', string='Employee', help='Employee linked to the applicant.'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
        'attachment_number': fields.function(_get_attachment_number, string='Number of Attachments', type="integer"),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': lambda s, cr, uid, c: uid,
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'department_id': lambda s, cr, uid, c: s._get_default_department_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s._get_default_company_id(cr, uid, s._get_default_department_id(cr, uid, c), c),
        'color': 0,
        'date_last_stage_update': fields.datetime.now,
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def onchange_job(self, cr, uid, ids, job_id=False, context=None):
        department_id = False
        if job_id:
            job_record = self.pool.get('hr.job').browse(cr, uid, job_id, context=context)
            department_id = job_record and job_record.department_id and job_record.department_id.id or False
            user_id = job_record and job_record.user_id and job_record.user_id.id or False
        return {'value': {'department_id': department_id, 'user_id': user_id}}

    def onchange_department_id(self, cr, uid, ids, department_id=False, stage_id=False, context=None):
        if not stage_id:
            stage_id = self.stage_find(cr, uid, [], department_id, [('fold', '=', False)], context=context)
        return {'value': {'stage_id': stage_id}}

    def onchange_partner_id(self, cr, uid, ids, partner_id, context=None):
        data = {'partner_phone': False,
                'partner_mobile': False,
                'email_from': False}
        if partner_id:
            addr = self.pool.get('res.partner').browse(cr, uid, partner_id, context)
            data.update({'partner_phone': addr.phone,
                        'partner_mobile': addr.mobile,
                        'email_from': addr.email})
        return {'value': data}

    def stage_find(self, cr, uid, cases, section_id, domain=[], order='sequence', context=None):
        """ Override of the base.stage method
            Parameter of the stage search taken from the lead:
            - department_id: if set, stages must belong to this section or
              be a default case
        """
        if isinstance(cases, (int, long)):
            cases = self.browse(cr, uid, cases, context=context)
        # collect all section_ids
        department_ids = []
        if section_id:
            department_ids.append(section_id)
        for case in cases:
            if case.department_id:
                department_ids.append(case.department_id.id)
        # OR all section_ids and OR with case_default
        search_domain = []
        if department_ids:
            search_domain += ['|', ('department_id', 'in', department_ids)]
        search_domain.append(('department_id', '=', False))
        # AND with the domain in parameter
        search_domain += list(domain)
        # perform search, return the first found
        stage_ids = self.pool.get('hr.recruitment.stage').search(cr, uid, search_domain, order=order, context=context)
        if stage_ids:
            return stage_ids[0]
        return False

    def action_makeMeeting(self, cr, uid, ids, context=None):
        """ This opens Meeting's calendar view to schedule meeting on current applicant
            @return: Dictionary value for created Meeting view
        """
        applicant = self.browse(cr, uid, ids[0], context)
        applicant_ids = []
        if applicant.partner_id:
            applicant_ids.append(applicant.partner_id.id)
        if applicant.department_id and applicant.department_id.manager_id and applicant.department_id.manager_id.user_id and applicant.department_id.manager_id.user_id.partner_id:
            applicant_ids.append(applicant.department_id.manager_id.user_id.partner_id.id)
        category = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_recruitment', 'categ_meet_interview', context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'calendar', 'action_calendar_event', context)
        res['context'] = {
            'default_partner_ids': applicant_ids,
            'default_user_id': uid,
            'default_name': applicant.name,
            'default_categ_ids': category and [category.id] or False,
        }
        return res

    def action_start_survey(self, cr, uid, ids, context=None):
        context = context if context else {}
        applicant = self.browse(cr, uid, ids, context=context)[0]
        survey_obj = self.pool.get('survey.survey')
        response_obj = self.pool.get('survey.user_input')
        # create a response and link it to this applicant
        if not applicant.response_id:
            response_id = response_obj.create(cr, uid, {'survey_id': applicant.survey.id, 'partner_id': applicant.partner_id.id}, context=context)
            self.write(cr, uid, ids[0], {'response_id': response_id}, context=context)
        else:
            response_id = applicant.response_id.id
        # grab the token of the response and start surveying
        response = response_obj.browse(cr, uid, response_id, context=context)
        context.update({'survey_token': response.token})
        return survey_obj.action_start_survey(cr, uid, [applicant.survey.id], context=context)

    def action_print_survey(self, cr, uid, ids, context=None):
        """ If response is available then print this response otherwise print survey form (print template of the survey) """
        context = context if context else {}
        applicant = self.browse(cr, uid, ids, context=context)[0]
        survey_obj = self.pool.get('survey.survey')
        response_obj = self.pool.get('survey.user_input')
        if not applicant.response_id:
            return survey_obj.action_print_survey(cr, uid, [applicant.survey.id], context=context)
        else:
            response = response_obj.browse(cr, uid, applicant.response_id.id, context=context)
            context.update({'survey_token': response.token})
            return survey_obj.action_print_survey(cr, uid, [applicant.survey.id], context=context)

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['&', ('res_model', '=', self._name), ('res_id', 'in', ids)])
        return action

    def message_get_reply_to(self, cr, uid, ids, context=None):
        """ Override to get the reply_to of the parent project. """
        applicants = self.browse(cr, SUPERUSER_ID, ids, context=context)
        job_ids = set([applicant.job_id.id for applicant in applicants if applicant.job_id])
        aliases = self.pool['project.project'].message_get_reply_to(cr, uid, list(job_ids), context=context)
        return dict((applicant.id, aliases.get(applicant.job_id and applicant.job_id.id or 0, False)) for applicant in applicants)

    def message_get_suggested_recipients(self, cr, uid, ids, context=None):
        recipients = super(hr_applicant, self).message_get_suggested_recipients(cr, uid, ids, context=context)
        for applicant in self.browse(cr, uid, ids, context=context):
            if applicant.partner_id:
                self._message_add_suggested_recipient(cr, uid, recipients, applicant, partner=applicant.partner_id, reason=_('Contact'))
            elif applicant.email_from:
                self._message_add_suggested_recipient(cr, uid, recipients, applicant, email=applicant.email_from, reason=_('Contact Email'))
        return recipients

    def message_new(self, cr, uid, msg, custom_values=None, context=None):
        """ Overrides mail_thread message_new that is called by the mailgateway
            through message_process.
            This override updates the document according to the email.
        """
        if custom_values is None:
            custom_values = {}
        val = msg.get('from').split('<')[0]
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'partner_name': val,
            'email_from': msg.get('from'),
            'email_cc': msg.get('cc'),
            'user_id': False,
            'partner_id': msg.get('author_id', False),
        }
        if msg.get('priority'):
            defaults['priority'] = msg.get('priority')
        defaults.update(custom_values)
        return super(hr_applicant, self).message_new(cr, uid, msg, custom_values=defaults, context=context)

    def create(self, cr, uid, vals, context=None):
        if context is None:
            context = {}
        context['mail_create_nolog'] = True
        if vals.get('department_id') and not context.get('default_department_id'):
            context['default_department_id'] = vals.get('department_id')
        if vals.get('job_id') or context.get('default_job_id'):
            job_id = vals.get('job_id') or context.get('default_job_id')
            vals.update(self.onchange_job(cr, uid, [], job_id, context=context)['value'])
        obj_id = super(hr_applicant, self).create(cr, uid, vals, context=context)
        applicant = self.browse(cr, uid, obj_id, context=context)
        if applicant.job_id:
            name = applicant.partner_name if applicant.partner_name else applicant.name
            self.pool['hr.job'].message_post(
                cr, uid, [applicant.job_id.id],
                body=_('New application from %s') % name,
                subtype="hr_recruitment.mt_job_applicant_new", context=context)
        return obj_id

    def write(self, cr, uid, ids, vals, context=None):
        if isinstance(ids, (int, long)):
            ids = [ids]
        res = True

        # user_id change: update date_open
        if vals.get('user_id'):
            vals['date_open'] = fields.datetime.now()
        # stage_id: track last stage before update
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = fields.datetime.now()
            for applicant in self.browse(cr, uid, ids, context=None):
                vals['last_stage_id'] = applicant.stage_id.id
                res = super(hr_applicant, self).write(cr, uid, [applicant.id], vals, context=context)
        else:
            res = super(hr_applicant, self).write(cr, uid, ids, vals, context=context)

        # post processing: if job changed, post a message on the job
        if vals.get('job_id'):
            for applicant in self.browse(cr, uid, ids, context=None):
                name = applicant.partner_name if applicant.partner_name else applicant.name
                self.pool['hr.job'].message_post(
                    cr, uid, [vals['job_id']],
                    body=_('New application from %s') % name,
                    subtype="hr_recruitment.mt_job_applicant_new", context=context)

        # post processing: if stage changed, post a message in the chatter
        if vals.get('stage_id'):
            stage = self.pool['hr.recruitment.stage'].browse(cr, uid, vals['stage_id'], context=context)
            if stage.template_id:
                # TDENOTE: probably factorize me in a message_post_with_template generic method FIXME
                compose_ctx = dict(context,
                                   active_ids=ids)
                compose_id = self.pool['mail.compose.message'].create(
                    cr, uid, {
                        'model': self._name,
                        'composition_mode': 'mass_mail',
                        'template_id': stage.template_id.id,
                        'same_thread': True,
                        'post': True,
                        'notify': True,
                    }, context=compose_ctx)
                self.pool['mail.compose.message'].write(
                    cr, uid, [compose_id],
                    self.pool['mail.compose.message'].onchange_template_id(
                        cr, uid, [compose_id],
                        stage.template_id.id, 'mass_mail', self._name, False,
                        context=compose_ctx)['value'],
                    context=compose_ctx)
                self.pool['mail.compose.message'].send_mail(cr, uid, [compose_id], context=compose_ctx)
        return res

    def create_employee_from_applicant(self, cr, uid, ids, context=None):
        """ Create an hr.employee from the hr.applicants """
        if context is None:
            context = {}
        hr_employee = self.pool.get('hr.employee')
        model_data = self.pool.get('ir.model.data')
        act_window = self.pool.get('ir.actions.act_window')
        emp_id = False
        for applicant in self.browse(cr, uid, ids, context=context):
            address_id = contact_name = False
            if applicant.partner_id:
                address_id = self.pool.get('res.partner').address_get(cr, uid, [applicant.partner_id.id], ['contact'])['contact']
                contact_name = self.pool.get('res.partner').name_get(cr, uid, [applicant.partner_id.id])[0][1]
            if applicant.job_id and (applicant.partner_name or contact_name):
                applicant.job_id.write({'no_of_hired_employee': applicant.job_id.no_of_hired_employee + 1}, context=context)
                create_ctx = dict(context, mail_broadcast=True)
                emp_id = hr_employee.create(cr, uid, {'name': applicant.partner_name or contact_name,
                                                     'job_id': applicant.job_id.id,
                                                     'address_home_id': address_id,
                                                     'department_id': applicant.department_id.id or False,
                                                     'address_id': applicant.company_id and applicant.company_id.partner_id and applicant.company_id.partner_id.id or False,
                                                     'work_email': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.email or False,
                                                     'work_phone': applicant.department_id and applicant.department_id.company_id and applicant.department_id.company_id.phone or False,
                                                     }, context=create_ctx)
                self.write(cr, uid, [applicant.id], {'emp_id': emp_id}, context=context)
                self.pool['hr.job'].message_post(
                    cr, uid, [applicant.job_id.id],
                    body=_('New Employee %s Hired') % applicant.partner_name if applicant.partner_name else applicant.name,
                    subtype="hr_recruitment.mt_job_applicant_hired", context=context)
            else:
                raise osv.except_osv(_('Warning!'), _('You must define an Applied Job and a Contact Name for this applicant.'))

        action_model, action_id = model_data.get_object_reference(cr, uid, 'hr', 'open_view_employee_list')
        dict_act_window = act_window.read(cr, uid, action_id, [])
        if emp_id:
            dict_act_window['res_id'] = emp_id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

    def get_empty_list_help(self, cr, uid, help, context=None):
        context['empty_list_help_model'] = 'hr.job'
        context['empty_list_help_id'] = context.get('default_job_id', None)
        context['empty_list_help_document_name'] = _("job applicants")
        return super(hr_applicant, self).get_empty_list_help(cr, uid, help, context=context)


class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _inherits = {'mail.alias': 'alias_id'}

    def _get_attached_docs(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        attachment_obj = self.pool.get('ir.attachment')
        for job_id in ids:
            applicant_ids = self.pool.get('hr.applicant').search(cr, uid, [('job_id', '=', job_id)], context=context)
            res[job_id] = attachment_obj.search(
                cr, uid, [
                    '|',
                    '&', ('res_model', '=', 'hr.job'), ('res_id', '=', job_id),
                    '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicant_ids)
                ], context=context)
        return res

    def _count_all(self, cr, uid, ids, field_name, arg, context=None):
        Applicant = self.pool['hr.applicant']
        return {
            job_id: {
                'application_count': Applicant.search_count(cr,uid, [('job_id', '=', job_id)], context=context),
                'documents_count': len(self._get_attached_docs(cr, uid, [job_id], field_name, arg, context=context)[job_id])
            }
            for job_id in ids
        }

    _columns = {
        'survey_id': fields.many2one('survey.survey', 'Interview Form', help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job"),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                    help="Email alias for this job position. New emails will automatically "
                                         "create new applicants for this job position."),
        'address_id': fields.many2one('res.partner', 'Job Location', help="Address where employees are working"),
        'application_ids': fields.one2many('hr.applicant', 'job_id', 'Applications'),
        'application_count': fields.function(_count_all, type='integer', string='Applications', multi=True),
        'manager_id': fields.related('department_id', 'manager_id', type='many2one', string='Department Manager', relation='hr.employee', readonly=True, store=True),
        'document_ids': fields.function(_get_attached_docs, type='one2many', relation='ir.attachment', string='Applications'),
        'documents_count': fields.function(_count_all, type='integer', string='Documents', multi=True),
        'user_id': fields.many2one('res.users', 'Recruitment Responsible', track_visibility='onchange'),
        'color': fields.integer('Color Index'),
    }

    def _address_get(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user.company_id.partner_id.id

    _defaults = {
        'address_id': _address_get
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all jobs and avoid constraint errors."""
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(hr_job, self)._auto_init,
            'hr.applicant', self._columns['alias_id'], 'name', alias_prefix='job+', alias_defaults={'job_id': 'id'}, context=context)

    def create(self, cr, uid, vals, context=None):
        alias_context = dict(context, alias_model_name='hr.applicant', alias_parent_model_name=self._name)
        job_id = super(hr_job, self).create(cr, uid, vals, context=alias_context)
        job = self.browse(cr, uid, job_id, context=context)
        self.pool.get('mail.alias').write(cr, uid, [job.alias_id.id], {'alias_parent_thread_id': job_id, "alias_defaults": {'job_id': job_id}}, context)
        return job_id

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the job position.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [job.alias_id.id for job in self.browse(cr, uid, ids, context=context) if job.alias_id]
        res = super(hr_job, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def action_print_survey(self, cr, uid, ids, context=None):
        job = self.browse(cr, uid, ids, context=context)[0]
        survey_id = job.survey_id.id
        return self.pool.get('survey.survey').action_print_survey(cr, uid, [survey_id], context=context)

    def action_get_attachment_tree_view(self, cr, uid, ids, context=None):
        #open attachments of job and related applicantions.
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'action_attachment')
        action = self.pool.get(model).read(cr, uid, action_id, context=context)
        applicant_ids = self.pool.get('hr.applicant').search(cr, uid, [('job_id', 'in', ids)], context=context)
        action['context'] = {'default_res_model': self._name, 'default_res_id': ids[0]}
        action['domain'] = str(['|', '&', ('res_model', '=', 'hr.job'), ('res_id', 'in', ids), '&', ('res_model', '=', 'hr.applicant'), ('res_id', 'in', applicant_ids)])
        return action

    def action_set_no_of_recruitment(self, cr, uid, id, value, context=None):
        return self.write(cr, uid, [id], {'no_of_recruitment': value}, context=context)


class applicant_category(osv.osv):
    """ Category of applicant """
    _name = "hr.applicant_category"
    _description = "Category of applicant"
    _columns = {
        'name': fields.char('Name', required=True, translate=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
