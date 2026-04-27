from odoo import api, fields, models, _, Command
from ..api.swissdec_declarations import SwissdecDeclaration
from werkzeug.urls import url_parse, url_unparse, url_encode, url_decode
from pytz import utc
import base64
from decimal import Decimal
import datetime
from odoo.tools.pdf import PdfFileReader, PdfFileWriter
from io import BytesIO
from markupsafe import Markup
from dateutil.relativedelta import relativedelta
import uuid

XSD_SKIP_VALUE = "XSDSKIP"


class L10nCHSwissdecJobResult(models.Model):
    _name = "l10n.ch.swissdec.job.result"
    _inherit = 'mail.thread'
    _description = "Swissdec Job"

    declaration_id = fields.Many2one("l10n.ch.swissdec.declaration", required=True)
    swissdec_declaration_id = fields.Char(related="declaration_id.swissdec_declaration_id")
    test_transmission = fields.Boolean(related="declaration_id.test_transmission")
    transmission_date = fields.Datetime(related="declaration_id.transmission_date")
    domain = fields.Selection(selection=[('AHV-AVS', 'AVS'),
                                         ('FAK-CAF', 'CAF'),
                                         ('BVG-LPP', 'LPP'),
                                         ('UVG-LAA', 'LAA'),
                                         ('UVGZ-LAAC', 'LAAC'),
                                         ('KTG-AMC', 'IJM'),
                                         ('Tax', 'Tax'),
                                         ('TaxAtSource', 'Source Tax'),
                                         ('TaxCrossborder', 'Tax Crossborder'),
                                         ('Statistic', 'Statistic')], required=True)

    general_state = fields.Selection(string="Declaration Status",
                                     selection=[("Ignored", "Ignored"),
                                                ("Processing", "Processing"),
                                                ("Success", "Success"),
                                                ("Error", "Error"),
                                                ("NotSupported", "Operation Not Supported")])

    success_state = fields.Selection(string="Response Status",
                                     selection=[("CompletionAndResult", "Waiting for Completion"),
                                                ("DialogAndResult", "Waiting for Dialog Response"),
                                                ("Result", "Results Available")])


    result_state = fields.Selection(string="Result Status", selection=[("waiting", "Waiting for Results"),
                                               ("CompletionReleaseIsMissing", "Release Missing"),
                                               ("Processing", "Processing"),
                                               ("Success", "Success"),
                                               ("Error", "Error"),
                                               ("NotSupported", "Operation Not supported")], default="waiting")

    dialog_response_json = fields.Json()
    credential_key = fields.Char()
    credential_password = fields.Char()
    completion_url = fields.Char()

    dialog_message_ids = fields.One2many('l10n.ch.dialog.message', 'swissdec_job_id')

    result_meta_data = fields.Json()
    institution_id_ref = fields.Char()
    status_response_json = fields.Json()
    result_response_json = fields.Json()
    last_raw_response = fields.Char()

    has_proof_of_insurance = fields.Boolean(compute="_compute_has_proof_of_insurance")
    has_lpp_contributions = fields.Boolean(compute="_compute_has_lpp_contributions")
    has_st_corrections = fields.Boolean(compute="_compute_has_st_corrections")
    attachment_ids = fields.One2many('ir.attachment', 'res_id', string='Attachments')
    proof_of_insurance_count = fields.Integer(compute="_compute_proof_of_insurance_count")


    @api.depends("result_meta_data")
    def _compute_display_name(self):
        for rec in self:
            name = rec.domain
            if rec.result_meta_data:
                if rec.domain == "AHV-AVS" and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("AK-CC-BranchNumber", False)
                    name = f'{rec.domain} ({ref_id})'
                elif rec.domain == "FAK-CAF" and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("FAK-CAF-BranchNumber", False)
                    name = f'{rec.domain} ({ref_id})'
                elif rec.domain in ["BVG-LPP", "UVG-LAA", "UVGZ-LAAC", "KTG-AMC"] and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("InsuranceCompanyName", False)
                    name = f'{rec.domain} ({ref_id})'
                elif rec.domain == "Tax" and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("CantonID", False)
                    name = f'{rec.domain} ({ref_id})'
                elif rec.domain == "TaxAtSource" and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("CantonID", False)
                    name = _("Source-Tax (%s)", ref_id)
                elif rec.domain == "TaxCrossborder" and rec.result_meta_data.get("institution_description", {}):
                    ref_id = rec.result_meta_data.get("institution_description", {}).get("CantonID", False)
                    name = _("Tax-Crossborder (%s)", ref_id)
                elif rec.domain == "Statistic":
                    name = _("Federal Office of Statistic")
            rec.display_name = name

    @api.depends("last_raw_response")
    def _compute_has_proof_of_insurance(self):
        for job in self:
            job.has_proof_of_insurance = job.last_raw_response and "ProofOfInsurance" in job.last_raw_response

    @api.depends("last_raw_response")
    def _compute_has_lpp_contributions(self):
        for job in self:
            job.has_lpp_contributions = job.last_raw_response and "EmployeeContribution" in job.last_raw_response

    @api.depends("last_raw_response")
    def _compute_has_st_corrections(self):
        for job in self:
            job.has_st_corrections = job.last_raw_response and (
                        "Reversal" in job.last_raw_response or "AwaitCorrectionFromCompany" in job.last_raw_response)
            
    def action_open_swissdec_job_result(self):
        self.ensure_one()
        target = "current" if self.result_state == "Success" or self.dialog_message_ids else "new"
        return {
            'name': _('Institution Result'),
            'res_model': 'l10n.ch.swissdec.job.result',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'target': target
        }

    def action_open_status_notification(self):
        self.ensure_one()
        return {
            'name': _('Institution Status'),
            'res_model': 'l10n.ch.swissdec.job.result',
            'type': 'ir.actions.act_window',
            "view_id": self.env.ref("l10n_ch_hr_payroll_elm_transmission.view_l10n_ch_swissdec_job_result_status_form").id,
            'view_mode': 'form',
            'res_id': self.id,
            "target": "new",
        }

    def action_open_completion_url(self):
        self.ensure_one()
        if self.success_state == "CompletionAndResult" and self.completion_url and self.credential_key and self.credential_password:
            url = self.completion_url
            key = self.credential_key
            password = self.credential_password
            parsed_url = url_parse(url)
            query_params = url_decode(parsed_url.query)

            query_params['key'] = key
            query_params['password'] = password

            new_query = url_encode(query_params)

            updated_url = url_unparse((
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                new_query,
                parsed_url.fragment
            ))

            return {
                'name': _("Institution Completion"),
                'type': 'ir.actions.act_url',
                'target': 'new',
                'url': updated_url
            }

    def action_open_dialog_message_ids(self):
        self.ensure_one()
        return {
            'name': _('Dialog Messages'),
            'res_model': 'l10n.ch.dialog.message',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('swissdec_job_id', '=', self.id)],
        }

    def action_get_dialog_and_open_result(self):
        self.ensure_one()
        self.action_get_dialog()
        return {
            'name': _('Declaration'),
            'res_model': 'l10n.ch.swissdec.job.result',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_id': self.id,
            'target': "current"
        }

    def action_get_result_from_declare_salary(self):
        corresponding_report = self.env[self.declaration_id.res_model].browse(self.declaration_id.res_id)

        swissdec_declaration = SwissdecDeclaration()
        for institution in self:
            declaration = swissdec_declaration.create_get_result_from_declare_salary(
                domain=institution.domain,
                key=institution.credential_key,
                password=institution.credential_password,
                institution_description=institution.result_meta_data.get("institution_description"),
            )

            result = institution.env.company._l10n_ch_swissdec_request('get_result_from_declare_salary', data=declaration, is_test=corresponding_report.test_transmission)
            response = result['soap_response']
            message = result['response_xml']
            request_archive = result['request_xml']

            institution.result_response_json = response

            if response.get('SalaryResult', {}).get(institution.domain, {}).get('Error', False):
                institution.result_state = 'Error'
            elif response.get('SalaryResult', {}).get(institution.domain, {}).get('Success', False):
                institution.result_state = 'Success'
            elif response.get('SalaryResult', {}).get(institution.domain, {}).get('NotSupported', False):
                institution.result_state = 'NotSupported'
            elif response.get('SalaryResult', {}).get(institution.domain, {}).get('CompletionReleaseIsMissing', False):
                institution.result_state = 'CompletionReleaseIsMissing'
            elif response.get('SalaryResult', {}).get(institution.domain, {}).get('Processing', False):
                institution.result_state = 'Processing'
            elif response.get('SalaryResult', {}).get(institution.domain, {}).get('Error', False):
                institution.result_state = 'Error'

            attachment = self.env['ir.attachment'].create({
                'name': _("get_result_response_%s.xml", institution.domain),
                'datas': base64.encodebytes(message.encode()),
                'res_id': institution.id,
                'res_model': institution._name,
            })

            message_attachment = self.env['ir.attachment'].create({
                'name': _("get_resultµ_request_%s.xml", institution.domain),
                'datas': base64.encodebytes(request_archive.encode()),
                'res_id': institution.id,
                'res_model': institution._name,
            })
            institution.last_raw_response = message
            institution.message_post(attachment_ids=[message_attachment.id, attachment.id], body=_("Get Result Archive %s", institution.domain))

    def action_get_dialog(self):
        self.ensure_one()
        corresponding_report = self.env[self.declaration_id.res_model].browse(self.declaration_id.res_id)

        swissdec_declaration = SwissdecDeclaration()
        declaration = swissdec_declaration.create_get_result_from_declare_salary(
            domain=self.domain,
            key=self.credential_key,
            password=self.credential_password,
            institution_description=self.result_meta_data.get("institution_description"),
        )
        result = self.env.company._l10n_ch_swissdec_request('get_dialog', data=declaration, is_test=corresponding_report.test_transmission)
        response = result['soap_response']
        message = result['request_xml']
        request_archive = result['response_xml']

        self.dialog_response_json = response
        success = response.get("Dialog", {}).get(self.domain, {}).get("Success", {})
        if success:
            result_dialogs = success.get("DialogMessages", {})
            if result_dialogs:
                for dialog in result_dialogs.get("DialogMessage", []):
                    self._process_dialog_message(dialog)


    def _reply_dialog(self, dialog_id):
        self.ensure_one()
        corresponding_declaration = self.declaration_id
        corresponding_report = self.env[corresponding_declaration.res_model].browse(corresponding_declaration.res_id)
        swissdec_declaration = SwissdecDeclaration()
        declaration = swissdec_declaration.create_reply_dialog(
            domain=self.domain,
            key=self.credential_key,
            password=self.credential_password,
            institution_description=self.result_meta_data.get("institution_description"),
            dialog=dialog_id.to_swissdec_dict(),
        )
        result = self.env.company._l10n_ch_swissdec_request('reply_dialog', data=declaration, is_test=corresponding_report.test_transmission)
        response = result['soap_response']
        message = result['response_xml']
        request_archive = result['request_xml']

        self.dialog_response_json = response

        success = response.get("Dialog", {}).get(self.domain, {}).get("Success", {})
        processing = response.get("Dialog", {}).get(self.domain, {}).get("Processing", {})
        if success:
            dialog_id.status = "Finished"
            result_dialogs = success.get("DialogMessages", {})
            if result_dialogs:
                for dialog in result_dialogs.get("DialogMessage", []):
                    self._process_dialog_message(dialog)
        elif processing:
            dialog_id.status = "Processing"

    def _poll_dialog(self, dialog_id):
        self.ensure_one()
        self.ensure_one()
        corresponding_declaration = self.declaration_id
        corresponding_report = self.env[corresponding_declaration.res_model].browse(corresponding_declaration.res_id)
        swissdec_declaration = SwissdecDeclaration()
        declaration = swissdec_declaration.create_poll_dialog(
            domain=self.domain,
            key=self.credential_key,
            password=self.credential_password,
            institution_description=self.result_meta_data.get("institution_description"),
            dialog_story_id=dialog_id.swissdec_story_id,
        )
        result = self.env.company._l10n_ch_swissdec_request('reply_dialog', data=declaration, is_test=corresponding_report.test_transmission)
        response = result['soap_response']
        message = result['response_xml']
        request_archive = result['request_xml']

        self.dialog_response_json = response
        success = response.get("Dialog", {}).get(self.domain, {}).get("Success", {})
        if success:
            dialog_id.status = "Finished"
            result_dialogs = success.get("DialogMessages", {})
            if result_dialogs:
                for dialog in result_dialogs.get("DialogMessage", []):
                    self._process_dialog_message(dialog)


    def _process_dialog_message(self, dialog):
        self.ensure_one()
        any_answer = False
        raw_sections = dialog.get("Section", [])
        if isinstance(raw_sections, dict):
            raw_sections = [raw_sections]

        raw_paragraphs = dialog.get("Paragraph", [])
        if isinstance(raw_paragraphs, dict):
            raw_paragraphs = [raw_paragraphs]

        # Extract sections
        sections_data = {}
        section_order = []
        for s in raw_sections:
            s_id = s.get("sectionID")
            sections_data[s_id] = {
                "sectionID": s_id,
                "Heading": s.get("Heading"),
                "Description": s.get("Description"),
            }
            section_order.append(s_id)

        # Extract paragraphs
        paragraphs_data = []
        for p in raw_paragraphs:
            paragraphs_data.append(p)

        # Assign sequences so that sections appear first
        sequence = 10
        section_sequence_map = {}
        for s_id in section_order:
            section_sequence_map[s_id] = sequence
            sequence += 10

        dialog_field_vals = []

        # Create section fields first
        for s_id in section_order:
            s_data = sections_data[s_id]
            dialog_field_vals.append(Command.create({
                "field_type": "section",
                "swissdec_id": "0",
                "swissdec_section_id_ref": s_id,
                "swissdec_label": s_data["Heading"],
                "swissdec_value": s_data["Description"],
                "sequence": section_sequence_map[s_id],
            }))

        def _extract_value_type_and_data(value_dict):
            for v_type in ["String", "Integer", "Double", "Boolean", "Date", "DateTime", "YesNoUnknown", "Amount", "Problem"]:
                val = value_dict.get(v_type)
                if val is not None:
                    return v_type, val
            return None, None

        def _assign_answer_fields(vals, a_type, a_default, a_value):
            # If no value but we have a default, treat default as value too
            # This ensures the UI shows the default as a prefilled answer.
            if a_value is None and a_default is not None:
                a_value = a_default

            field_default_name = f"swissdec_answer_default_{a_type}"
            field_value_name = f"swissdec_answer_value_{a_type}"

            # Convert date/datetime to naive UTC if tz-aware
            def normalize_dt(dt_val):
                if isinstance(dt_val, datetime.datetime) and dt_val.tzinfo:
                    dt_val = dt_val.replace(tzinfo=None)
                return dt_val

            a_default = normalize_dt(a_default)
            a_value = normalize_dt(a_value)

            if isinstance(a_value, Decimal):
                a_value = float(a_value)
            if isinstance(a_default, Decimal):
                a_default = float(a_default)

            vals[field_default_name] = a_default
            vals[field_value_name] = a_value

        def _extract_answer_type_and_data(answer_dict):
            is_optional = 'optional' in answer_dict and answer_dict['optional'] is not None
            for a_type in ["String", "Integer", "Double", "Boolean", "Date", "DateTime", "YesNoUnknown", "Amount", "Problem"]:
                a_data = answer_dict.get(a_type)
                if a_data is not None:
                    a_default = a_data.get("Default", None)
                    a_value = a_data.get("Value", None)
                    # If we only have default and no value, value will be set = default later in _assign_answer_fields
                    return a_type, a_default, a_value, is_optional
            return None, None, None, is_optional

        for p in paragraphs_data:
            p_id = p.get("ID")
            label = p.get("Label")
            label = label if label != XSD_SKIP_VALUE else ""
            section_id_ref = p.get("sectionIDRef")
            paragraph_seq = section_sequence_map.get(section_id_ref, 0)

            value_dict = p.get("Value")
            answer_dict = p.get("Answer")

            vals = {
                "swissdec_id": p_id,
                "swissdec_section_id_ref": section_id_ref,
                "swissdec_label": label,
                "sequence": paragraph_seq
            }

            if value_dict:
                v_type, v_val = _extract_value_type_and_data(value_dict)
                if v_type:
                    # Normalize datetime if needed
                    if v_type == "DateTime" and v_val and hasattr(v_val, 'tzinfo') and v_val.tzinfo:
                        v_val = v_val.astimezone(utc).replace(tzinfo=None)
                    if isinstance(v_val, Decimal):
                        v_val = float(v_val)
                    vals.update({
                        "field_type": "value",
                        "swissdec_value_type": v_type,
                        "swissdec_value": str(v_val) if v_val is not None else False,
                    })
                else:
                    vals.update({
                        "field_type": "value",
                        "swissdec_value_type": False,
                        "swissdec_value": False,
                    })
            elif answer_dict:
                any_answer = True
                a_type, a_default, a_value, a_optional = _extract_answer_type_and_data(answer_dict)
                vals["field_type"] = "answer"
                if a_type:
                    vals["swissdec_answer_value_type"] = a_type
                    vals["swissdec_answer_optional"] = a_optional
                    _assign_answer_fields(vals, a_type, a_default, a_value)
                else:
                    vals["swissdec_answer_value_type"] = False
                if a_default is not None:
                    vals["swissdec_has_default"] = True
            else:
                vals.update({
                    "field_type": "value",
                    "swissdec_value_type": False,
                    "swissdec_value": False,
                })

            dialog_field_vals.append(Command.create(vals))

        creation_dt = dialog.get("Creation")
        if creation_dt:
            creation_dt = fields.Datetime.from_string(creation_dt)

        self.env['l10n.ch.dialog.message'].create({
            "swissdec_job_id": self.id,
            "swissdec_creation": creation_dt,
            "swissdec_story_id": uuid.uuid4(),
            "swissdec_StandardDialogID": dialog.get("StandardDialogID"),
            "swissdec_Previous": dialog.get("Previous"),
            "swissdec_Title": dialog.get("Title"),
            "swissdec_Description": dialog.get("Description"),
            "dialog_field_ids": dialog_field_vals,
            "status": "Waiting" if any_answer else "Finished"
        })

    def import_lpp_contributions(self):
        self.ensure_one()
        response_dict = self.result_response_json
        staff = response_dict.get("SalaryResult", {}).get(self.domain, {}).get('Success', {}).get('Staff', {}).get('Person', [])
        message_log = []
        for person in staff:
            contributions = person.get('Contributions', {}).get('Contribution', [])
            employee_first_name = person.get('Firstname', False)
            employee_last_name = person.get('Lastname', False)
            sv_as_number = person.get('Social-InsuranceIdentification', {}).get("SV-AS-Number", False)
            domain = [
                ("l10n_ch_legal_first_name", '=', employee_first_name),
                ("l10n_ch_legal_last_name", '=', employee_last_name),
                ("l10n_ch_sv_as_number", '=', sv_as_number),
            ]
            matching_employee = self.env['hr.employee'].search(domain, limit=1)

            if contributions and matching_employee and matching_employee.contract_id:
                vals = {}
                employee_contributions = float(contributions[0].get('EmployeeContribution') or 0)
                employer_contributions = float(contributions[0].get('EmployerContribution') or 0)
                if employee_contributions:
                    vals["lpp_employee_amount"] = employee_contributions
                if employer_contributions:
                    vals["lpp_company_amount"] = employer_contributions
                if vals:
                    matching_employee.contract_id.write(vals)
                    message_log.append(_("LPP Contributions successfully imported in the following contract: %s", matching_employee.contract_id._get_html_link()))
        if message_log:
            self.message_post(body=Markup('<br/>\n').join(message_log))

    def import_source_tax_corrections(self):
        self.ensure_one()
        response_dict = self.result_response_json
        staff = response_dict.get("SalaryResult", {}).get(self.domain, {}).get('Success', {}).get('Staff', {}).get('Person', [])
        message_log = []

        def _find_employee(firstname, lastname, sv_as_number):
            domain = [
                ("l10n_ch_legal_first_name", '=', firstname),
                ("l10n_ch_legal_last_name", '=', lastname),
                ("l10n_ch_sv_as_number", '=', sv_as_number),
            ]
            return self.env['hr.employee'].search(domain, limit=1)

        def _parse_month_to_date(month):
            return datetime.date(month[0], month[1], 1) + relativedelta(months=1, days=-1)

        def _find_payslips_to_correct(employee, target_date):
            # Find payslips covering the given month (target_date is first day of month)
            first_day = target_date.replace(day=1)
            last_day = (first_day + relativedelta(months=1)) - relativedelta(days=1)
            # Payslips that overlap this month and are done or paid
            payslips = self.env['hr.payslip'].search([
                ('employee_id', '=', employee.id),
                ('state', 'in', ['done', 'paid']),
                ('date_from', '<=', last_day),
                ('date_to', '>=', first_day),
            ])
            return payslips

        def create_lines_from_data(correction, data_dict, payslips, canton, municipality, code_data):
            corrected_payslip = payslips[0]

            taxable_earning = data_dict.get('TaxableEarning')
            sporadic_benefits = data_dict.get('SporadicBenefits')
            ascertained_earning = data_dict.get('AscertainedTaxableEarning')
            tax_at_source = data_dict.get('TaxAtSource')

            corr_vals = {
                **code_data,
                'payslip_id': corrected_payslip.id,
                'l10n_ch_source_tax_canton': canton,
                'l10n_ch_source_tax_municipality': municipality,
                'is_correction_id': correction.id,
                'source_tax_salary': taxable_earning,
                'rate_determinant_salary': ascertained_earning,
                'source_tax_amount': tax_at_source
            }
            if sporadic_benefits:
                corr_vals['source_tax_aperiodic_determinant_salary'] = sporadic_benefits
            self.env["hr.employee.is.line.correction"].create(corr_vals)

        def _parse_st_code(data):
            l10n_ch_tax_scale = False
            l10n_ch_category_predefined = False
            l10n_ch_category_open = False
            children = False
            church = False
            tax_at_source_code = data.get('TaxAtSourceCategory', {}).get('TaxAtSourceCode', None)
            tax_at_source_category = data.get('TaxAtSourceCategory', {}).get('CategoryPredefined', None)
            tax_at_source_open = data.get('TaxAtSourceCategory', {}).get('CategoryOpen', None)
            if tax_at_source_code:
                category = "TaxAtSourceCode"
                l10n_ch_tax_scale = tax_at_source_code[0]
                children = int(tax_at_source_code[1])
                church = True if tax_at_source_code[-1] == "Y" else False
            elif tax_at_source_category:
                category = "CategoryPredefined"
                l10n_ch_category_predefined = tax_at_source_category
            else:
                category = "CategoryOpen"
                l10n_ch_category_open = tax_at_source_open

            return {
                "l10n_ch_tax_scale_type": category,
                "l10n_ch_tax_scale": l10n_ch_tax_scale,
                "children": children,
                "l10n_ch_church_tax": church,
                "l10n_ch_pre_defined_tax_scale": l10n_ch_category_predefined,
                "l10n_ch_open_tax_scale": l10n_ch_category_open
            }

        for person in staff:
            employee_first_name = person.get('Firstname', False)
            employee_last_name = person.get('Lastname', False)
            sv_as_number = (person.get('Social-InsuranceIdentification', {}).get("SV-AS-Number", False))
            employee = _find_employee(employee_first_name, employee_last_name, sv_as_number)
            if not employee:
                continue

            tax_salaries = (person.get('TaxAtSourceSalaries', {}).get('TaxAtSourceSalary', []))
            if isinstance(tax_salaries, dict):
                tax_salaries = [tax_salaries]

            for tax_salary in tax_salaries:
                canton = tax_salary.get('TaxAtSourceCanton')
                municipality = str(tax_salary.get('TaxAtSourceMunicipalityID') or '')
                corrections = tax_salary.get('Correction', [])

                for corr in corrections:
                    if corr.get("Reversal") is not None:
                        reversal = corr['Reversal']
                        if reversal.get('Month'):
                            valid_as_of = _parse_month_to_date(reversal['Month'])
                        else:
                            valid_as_of = fields.Date.today()

                        new_data = reversal.get('New', {})

                        code_data = _parse_st_code(new_data)

                        payslips = _find_payslips_to_correct(employee, valid_as_of)
                        if not payslips:
                            continue
                        correction = self.env['hr.employee.is.line'].create({
                            'employee_id': employee.id,
                            'correction_type': 'aci',
                            'reason': _("Source Tax Reversal"),
                            'correction_method': 'manual',
                            'valid_as_of': valid_as_of,
                            'correction_date': fields.Date.today(),
                            'payslips_to_correct': [(6, 0, payslips.ids)],
                        })
                        message_log.append(_("Source Tax Correction (%(link)s) imported for %(employees)s", link=correction._get_html_link(), employees=employee._get_html_link()))

                        new_data = reversal.get('New', {})
                        create_lines_from_data(correction, new_data, payslips, canton, municipality, code_data)

                    if corr.get("AwaitCorrectionFromCompany") is not None:
                        await_corr = corr['AwaitCorrectionFromCompany']
                        if await_corr.get('ValidAsOf'):
                            valid_as_of_str = await_corr['ValidAsOf']
                            valid_as_of = _parse_month_to_date(valid_as_of_str)
                        else:
                            valid_as_of = fields.Date.today()
                        payslips = _find_payslips_to_correct(employee, valid_as_of)
                        if not payslips:
                            continue
                        correction = self.env['hr.employee.is.line'].create({
                            'employee_id': employee.id,
                            'reason': "Awaiting Correction From Company",
                            'correction_method': 'auto',
                            'valid_as_of': valid_as_of,
                            'correction_date': fields.Date.today(),
                            'payslips_to_correct': [(6, 0, payslips.ids)],
                        })
                        message_log.append(Markup(_("Source Tax Correction (%(link)s) imported for %(employees)s", link=correction._get_html_link(), employees=employee._get_html_link())))
        if message_log:
            self.message_post(body=_("The following Corrections were imported, please confirm them:") + Markup("<br/>") + Markup('<br/>\n').join(message_log))

    def generate_proof_of_insurance(self):
        self.ensure_one()

        response_dict = self.result_response_json
        staff = response_dict.get("SalaryResult", {}).get(self.domain, {}).get('Success', {}).get('Staff', {})
        persons = staff.get('Person', [])
        persons_with_poi = [p for p in persons if p.get('ProofOfInsurance', False)]
        employee_declaration_vals = []
        employees = self.env['hr.employee'].search([('l10n_ch_legal_last_name', '!=', False), ('l10n_ch_legal_first_name', '!=', False)])

        if persons and persons_with_poi:
            result = self.env.company._l10n_ch_swissdec_request('generate_proof_of_insurance', raw_xml=self.last_raw_response)
            binary_pdf = result['proof_of_insurance']
            pdf_bytes = base64.b64decode(binary_pdf.encode())
            pdf_reader = PdfFileReader(BytesIO(pdf_bytes))
            attachments_no_match = self.env['ir.attachment']

            for i, person in enumerate(persons_with_poi):
                pdf_writer = PdfFileWriter()
                pdf_writer.addPage(pdf_reader.pages[i])
                single_page_pdf_stream = BytesIO()
                pdf_writer.write(single_page_pdf_stream)
                single_page_pdf_data = single_page_pdf_stream.getvalue()

                lastname = person.get('Lastname')
                firstname = person.get('Firstname')
                avs_number = person.get('Social-InsuranceIdentification', {}).get("SV-AS-Number", False)
                employee = employees.filtered(lambda e: e.l10n_ch_legal_last_name == lastname and e.l10n_ch_legal_first_name == firstname and e.l10n_ch_sv_as_number == avs_number)

                if len(employee) == 0:
                    attachment_name = f"{lastname}_{firstname}_proof_of_finsurance_{self.transmission_date.year}_{self.transmission_date.month}.pdf"
                    attachments_no_match += self.env['ir.attachment'].create({
                        'name': attachment_name,
                        'datas': base64.encodebytes(single_page_pdf_data),
                        'res_id': self.id,
                        'res_model': self._name,
                    })
                else:
                    employee_declaration_vals.append({
                        'employee_id': employee.id,
                        'res_model': self._name,
                        'res_id': self.id,
                        'pdf_filename': _("Proof_of_insurance_%(year)s_%(name)s", year=self.transmission_date.year, name=employee.name),
                        'pdf_to_generate': False,
                        'state': 'pdf_generated',
                        'pdf_file': base64.encodebytes(single_page_pdf_data)
                    })

            self.env['hr.payroll.employee.declaration'].create(employee_declaration_vals)
            self.message_post(body=_("Proof of Inusrance generated for %s employees", len(employee_declaration_vals)))
            if attachments_no_match:
                self.message_post(body=_("No matched employees were found in the system for %s Proof of insurances", len(attachments_no_match)), attachment_ids=attachments_no_match.ids)

    def _compute_proof_of_insurance_count(self):
        mapped_employee_declarations = dict(self.env['hr.payroll.employee.declaration']._read_group(domain=[('res_model', '=', self._name)], groupby=['res_id'], aggregates=['__count']))

        for declaration in self:
            declaration.proof_of_insurance_count = mapped_employee_declarations.get(declaration.id, 0)

    def action_open_proof_of_insurance(self):
        self.ensure_one()
        return {
            'name': _('Proof of Insurances %(year)s-%(name)s', year=self.transmission_date.year, name=str(self.transmission_date.month).zfill(2)),
            'res_model': 'hr.payroll.employee.declaration',
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'domain': [('res_model', '=', self._name), ('res_id', '=', self.id)],
        }

    def generate_is_statement(self):
        self.ensure_one()
        result = self.env.company._l10n_ch_swissdec_request('generate_verified_tax_statement', raw_xml=self.last_raw_response)
        binary_pdf = result['verified_tax_statement']

        attachment = self.env['ir.attachment'].create({
            'name': f"Verified_st_statement_{self.declaration_id.swissdec_declaration_id}.pdf",
            'datas': binary_pdf,
            'res_id': self.id,
            'res_model': self._name,
        })
        self.message_post(attachment_ids=[attachment.id],
                                 body=_('Verified Source-Tax Statement'))
