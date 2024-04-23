# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.web.controllers.dataset import DataSet


class ProjectSharingDataset(DataSet):
    @route()
    def call_kw(self, model, method, args, kwargs, path=None):
        """ Override the call_kw method to add the project_sharing_ prefix to the method name if the user is a portal user. """
        Model = request.env[model]
        if not method.startswith("project_sharing_") and getattr(Model, "_get_project_sharing_methods", None):
            project_sharing_methods = Model._get_project_sharing_methods()
            if method in project_sharing_methods and request.env.user.share:
                method = f"project_sharing_{method}"
        return super().call_kw(model, method, args, kwargs, path)
