# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseModuleUninstall(models.TransientModel):
    _name = "base.module.uninstall"
    _description = "Module Uninstall"

    show_all = fields.Boolean()
    module_id = fields.Many2one(
        'ir.module.module', string="Module", required=True,
        domain=[('state', 'in', ['installed', 'to upgrade', 'to install'])],
        ondelete='cascade', readonly=True,
    )
    module_ids = fields.Many2many('ir.module.module', string="Impacted modules",
                                  compute='_compute_module_ids')
    model_ids = fields.Many2many('ir.model', string="Impacted data models",
                                 compute='_compute_model_ids')

    def _get_modules(self):
        """ Return all the modules impacted by self. """
        return self.module_id.downstream_dependencies(self.module_id)

    @api.depends('module_id', 'show_all')
    def _compute_module_ids(self):
        for wizard in self:
            modules = wizard._get_modules().sorted(lambda m: (not m.application, m.sequence))
            wizard.module_ids = modules if wizard.show_all else modules.filtered('application')

    def _get_models(self):
        """ Return the models (ir.model) to consider for the impact. """
        return self.env['ir.model'].search([('transient', '=', False)])

    @api.depends('module_ids')
    def _compute_model_ids(self):
        ir_models = self._get_models()
        ir_models_xids = ir_models._get_external_ids()
        for wizard in self:
            if wizard.module_id:
                module_names = set(wizard._get_modules().mapped('name'))

                def lost(model):
                    xids = ir_models_xids.get(model.id, ())
                    return xids and all(xid.split('.')[0] in module_names for xid in xids)

                # find the models that have all their XIDs in the given modules
                self.model_ids = ir_models.filtered(lost).sorted('name')

    @api.onchange('module_id')
    def _onchange_module_id(self):
        # if we select a technical module, show technical modules by default
        if not self.module_id.application:
            self.show_all = True

    def action_uninstall(self):
        modules = self.module_id
        return modules.button_immediate_uninstall()
