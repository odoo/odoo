# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    def website_form_input_filter(self, request, values):
        if values.get('job_id'):
            job = self.env['hr.job'].browse(values.get('job_id'))
            if not job.sudo().active:
                raise UserError(self.env._("The job opportunity has been closed."))
            stage = self.env['hr.recruitment.stage'].sudo().search([
                ('fold', '=', False),
                '|', ('job_ids', '=', False), ('job_ids', '=', values['job_id']),
            ], order='sequence asc', limit=1)
            if stage:
                values['stage_id'] = stage.id
        return values

    def _generate_duplicate_applicant_message(self, message, matching_applicants):
        return Markup("<p>{message}</p><ul>{applicants}</ul>").format(
            message=message,
            applicants=Markup().join(
                [
                    Markup("<li><a href='/odoo/hr.applicant/{id}'>{name}</li>").format(
                        id=applicant.id,
                        name=applicant.partner_name,
                    )
                    for applicant in matching_applicants
                ],
            ),
        )

    def _handle_potential_duplicate_web_applications(self):
        """
        This method checks if any newly created applicants in self can be considered duplicates of existing applicants
        and adds an activity on the duplicate record. An applicant is considered a duplicate if it belongs to the same
        job position and shares any or all of the following fields: email address, phone number and linkedin profile.
        """
        existing_applicants_domain = Domain.AND(
            [
                self._get_similar_applicants_domain(ignore_talent=True),
                Domain("job_id", "in", [job for job in self.mapped("job_id.id") if job]),
                Domain.OR(
                    [
                        Domain("refuse_date", ">=", fields.Datetime.now() - relativedelta(months=6)),
                        Domain("refuse_date", "=", False),
                    ],
                ),
                Domain("id", "not in", self.ids),
            ],
        )
        existing_applicants = self.with_context(active_test=False).search(
            domain=existing_applicants_domain,
            order="create_date desc",
        )

        refused_existing_applicants = defaultdict(lambda: defaultdict(lambda: self.env["hr.applicant"]))
        ongoing_existing_applicants = defaultdict(lambda: defaultdict(lambda: self.env["hr.applicant"]))

        for applicant in existing_applicants:
            if applicant.application_status == "refused":
                refused_existing_applicants[applicant.job_id.id][applicant.email_normalized] += applicant
                refused_existing_applicants[applicant.job_id.id][applicant.partner_phone_sanitized] += applicant
                refused_existing_applicants[applicant.job_id.id][applicant.linkedin_profile] += applicant
            elif applicant.application_status == "ongoing":
                ongoing_existing_applicants[applicant.job_id.id][applicant.email_normalized] += applicant
                ongoing_existing_applicants[applicant.job_id.id][applicant.partner_phone_sanitized] += applicant
                ongoing_existing_applicants[applicant.job_id.id][applicant.linkedin_profile] += applicant

        for applicant in self:
            refused_job_matches = refused_existing_applicants.get(applicant.job_id.id)
            ongoing_job_matches = ongoing_existing_applicants.get(applicant.job_id.id)

            if refused_job_matches:
                if matching_applicants := (
                    refused_job_matches.get(applicant.email_normalized, self.env["hr.applicant"])
                    | refused_job_matches.get(applicant.partner_phone_sanitized, self.env["hr.applicant"])
                    | refused_job_matches.get(applicant.linkedin_profile, self.env["hr.applicant"])
                ):
                    applicant.activity_schedule(
                        act_type_xmlid="mail_activity_data_todo",
                        summary=self.env._("Potential Duplicate Detected: Refused Application"),
                        note=self._generate_duplicate_applicant_message(
                            self.env._(
                                "The following recently refused applications share an email address, phone number and/or linkedin profile with this application:",
                            ),
                            matching_applicants,
                        ),
                        user_id=applicant.recruiter_id.user_id.id or applicant.job_id.recruiter_id.user_id.id,
                    )
            elif ongoing_job_matches:
                if matching_applicants := (
                    ongoing_job_matches.get(applicant.email_normalized, self.env["hr.applicant"])
                    | ongoing_job_matches.get(applicant.partner_phone_sanitized, self.env["hr.applicant"])
                    | ongoing_job_matches.get(applicant.linkedin_profile, self.env["hr.applicant"])
                ):
                    applicant.activity_schedule(
                        act_type_xmlid="mail_activity_data_todo",
                        summary=self.env._("Potential Duplicate Detected: Ongoing Application"),
                        note=self._generate_duplicate_applicant_message(
                            self.env._(
                                "The following ongoing applications share an email address, phone number and/or linkedin profile with this application:",
                            ),
                            matching_applicants,
                        ),
                        user_id=applicant.recruiter_id.user_id.id or applicant.job_id.recruiter_id.user_id.id,
                    )

    @api.model_create_multi
    def create(self, vals_list):
        applicants = super().create(vals_list)

        applicants_applied_through_website = "website_id" in self.env.context
        if applicants_applied_through_website:
            applicants._handle_potential_duplicate_web_applications()

        return applicants
