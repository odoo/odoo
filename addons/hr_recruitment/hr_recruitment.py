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

import time
from openerp import tools

from openerp.addons.base_status.base_stage import base_stage
from datetime import datetime
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools import html2plaintext

AVAILABLE_STATES = [
    ('draft', 'New'),
    ('cancel', 'Refused'),
    ('open', 'In Progress'),
    ('pending', 'Pending'),
    ('done', 'Hired')
]

AVAILABLE_PRIORITIES = [
    ('', ''),
    ('5', 'Not Good'),
    ('4', 'On Average'),
    ('3', 'Good'),
    ('2', 'Very Good'),
    ('1', 'Excellent')
]

class hr_recruitment_source(osv.osv):
    """ Sources of HR Recruitment """
    _name = "hr.recruitment.source"
    _description = "Source of Applicants"
    _columns = {
        'name': fields.char('Source Name', size=64, required=True, translate=True),
    }

class hr_recruitment_stage(osv.osv):
    """ Stage of HR Recruitment """
    _name = "hr.recruitment.stage"
    _description = "Stage of Recruitment"
    _order = 'sequence'
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of stages."),
        'department_id':fields.many2one('hr.department', 'Specific to a Department', help="Stages of the recruitment process may be different per department. If this stage is common to all departments, keep this field empty."),
        'state': fields.selection(AVAILABLE_STATES, 'Status', required=True, help="The related status for the stage. The status of your document will automatically change according to the selected stage. Example, a stage is related to the status 'Close', when your document reach this stage, it will be automatically closed."),
        'fold': fields.boolean('Hide in views if empty', help="This stage is not visible, for example in status bar or kanban view, when there are no records in that stage to display."),
        'requirements': fields.text('Requirements'),
    }
    _defaults = {
        'sequence': 1,
        'state': 'draft',
        'fold': False,
    }

class hr_recruitment_degree(osv.osv):
    """ Degree of HR Recruitment """
    _name = "hr.recruitment.degree"
    _description = "Degree of Recruitment"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
        'sequence': fields.integer('Sequence', help="Gives the sequence order when displaying a list of degrees."),
    }
    _defaults = {
        'sequence': 1,
    }
    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'The name of the Degree of Recruitment must be unique!')
    ]

