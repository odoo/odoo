# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from markupsafe import Markup, escape
from werkzeug.urls import url_encode

from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.misc import str2bool


class Applicant(models.Model):
    _inherit = ["hr.applicant"]

    ref_user_id = fields.Many2one('res.users', string='Referred By User', tracking=True,
        compute='_compute_ref_user_id', inverse='_inverse_ref_user_id', store=True, copy=False)
    referral_points_ids = fields.One2many('hr.referral.points', 'applicant_id', copy=False)
    earned_points = fields.Integer(compute='_compute_earned_points')
    referral_state = fields.Selection([
        ('progress', 'In Progress'),
        ('hired', 'Hired'),
        ('closed', 'Not Hired')], required=True, default='progress')
    shared_item_infos = fields.Text(compute="_compute_shared_item_infos")
    max_points = fields.Integer(related="job_id.max_points")
    friend_id = fields.Many2one('hr.referral.friend', copy=False)
    last_valuable_stage_id = fields.Many2one('hr.recruitment.stage', "Last Valuable Stage")
    is_accessible_to_current_user = fields.Boolean(
        compute='_compute_is_accessible_to_current_user',
        search='_search_is_accessible_to_current_user')

    def _search_is_accessible_to_current_user(self, operator, value):
        if not isinstance(value, bool) or operator not in ['=', '!=']:
            raise NotImplementedError(_("Unsupported search on field is_accessible_to_current_user: %s operator & %s value. Only = and != operator and boolean values are supported.", operator, value))
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            return []
        applications = self.env['hr.applicant'].with_context(active_test=False).search([
            '|',
                ('job_id', 'any', [('interviewer_ids', 'in', self.env.user.id)]),
                ('interviewer_ids', 'in', self.env.user.id),
        ])
        domain_operator = 'in' if value ^ (operator == '!=') else 'not in'
        return [('id', domain_operator, applications.ids)]

    @api.depends_context('uid')
    def _compute_is_accessible_to_current_user(self):
        if self.env.user.has_group('hr_recruitment.group_hr_recruitment_user'):
            self.is_accessible_to_current_user = True
        else:
            for applicant in self:
                interviewers = applicant.interviewer_ids
                corresponding_job_interviewers = applicant.job_id.interviewer_ids
                applicant.is_accessible_to_current_user = self.env.user in interviewers or self.env.user in corresponding_job_interviewers
                if not applicant.is_accessible_to_current_user:
                    raise AccessError(_("You are not allowed to access this application record because you're not one of the interviewers of this application. If you think that's an error, please contact your administrator."))

    @api.depends('source_id')
    def _compute_ref_user_id(self):
        for applicant in self:
            if applicant.source_id:
                applicant.ref_user_id = self.env['res.users'].search([('utm_source_id', '=', applicant.source_id.id)], limit=1)
            else:
                applicant.ref_user_id = False

    def _inverse_ref_user_id(self):
        for applicant in self:
            applicant.source_id = applicant.ref_user_id.utm_source_id

    def _check_referral_fields_access(self, fields):
        referral_fields = {'name', 'partner_name', 'job_id', 'referral_points_ids', 'earned_points', 'max_points', 'active', 'response_id',
                           'shared_item_infos', 'referral_state', 'user_id', 'friend_id', 'write_date', 'ref_user_id', 'id'}
        if not (self.env.is_admin() or self.user_has_groups('hr_recruitment.group_hr_recruitment_interviewer')):
            if set(fields or []) - referral_fields:
                raise AccessError(_('You are not allowed to access applicant records.'))

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        self._check_referral_fields_access(fields)
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    def read(self, fields=None, load='_classic_read'):
        self._check_referral_fields_access(fields)
        return super().read(fields, load)

    @api.model
    def _read_group_check_field_access_rights(self, field_names):
        super()._read_group_check_field_access_rights(field_names)
        self._check_referral_fields_access(field_names)

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None, access_rights_uid=None):
        fields = {term[0] for term in domain if isinstance(term, (tuple, list))}
        self._check_referral_fields_access(fields)
        return super()._search(domain, offset, limit, order, access_rights_uid)

    def mapped(self, func):
        if func and isinstance(func, str):
            fields = func.split('.')
            self._check_referral_fields_access(fields)
        return super().mapped(func)

    def filtered_domain(self, domain):
        fields = [term[0] for term in domain if isinstance(term, (tuple, list))]
        self._check_referral_fields_access(fields)
        return super().filtered_domain(domain)

    @api.depends('referral_points_ids')
    def _compute_shared_item_infos(self):
        for applicant in self:
            stages = self.env['hr.recruitment.stage'].search([('use_in_referral', '=', True), '|', ('job_ids', '=', False), ('job_ids', '=', applicant.job_id.id)])
            infos = [{
                'name': stage.name,
                'points': stage.points,
                'done': bool(len(applicant.referral_points_ids.filtered(lambda point: point.stage_id == stage)) % 2),
                'seq': stage.sequence,
            } for stage in stages]
            applicant.shared_item_infos = json.dumps(infos)

    def _compute_earned_points(self):
        for applicant in self:
            applicant.earned_points = sum(applicant.referral_points_ids.mapped('points'))

    def write(self, vals):
        res = super(Applicant, self).write(vals)
        if 'ref_user_id' in vals or 'stage_id' in vals or 'date_closed' in vals:
            for applicant in self.filtered(lambda a: a.ref_user_id):
                if 'ref_user_id' in vals:
                    applicant.referral_points_ids.unlink()
                applicant.sudo()._update_points(applicant.stage_id.id, vals.get('last_stage_id', False))
                if 'stage_id' in vals and vals['stage_id']:
                    if self.env['hr.recruitment.stage'].browse(vals['stage_id']).use_in_referral:
                        applicant.last_valuable_stage_id = vals['stage_id']
                if 'date_closed' in vals:
                    if not vals['date_closed'] and not applicant.stage_id.hired_stage:
                        applicant.referral_state = 'progress'
        return res

    @api.model_create_multi
    def create(self, vals_list):
        applicants = super().create(vals_list)
        for applicant in applicants:
            if applicant.ref_user_id and applicant.stage_id:
                applicant.sudo()._update_points(applicant.stage_id.id, False)
                if applicant.stage_id.use_in_referral:
                    applicant.last_valuable_stage_id = applicant.stage_id
        return applicants

    def archive_applicant(self):
        for applicant in self:
            if applicant.ref_user_id:
                applicant._send_notification(_("Sorry, your referral %s has been refused in the recruitment process.", applicant.name))
        self.write({'referral_state': 'closed'})
        return super(Applicant, self).archive_applicant()

    def _send_notification(self, body):
        if self.partner_name:
            subject = _('Referral: %s (%s)', self.partner_name, self.name)
        else:
            subject = _('Referral: %s', self.name)
        url = url_encode({'action': 'hr_referral.action_hr_applicant_employee_referral', 'active_model': self._name})
        action_url = '/web#' + url
        body = Markup("<a class='o_document_link' href=%s>%s</a><br>%s") % (action_url, subject, body)
        odoobot = self.env.ref('base.partner_root')
        # Do *not* notify on `self` as it will lead to unintended behavior.
        # See opw-3285752
        self.env['mail.thread'].sudo().message_notify(
            model=self._name,
            subject=subject,
            body=body,
            author_id=odoobot.id,
            partner_ids=[self.ref_user_id.partner_id.id],
            email_layout_xmlid='mail.mail_notification_light',
        )

    def _update_points(self, new_state_id, old_state_id):
        if not self.company_id:
            raise UserError(_("Applicant must have a company."))
        new_state = self.env['hr.recruitment.stage'].browse(new_state_id)
        if not new_state.use_in_referral:
            return
        old_state = self.env['hr.recruitment.stage'].browse(old_state_id)
        if old_state and old_state.use_in_referral:
            old_state_sequence = old_state.sequence
        elif old_state:
            old_state_sequence = self.last_valuable_stage_id.sequence or -1
        else:
            old_state_sequence = -1
        point_stage = []

        # Decrease stage sequence
        if new_state.sequence < old_state_sequence:
            stages_to_remove = self.env['hr.referral.points']._read_group(
                [
                    ('applicant_id', '=', self.id),
                    ('stage_id.sequence', '<=', old_state_sequence),
                    ('stage_id.sequence', '>', new_state.sequence)
                ], ['stage_id'], ['points:sum'])
            for stage, point_sum in stages_to_remove:
                point_stage.append({
                    'applicant_id': self.id,
                    'stage_id': stage.id,
                    'points': - point_sum,
                    'ref_user_id': self.ref_user_id.id,
                    'company_id': self.company_id.id
                })
            if not self.date_closed and not new_state.hired_stage:
                self.referral_state = 'progress'

        # Increase stage sequence
        elif new_state.sequence > old_state_sequence:
            stages_to_add = self.env['hr.recruitment.stage'].search([
                ('use_in_referral', '=', True),
                ('sequence', '>', old_state_sequence), ('sequence', '<=', new_state.sequence),
                '|', ('job_ids', '=', False), ('job_ids', '=', self.job_id.id)])
            gained_points = 0
            available_points = sum(self.env['hr.referral.points'].search([('ref_user_id', '=', self.ref_user_id.id), ('company_id', '=', self.company_id.id)]).mapped('points'))
            for stage in stages_to_add:
                gained_points += stage.points
                point_stage.append({
                    'applicant_id': self.id,
                    'stage_id': stage.id,
                    'points': stage.points,
                    'sequence_stage': stage.sequence,
                    'ref_user_id': self.ref_user_id.id,
                    'company_id': self.company_id.id
                })
            available_points += gained_points
            additional_message = ''
            if gained_points > 0:
                additional_message = escape(_(
                    " You've gained {gained} points with this progress.{new_line}"
                    "It makes you a new total of {total} points. Visit {link1}this link{link2} to pick a gift!")).format(
                    gained=gained_points,
                    new_line=Markup('<br/>'),
                    total=available_points,
                    link1=Markup('<a href="/web#action=hr_referral.action_hr_referral_reward&active_model=hr.referral.reward">'),
                    link2=Markup('</a>'),
                )
            if self.stage_id.hired_stage:
                self.referral_state = 'hired'
                self._send_notification(_('Your referrer is hired!') + additional_message)
            else:
                self._send_notification(_('Your referrer got a step further!') + additional_message)

        self.env['hr.referral.points'].create(point_stage)
        self.invalidate_recordset(['earned_points'])

    def choose_a_friend(self, friend_id):
        self.ensure_one()
        self_sudo = self.sudo()
        if not self.env.user:
            return
        if self_sudo.ref_user_id == self.env.user and not self_sudo.friend_id:
            # Use sudo, user has normaly not the right to write on applicant
            self_sudo.write({'friend_id': friend_id})

    def _get_onboarding_steps(self):
        return [{
            'text': onboarding.text,
            'image': onboarding.image
        } for onboarding in self.env['hr.referral.onboarding'].search([])]

    def _get_friends(self, applicant_names):
        return [{
            'id': friend.id,
            'friend': applicant_names.get(friend.id, ''),
            'name': applicant_names.get(friend.id, friend.name),
            'position': friend.position,
            'image': friend.image,
        } for friend in self.env['hr.referral.friend'].search([]) if friend.id in applicant_names]

    def _get_friends_head(self, applicant_names):
        return [{
            'id': friend.id,
            'friend': applicant_names.get(friend.id, ''),
            'name': friend.name,
            'image': friend.image_head,
        } for friend in self.env['hr.referral.friend'].search([])]

    @api.model
    def retrieve_referral_data(self):
        return {
            'show_grass': str2bool(self.env["ir.config_parameter"].sudo().get_param('hr_referral.show_grass')),
        }

    @api.model
    def retrieve_referral_welcome_screen(self):
        result = self.retrieve_referral_data()
        user_id = self.env.user

        result['id'] = user_id.id
        if not user_id.hr_referral_onboarding_page:
            result['onboarding_screen'] = True
            result['onboarding'] = self._get_onboarding_steps()
            return result

        applicant = self.sudo().search([('ref_user_id', '=', user_id.id), ('company_id', 'in', self.env.companies.ids)])
        applicants_hired = applicant.filtered(lambda r: r.referral_state == 'hired')
        applicant_name = {applicant_hired.friend_id.id: applicant_hired.partner_name or applicant_hired.name for applicant_hired in applicants_hired}
        applicant_without_friend = applicants_hired.filtered(lambda r: not r.friend_id)

        # If there are applicant hired without friend and available friends.
        available_friend_count = self.env['hr.referral.friend'].search_count([])
        if bool(applicant_without_friend) and (len(applicants_hired) - len(applicant_without_friend) < available_friend_count):
            result['choose_new_friend'] = True
            result['new_friend_name'] = applicant_without_friend[0].partner_name or applicant_without_friend[0].name
            result['new_friend_id'] = applicant_without_friend[0].id

            result['friends'] = self._get_friends_head(applicant_name)
            return result

        result['friends'] = self._get_friends(applicant_name)

        referal_points = self.env['hr.referral.points'].search([('ref_user_id', '=', user_id.id)])
        result['point_received'] = sum(referal_points.filtered(lambda x: not x.hr_referral_reward_id).mapped('points'))
        result['point_to_spend'] = sum(referal_points.mapped('points'))

        # Employee comes for the first time on this app
        if not user_id.hr_referral_level_id:
            user_id.hr_referral_level_id = self.env['hr.referral.level'].search([], order='points asc', limit=1).id

        current_level = user_id.hr_referral_level_id
        next_level = self.env['hr.referral.level'].search([('points', '>', current_level.points)], order='points asc', limit=1)

        result['level'] = {
            'image': current_level.image,
            'name': current_level.name,
            'points': current_level.points
        }

        # Next referral levels
        result['level_percentage'] = 100
        if next_level:
            if result['point_received'] >= next_level['points']:
                result['reach_new_level'] = True
            step_level = next_level['points'] - current_level['points']
            result['level_percentage'] = round((min(result['point_received'], next_level['points']) - current_level['points']) * 100 / step_level)

        result['referral'] = {
            'all': len(applicant),
            'hired': len(applicant.filtered(lambda r: r.referral_state == 'hired')),
            'progress': len(applicant.filtered(lambda r: r.referral_state == 'progress')),
        }

        today = fields.Date.today()
        messages = self.env['hr.referral.alert'].search([
            ('active', '=', True), ('dismissed_user_ids', 'not in', self.env.user.id),
            '|', ('date_from', '<=', today), ('date_from', '=', False),
            '|', ('date_to', '>', today), ('date_to', '=', False)])

        result['message'] = []
        for message in messages:
            msg = {'id': message.id,
                   'text': message.name}
            if message.onclick == 'url':
                msg['url'] = message.url
            elif message.onclick == 'all_jobs':
                msg['url'] = '/web#%s' % url_encode({'action': 'hr_referral.action_hr_job_employee_referral'})
            result['message'].append(msg)

        return result

    @api.model
    def upgrade_level(self):
        if not self.env.user:
            return
        user_id = self.env.user
        user_points = sum(self.env['hr.referral.points'].search([
            ('ref_user_id', '=', user_id.id),
            ('hr_referral_reward_id', '=', False)]).mapped('points'))
        next_referral_level = self.env['hr.referral.level'].search([
            ('points', '>', user_id.hr_referral_level_id.points),
            ('points', '<=', user_points)
        ], order='points asc', limit=1)
        if next_referral_level:
            user_id.write({'hr_referral_level_id': next_referral_level.id})


class RecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    points = fields.Integer('Points', help="Amount of points that the referent will receive when the applicant will reach this stage")
    use_in_referral = fields.Boolean('Show in Referrals', help="This option is used in app 'Referrals'. If checked, the stage is displayed in 'Referrals Dashboard' and points are given to the employee.")
