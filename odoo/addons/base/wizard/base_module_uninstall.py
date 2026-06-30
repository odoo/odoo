# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseModuleUninstall(models.TransientModel):
    _name = 'base.module.uninstall'
    _description = "Module Uninstall"

    show_all = fields.Boolean()
    module_ids = fields.Many2many(
        'ir.module.module', string="Module(s)", required=True,
        domain=[('state', 'in', ['installed', 'to upgrade', 'to install'])],
        ondelete='cascade', readonly=True,
    )
    impacted_module_ids = fields.Many2many('ir.module.module', string="Impacted modules",
                                  compute='_compute_impacted_module_ids')
    model_ids = fields.Many2many('ir.model', string="Impacted data models",
                                 compute='_compute_model_ids')

    def _get_modules(self):
        """ Return all the modules impacted by self. """
        return self.module_ids.downstream_dependencies(self.module_ids)

    @api.depends('module_ids', 'show_all')
    def _compute_impacted_module_ids(self):
        for wizard in self:
            modules = wizard._get_modules().sorted(lambda m: (not m.application, m.sequence))
            wizard.impacted_module_ids = modules if wizard.show_all else wizard._modules_to_display(modules)

    @api.model
    def _modules_to_display(self, modules):
        return modules.filtered('application')

    def _get_models(self):
        """ Return the models (ir.model) to consider for the impact. """
        return self.env['ir.model'].search([('transient', '=', False)])

    @api.depends('impacted_module_ids')
    def _compute_model_ids(self):
        ir_models = self._get_models()
        ir_models_xids = ir_models._get_external_ids()
        for wizard in self:
            if wizard.module_ids:
                module_names = set(wizard._get_modules().mapped('name'))

                def lost(model):
                    xids = ir_models_xids.get(model.id, ())
                    return xids and all(xid.split('.')[0] in module_names for xid in xids)

                # find the models that have all their XIDs in the given modules
                wizard.model_ids = ir_models.filtered(lost).sorted('name')
            else:
                wizard.model_ids = False

    @api.onchange('module_ids')
    def _onchange_module_ids(self):
        # if the user selects only technical modules, show technical modules.
        if self.module_ids and not any(m.application for m in self.module_ids):
            self.show_all = True

    def action_uninstall(self):
        modules = self.module_ids
        return modules.button_immediate_uninstall()
