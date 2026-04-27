# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BudgetAnalytic(models.Model):
    _name = "budget.analytic"
    _description = "Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Budget Name', required=True)
    parent_id = fields.Many2one(
        string="Revision Of",
        comodel_name='budget.analytic',
        ondelete='cascade',
    )
    children_ids = fields.One2many(
        string="Revisions",
        comodel_name='budget.analytic',
        inverse_name='parent_id',
    )
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    date_from = fields.Date('Start Date', required=True)
    date_to = fields.Date('End Date', required=True)
    state = fields.Selection(
        string="Status",
        selection=[
            ('draft', "Draft"),
            ('confirmed', "Open"),
            ('revised', "Revised"),
            ('done', "Done"),
            ('canceled', "Canceled")
        ],
        required=True, default='draft',
        readonly=True,
        copy=False,
        tracking=True,
    )
    budget_type = fields.Selection(
        string="Budget Type",
        selection=[
            ('revenue', "Revenue"),
            ('expense', "Expense"),
            ('both', "Both"),
        ],
        required=True, default='expense',
        copy=False,
    )
    budget_line_ids = fields.One2many('budget.line', 'budget_analytic_id', 'Budget Lines', copy=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)

    @api.constrains('parent_id')
    def _check_parent_id(self):
        for budget in self:
            if budget._has_cycle():
                raise ValidationError(_('You cannot create recursive revision of budget.'))

    @api.ondelete(at_uninstall=False)
    def _unlink_except_draft_or_cancel(self):
        if any(budget.state not in ('draft', 'canceled') for budget in self):
            raise UserError(_("Deletion is only allowed in the Draft and Canceled stages."))

    def action_budget_confirm(self):
        self.parent_id.filtered(lambda b: b.state == 'confirmed').state = 'revised'
        for budget in self:
            budget.state = 'revised' if budget.children_ids else 'confirmed'

    def action_budget_draft(self):
        self.state = 'draft'

    def action_budget_cancel(self):
        self.state = 'canceled'

    def action_budget_done(self):
        self.state = 'done'

    def create_revised_budget(self):
        revised = self.browse()
        for budget in self:
            revised_budget = budget.copy(default={'name': _('REV %s', budget.name), 'parent_id': budget.id, 'budget_type': budget.budget_type})
            revised += revised_budget
            budget.message_post(
                body=Markup("%s: <a href='#' data-oe-model='budget.analytic' data-oe-id='%s'>%s</a>") % (
                    _("New revision"),
                    revised_budget.id,
                    revised_budget.name,
                ))
        return revised._get_records_action()

    def action_open_budget_lines(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Budget Lines'),
            'res_model': 'budget.line',
            'view_mode': 'list,pivot,graph',
            'domain': [('budget_analytic_id', 'in', self.ids)],
        }

    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        return self.env['analytic.plan.fields.mixin']._patch_view(arch, view, view_type)  # patch the budget lines list view
