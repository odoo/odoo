# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class MrpWorkorderIncompleteQty(models.TransientModel):
    _name = 'mrp.workorder.incomplete.qty'
    _description = 'Warn Incomplete Workorder Quantity'

    workorder_ids = fields.Many2many('mrp.workorder', string='Workorders')
    filtered_workorder_ids = fields.Many2many(
        'mrp.workorder',
        string='Incomplete Workorders',
        compute='_compute_filtered_workorder_ids',
        readonly=True,
    )
    calling_method = fields.Char(
        string='Calling Method',
        readonly=True, required=True,
    )
    caller_kwargs = fields.Json(
        string='Caller Arguments',
        readonly=True,
    )

    def _compute_filtered_workorder_ids(self):
        self.filtered_workorder_ids = self.workorder_ids.filtered(
            lambda wo: wo.product_uom_id.compare(wo.qty_remaining, 0) > 0 and wo.state != 'done'
        )

    def action_complete(self):
        # Process the remaining quantity for each workorder
        self.ensure_one()
        for workorder in self.filtered_workorder_ids:
            workorder.qty_produced = 1 if workorder.product_tracking == 'serial' else min(workorder.qty_production, workorder.qty_production - workorder.qty_reported_from_previous_wo)
        self.action_validate()

    def action_validate(self):
        self.ensure_one()
        # `calling_method` names are quite different such that we can't prefix them
        # We instead define a whitelist of allowed methods for security
        allowed_methods = {'action_mark_as_done', 'do_finish', 'set_state', 'pre_button_mark_done'}
        caller_kwargs = self.caller_kwargs or {}
        res = self.workorder_ids.production_id if self.calling_method == 'pre_button_mark_done' else self.workorder_ids
        if self.calling_method in allowed_methods and hasattr(res, self.calling_method):
            try:
                return getattr(res.with_context(skip_check_qty_on_set_state_done=True), self.calling_method)(**caller_kwargs)
            except AttributeError as e:
                raise ValidationError(str(e)) from e
        else:
            raise ValidationError(
            _("Method '%(method_name)s' is not allowed or not found. Please check the context or the method name.", method_name=self.calling_method)
            )
