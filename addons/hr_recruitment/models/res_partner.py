# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.hr_recruitment.models.hr_recruitment import AVAILABLE_PRIORITIES


class ResPartner(models.Model):
    _inherit = "res.partner"

    application_ids = fields.One2many('hr.applicant', 'partner_id')
    application_count = fields.Integer(compute='_compute_application_count', store=True)
    appreciation = fields.Selection(AVAILABLE_PRIORITIES, 'Appreciation', compute='_compute_applicant', store=True)
    applicant_hired = fields.Boolean(compute='_compute_applicant', store=True)
    applicant_degree = fields.Many2one('hr.recruitment.degree', compute='_compute_applicant', store=True)
    applicant_job_id = fields.Many2one('hr.job', compute='_compute_applicant', store=True)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_applications(self):
        if self.application_ids:
            raise UserError(
                _('You cannot delete a Contact linked to recruitment applications, consider archiving it instead.'))

    @api.depends('application_ids')
    def _compute_application_count(self):
        application_data = self.env['hr.applicant'].with_context(active_test=False).read_group(
            [('partner_id', 'in', self.ids)], ['partner_id'], ['partner_id'])
        applications = {a['partner_id'][0]: a['partner_id_count'] for a in application_data}
        for partner in self:
            partner.application_count = applications.get(partner.id, 0)

    @api.depends('application_ids', 'application_ids.priority', 'application_ids.date_closed', 'application_ids.type_id')
    def _compute_applicant(self):
        available_appreciation = dict(AVAILABLE_PRIORITIES).keys()
        for partner in self:
            appreciation_avg = str(round(sum(partner.application_ids.mapped(lambda a: int(a.priority))) / (partner.application_count or 1)))
            partner.applicant_hired = partner.application_ids.filtered('date_closed')
            partner.appreciation = appreciation_avg if appreciation_avg in available_appreciation else '0'
            partner.applicant_degree = next((a.type_id for a in partner.application_ids.sorted('create_date', reverse=True) if a.type_id), False)
            application_hired = partner.application_ids.filtered('emp_id')
            partner.applicant_job_id = application_hired[0].job_id if application_hired else False

    def action_applicant_history(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Job Applications for %s', self.name),
            'res_model': 'hr.applicant',
            'view_mode': 'tree,kanban,form',
            'views': [[False, 'list'], [False, 'kanban'], [False, 'form']],
            'domain': [('partner_id', '=', self.id)],
            'context': {
                'active_test': False
            },
        }
