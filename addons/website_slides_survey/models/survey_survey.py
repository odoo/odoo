# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api, _
from odoo.exceptions import ValidationError


class Survey(models.Model):
    _inherit = 'survey.survey'

    @api.constrains('certificate')
    def _check_if_referenced_by_certification_slides(self):
        for record in self:
            if not record.certificate:
                matched_slides = record.env['slide.slide'].search([('slide_type', '=', 'certification'), ('survey_id', '=', record.id)])
                if matched_slides:
                    raise ValidationError(_('You cannot remove the certificate status of a survey that is still referenced by a course as its certification. '
                                            'Please reactivate the certificate status or remove the survey as a certification for the courses:') +
                                          f' {", ".join([slide.name for slide in matched_slides])}.')

    def _check_answer_creation(self, user, partner, email, test_entry=False, check_attempts=True, invite_token=False):
        """ Overridden to allow website_publisher to test certifications. """
        self.ensure_one()
        if test_entry and user.has_group('website.group_website_publisher'):
            return True

        return super(Survey, self)._check_answer_creation(user, partner, email, test_entry=test_entry, check_attempts=check_attempts, invite_token=invite_token)
