# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import expr_eval
from odoo.osv import expression

class IrActionsTopbar(models.Model):
    _name = 'ir.actions.topbar'
    _description = 'TopBar Actions'
    _table = 'ir_act_topbar'
    _order = 'sequence'

    parent_action_id = fields.Many2one('ir.actions.act_window', string='Parent Action', ondelete="cascade")
    name = fields.Char(string='Action Name', required=False, translate=True)
    sequence = fields.Integer()
    res_id = fields.Integer(string="Active Parent Id")
    res_model = fields.Char(string='Active Parent Model', required=True)
    # It is required to have either action_id or python_action
    action_id = fields.Many2one('ir.actions.act_window', string="Action Id", ondelete="cascade")
    python_action = fields.Char(string="Python Action")
    user_id = fields.Many2one('res.users', string="User specific topbar action. If empty, shared topbar action", ondelete="cascade")
    is_deletable = fields.Boolean(compute="_compute_is_deletable")
    default_view_mode = fields.Char(string="Default view (if none, default view of the action is taken)")
    filter_ids = fields.One2many("ir.filters", "topbar_action_id", string="Default filter of the topbar action (if none, no filters)")
    is_visible = fields.Boolean(string="Computed field to check if the record should be visible acording to the domain", compute="_compute_is_visible")
    domain = fields.Char(string='Domain Value', default="[]",
                         help="Domain applied to the current Id of the Parent Model")
    context = fields.Char(string='Context Value', default={},
                          help="Context dictionary as Python expression, empty by default (Default: {})")
    groups_id = fields.Many2many('res.groups', 'ir_topbar_act_group_rel',
                                 'act_id', 'gid', string='Allowed Groups', help='Groups that can execute the topbar action. Leave empty to allow everybody.')

    @api.constrains('action_id', 'python_action')
    def _check_only_one_action_defined(self):
        for record in self:
            if bool(record.action_id) == bool(record.python_action):
                raise ValidationError("You cannot define a xml action and a python action for the same topbar action.")
            elif record.python_action and not record.name:
                raise ValidationError("You cannot define a python action and not define the name.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "name" not in vals:
                vals["name"] = self.env["ir.actions.act_window"].browse(vals["action_id"]).name
        return super().create(vals_list)

    def _compute_is_deletable(self):
        external_ids = self._get_external_ids()
        for record in self:
            record_external_ids = external_ids[record.id]
            record.is_deletable = all(
                ex_id.startswith(("__export__", "__custom__")) for ex_id in record_external_ids
            )

    def _compute_is_visible(self):
        active_id = self.env.context.get("active_id", False)
        domain_id = [("id", "=", active_id)] if active_id else []
        for record in self:
            action_groups = record.groups_id
            if not action_groups or (action_groups & self.env.user.groups_id):
                domain_model = expr_eval(record.domain)
                record.is_visible = self.env[record.res_model].search_count(expression.AND([domain_id, domain_model]))
            else:
                record.is_visible = False

    @api.ondelete(at_uninstall=True)
    def _unlink_if_action_deletable(self):
        for record in self:
            if not record.is_deletable:
                raise UserError(_('You cannot delete a default topbar action'))
            else:
                record.filter_ids.unlink()
