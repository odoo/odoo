from odoo import models, api
from odoo.fields import Domain


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        domain = domain or []
        context = dict(self.env.context)
        if "dashboard_inner_model" in context:
            return super(IrModel, self).name_search(
                name=name, domain=domain, operator=operator, limit=limit
            )
        if "dashboard_model" in context:
            search_models = self.with_context(**{"dashboard_inner_model": True}).search(
                domain
            )
            exclude_model_list = []
            for model_id in search_models:
                if isinstance(
                    self.env[model_id.model], models.AbstractModel
                ) and not isinstance(self.env[model_id.model], models.Model):
                    exclude_model_list.append(model_id.id)
            domain.append(("id", "not in", exclude_model_list))
        return super(IrModel, self).name_search(
            name=name, domain=domain, operator=operator, limit=limit
        )

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        domain = domain or []
        context = dict(self.env.context)
        if "dashboard_inner_model" in context:
            return super(IrModel, self).search_fetch(
                domain=domain,
                field_names=field_names,
                offset=offset,
                limit=limit,
                order=order,
            )
        if "dashboard_model" in context:
            search_models = self.with_context(**{"dashboard_inner_model": True}).search(
                domain
            )
            exclude_model_list = []
            for model_id in search_models:
                if isinstance(
                    self.env[model_id.model], models.AbstractModel
                ) and not isinstance(self.env[model_id.model], models.Model):
                    exclude_model_list.append(model_id.id)
            domain = list(domain) if isinstance(domain, Domain) else domain
            domain.append(("id", "not in", exclude_model_list))
        return super(IrModel, self).search_fetch(
            domain=domain,
            field_names=field_names,
            offset=offset,
            limit=limit,
            order=order,
        )
