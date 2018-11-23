# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class BaseModuleUninstall(models.TransientModel):
    _name = "base.module.uninstall"
    _description = "Module Uninstallation"

    show_all = fields.Boolean()
    module_id = fields.Many2one('ir.module.module', string="Module", required=True,
                                domain=[('state', 'in', ['installed', 'to upgrade', 'to install'])])
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
            modules = wizard._get_modules()
            wizard.module_ids = modules if wizard.show_all else modules.filtered('application')

    def _get_models(self):
        """ Return the models (ir.model) to consider for the impact. """
        return self.env['ir.model'].search([('transient', '=', False)])

    def _get_models_specific_to_module(self):
        # get only the models related to the module
        domain = [('model', '=', 'ir.model'), ('module', '=', self.module_id.name)]
        data = self.env['ir.model.data'].search_read(domain, ['res_id'])
        return self.env['ir.model'].browse([item['res_id'] for item in data])

    @api.depends('module_ids')
    def _compute_model_ids(self):
        mail_thread_models = self._get_models()
        mail_thread_models_xids = mail_thread_models._get_external_ids()
        module_models = self._get_models_specific_to_module()
        module_models_xids = module_models._get_external_ids()

        for wizard in self:
            if wizard.module_id:
                module_names = set(wizard._get_modules().mapped('name'))

                def lost(model_xids):
                    def func(model):
                        xids = model_xids.get(model.id, ())
                        return xids and all(xid.split('.')[0] in module_names for xid in xids)
                    return func
                # find the models that have all their XIDs in the given modules
                mail_thread_models = mail_thread_models.filtered(lost(mail_thread_models_xids))
                module_models = module_models.filtered(lost(module_models_xids))
                self.model_ids = (mail_thread_models or module_models).sorted('name')

    @api.onchange('module_id')
    def _onchange_module_id(self):
        # if we select a technical module, show technical modules by default
        if not self.module_id.application:
            self.show_all = True

    @api.multi
    def action_uninstall(self):
        modules = self.mapped('module_id')
        return modules.button_immediate_uninstall()
