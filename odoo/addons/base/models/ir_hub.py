# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrHub(models.Model):
    _name = 'ir.hub'
    _description = 'Hub'
    _order = 'name, id'
    _allow_sudo_commands = False

    name = fields.Char(required=True, translate=True)
    res_model = fields.Char(string='Model', required=True, help="Model of the record the hub is opened for")
    item_ids = fields.One2many('ir.hub.item', 'hub_id', string='Items')

    _unique_res_model = models.Constraint(
        'UNIQUE(res_model)',
        "A model can only have one hub.",
    )


class IrHubItem(models.Model):
    _name = 'ir.hub.item'
    _description = 'Hub Item'
    _order = 'sequence, id'
    _allow_sudo_commands = False

    hub_id = fields.Many2one('ir.hub', string='Hub', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(translate=True)
    # exactly one of action_id or python_method is set
    action_id = fields.Many2one('ir.actions.actions', string='Action', ondelete='cascade')
    python_method = fields.Char(help="Method of the hub's model, called on the hub's record, returning an action")
    res_model = fields.Char(
        string='Model',
        help="Model of the records opened by the python method. The item is only visible to the "
             "users who can read it, as for the model of the action of an item with an action.",
    )
    context = fields.Char(default='{}')
    group_ids = fields.Many2many(
        'res.groups', string='Groups',
        help="Groups that can see the item, on top of the access to its action. "
             "Leave empty to allow everybody.",
    )

    _check_action_or_python_method = models.Constraint(
        'CHECK((action_id IS NULL) != (python_method IS NULL))',
        "A hub item must have either an action or a python method, but not both.",
    )
    _check_python_method_requires_name = models.Constraint(
        'CHECK(python_method IS NULL OR name IS NOT NULL)',
        "A hub item with a python method must have a name.",
    )
    _check_python_method_requires_res_model = models.Constraint(
        'CHECK(python_method IS NULL OR res_model IS NOT NULL)',
        "A hub item with a python method must have a model.",
    )
    _check_python_method_is_action = models.Constraint(
        "CHECK(python_method IS NULL OR python_method LIKE 'action\\_%')",
        "The python method of a hub item must be an action method (action_*).",
    )

    @api.depends('name', 'action_id.name')
    def _compute_display_name(self):
        for item in self:
            # the user might not have access to the action
            item.display_name = item.name or item.action_id.sudo().name

    def _filter_visible(self):
        """ Return the items of ``self`` visible to the current user: the user
        must belong to one of the groups of the item and of its action (if any),
        and be able to read the model of the item and of its action (if any).
        """
        user_groups = self.env.user.all_group_ids

        def has_groups(record):
            groups = record.group_ids if 'group_ids' in record._fields else None
            return not groups or bool(groups & user_groups)

        def can_read(model_name):
            return not model_name or (model_name in self.env and self.env[model_name].has_access('read'))

        def is_visible(item):
            if not has_groups(item) or not can_read(item.res_model):
                return False
            if item.action_id:
                # the user might not have access to the action
                action = item.action_id.sudo()
                action = self.env[action.type].sudo().browse(action.id)
                if not has_groups(action):
                    return False
                if 'res_model' in action._fields and not can_read(action.res_model):
                    return False
            return True

        return self.filtered(is_visible)
