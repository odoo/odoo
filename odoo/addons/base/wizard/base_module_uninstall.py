# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseModuleUninstall(models.TransientModel):
    _name = 'base.module.uninstall'
    _description = "Module Uninstall"

    module_ids = fields.Many2many(
        'ir.module.module', string="Module(s)", required=True,
        domain=[('state', 'in', ['installed', 'to upgrade', 'to install'])],
        ondelete='cascade', readonly=True,
    )
    impacted_application_count = fields.Integer(compute='_compute_impacted_module_ids')
    impacted_application_ids = fields.Many2many('ir.module.module', string="Impacted applications",
                                  compute='_compute_impacted_module_ids')
    impacted_module_count = fields.Integer(compute='_compute_impacted_module_ids')
    impacted_module_ids = fields.Many2many('ir.module.module', string="Impacted modules",
                                  compute='_compute_impacted_module_ids')
    model_count = fields.Integer(compute='_compute_model_ids')
    model_ids = fields.Many2many('ir.model', string="Models to be deleted",
                                 compute='_compute_model_ids')

    def _get_modules(self):
        """ Return all the modules impacted by self. """
        return self.module_ids.downstream_dependencies(self.module_ids)

    @api.depends('module_ids')
    def _compute_impacted_module_ids(self):
        for wizard in self:
            modules = wizard._get_modules().sorted(lambda m: (m.sequence, m.name))
            wizard.impacted_application_ids = modules.filtered('application')
            wizard.impacted_application_count = len(wizard.impacted_application_ids)
            wizard.impacted_module_ids = modules - wizard.impacted_application_ids
            wizard.impacted_module_count = len(wizard.impacted_module_ids)

    def _get_models(self):
        """ Return the models (ir.model) to consider for the impact. """
        return self.env['ir.model'].search([('transient', '=', False)])

    @api.depends('module_ids')
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
                wizard.model_count = len(wizard.model_ids)
            else:
                wizard.model_ids = False
                wizard.model_count = 0

    def action_uninstall(self):
        modules = self.module_ids
        return modules.button_immediate_uninstall()
