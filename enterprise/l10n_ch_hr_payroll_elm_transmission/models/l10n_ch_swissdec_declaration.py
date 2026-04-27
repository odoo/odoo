# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

from odoo import api, fields, models, _, Command
from odoo.exceptions import UserError
from ..api.swissdec_declarations import SwissdecDeclaration
from .hr_employee import CANTONS

import json
import base64
import re

XSD_SKIP_VALUE = "XSDSKIP"


class L10nCHSwissdecDeclaration(models.Model):
    _name = 'l10n.ch.swissdec.declaration'
    _inherit = 'mail.thread'
    _description = 'Swissdec Declaration'
    _order = "transmission_date desc"

    @api.model
    def default_get(self, field_list=None):
        if self.env.company.country_id.code != "CH":
            raise UserError(_('You must be logged in a Swiss company to use this feature'))
        return super().default_get(field_list)

    res_model = fields.Char(
        'Declaration Model Name', required=True, index=True)
    res_id = fields.Many2oneReference(
        'Declaration Model Id', index=True, model_field='res_model', required=True)
    name = fields.Char(required=True, readonly=True)
    state = fields.Selection(selection=[("waiting", "Waiting for Status"),
                                        ("plausibility", "Verifying Plausibility"),
                                        ("processing", "Processing"),
                                        ("finished", "Finished")], default="waiting", required=True)
    year = fields.Integer(readonly=True)
    month = fields.Char(readonly=True)
    transmission_date = fields.Datetime(required=True, readonly=True)
    test_transmission = fields.Boolean(string="Test Transmission")
    swissdec_declaration_id = fields.Char(string="Declaration ID", required=True, readonly=True)
    job_key = fields.Char(required=True, readonly=True)
    general_warnings = fields.Json()
    l10n_ch_swissdec_job_result_ids = fields.One2many('l10n.ch.swissdec.job.result', 'declaration_id', string="Results")

    def _process_responses(self, vals):
        self.ensure_one()
        current_running_jobs = self.l10n_ch_swissdec_job_result_ids.grouped('institution_id_ref')
        lines_to_create = []
        for institution in vals:
            existing_job = current_running_jobs.get(institution["institution_id_ref"], self.env["l10n.ch.swissdec.job.result"])
            if existing_job:
                existing_job.update(institution)
            else:
                lines_to_create.append((0, 0, institution))
        self.update({'l10n_ch_swissdec_job_result_ids': lines_to_create})

    def _match_foreign_canton(self, notifications):
        """
        When salary certificates are for foreign employees, the canton it is sent to is not straightforward and has to be guessed from notifications
        """
        pattern = re.compile(
            r'\b(' + '|'.join(re.escape(code[0]) for code in CANTONS) + r')\b'
        )
        canton = False
        for notification in notifications:
            match = pattern.search(notification.get("Description", ""))
            if match:
                canton = match.group(1)
                break
        if not canton: # We have to fallback in case swissdec did not provide a notification
            canton = self.env.company.l10n_ch_work_location_ids[0].canton
        return canton

    def get_status_from_declare_salary(self):
        self.ensure_one()
        if self.state != "finished":
            swissdec_declaration = SwissdecDeclaration()
            declaration = swissdec_declaration.create_get_status_from_declare_salary(
                job_key=self.job_key,
            )

            result = self.env.company._l10n_ch_swissdec_request('get_status_from_declare_salary', data=declaration, is_test=self.test_transmission)
            response = result['soap_response']
            message_archive = result['request_xml']
            response_archive = result['response_xml']

            if response:
                attachment_request = self.env['ir.attachment'].create({
                    'name': _("Get_Status_%s_request.xml", self.swissdec_declaration_id),
                    'datas': base64.encodebytes(message_archive.encode()),
                    'res_id': self.id,
                    'res_model': self._name,
                })

                attachment_response = self.env['ir.attachment'].create({
                    'name': _("Declaration_%s_response.xml", self.swissdec_declaration_id),
                    'datas': base64.encodebytes(response_archive.encode()),
                    'res_id': self.id,
                    'res_model': self._name,
                })
                self.message_post(attachment_ids=[attachment_request.id, attachment_response.id], body=_('Get Status Archive'))


                #response = serialize_object(response)
                corresponding_report = self.env[self.res_model].browse(self.res_id)
                institution_descriptions = swissdec_declaration.get_mapped_institution_descriptions(institutions=corresponding_report._get_institutions())
                job_responses = []

                plausiblity_state = response.get("PlausibilityState", {}).get("Plausible")
                if not plausiblity_state:
                    self.state = "plausibility"
                else:
                    if response.get("JobFinished", False):
                        self.state = "finished"
                    else:
                        self.state = "processing"
                    if plausiblity_state.get("Info", None) or plausiblity_state.get("Warning", None):
                        self.general_warnings = {
                            "Info": plausiblity_state.get("Info", None),
                            "Warning": plausiblity_state.get("Warning", None)
                        }
                    else:
                        self.general_warnings = False

                    job_state = plausiblity_state.get("JobState")
                    for domain, institutions in job_state.items():
                        if institutions:
                            for institution in iter([institutions] if not isinstance(institutions, list) else institutions):
                                if domain not in ["Tax", "Statistic"]:
                                    institution_description = institution_descriptions.get(institution.get("institutionIDRef", False))
                                    id_ref = institution.get("institutionIDRef", False)
                                elif domain == "Tax":
                                    id_ref = institution.get("canton")
                                    if id_ref == 'EX':
                                        notifications_success = institution.get("Success", {})
                                        notifications = []
                                        if notifications_success:
                                            notifications = notifications_success.get("ResponseState", {}).get("Info", {}).get("Notification", [])
                                        canton = self._match_foreign_canton(notifications)
                                    else:
                                        canton = id_ref
                                    institution_description = {
                                        "CantonID": canton
                                    }
                                else:
                                    id_ref = "#BFS"
                                    institution_description = False

                                meta_data = {
                                    "institution_id_ref": id_ref,
                                    "institution_description": institution_description,
                                }
                                job_vals = {
                                    "domain": domain,
                                    "declaration_id": self.id,
                                    "institution_id_ref": id_ref
                                }

                                if institution.get("Ignored"):
                                    job_vals.update({
                                        "general_state": "Ignored",
                                    })
                                if institution.get("NotSupported"):
                                    job_vals.update({
                                        "general_state": "NotSupported",
                                    })
                                elif institution.get("Processing"):
                                    job_vals.update({
                                        "general_state": "Processing",
                                    })
                                elif institution.get("Error"):
                                    job_vals.update({
                                        "general_state": "Error",
                                        "status_response_json": json.loads(json.dumps(institution.get("Error"), default=str)),
                                    })
                                elif institution.get("Success"):
                                    job_vals.update({
                                        "general_state": "Success",
                                    })
                                    if institution.get("Success").get("ResponseState", {}).get("Info", {}) or institution.get("Success").get("ResponseState", {}).get("Warning", {}):
                                        job_vals.update({
                                            "status_response_json": json.loads(json.dumps(institution.get("Success"), default=str)),
                                        })
                                    success_vals = institution.get("Success")
                                    if success_vals.get("CompletionAndResult"):
                                        completion_result = success_vals.get("CompletionAndResult")
                                        job_vals.update({
                                            "success_state": "CompletionAndResult",
                                            "completion_url": completion_result.get("Completion", {}).get("Url"),
                                            "credential_key": completion_result.get("Credentials", {}).get("Key"),
                                            "credential_password": completion_result.get("Credentials", {}).get("Password")
                                        })
                                    elif success_vals.get("Result"):
                                        institution_result = success_vals.get("Result")
                                        job_vals.update({
                                            "success_state": "Result",
                                            "credential_key": institution_result.get("Credentials", {}).get("Key"),
                                            "credential_password": institution_result.get("Credentials", {}).get("Password")
                                        })
                                    elif success_vals.get("DialogAndResult"):
                                        dialog_result = success_vals.get("DialogAndResult")
                                        job_vals.update({
                                            "success_state": "DialogAndResult",
                                            "credential_key": dialog_result.get("Credentials", {}).get("Key"),
                                            "credential_password": dialog_result.get("Credentials", {}).get("Password")
                                        })
                                job_vals.update({
                                    "result_meta_data": meta_data
                                })
                                job_responses.append(job_vals)

                    self._process_responses(job_responses)
