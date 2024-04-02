# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class RecruitmentSource(models.Model):
    _name = "hr.recruitment.source"
    _description = "Source of Applicants"
    _inherit = ['utm.source.mixin']

    email = fields.Char(related='alias_id.display_name', string="Email", readonly=True)
    has_domain = fields.Char(compute='_compute_has_domain')
    job_id = fields.Many2one('hr.job', "Job", ondelete='cascade')
    alias_id = fields.Many2one('mail.alias', "Alias ID")
    medium_id = fields.Many2one('utm.medium', default=lambda self: self.env.ref('utm.utm_medium_website'))

    def _compute_has_domain(self):
        self.has_domain = bool(self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain"))

    def create_alias(self):
        campaign = self.env.ref('hr_recruitment.utm_campaign_job')
        medium = self.env.ref('utm.utm_medium_email')
        for source in self:
            vals = {
                'alias_parent_thread_id': source.job_id.id,
                'alias_model_id': self.env['ir.model']._get('hr.applicant').id,
                'alias_parent_model_id': self.env['ir.model']._get('hr.job').id,
                'alias_name': "%s+%s" % (source.job_id.alias_name or source.job_id.name, source.name),
                'alias_defaults': {
                    'job_id': source.job_id.id,
                    'campaign_id': campaign.id,
                    'medium_id': medium.id,
                    'source_id': source.source_id.id,
                },
            }
            # check that you can create source before to call mail.alias in sudo with known/controlled vals
            source.check_access_rights('create')
            source.check_access_rule('create')
            source.alias_id = self.env['mail.alias'].sudo().create(vals)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'tree' and not bool(self.env["ir.config_parameter"].sudo().get_param("mail.catchall.domain")):
            email = arch.xpath("//field[@name='email']")[0]
            email.getparent().remove(email)
        return arch, view
