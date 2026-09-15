from typing import TYPE_CHECKING

from odoo import fields, models

if TYPE_CHECKING:
    from .resource_resource import ResourceResource
    from odoo.addons.base.models.res_company import ResCompany


class ResPartner(models.Model):
    _inherit = "res.partner"

    resource_ids = fields.One2many(
        comodel_name="resource.resource",
        inverse_name="partner_id",
        string="Resources",
    )

    def _get_resources(self, company: ResCompany) -> ResourceResource:
        return (
            self.env["resource.resource"]
            .with_context(active_test=False)
            .search(
                [
                    ("partner_id", "in", self.ids),
                    ("resource_type", "=", "user"),
                    ("company_id", "=", company.id),
                ]
            )
        )

    def _get_or_create_resources(self, company: ResCompany) -> ResourceResource:
        resource_by_party = {
            resource.partner_id: resource for resource in self._get_resources(company)
        }
        missing = self.browse(
            list(dict.fromkeys(p.id for p in self if p not in resource_by_party))
        )
        created = self.env["resource.resource"].create(
            [
                {
                    "partner_id": party.id,
                    "resource_type": "user",
                    "company_id": company.id,
                }
                for party in missing
            ]
        )
        resource_by_party.update(zip(missing, created, strict=True))
        return self.env["resource.resource"].browse(
            [resource_by_party[party].id for party in self]
        )
