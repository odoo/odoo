# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models
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
    # calling_method = fields.Char(
        # string='Calling Method',
        # readonly=True, required=True,
    # )
    # caller_kwargs = fields.Json(
        # string='Caller Arguments',
        # readonly=True, default=lambda self: {},
    # )

    def _compute_filtered_workorder_ids(self):
        """ Compute the workorders with qty_remaining > 0 """
        self.filtered_workorder_ids = self.workorder_ids.filtered(
            lambda wo: wo.product_uom_id.compare(wo.qty_remaining, 0) > 0 and wo.product_uom_id.compare(wo.qty_produced, 0) != 0
        )

    def action_validate(self):
        self.ensure_one()
        # FIXME: set calling_method & caller_kwargs outside of the context, in a char field for example ???
        calling_method = self._context.get('calling_method')
        caller_kwargs = self._context.get('caller_kwargs', {})
        # ´calling_method´ names are quite different such that we can't prefix them
        # Define a whitelist of allowed methods for security instead
        allowed_methods = {'action_mark_as_done', 'do_finish', 'set_state'}
        if calling_method in allowed_methods and hasattr(self.env['mrp.workorder'], calling_method):
            try:
                getattr(self.workorder_ids.with_context(skip_check_qty_on_set_state_done=True), calling_method)(**caller_kwargs)
            except AttributeError as e:
                raise ValidationError(f"{e}")
        else:
            raise ValidationError(
                f"Method '{calling_method}' is not allowed or not found in 'mrp.workorder'. "
                "Please check the context or the method name."
            )