class hr_applicant(base_stage, osv.Model):
    _name = "hr.applicant"
    _description = "Applicant"
    _order = "id desc"
    _inherit = ['mail.thread', 'ir.needaction_mixin']
    _track = {
        'state': {
            'hr_recruitment.mt_applicant_hired': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'done',
            'hr_recruitment.mt_applicant_refused': lambda self, cr, uid, obj, ctx=None: obj['state'] == 'cancel',
        },
        'stage_id': {
            'hr_recruitment.mt_stage_changed': lambda self, cr, uid, obj, ctx=None: obj['state'] not in ['done', 'cancel'],
        },
    }

    def _get_default_department_id(self, cr, uid, context=None):
        """ Gives default department by checking if present in the context """
        return (self._resolve_department_id_from_context(cr, uid, context=context) or False)

    def _get_default_stage_id(self, cr, uid, context=None):
        """ Gives default stage_id """
        department_id = self._get_default_department_id(cr, uid, context=context)
        return self.stage_find(cr, uid, [], department_id, [('state', '=', 'draft')], context=context)

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

    _columns = {
        'name': fields.char('Subject', size=128, required=True),
        'active': fields.boolean('Active', help="If the active field is set to false, it will allow you to hide the case without removing it."),
        'description': fields.text('Description'),
        'email_from': fields.char('Email', size=128, help="These people will receive email."),
        'email_cc': fields.text('Watchers Emails', size=252, help="These email addresses will be added to the CC field of all inbound and outbound emails for this record before being sent. Separate multiple email addresses with a comma"),
        'probability': fields.float('Probability'),
        'partner_id': fields.many2one('res.partner', 'Contact'),
        'create_date': fields.datetime('Creation Date', readonly=True, select=True),
        'write_date': fields.datetime('Update Date', readonly=True),
        'stage_id': fields.many2one ('hr.recruitment.stage', 'Stage', track_visibility='onchange',
                        domain="['&', ('fold', '=', False), '|', ('department_id', '=', department_id), ('department_id', '=', False)]"),
        'state': fields.related('stage_id', 'state', type="selection", store=True,
                selection=AVAILABLE_STATES, string="Status", readonly=True,
                help='The status is set to \'Draft\', when a case is created.\
                      If the case is in progress the status is set to \'Open\'.\
                      When the case is over, the status is set to \'Done\'.\
                      If the case needs to be reviewed then the status is \
                      set to \'Pending\'.'),
        'categ_ids': fields.many2many('hr.applicant_category', string='Tags'),
        'company_id': fields.many2one('res.company', 'Company'),
        'user_id': fields.many2one('res.users', 'Responsible', track_visibility='onchange'),
        # Applicant Columns
        'date_closed': fields.datetime('Closed', readonly=True, select=True),
        'date_open': fields.datetime('Opened', readonly=True, select=True),
        'date': fields.datetime('Date'),
        'date_action': fields.date('Next Action Date'),
        'title_action': fields.char('Next Action', size=64),
        'priority': fields.selection(AVAILABLE_PRIORITIES, 'Appreciation'),
        'job_id': fields.many2one('hr.job', 'Applied Job'),
        'salary_proposed_extra': fields.char('Proposed Salary Extra', size=100, help="Salary Proposed by the Organisation, extra advantages"),
        'salary_expected_extra': fields.char('Expected Salary Extra', size=100, help="Salary Expected by Applicant, extra advantages"),
        'salary_proposed': fields.float('Proposed Salary', help="Salary Proposed by the Organisation"),
        'salary_expected': fields.float('Expected Salary', help="Salary Expected by Applicant"),
        'availability': fields.integer('Availability'),
        'partner_name': fields.char("Applicant's Name", size=64),
        'partner_phone': fields.char('Phone', size=32),
        'partner_mobile': fields.char('Mobile', size=32),
        'type_id': fields.many2one('hr.recruitment.degree', 'Degree'),
        'department_id': fields.many2one('hr.department', 'Department'),
        'survey': fields.related('job_id', 'survey_id', type='many2one', relation='survey', string='Survey'),
        'response': fields.integer("Response"),
        'reference': fields.char('Referred By', size=128),
        'source_id': fields.many2one('hr.recruitment.source', 'Source'),
        'day_open': fields.function(_compute_day, string='Days to Open', \
                                multi='day_open', type="float", store=True),
        'day_close': fields.function(_compute_day, string='Days to Close', \
                                multi='day_close', type="float", store=True),
        'color': fields.integer('Color Index'),
        'emp_id': fields.many2one('hr.employee', 'employee'),
        'user_email': fields.related('user_id', 'email', type='char', string='User Email', readonly=True),
    }

    _defaults = {
        'active': lambda *a: 1,
        'user_id': lambda s, cr, uid, c: uid,
        'email_from': lambda s, cr, uid, c: s._get_default_email(cr, uid, c),
        'stage_id': lambda s, cr, uid, c: s._get_default_stage_id(cr, uid, c),
        'department_id': lambda s, cr, uid, c: s._get_default_department_id(cr, uid, c),
        'company_id': lambda s, cr, uid, c: s._get_default_company_id(cr, uid, s._get_default_department_id(cr, uid, c), c),
        'color': 0,
    }

    _group_by_full = {
        'stage_id': _read_group_stage_ids
    }

    def onchange_job(self, cr, uid, ids, job, context=None):
        if job:
            job_record = self.pool.get('hr.job').browse(cr, uid, job, context=context)
            if job_record and job_record.department_id:
                return {'value': {'department_id': job_record.department_id.id}}
        return {}

    def onchange_department_id(self, cr, uid, ids, department_id=False, context=None):
        obj_recru_stage = self.pool.get('hr.recruitment.stage')
        stage_ids = obj_recru_stage.search(cr, uid, ['|',('department_id','=',department_id),('department_id','=',False)], context=context)
        stage_id = stage_ids and stage_ids[0] or False
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
        category = self.pool.get('ir.model.data').get_object(cr, uid, 'hr_recruitment', 'categ_meet_interview', context)
        res = self.pool.get('ir.actions.act_window').for_xml_id(cr, uid, 'base_calendar', 'action_crm_meeting', context)
        res['context'] = {
            'default_partner_ids': applicant.partner_id and [applicant.partner_id.id] or False,
            'default_user_id': uid,
            'default_name': applicant.name,
            'default_categ_ids': category and [category.id] or False,
        }
        return res

    def action_print_survey(self, cr, uid, ids, context=None):
        """
        If response is available then print this response otherwise print survey form(print template of the survey).

        @param self: The object pointer
        @param cr: the current row, from the database cursor,
        @param uid: the current user’s ID for security checks,
        @param ids: List of Survey IDs
        @param context: A standard dictionary for contextual values
        @return: Dictionary value for print survey form.
        """
        if context is None:
            context = {}
        record = self.browse(cr, uid, ids, context=context)
        record = record and record[0]
        context.update({'survey_id': record.survey.id, 'response_id': [record.response], 'response_no': 0, })
        value = self.pool.get("survey").action_print_survey(cr, uid, ids, context=context)
        return value

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
        desc = html2plaintext(msg.get('body')) if msg.get('body') else ''
        defaults = {
            'name':  msg.get('subject') or _("No Subject"),
            'description': desc,
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
        if vals.get('department_id') and not context.get('default_department_id'):
            context['default_department_id'] = vals.get('department_id')

        obj_id = super(hr_applicant, self).create(cr, uid, vals, context=context)
        applicant = self.browse(cr, uid, obj_id, context=context)
        if applicant.job_id:
            self.pool.get('hr.job').message_post(cr, uid, [applicant.job_id.id], body=_('Applicant <b>created</b>'), subtype="hr_recruitment.mt_job_new_applicant", context=context)
        return obj_id

    def case_open(self, cr, uid, ids, context=None):
        """
            open Request of the applicant for the hr_recruitment
        """
        res = super(hr_applicant, self).case_open(cr, uid, ids, context)
        date = self.read(cr, uid, ids, ['date_open'])[0]
        if not date['date_open']:
            self.write(cr, uid, ids, {'date_open': time.strftime('%Y-%m-%d %H:%M:%S'),})
        return res

    def case_close(self, cr, uid, ids, context=None):
        res = super(hr_applicant, self).case_close(cr, uid, ids, context)
        return res

    def case_close_with_emp(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        hr_employee = self.pool.get('hr.employee')
        model_data = self.pool.get('ir.model.data')
        act_window = self.pool.get('ir.actions.act_window')
        emp_id = False
        for applicant in self.browse(cr, uid, ids, context=context):
            address_id = False
            if applicant.partner_id:
                address_id = self.pool.get('res.partner').address_get(cr,uid,[applicant.partner_id.id],['contact'])['contact']
            if applicant.job_id:
                applicant.job_id.write({'no_of_recruitment': applicant.job_id.no_of_recruitment - 1})
                emp_id = hr_employee.create(cr,uid,{'name': applicant.partner_name or applicant.name,
                                                     'job_id': applicant.job_id.id,
                                                     'address_home_id': address_id,
                                                     'department_id': applicant.department_id.id
                                                     })
                self.write(cr, uid, [applicant.id], {'emp_id': emp_id}, context=context)
                self.case_close(cr, uid, [applicant.id], context)
            else:
                raise osv.except_osv(_('Warning!'), _('You must define Applied Job for this applicant.'))

        action_model, action_id = model_data.get_object_reference(cr, uid, 'hr', 'open_view_employee_list')
        dict_act_window = act_window.read(cr, uid, action_id, [])
        if emp_id:
            dict_act_window['res_id'] = emp_id
        dict_act_window['view_mode'] = 'form,tree'
        return dict_act_window

    def case_cancel(self, cr, uid, ids, context=None):
        """Overrides cancel for crm_case for setting probability
        """
        res = super(hr_applicant, self).case_cancel(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability': 0.0})
        return res

    def case_pending(self, cr, uid, ids, context=None):
        """Marks case as pending"""
        res = super(hr_applicant, self).case_pending(cr, uid, ids, context)
        self.write(cr, uid, ids, {'probability': 0.0})
        return res

    def case_reset(self, cr, uid, ids, context=None):
        """Resets case as draft
        """
        res = super(hr_applicant, self).case_reset(cr, uid, ids, context)
        self.write(cr, uid, ids, {'date_open': False, 'date_closed': False})
        return res

    def set_priority(self, cr, uid, ids, priority, *args):
        """Set applicant priority
        """
        return self.write(cr, uid, ids, {'priority': priority})

    def set_high_priority(self, cr, uid, ids, *args):
        """Set applicant priority to high
        """
        return self.set_priority(cr, uid, ids, '1')

    def set_normal_priority(self, cr, uid, ids, *args):
        """Set applicant priority to normal
        """
        return self.set_priority(cr, uid, ids, '3')


class hr_job(osv.osv):
    _inherit = "hr.job"
    _name = "hr.job"
    _inherits = {'mail.alias': 'alias_id'}
    _columns = {
        'survey_id': fields.many2one('survey', 'Interview Form', help="Choose an interview form for this job position and you will be able to print/answer this interview from all applicants who apply for this job"),
        'alias_id': fields.many2one('mail.alias', 'Alias', ondelete="restrict", required=True,
                                    help="Email alias for this job position. New emails will automatically "
                                         "create new applicants for this job position."),
    }
    _defaults = {
        'alias_domain': False, # always hide alias during creation
    }

    def _auto_init(self, cr, context=None):
        """Installation hook to create aliases for all jobs and avoid constraint errors."""
        if context is None:
            context = {}
        alias_context = dict(context, alias_model_name='hr.applicant')
        return self.pool.get('mail.alias').migrate_to_alias(cr, self._name, self._table, super(hr_job, self)._auto_init,
            self._columns['alias_id'], 'name', alias_prefix='job+', alias_defaults={'job_id': 'id'}, context=alias_context)

    def create(self, cr, uid, vals, context=None):
        mail_alias = self.pool.get('mail.alias')
        if not vals.get('alias_id'):
            vals.pop('alias_name', None) # prevent errors during copy()
            alias_id = mail_alias.create_unique_alias(cr, uid,
                          # Using '+' allows using subaddressing for those who don't
                          # have a catchall domain setup.
                          {'alias_name': 'jobs+'+vals['name']},
                          model_name="hr.applicant",
                          context=context)
            vals['alias_id'] = alias_id
        res = super(hr_job, self).create(cr, uid, vals, context)
        mail_alias.write(cr, uid, [vals['alias_id']], {"alias_defaults": {'job_id': res}}, context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        # Cascade-delete mail aliases as well, as they should not exist without the job position.
        mail_alias = self.pool.get('mail.alias')
        alias_ids = [job.alias_id.id for job in self.browse(cr, uid, ids, context=context) if job.alias_id]
        res = super(hr_job, self).unlink(cr, uid, ids, context=context)
        mail_alias.unlink(cr, uid, alias_ids, context=context)
        return res

    def action_print_survey(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        datas = {}
        record = self.browse(cr, uid, ids, context=context)[0]
        if record.survey_id:
            datas['ids'] = [record.survey_id.id]
        datas['model'] = 'survey.print'
        context.update({'response_id': [0], 'response_no': 0,})
        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'survey.form',
            'datas': datas,
            'context' : context,
            'nodestroy':True,
        }

class applicant_category(osv.osv):
    """ Category of applicant """
    _name = "hr.applicant_category"
    _description = "Category of applicant"
    _columns = {
        'name': fields.char('Name', size=64, required=True, translate=True),
    }
