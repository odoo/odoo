# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hashlib

from collections import defaultdict, OrderedDict
from odoo import fields, http, models, _, Command, SUPERUSER_ID

from odoo.addons.sign.controllers.main import Sign
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import consteq
from odoo.tools.image import image_data_uri
from werkzeug.exceptions import NotFound
from werkzeug.wsgi import get_current_url
from urllib.parse import urlparse, parse_qs
from datetime import datetime


class SignContract(Sign):

    @http.route()
    def sign(self, sign_request_id, token, sms_token=False, signature=None, **kwargs):
        result = super().sign(sign_request_id, token, sms_token=sms_token, signature=signature, **kwargs)
        if result.get('success'):
            request_item = request.env['sign.request.item'].sudo().search([('access_token', '=', token)])
            contract = request.env['hr.contract'].sudo().with_context(active_test=False).search([
                ('sign_request_ids', 'in', request_item.sign_request_id.ids)])
            offer = request.env['hr.contract.salary.offer'].sudo().search([
                ('sign_request_ids', 'in', request_item.sign_request_id.ids)])
            if offer.state in ['expired', 'refused']:
                raise UserError(_('This offer is outdated, please request an updated link...'))
            request_template_id = request_item.sign_request_id.template_id.id
            # Only if the signed document is the document to sign from the salary package
            contract_documents = [
                contract.sign_template_id.id,
                contract.contract_update_template_id.id,
            ]
            if contract and request_template_id in contract_documents:
                self._update_contract_on_signature(request_item, contract, offer)
                if request_item.sign_request_id.nb_closed == 1:
                    return dict(result, **{'url': '/salary_package/thank_you/' + str(contract.id)})
        return result

    def _update_contract_on_signature(self, request_item, contract, offer):
        # Only the applicant/employee has signed
        if request_item.sign_request_id.nb_closed == 1:
            contract.active = True
            contract.hash_token = False
            if contract.applicant_id:
                contract.applicant_id.emp_id = contract.employee_id
            self._create_activity_benefit(contract, 'running')
            contract.wage_on_signature = contract.wage_with_holidays
            offer.state = "half_signed"

        # Both applicant/employee and HR responsible have signed
        if request_item.sign_request_id.nb_closed == 2:
            if contract.employee_id:
                contract.employee_id.active = True
                if contract.applicant_id:
                    contract.applicant_id._move_to_hired_stage()
            if contract.employee_id.work_contact_id:
                contract.employee_id.work_contact_id.active = True
            self._create_activity_benefit(contract, 'countersigned')
            self._send_benefit_sign_request(contract)
            offer.state = "full_signed"

    def _create_activity_benefit(self, contract, contract_state):
        benefits = request.env['hr.contract.salary.benefit'].sudo().search([
            ('structure_type_id', '=', contract.structure_type_id.id),
            ('activity_type_id', '!=', False),
            ('activity_creation', '=', contract_state)])
        for benefit in benefits:
            field = benefit.res_field_id.name
            value = contract[field]
            if (benefit.activity_creation_type == "onchange" and contract[field] != contract.origin_contract_id[field]) or \
                    benefit.activity_creation_type == "always" and value:
                contract.activity_schedule(
                    activity_type_id=benefit.activity_type_id.id,
                    note="%s: %s" % (benefit.name or benefit.res_field_id.name, value),
                    user_id=benefit.activity_responsible_id.id)

    def _send_benefit_sign_request(self, contract):
        benefits = request.env['hr.contract.salary.benefit'].sudo().search([
            ('structure_type_id', '=', contract.structure_type_id.id),
            ('sign_template_id', '!=', False)])

        # ask the contract responsible to create sign requests
        SignRequestSudo = request.env['sign.request'].with_user(contract.hr_responsible_id).sudo()

        sent_templates = request.env['sign.template']
        for benefit in benefits:
            field = benefit.res_field_id.name
            value = contract[field]
            sign_template = benefit.sign_template_id
            if sign_template in sent_templates:
                continue
            if (benefit.activity_creation_type == "onchange" and contract[field] != contract.origin_contract_id[field]) or \
                    benefit.activity_creation_type == "always" and value:

                sent_templates |= sign_template

                sign_request_sudo = SignRequestSudo.create({
                    'template_id': sign_template.id,
                    'request_item_ids': [
                        Command.create({'role_id': request.env.ref('sign.sign_item_role_employee').id,
                                        'partner_id': contract.employee_id.work_contact_id.id}),
                        Command.create({'role_id': request.env.ref('hr_contract_sign.sign_item_role_job_responsible').id,
                                        'partner_id': contract.hr_responsible_id.partner_id.id}),
                    ],
                    'reference': _('Signature Request - %s', benefit.name or contract.name),
                    'subject': _('Signature Request - %s', benefit.name or contract.name),
                })
                sign_request_sudo.message_subcribe(partner_ids=benefit.sign_copy_partner_id.ids)
                sign_request_sudo.toggle_favorited()

                contract.sign_request_ids += sign_request_sudo

