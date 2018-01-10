# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class RepairCancel(models.TransientModel):
    _name = 'mrp.repair.cancel'
    _description = 'Cancel Repair'

    @api.multi
    def cancel_repair(self):
        if not self._context.get('active_id'):
            return {'type': 'ir.actions.act_window_close'}
        repair = self.env['mrp.repair'].browse(self._context['active_id'])
        if repair.invoiced or repair.invoice_method == 'none':
            repair.action_cancel()
        else:
            raise UserError(_('Repair order is not invoiced.'))
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(RepairCancel, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,submenu=submenu)
        repair_id = self._context.get('active_id')
        if not repair_id or self._context.get('active_model') != 'mrp.repair':
            return res

        repair = self.env['mrp.repair'].browse(repair_id)
        if not repair.invoiced:
            res['arch'] = """
                <form string="Cancel Repair">
                    <header>
                        <button name="cancel_repair" string="_Yes" type="object" class="btn-primary"/>
                        <button string="Cancel" class="btn-default" special="cancel"/>
                    </header>
                    <label string="Do you want to continue?"/>
                </form>
            """
        return res
