# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class IrActionsHub(models.Model):
    _name = 'ir.actions.hub'
    _description = 'Hub Action'
    _inherit = ['ir.actions.actions']
    _table = 'ir_act_hub'
    _order = 'name, id'
    _allow_sudo_commands = False

    type = fields.Char(default='ir.actions.hub')
    res_model = fields.Char(string='Model', required=True, help="Model of the record the hub is opened for")
    item_ids = fields.One2many('ir.actions.hub.item', 'hub_id', string='Items')

    _unique_res_model = models.Constraint(
        'UNIQUE(res_model)',
        "A model can only have one hub.",
    )

    def _get_readable_fields(self):
        return super()._get_readable_fields() | {
            "res_model", "item_ids",
        }

    def _get_action_dict(self):
        result = super()._get_action_dict()

        # Load hub items
        Items = self.env['ir.actions.hub.item']
        result['item_ids'] = Items.browse(result['item_ids']).read(list(Items._get_readable_fields()))

        # set display_name based on active record
        if active_id := self.env.context.get('active_id'):
            active_record = self.env[self.res_model].sudo(False).browse(active_id).read(['display_name'])
            result['display_name'] = active_record[0]['display_name']

        return result


# TODO: what happens when an action an item points to is deleted ? we need to also delete the item
class IrActionsHubItem(models.Model):
    _name = 'ir.actions.hub.item'
    _description = 'Hub Action Item'
    _order = 'sequence, id'
    _allow_sudo_commands = False

    hub_id = fields.Many2one('ir.actions.hub', string='Hub', required=True, index=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    name = fields.Char(translate=True)
    # exactly one of action_id or python_method is set
    action_id = fields.Many2one('ir.actions.actions', string='Action', ondelete='cascade')
    python_method = fields.Char(help="Method of the hub's model, called on the hub's record, returning an action")
    context = fields.Char(default='{}')

    _check_action_or_python_method = models.Constraint(
        'CHECK((action_id IS NULL) != (python_method IS NULL))',
        "A hub item must have either an action or a python method, but not both.",
    )
    _check_python_method_requires_name = models.Constraint(
        'CHECK(python_method IS NULL OR name IS NOT NULL)',
        "A hub item with a python method must have a name.",
    )

    @api.depends('name', 'action_id.name')
    def _compute_display_name(self):
        for item in self:
            # the user might not have access to the action
            item.display_name = item.name or item.action_id.sudo().name

    def _get_readable_fields(self):
        """ Fields sent to the web client along with the hub. """
        return {"id", "display_name", "action_id", "python_method", "context"}
