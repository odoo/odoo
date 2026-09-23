# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.fields import Domain

from odoo.addons.delivery import const


class IrModuleModule(models.Model):
    _name = "ir.module.module"
    _inherit = ["ir.module.module"]

    @api.model
    def web_search_read(self, domain, *args, **kwargs):
        """Override of `web` to filter legacy delivery providers based on the context."""
        domain = self._add_legacy_delivery_providers_domain(domain)
        return super().web_search_read(domain, *args, **kwargs)

    @api.model
    def web_read_group(self, domain, *args, **kwargs):
        """Override of `web` to filter legacy delivery providers based on the context."""
        domain = self._add_legacy_delivery_providers_domain(domain)
        return super().web_read_group(domain, *args, **kwargs)

    @api.model
    def _add_legacy_delivery_providers_domain(self, domain):
        """Restrict the domain on legacy delivery providers based on the context.

        :param list domain: The domain to restrict.
        :return: The restricted domain.
        :rtype: Domain
        """
        legacy = self.env.context.get("legacy_delivery_providers")
        if legacy is None:
            return domain
        return Domain(domain) & Domain(
            "name", "in" if legacy else "not in", const.LEGACY_DELIVERY_PROVIDERS,
        )

    def action_view_delivery_methods(self):
        self.ensure_one()
        if self.state != "installed":
            return False

        module_by_type = self.env["delivery.carrier"]._get_module_by_delivery_type()
        delivery_type = next(
            (dtype for dtype, module in module_by_type.items() if module == self.name), None,
        )
        if not delivery_type:
            return False

        action = self.env["ir.actions.act_window"]._for_xml_id(
            "delivery.action_delivery_carrier_form",
        )
        action["context"] = {"search_default_delivery_type": delivery_type}
        return action
