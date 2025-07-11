# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ast import literal_eval


class IrEmbeddedActions(models.Model):
    _name = 'ir.embedded.actions'
    _description = 'Embedded Actions'
    _order = 'sequence, id'

    name = fields.Char(translate=True)
    sequence = fields.Integer()
    parent_action_id = fields.Many2one('ir.actions.act_window', required=True, string='Parent Action', ondelete="cascade")
    parent_res_id = fields.Integer(string="Active Parent Id")
    parent_res_model = fields.Char(string='Active Parent Model', required=True)
    # It is required to have either action_id or python_method
    action_id = fields.Many2one('ir.actions.actions', string="Action", ondelete="cascade")
    python_method = fields.Char(help="Python method returning an action")

    user_id = fields.Many2one('res.users', string="User", help="User specific embedded action. If empty, shared embedded action", ondelete="cascade")
    is_deletable = fields.Boolean(compute="_compute_is_deletable")
    default_view_mode = fields.Char(string="Default View", help="Default view (if none, default view of the action is taken)")
    filter_ids = fields.One2many("ir.filters", "embedded_action_id", help="Default filter of the embedded action (if none, no filters)")
    is_visible = fields.Boolean(string="Embedded visibility", help="Computed field to check if the record should be visible according to the domain", compute="_compute_is_visible")
    domain = fields.Char(default="[]", help="Domain applied to the active id of the parent model")
    context = fields.Char(default="{}", help="Context dictionary as Python expression, empty by default (Default: {})")
    groups_ids = fields.Many2many('res.groups', help='Groups that can execute the embedded action. Leave empty to allow everybody.')

    _check_only_one_action_defined = models.Constraint(
        '''CHECK(
            (action_id IS NOT NULL AND python_method IS NULL)
            OR (action_id IS NULL AND python_method IS NOT NULL)
        )''',
        "Constraint to ensure that either an XML action or a python_method is defined, but not both.",
    )
    _check_python_method_requires_name = models.Constraint(
        'CHECK(NOT (python_method IS NOT NULL AND name IS NULL))',
        "Constraint to ensure that if a python_method is defined, then the name must also be defined.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # The name by default is computed based on the triggered action if a action_id is defined.
        for vals in vals_list:
            if "name" not in vals:
                vals["name"] = self.env["ir.actions.actions"].browse(vals["action_id"]).name
            if "python_method" in vals and "action_id" in vals:
                if vals.get("python_method"):
                    # then remove the action_id since the action surely given by the python method.
                    del vals["action_id"]
                else:  # remove python_method in the vals since the vals is falsy.
                    del vals["python_method"]
        return super().create(vals_list)

    # The record is deletable if it hasn't been created from a xml record (i.e. is not a default embedded action)
    def _compute_is_deletable(self):
        external_ids = self._get_external_ids()
        for record in self:
            record_external_ids = external_ids[record.id]
            record.is_deletable = all(
                ex_id.startswith(("__export__", "__custom__")) for ex_id in record_external_ids
            )

    # Compute if the record should be visible to the user based on the domain applied to the active id of the parent
    # model and based on the groups allowed to access the record.
    def _compute_is_visible(self):
        active_id = self.env.context.get("active_id", False)
        if not active_id:
            self.is_visible = False
            return
        domain_id = [("id", "=", active_id)]
        for parent_res_model, records in self.grouped('parent_res_model').items():
            active_model_record = self.env[parent_res_model].search(domain_id, order='id')
            for record in records:
                action_groups = record.groups_ids
                is_valid_method = not record.python_method or hasattr(self.env[parent_res_model], record.python_method)
                if is_valid_method and (not action_groups or (action_groups & self.env.user.all_group_ids)):
                    domain_model = literal_eval(record.domain or '[]')
                    record.is_visible = (
                        record.parent_res_id in (False, self.env.context.get('active_id', False))
                        and record.user_id.id in (False, self.env.uid)
                        and active_model_record.filtered_domain(domain_model)
                    )
                else:
                    record.is_visible = False

    # Delete the filters linked to a embedded action.
    @api.ondelete(at_uninstall=False)
    def _unlink_if_action_deletable(self):
        for record in self:
            if not record.is_deletable:
                raise UserError(_('You cannot delete a default embedded action'))

    def _get_readable_fields(self):
        """ return the list of fields that are safe to read
        """
        return {
            "name", "parent_action_id", "parent_res_id", "parent_res_model", "action_id", "python_method", "user_id",
            "is_deletable", "default_view_mode", "filter_ids", "domain", "context", "groups_ids"
        }
