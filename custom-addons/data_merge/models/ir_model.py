# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _

class IrModel(models.Model):
    _inherit = 'ir.model'

    hide_merge_action = fields.Boolean(
        string='Hide merge action button', compute="_compute_hide_merge_action",
        help="""If the model already has a custom merge method, the class attribute `_merge_disabled` is set to true on
             that model and the generic data merge action should not be available on that model."""
    )
    # contextual merge records server action
    ref_merge_ir_act_server_id = fields.Many2one(
        'ir.actions.server', string='Merge Server Action', readonly=True, copy=False,
        help="Contextual menu action that redirects to the deduplicate view of data_merge."
    )
    is_merge_enabled = fields.Boolean(
        string="Can Be Merged", compute='_compute_is_merge_enabled',
        help="""If True, the generic data merge tool is available in the contextual menu of this model."""
    )

    def _compute_hide_merge_action(self):
        """ This method is meant to be overridden to add display conditions for "enable/disable merge action" button
         in the model's form view.
         Typically, models like res.partner or crm.lead already has a custom merge action and we do not want to
         enable generic merge action on those models."""
        for model in self:
            model.hide_merge_action = getattr(self.env[model.model], "_disable_data_merge", False)

    @api.depends('ref_merge_ir_act_server_id')
    def _compute_is_merge_enabled(self):
        for model in self:
            model.is_merge_enabled = bool(model.ref_merge_ir_act_server_id)

    # ---------------
    # Actions
    # ---------------

    def action_merge_contextual_enable(self):
        server_action_values = {
            'name': _('Merge'),
            'binding_view_types': 'list',
            'state': 'code',
            'code': "action = env['data_merge.record'].action_deduplicates(records)",
            'groups_id': [(4, self.env.ref('base.group_system').id)] # only the system admins have the rights on data_merge models.
        }

        for model in self:
            # Do nothing if current model has a custom merge method.
            if getattr(self.env[model.model], "_disable_data_merge", False):
                return

            # Check that a merge server action does not exist already for that model
            if model.ref_merge_ir_act_server_id:
                return

            server_action_values.update({
                'binding_model_id': model.id,
                'model_id': model.id,
            })

            server_action = self.env['ir.actions.server'].sudo().create(server_action_values)
            model.write({'ref_merge_ir_act_server_id': server_action.id})

            IrModelData = self.env['ir.model.data']
            xid = f'merge_action_{model.model.replace(".","_")}'
            imd = IrModelData.search([('module', '=', 'data_merge'), ('name', '=', xid)])
            if imd:
                imd.res_id = server_action.id
            else:
                # Create xml_id for the server action so it doesn't count as customization in cloc
                IrModelData.create({
                    'name': xid,
                    'module': 'data_merge',
                    'res_id': server_action.id,
                    'model': 'ir.actions.server',
                    # noupdate is set to true to avoid to delete record at module update
                    'noupdate': True,
                })

    def action_merge_contextual_disable(self):
        self.ref_merge_ir_act_server_id.unlink()