class HrContractSalary(http.Controller):

    def _check_access_rights(self, contract_id):
        contract_sudo = request.env['hr.contract'].sudo().browse(contract_id)
        if not contract_sudo.employee_id or contract_sudo.employee_id.user_id == request.env.user:
            return contract_sudo
        contract = request.env['hr.contract'].with_context(allowed_company_ids=request.env.user.company_ids.ids).browse(contract_id)
        contract.check_access_rights('read')
        contract.check_access_rule('read')
        return contract_sudo

    def _get_default_template_values(self, contract, offer):
        values = self._get_salary_package_values(contract, offer)
        values.update({
            'redirect_to_job': False,
            # YTI PROBABLY TO REMOVE
            'applicant_id': offer.applicant_id.id,
            'employee_contract_id': offer.employee_contract_id.id,
            'employee_job_id': offer.employee_job_id.id,
            'department_id': offer.department_id.id,
            'job_title': offer.job_title,
            'whitelist': False,
            'part_time': False,
            'final_yearly_costs': offer.final_yearly_costs,
        })
        return values

    @http.route(['/salary_package/simulation/contract/<int:contract_id>'], type='http', auth="public", website=True, sitemap=False)
    def salary_package_deprecated(self, contract_id=None, **kw):
        return request.render('http_routing.http_error', {
            'status_code': _('Oops'),
            'status_message': _('This offer is outdated, please request an updated link...')})

    @http.route(['/salary_package/simulation/offer/<int:offer_id>'], type='http', auth="public", website=True, sitemap=False)
    def salary_package(self, offer_id=None, **kw):
        response = False

        debug = request.session.debug
        for bundle_name in ["web.assets_frontend", "web.assets_frontend_lazy"]:
            request.env["ir.qweb"]._get_asset_nodes(bundle_name, debug=debug, js=True, css=True)
        request.env.cr.commit()

        request.env.cr.execute('SAVEPOINT salary')

        offer = request.env['hr.contract.salary.offer'].sudo().browse(offer_id)
        contract = offer.contract_template_id
        if not offer.exists() or offer.state in ['expired', 'refused']:
            return request.render('http_routing.http_error', {
                'status_code': _('Oops'),
                'status_message': _('This offer has been updated, please request an updated link..')})

        if not request.env.user.has_group('hr_contract.group_hr_contract_manager'):
            if offer.applicant_id:
                if not kw.get('token') or \
                        not offer.access_token or \
                        not consteq(offer.access_token, kw.get('token')) or \
                        offer.offer_end_date < fields.Date.today():
                    return request.render('http_routing.http_error', {
                        'status_code': _('Oops'),
                        'status_message': _('This link is invalid. Please contact the HR Responsible to get a new one...')})
            if contract.employee_id and not contract.employee_id.user_id and not offer.applicant_id:
                return request.render('http_routing.http_error', {
                    'status_code': _('Oops'),
                    'status_message': _('The employee is not linked to an existing user, please contact the administrator..')})
            if contract.employee_id and contract.employee_id.user_id != request.env.user:
                raise NotFound()
            if contract.employee_id and offer.offer_end_date < fields.Date.today():
                return request.render('http_routing.http_error', {
                    'status_code': _('Oops'),
                    'status_message': _('This link is invalid. Please contact the HR Responsible to get a new one...')})

        employee_contract = False
        if offer.employee_contract_id:
            employee_contract = offer.employee_contract_id
            # do not recreate a new employee if the salary configurator is launched with a new
            # type of contract (in the event that the employee changes jobs) since the contract
            # is a template without an employee
            if not contract.employee_id and employee_contract.employee_id:
                contract.employee_id = employee_contract.employee_id
            if not request.env.user.has_group('hr_contract.group_hr_contract_manager') and employee_contract.employee_id \
                    and employee_contract.employee_id.user_id != request.env.user:
                raise NotFound()

        if not contract.employee_id or not employee_contract:
            contract_country = contract.company_id.country_id
            # Pre-filling
            temporary_name = False
            temporary_mobile = False
            private_email = False
            # Pre-filling name / phone / mail if coming from an applicant
            if offer.applicant_id:
                temporary_name = offer.applicant_id.partner_name
                temporary_mobile = offer.applicant_id.partner_phone
                private_email = offer.applicant_id.email_from
            contract.employee_id = request.env['hr.employee'].with_context(
                tracking_disable=True,
                salary_simulation=True,
            ).with_user(SUPERUSER_ID).sudo().create({
                'name': temporary_name,
                'private_phone': temporary_mobile,
                'private_email': private_email,
                'active': False,
                'country_id': contract_country.id,
                'private_country_id': contract_country.id,
                'certificate': False,  # To force encoding it
                'company_id': contract.company_id.id,
                'resource_calendar_id': contract.resource_calendar_id.id,
            })

        if offer.applicant_id:
            contract = contract.with_context(is_applicant=True)

        values = self._get_default_template_values(contract, offer)
        for field_name, value in kw.items():
            if field_name == 'job_id':
                values['redirect_to_job'] = value
            if field_name == 'allow':
                values['whitelist'] = value
            if field_name == 'part':
                values['part_time'] = True
        new_gross = contract.sudo()._get_gross_from_employer_costs(values['final_yearly_costs'])
        contract.write({
            'wage': new_gross,
            'final_yearly_costs': values['final_yearly_costs'],
        })
        values.update({
            'need_personal_information': not values['redirect_to_job'],
            'submit': not values['redirect_to_job'],
            'default_mobile': request.env['ir.default'].sudo()._get('hr.contract', 'mobile'),
            'original_link': get_current_url(request.httprequest.environ),
            'token': kw.get('token'),
            'offer_id': offer.id,
            'master_department_id': request.env['hr.department'].sudo().browse(int(values['department_id'])).master_department_id.id if values['department_id'] else False
        })

        response = request.render("hr_contract_salary.salary_package", values)
        response.flatten()
        request.env.flush_all()
        request.env.cr.precommit.clear()
        request.env.cr.execute('ROLLBACK TO SAVEPOINT salary')
        return response

    @http.route(['/salary_package/thank_you/<int:contract_id>'], type='http', auth="public", website=True, sitemap=False)
    def salary_package_thank_you(self, contract_id=None, **kw):
        contract = request.env['hr.contract'].sudo().browse(contract_id)
        return request.render("hr_contract_salary.salary_package_thank_you", {
            'responsible_name': contract.hr_responsible_id.partner_id.name or contract.job_id.user_id.partner_id.name,
            'responsible_email': contract.hr_responsible_id.work_email or contract.job_id.user_id.partner_id.email,
            'responsible_phone': contract.hr_responsible_id.work_phone or contract.job_id.user_id.partner_id.phone,
        })

    def _get_personal_infos_countries(self, contract, personal_info):
        return request.env['res.country'].search([])

    def _get_personal_infos_states(self, contract, personal_info):
        return request.env['res.country.state'].search([])

    def _get_personal_infos_langs(self, contract, personal_info):
        return request.env['res.lang'].search([])

    def _get_personal_infos(self, contract):
        initial_values = {}
        dropdown_options = {}
        targets = {
            'employee': contract.employee_id,
            'bank_account': contract.employee_id.bank_account_id,
        }

        # PERSONAL INFOS
        personal_infos = request.env['hr.contract.salary.personal.info'].sudo().search([
            '|',
            ('structure_type_id', '=', False),
            ('structure_type_id', '=', contract.structure_type_id.id)]).sorted(lambda info: (info.info_type_id.sequence, info.sequence))
        mapped_personal_infos = [
            defaultdict(lambda: request.env['hr.contract.salary.personal.info']), # Main Panel
            request.env['hr.contract.salary.personal.info'], # Side Panel
        ]
        for personal_info in personal_infos:
            if personal_info.position == 'left':
                mapped_personal_infos[0][personal_info.info_type_id.name] |= personal_info
            else:
                mapped_personal_infos[1] |= personal_info

            target = targets[personal_info.applies_on]

            if personal_info.display_type == 'document':
                if personal_info.field in target and target[personal_info.field]:
                    if target[personal_info.field][:7] == b'JVBERi0':
                        content = "data:application/pdf;base64,%s" % (target[personal_info.field].decode())
                    else:
                        content = image_data_uri(target[personal_info.field])
                else:
                    content = False
                initial_values[personal_info.field] = content
                initial_values[personal_info.field + '_filename'] = contract[personal_info.field + '_filename'] or personal_info.field
            else:
                initial_values[personal_info.field] = target[personal_info.field] if personal_info.field in target else ''

            if personal_info.display_type == 'dropdown':
                # Set record id instead of browse record as value
                if isinstance(initial_values[personal_info.field], models.BaseModel):
                    initial_values[personal_info.field] = initial_values[personal_info.field].id

                if personal_info.dropdown_selection == 'specific':
                    values = [(value.value, value.name) for value in personal_info.value_ids]
                elif personal_info.dropdown_selection == 'country':
                    values = [(country.id, country.name) for country in self._get_personal_infos_countries(contract, personal_info)]
                elif personal_info.dropdown_selection == 'state':
                    values = [(state.id, state.name, state.country_id.id) for state in self._get_personal_infos_states(contract, personal_info)]
                elif personal_info.dropdown_selection == 'lang':
                    values = [(lang.code, lang.name) for lang in self._get_personal_infos_langs(contract, personal_info)]
                dropdown_options[personal_info.field] = values
        return mapped_personal_infos, dropdown_options, initial_values

    def _get_benefits(self, contract, offer):
        return request.env['hr.contract.salary.benefit'].sudo().search([
            ('structure_type_id', '=', contract.structure_type_id.id)])

    def _get_benefits_values(self, contract, offer):
        initial_values = {}
        dropdown_options = {}
        dropdown_group_options = {}

        # benefits
        benefits = self._get_benefits(contract, offer)
        mapped_benefits = defaultdict(lambda: request.env['hr.contract.salary.benefit'])
        for benefit in benefits:
            mapped_benefits[benefit.benefit_type_id] |= benefit
            field = benefit.field
            initial_values[field] = contract[field]

            if benefit.folded:
                fold_field = 'fold_%s' % (benefit.field)
                benefit_fold_field = benefit.fold_field or benefit.field
                initial_values[fold_field] = contract[benefit_fold_field] if benefit_fold_field and benefit_fold_field in contract else 0

            if benefit.display_type == 'manual':
                manual_field = '%s_manual' % (benefit.field)
                field = benefit.manual_field or benefit.field
                initial_values[manual_field] = contract[field] if field and field in contract else 0
            if benefit.display_type == 'text':
                text_field = '%s_text' % (benefit.field)
                field = benefit.manual_field or benefit.field
                initial_values[text_field] = contract[field] if field and field in contract else ''
            elif benefit.display_type == 'dropdown' or benefit.display_type == 'dropdown-group':
                initial_values['select_%s' % field] = contract[field]

        dropdown_benefits = benefits.filtered(lambda a: a.display_type == 'dropdown')
        for dropdown_benefit in dropdown_benefits:
            dropdown_options[dropdown_benefit.field] = \
                [(value.value, value.value) for value in dropdown_benefit.value_ids.filtered(lambda v: v.display_type == 'line')]
        dropdown_group_benefits = benefits.filtered(lambda a: a.display_type == 'dropdown-group')
        for dropdown_group_benefit in dropdown_group_benefits:
            values = OrderedDict()
            values[""] = []
            current_section = ""
            for value in dropdown_group_benefit.value_ids:
                if value.display_type == 'section':
                    current_section = value.name
                    values[current_section] = []
                else:
                    values[current_section].append((value.value, value.value))
            dropdown_group_options[dropdown_group_benefit.field] = values
        benefit_types = sorted(benefits.mapped('benefit_type_id'), key=lambda x: x.sequence)
        mapped_dependent_benefits = defaultdict(lambda: '')
        mapped_mandatory_benefits = defaultdict(lambda: '')
        # When the dependent benefit is disabled, on hover over we display the information
        # regarding which (mandatory) benefits need to be selected, in order to be able to select
        # the (dependent) benefit in question. For this purpose, here we build the string for each dependent benefit.
        # The string starts with the display name of the dependent benefit and is followed by the display names
        # of the mandatory benefits, separated by semicolon.
        mapped_mandatory_benefits_names = defaultdict(lambda: '')
        for dependent_benefit in benefits:
            if not dependent_benefit.field:
                continue
            mapped_mandatory_benefits_names[dependent_benefit] = (dependent_benefit.fold_label or dependent_benefit.name) + ';'
            if dependent_benefit.folded:
                dependent_name = 'fold_%s' % (dependent_benefit.field)
            else:
                dependent_name = dependent_benefit.field + '_' + dependent_benefit.display_type
            dependent_benefit_str = dependent_name + ' '
            for mandatory_benefit in dependent_benefit.benefit_ids:
                mapped_dependent_benefits[mandatory_benefit] += dependent_benefit_str
                if mandatory_benefit.folded:
                    mandatory_name = 'fold_%s' % (mandatory_benefit.field)
                else:
                    mandatory_name = mandatory_benefit.field + '_' + mandatory_benefit.display_type
                mapped_mandatory_benefits[dependent_benefit] += mandatory_name + ' '
                mapped_mandatory_benefits_names[dependent_benefit] += (mandatory_benefit.fold_label or mandatory_benefit.name) + ';'
        return mapped_benefits, mapped_dependent_benefits, mapped_mandatory_benefits, mapped_mandatory_benefits_names, benefit_types, dropdown_options, dropdown_group_options, initial_values

    def _get_salary_package_values(self, contract, offer):
        mapped_personal_infos, dropdown_options_1, initial_values_1 = self._get_personal_infos(contract)
        mapped_benefits, mapped_dependent_benefits, mandatory_benefits, mandatory_benefits_names, benefit_types, dropdown_options_2, dropdown_group_options, initial_values_2 = self._get_benefits_values(contract, offer)
        all_initial_values = {**initial_values_1, **initial_values_2}
        all_initial_values = {key: round(value, 2) if isinstance(value, float) else value for key, value in all_initial_values.items()}
        all_dropdown_options = {**dropdown_options_1, **dropdown_options_2}
        return {
            'contract': contract,
            'states': request.env['res.country.state'].search([]),
            'countries': request.env['res.country'].search([]),
            'benefits': mapped_benefits,
            'dependent_benefits': mapped_dependent_benefits,
            'mandatory_benefits': mandatory_benefits,
            'mandatory_benefits_names': mandatory_benefits_names,
            'benefit_types': benefit_types,
            'mapped_personal_infos': mapped_personal_infos,
            'dropdown_options': all_dropdown_options,
            'dropdown_group_options': dropdown_group_options,
            'initial_values': all_initial_values,
        }

    def _get_new_contract_values(self, contract, employee, benefits, offer):
        contract_benefits = self._get_benefits(contract, offer)
        contract_vals = {
            'active': False,
            'name': contract.name if contract.state == 'draft' else "Package Simulation",
            'job_id': offer.employee_job_id.id or contract.job_id.id or employee.job_id.id,
            'department_id': offer.department_id.id or contract.department_id.id or employee.department_id.id,
            'company_id': contract.company_id.id,
            'currency_id': contract.company_id.currency_id.id,
            'employee_id': employee.id,
            'structure_type_id': contract.structure_type_id.id,
            'wage': benefits['wage'],
            'final_yearly_costs': benefits['final_yearly_costs'],
            'resource_calendar_id': contract.resource_calendar_id.id,
            'default_contract_id': contract.default_contract_id.id,
            'hr_responsible_id': contract.hr_responsible_id.id,
            'sign_template_id': contract.sign_template_id.id,
            'contract_update_template_id': contract.contract_update_template_id.id,
            'date_start': offer.contract_start_date or fields.Date.today().replace(day=1),
            'contract_type_id': contract.contract_type_id.id,
        }
        if 'work_entry_source' in contract:
            contract_vals['work_entry_source'] = contract.work_entry_source

        for benefit in contract_benefits:
            if not benefit.res_field_id or benefit.field not in contract:
                continue
            if hasattr(contract, '_get_benefit_values_%s' % (benefit.field)):
                contract_vals.update(getattr(contract, '_get_benefit_values_%s' % (benefit.field))(contract, benefits))
                continue
            if benefit.folded:
                contract_vals[benefit.fold_field or benefit.field] = benefits['fold_%s' % (benefit.field)]
            if benefit.display_type == 'dropdown':
                contract_vals[benefit.field] = benefits[benefit.field]
            if benefit.display_type in ['manual', 'text']:
                contract_vals[benefit.manual_field or benefit.field] = benefits['%s_%s' % (benefit.field, 'manual' if benefit.display_type == 'manual' else 'text')]
            else:
                contract_vals[benefit.field] = benefits[benefit.field]
        return contract_vals

    def _update_personal_info(self, employee, contract, personal_infos_values, no_name_write=False):
        def resolve_value(field_name, values):
            targets = {
                'employee': request.env['hr.employee'],
                'bank_account': request.env['res.partner.bank'],
            }
            field_value = values[field_name]

            target = targets[personal_info.applies_on]
            if field_name in target and isinstance(target[field_name], models.BaseModel):
                field_value = int(field_value) if field_value else False
            return field_value

        def _is_valid_date(date):
            return fields.Date.from_string(date) < fields.Date.from_string('1900-01-01')

        personal_infos = request.env['hr.contract.salary.personal.info'].sudo().search([
            '|', ('structure_type_id', '=', False), ('structure_type_id', '=', contract.structure_type_id.id)])

        employee_infos = personal_infos_values['employee']
        bank_account_infos = personal_infos_values['bank_account']

        for key in ['employee_job_id', 'department_id']:
            try:
                employee_infos[key] = int(employee_infos[key])
            except ValueError:
                employee_infos[key] = None

        job = request.env['hr.job'].sudo().browse(employee_infos['employee_job_id'])
        if not employee_infos['job_title']:
            employee_infos['job_title'] = job.name

        if employee.department_id.parent_path:
            employee_department = employee.department_id.id if str(employee_infos['department_id']) in employee.department_id.parent_path.split('/') else employee_infos['department_id']
        else:
            employee_department = employee_infos['department_id']

        employee_vals = {'job_title': employee_infos['job_title'],
                         'job_id': employee_infos['employee_job_id'],
                         'department_id': employee_department}
        work_contact_vals = {}
        bank_account_vals = {}
        attachment_create_vals = []

        if employee_infos.get('birthday') and _is_valid_date(employee_infos['birthday']):
            employee_infos['birthday'] = ''

        for personal_info in personal_infos:
            field_name = personal_info.field

            if personal_info.display_type == 'document' and not employee_infos.get(field_name):
                continue

            if field_name in employee_infos and personal_info.applies_on == 'employee':
                employee_vals[field_name] = resolve_value(field_name, employee_infos)
            elif field_name in bank_account_infos and personal_info.applies_on == 'bank_account':
                bank_account_vals[field_name] = resolve_value(field_name, bank_account_infos)

        work_contact_vals['name'] = employee_vals['name']
        work_contact_vals['email'] = employee_vals['private_email']

        # Update personal info on the private address
        if employee.work_contact_id:
            if no_name_write:
                del work_contact_vals['name']
            partner = employee.work_contact_id
            # We shouldn't modify the partner email like this
            if employee.work_contact_id.email:
                work_contact_vals.pop('email', None)
            partner.write(work_contact_vals)
        else:
            work_contact_vals['active'] = False
            partner = request.env['res.partner'].sudo().with_context(lang=None, tracking_disable=True).create(work_contact_vals)

        # Update personal info on the employee
        if bank_account_vals:
            bank_account_vals['partner_id'] = partner.id
            existing_bank_account = request.env['res.partner.bank'].sudo().search([
                ('partner_id', '=', partner.id),
                ('acc_number', '=', bank_account_vals['acc_number'])], limit=1)
            if existing_bank_account:
                bank_account = existing_bank_account
            else:
                bank_account = request.env['res.partner.bank'].sudo().create(bank_account_vals)

            employee_vals['bank_account_id'] = bank_account.id

        employee_vals['work_contact_id'] = partner.id

        if job.address_id:
            employee_vals['address_id'] = job.address_id.id

        if not no_name_write:
            employee_vals['name'] = employee_infos['name']
        employee.write(employee_vals)
        if attachment_create_vals:
            request.env['ir.attachment'].sudo().create(attachment_create_vals)

    def create_new_contract(self, contract, offer_id, benefits, no_write=False, **kw):
        # Generate a new contract with the current modifications
        contract_diff = []
        contract_values = benefits['contract']
        personal_infos = {
            'employee': benefits['employee'],
            'address': benefits['address'],
            'bank_account': benefits['bank_account'],
        }
        offer = request.env['hr.contract.salary.offer'].sudo().browse(offer_id).exists()
        applicant = offer.applicant_id
        employee = kw.get('employee') or contract.employee_id or applicant.emp_id
        if not employee and applicant:
            existing_contract = request.env['hr.contract'].sudo().with_context(active_test=False).search([
                ('applicant_id', '=', applicant.id), ('employee_id', '!=', False)], limit=1)
            employee = existing_contract.employee_id
        if not employee:
            employee = request.env['hr.employee'].sudo().with_context(
                tracking_disable=True,
                salary_simulation=not no_write,
            ).create({
                'name': 'Simulation Employee',
                'active': False,
                'company_id': contract.company_id.id,
                'lang': contract.company_id.partner_id.lang,
                'resource_calendar_id': contract.resource_calendar_id.id,
            })

        # get differences for personnal information
        if no_write:
            employee_fields = request.env['hr.employee']._fields
            for section in personal_infos:
                for field in personal_infos[section]:
                    if field in employee_fields:
                        current_value = employee[field]
                        new_value = personal_infos[section][field]

                        if isinstance(current_value, type(new_value)) and current_value == new_value:
                            continue

                        elif employee_fields[field].relational:
                            current_value = str(current_value.name)
                            if new_value:
                                new_record = request.env[employee_fields[field].comodel_name].sudo().browse(int(new_value))
                                new_value = new_record['name'] if new_record else ''

                        elif employee_fields[field].type in ['integer', 'float']:
                            current_value = str(current_value)
                            if not new_value:
                                new_value = '0'

                        elif employee_fields[field].type == 'date':
                            current_value = current_value.strftime('%Y-%m-%d') if current_value else ''

                        elif employee_fields[field].type == 'boolean':
                            current_value = str(current_value)
                            new_value = str(new_value)

                        elif employee_fields[field].type == 'binary':
                            continue

                        if current_value != new_value:
                            employee_field_name = employee_fields[field].string or field
                            contract_diff.append((employee_field_name, current_value, new_value))

        self._update_personal_info(employee, contract, personal_infos, no_name_write=bool(kw.get('employee')))
        new_contract = request.env['hr.contract'].with_context(
            tracking_disable=True
        ).sudo().create(self._get_new_contract_values(contract, employee, contract_values, offer))

        # get differences for contract information
        if no_write:
            contract_fields = request.env['hr.contract']._fields
            for field in contract_fields:
                if field in contract_values and contract[field] != new_contract[field]\
                        and (contract[field] or new_contract[field]):
                    current_value = contract[field]
                    new_value = new_contract[field]
                    contract_field_name = contract_fields[field].string or field
                    contract_diff.append((contract_field_name, current_value, new_value))

        if 'original_link' in kw:
            start_date = parse_qs(urlparse(kw['original_link']).query).get('contract_start_date', False)
            if start_date:
                new_contract.date_start = datetime.strptime(start_date[0], '%Y-%m-%d').date()

        new_contract.wage_with_holidays = contract_values['wage']
        new_contract.final_yearly_costs = float(contract_values['final_yearly_costs'] or 0.0)
        new_contract._inverse_wage_with_holidays()

        return new_contract, contract_diff

    @http.route('/salary_package/update_salary', type="json", auth="public")
    def update_salary(self, contract_id=None, offer_id=None, benefits=None, **kw):
        result = {}
        contract = self._check_access_rights(contract_id)

        new_contract = self.create_new_contract(contract, offer_id, benefits, no_write=True)[0]
        final_yearly_costs = float(benefits['contract']['final_yearly_costs'] or 0.0)
        new_gross = new_contract._get_gross_from_employer_costs(final_yearly_costs)
        new_contract.write({
            'wage': new_gross,
            'final_yearly_costs': final_yearly_costs,
        })

        result['new_gross'] = round(new_gross, 2)
        new_contract = new_contract.with_context(
            origin_contract_id=contract.id,
            simulation_working_schedule=kw.get('simulation_working_schedule', '100'))
        result.update(self._get_compute_results(new_contract))

        request.env.cr.rollback()
        return result

    def _get_compute_results(self, new_contract):
        new_contract.wage_on_signature = new_contract.wage_with_holidays

        result = {}
        result['wage_with_holidays'] = round(new_contract.wage_with_holidays, 2)
        # Allowed company ids might not be filled or request.env.user.company_ids might be wrong
        # since we are in route context, force the company to make sure we load everything
        resume_lines = request.env['hr.contract.salary.resume'].sudo().with_company(new_contract.company_id).search([
            '|',
            ('structure_type_id', '=', False),
            ('structure_type_id', '=', new_contract.structure_type_id.id),
            ('value_type', 'in', ['fixed', 'contract', 'monthly_total', 'sum'])])

        result['resume_categories'] = [c.name for c in sorted(resume_lines.mapped('category_id'), key=lambda x: x.sequence)]
        result['resume_lines_mapped'] = defaultdict(lambda: {})

        monthly_total = 0
        monthly_total_lines = resume_lines.filtered(lambda l: l.value_type == 'monthly_total')

        uoms = {'days': _('Days'), 'percent': '%', 'currency': new_contract.company_id.currency_id.symbol, 'position': new_contract.company_id.currency_id.position}

        resume_explanation = False
        for resume_line in resume_lines - monthly_total_lines:
            value = 0
            uom = uoms[resume_line.uom]
            resume_explanation = False
            if resume_line.value_type == 'fixed':
                value = resume_line.fixed_value
            if resume_line.value_type == 'contract':
                value = new_contract[resume_line.code] if resume_line.code in new_contract else 0
            if resume_line.value_type == 'sum':
                resume_explanation = _('Equals to the sum of the following values:\n\n%s',
                    '\n+ '.join(resume_line.benefit_ids.res_field_id.sudo().mapped('field_description')))
                for benefit in resume_line.benefit_ids:
                    if not benefit.fold_field or (benefit.fold_field and new_contract[benefit.fold_field]):
                        field = benefit.field
                        value += new_contract[field]
            if resume_line.impacts_monthly_total:
                monthly_total += value / 12.0 if resume_line.category_id.periodicity == 'yearly' else value
            try:
                value = round(float(value), 2)
            except:
                pass
            result['resume_lines_mapped'][resume_line.category_id.name][resume_line.code] = (resume_line.name, value, uom, resume_explanation, new_contract.company_id.currency_id.position, resume_line.uom)
        for resume_line in monthly_total_lines:
            result['resume_lines_mapped'][resume_line.category_id.name][resume_line.code] = (resume_line.name, round(float(monthly_total), 2), uoms['currency'], uoms['position'], resume_explanation, resume_line.uom)
        return result

    @http.route(['/salary_package/onchange_benefit'], type='json', auth='public')
    def onchange_benefit(self, benefit_field, new_value, contract_id, benefits):
        # Return a dictionary describing the new benefit configuration:
        # - new_value: The benefit new_value (same by default)
        # - description: The dynamic description corresponding to the benefit new value
        # - extra_value: A list of tuple (input name, input value) change another input due
        #                to the benefit new_value
        # Override this controllers to add customize
        # the returned value for a specific benefit
        contract = self._check_access_rights(contract_id)
        benefit = request.env['hr.contract.salary.benefit'].sudo().search([
            ('structure_type_id', '=', contract.structure_type_id.id),
            ('res_field_id.name', '=', benefit_field)], limit=1)
        if hasattr(contract, '_get_description_%s' % benefit_field):
            description = getattr(contract, '_get_description_%s' % benefit_field)(new_value)
        else:
            description = benefit.description
        return {'new_value': new_value, 'description': description, 'extra_values': False}

    @http.route(['/salary_package/onchange_personal_info'], type='json', auth='public')
    def onchange_personal_info(self, field, value):
        # sudo as public users can't access ir.model.fields
        info = request.env['hr.contract.salary.personal.info'].sudo().search([('field', '=', field)])
        if not info.child_ids:
            return {}
        if info.value_ids:
            value = info.value_ids.filtered(lambda v: v.value == value)
            return {'hide_children': value.hide_children, 'field': field}
        return {'hide_children': not bool(value), 'field': field}

    def _get_email_info(self, contract, **kw):
        field_names = {
            model: {
                field.name: field.field_description for field in request.env['ir.model.fields'].sudo().search([('model', '=', model)])
            } for model in ['hr.employee', 'hr.contract', 'res.partner', 'res.partner.bank']}
        result = {
            _('Salary Package Summary'): {
                'General Information': [
                    (_('Employee Name'), contract.employee_id.name),
                    (_('Job Position'), contract.job_id.name),
                    (_('Job Title'), contract.employee_id.job_title),
                    (_('Contract Type'), contract.contract_type_id.name),
                    (_('Original Link'), kw.get('original_link'))
                ],
            }
        }
        # Contract Information
        contract_benefits = request.env['hr.contract.salary.benefit'].sudo().search([('structure_type_id', '=', contract.structure_type_id.id)])
        contract_info = {benefit_type.name: [] for benefit_type in sorted(contract_benefits.mapped('benefit_type_id'), key=lambda x: x.sequence)}
        for benefit in contract_benefits:
            if benefit.folded and benefit.fold_field:
                value = _('Yes') if contract[benefit.fold_field] else _('No')
                contract_info[benefit.benefit_type_id.name].append((field_names['hr.contract'][benefit.fold_field], value))
            field_name = benefit.field
            if not field_name or field_name not in contract:
                continue
            field_value = contract[field_name]
            if isinstance(field_value, models.BaseModel):
                field_value = field_value.name
            elif isinstance(field_value, float):
                field_value = round(field_value, 2)
            contract_info[benefit.benefit_type_id.name].append((field_names['hr.contract'][field_name], field_value))
        # Add wage information
        contract_info[_('Wage')] = [
            (_('Monthly Gross Salary'), contract.wage_with_holidays),
            (_('Annual Employer Cost'), contract.final_yearly_costs),
        ]
        result[_('Contract Information:')] = contract_info
        # Personal Information
        infos = request.env['hr.contract.salary.personal.info'].sudo().search([('display_type', '!=', 'document'), '|', ('structure_type_id', '=', False), ('structure_type_id', '=', contract.structure_type_id.id)])
        personal_infos = {personal_info_type.name: [] for personal_info_type in sorted(infos.mapped('info_type_id'), key=lambda x: x.sequence)}
        for info in infos:
            if info.applies_on == 'employee':
                field_label = field_names['hr.employee'][info.field]
                field_value = contract.employee_id[info.field]
            if info.applies_on == 'bank_account':
                field_label = field_names['res.partner.bank'][info.field]
                field_value = contract.employee_id.bank_account_id[info.field]
            if isinstance(field_value, models.BaseModel):
                field_value = field_value.name
            elif isinstance(field_value, float):
                field_value = round(field_value, 2)
            personal_infos[info.info_type_id.name].append((field_label, field_value))
        result[_('Personal Information')] = personal_infos
        return {'mapped_data': result}

    def _send_mail_message(self, offer, template, kw, values, new_contract_id=None):
        model = 'hr.contract' if new_contract_id else 'hr.contract.salary.offer'
        res_id = new_contract_id or offer.id
        request.env[model].sudo().browse(res_id).message_post_with_source(
            template,
            render_values=values,
            subtype_xmlid='mail.mt_comment',
        )

    def send_email(self, offer, contract, **kw):
        self._send_mail_message(
            offer,
            'hr_contract_salary.hr_contract_salary_email_template',
            kw,
            self._get_email_info(contract, **kw))
        return contract.id

    def send_diff_email(self, offer, differences, new_contract_id, **kw):
        self._send_mail_message(
            offer,
            'hr_contract_salary.hr_contract_salary_diff_email_template',
            kw,
            {'differences': differences},
            new_contract_id)

    @http.route(['/salary_package/submit'], type='json', auth='public')
    def submit(self, contract_id=None, offer_id=None, benefits=None, **kw):
        offer = request.env['hr.contract.salary.offer'].sudo().browse(offer_id).exists()
        if not offer.applicant_id and not offer.employee_contract_id:
            raise UserError(_('This link is invalid. Please contact the HR Responsible to get a new one...'))

        contract = self._check_access_rights(contract_id)
        if offer.employee_contract_id:
            contract = offer.employee_contract_id
            if contract.employee_id.user_id == request.env.user:
                kw['employee'] = contract.employee_id
        kw['package_submit'] = True
        new_contract = self.create_new_contract(contract, offer_id, benefits, no_write=True, **kw)

        if isinstance(new_contract, dict) and new_contract.get('error'):
            return new_contract

        new_contract, contract_diff = new_contract

        # write on new contract differences with current one
        current_contract = request.env['hr.contract'].sudo().search([
            ('active', '=', True),
            ('employee_id', '=', new_contract.employee_id.id),
            ('state', '=', 'open'),
        ])
        if current_contract:
            self.send_diff_email(offer, contract_diff, new_contract.id, **kw)

        self.send_email(offer, new_contract, **kw)

        applicant = offer.applicant_id
        if applicant and offer.access_token:
            hash_token_access = hashlib.sha1(kw.get('token').encode("utf-8")).hexdigest()
            existing_contract = request.env['hr.contract'].sudo().search([
                ('applicant_id', '=', applicant.id), ('hash_token', '=', hash_token_access), ('active', '=', False)])
            existing_contract.sign_request_ids.write({'state': 'canceled', 'active': False})
            existing_contract.unlink()
            new_contract.hash_token = hash_token_access
        elif not applicant and contract.employee_id.user_id and contract.employee_id.user_id == request.env.user and kw.get('original_link', False):
            hash_token_access = hashlib.sha1(kw.get('original_link').encode("utf-8")).hexdigest()
            existing_contract = request.env['hr.contract'].sudo().search([
                ('employee_id', 'in', request.env.user.employee_ids.ids), ('hash_token', '=', hash_token_access), ('active', '=', False)])
            existing_contract.sign_request_ids.write({'state': 'canceled', 'active': False})
            existing_contract.unlink()
            new_contract.hash_token = hash_token_access

        if new_contract.id != contract.id:
            new_contract.write({
                'state': 'draft',
                'name': 'New contract - ' + new_contract.employee_id.name,
                'origin_contract_id': contract_id,
            })
        sign_template = new_contract.contract_update_template_id if offer.employee_contract_id else new_contract.sign_template_id
        if not sign_template:
            return {'error': 1, 'error_msg': _('No signature template defined on the contract. Please contact the HR responsible.')}
        if not new_contract.hr_responsible_id:
            return {'error': 1, 'error_msg': _('No HR responsible defined on the job position. Please contact an administrator.')}

        # ask the contract responsible to create a sign request
        SignRequestSudo = request.env['sign.request'].with_user(new_contract.hr_responsible_id).sudo()

        sign_request_sudo = SignRequestSudo.create({
            'template_id': sign_template.id,
            'request_item_ids': [
                Command.create({
                    'role_id': request.env.ref('sign.sign_item_role_employee').id,
                    'partner_id': new_contract.employee_id.work_contact_id.id,
                    'mail_sent_order': 1
                }),
                Command.create({
                    'role_id': request.env.ref('hr_contract_sign.sign_item_role_job_responsible').id,
                    'partner_id': new_contract.hr_responsible_id.partner_id.id,
                    'mail_sent_order': 2
                }),
            ],
            'reference': _('Signature Request - %s', new_contract.name),
            'subject': _('Signature Request - %s', new_contract.name),
        })
        sign_request_sudo.toggle_favorited()

        # Prefill the sign boxes
        sign_items = request.env['sign.item'].sudo().search([
            ('template_id', '=', sign_template.id),
            ('name', '!=', '')
        ])
        sign_values_by_role = defaultdict(lambda: defaultdict(lambda: request.env['sign.item']))
        for item in sign_items:
            try:
                new_value = None
                if item.name == 'car' and new_contract.transport_mode_car:
                    if not new_contract.new_car and new_contract.car_id:
                        new_value = new_contract.car_id.model_id.name
                    elif new_contract.new_car and new_contract.new_car_model_id:
                        new_value = new_contract.new_car_model_id.name
                # YTI FIXME: Clean that brol
                elif item.name == 'l10n_be_group_insurance_rate':
                    new_value = 1 if item.name in new_contract and new_contract[item.name] else 0
                elif item.name == "ip_wage_rate":
                    new_value = new_value if new_contract.ip else 0
                else:
                    new_values = new_contract.mapped(item.name)
                    if not new_values or isinstance(new_values, models.BaseModel):
                        raise Exception
                    new_value = new_values[0]
                    if isinstance(new_value, float):
                        new_value = round(new_value, 2)
                    if item.type_id.item_type == "checkbox":
                        new_value = 'on' if new_value else 'off'
                if new_value is not None:
                    sign_values_by_role[item.responsible_id][str(item.id)] = new_value
            except Exception:
                pass
        for sign_request_item in sign_request_sudo.request_item_ids:
            if sign_request_item.role_id in sign_values_by_role:
                sign_request_item._fill(sign_values_by_role[sign_request_item.role_id])

        access_token = request.env['sign.request.item'].sudo().search([
            ('sign_request_id', '=', sign_request_sudo.id),
            ('role_id', '=', request.env.ref('sign.sign_item_role_employee').id)
        ]).access_token

        new_contract.sign_request_ids += sign_request_sudo
        offer.sign_request_ids += sign_request_sudo

        if new_contract:
            if offer.applicant_id:
                new_contract.sudo().applicant_id = offer.applicant_id
            if offer.employee_contract_id:
                new_contract.sudo().origin_contract_id = offer.employee_contract_id

        return {
            'job_id': new_contract.job_id.id,
            'request_id': sign_request_sudo.id,
            'token': access_token,
            'error': 0,
            'new_contract_id': new_contract.id
        }
