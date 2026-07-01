# Copyright 2017 LasLabs Inc.
# Copyright 2023 Tecnativa - Pedro M. Baeza
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class MultiCompanyAbstract(models.AbstractModel):

    _name = "multi.company.abstract"
    _description = "Multi-Company Abstract"

    company_id = fields.Many2one(
        string="Company",
        comodel_name="res.company",
        compute="_compute_company_id",
        search="_search_company_id",
        inverse="_inverse_company_id",
    )
    company_ids = fields.Many2many(
        string="Companies",
        comodel_name="res.company",
    )

    @api.depends("company_ids")
    @api.depends_context("company", "_check_company_source_id")
    def _compute_company_id(self):
        for record in self:
            # Set this priority computing the company (if included in the allowed ones)
            # for avoiding multi company incompatibility errors:
            # - If this call is done from method _check_company, the company of the
            #   record to be compared.
            # - Otherwise, current company of the user.
            company_id = (
                self.env.context.get("_check_company_source_id")
                or self.env.context.get("force_company")
                or self.env.company.id
            )
            if company_id in record.company_ids.ids:
                record.company_id = company_id
            else:
                record.company_id = record.company_ids[:1].id

    def _inverse_company_id(self):
        # To allow modifying allowed companies by non-aware base_multi_company
        # through company_id field we:
        # - Remove all companies, then add the provided one
        for record in self:
            record.company_ids = [(6, 0, record.company_id.ids)]

    def _search_company_id(self, operator, value):
        return [("company_ids", operator, value)]

    @api.model_create_multi
    def create(self, vals_list):
        """Discard changes in company_id field if company_ids has been given."""
        for vals in vals_list:
            if "company_ids" in vals and "company_id" in vals:
                del vals["company_id"]
        return super().create(vals_list)

    def write(self, vals):
        """Discard changes in company_id field if company_ids has been given."""
        if "company_ids" in vals and "company_id" in vals:
            del vals["company_id"]
        return super().write(vals)

    @api.model
    def _patch_company_domain(self, args):
        # In some situations the 'in' operator is used with company_id in a
        # name_search or search_read. ORM does not convert to a proper WHERE clause when using
        # the 'in' operator.
        # e.g: ```
        #     WHERE "res_partner"."id" in (SELECT "res_partner_id"
        #     FROM "res_company_res_partner_rel" WHERE "res_company_id" IN (False, 1)
        # ```
        # patching the args to expand the cumbersome args int a OR clause fix
        # the issue.
        # e.g: ```
        #     WHERE "res_partner"."id" not in (SELECT "res_partner_id"
        #             FROM "res_company_res_partner_rel"
        #             where "res_partner_id" is not null)
        #         OR  ("res_partner"."id" in (SELECT "res_partner_id"
        #             FROM "res_company_res_partner_rel" WHERE "res_company_id" IN 1)
        # ```
        new_args = []
        if args is None:
            args = []
        for arg in args:
            if type(arg) in {list, tuple} and list(arg[:2]) == ["company_id", "in"]:
                fix = []
                for _i in range(len(arg[2]) - 1):
                    fix.append("|")
                for val in arg[2]:
                    fix.append(["company_id", "=", val])
                new_args.extend(fix)
            else:
                new_args.append(arg)
        return new_args

    @api.model
    def _name_search(
        self, name, args=None, operator="ilike", limit=100, name_get_uid=None
    ):
        new_args = self._patch_company_domain(args)
        return super()._name_search(
            name,
            args=new_args,
            operator=operator,
            limit=limit,
            name_get_uid=name_get_uid,
        )

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        new_domain = self._patch_company_domain(domain)
        return super().search_read(new_domain, fields, offset, limit, order)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        args = self._patch_company_domain(args)
        return super().search(
            args, offset=offset, limit=limit, order=order, count=count
        )
