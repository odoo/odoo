# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def display_name_for(self, models):
        """
        Returns the display names from provided models which the current user can access.
        The result is the same whether someone tries to access an inexistent model or a model they cannot access.
        :models list(str): list of technical model names to lookup (e.g. `["res.partner"]`)
        :return: list of dicts of the form `{ "model", "display_name" }` (e.g. `{ "model": "res_partner", "display_name": "Contact"}`)
        """
        # Store accessible models in a temporary list in order to execute only one SQL query
        accessible_models = []
        not_accessible_models = []
        for model in models:
            if self._check_model_access(model):
                accessible_models.append(model)
            else:
                not_accessible_models.append({"display_name": model, "model": model})
        return self._display_name_for(accessible_models) + not_accessible_models

    @api.model
    def _display_name_for(self, models):
        records = self.sudo().search_read([("model", "in", models)], ["name", "model"])
        return [{
            "display_name": model["name"],
            "model": model["model"],
        } for model in records]

    @api.model
    def _check_model_access(self, model):
        return (self.env.user._is_internal() and model in self.env
                and self.env[model].check_access_rights("read", raise_exception=False))

    @api.model
    def get_available_models(self):
        """
        Return the list of models the current user has access to, with their
        corresponding display name.
        """
        accessible_models = [model for model in self.pool.keys() if self._check_model_access(model)]
        return self._display_name_for(accessible_models)
