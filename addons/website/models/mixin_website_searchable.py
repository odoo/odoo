import logging
import re

from odoo import api, models
from odoo.fields import Domain
from odoo.tools import escape_psql

from odoo.addons.website.tools import text_from_html

logger = logging.getLogger(__name__)


class MixinWebsiteSearchable(models.AbstractModel):
    _name = "mixin.website.searchable"
    _description = "Website Searchable Mixin"

    @api.model
    def _search_build_domain(self, domain_list, search, fields, extra=None):
        domain = Domain.AND(domain_list)
        if search:
            for search_term in search.split():
                subdomains = [
                    Domain(field, "ilike", escape_psql(search_term)) for field in fields
                ]
                if extra:
                    subdomains.append(extra(self.env, search_term))
                domain &= Domain.OR(subdomains)
        return domain

    @api.model
    def _search_get_detail(self, website, order, options):
        raise NotImplementedError

    @api.model
    def _search_fetch(self, search_detail, search, limit, order):
        fields = search_detail["search_fields"]
        base_domain = search_detail["base_domain"]
        domain = self._search_build_domain(
            base_domain, search, fields, search_detail.get("search_extra")
        )
        model = self.sudo() if search_detail.get("requires_sudo") else self
        results = model.search(
            domain, limit=limit, order=search_detail.get("order", order)
        )
        count = (
            model.search_count(domain)
            if limit and limit == len(results)
            else len(results)
        )
        return results, count

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        records = self[:limit]
        results_data = records.with_prefetch(records.ids).read(fetch_fields)
        for result in results_data:
            result["_fa"] = icon
            result["_mapping"] = mapping
        # `escaped_twice` is declared by the detail, not guessed from a field
        # name. It used to read `if html_field == "arch"` -- one model's field
        # name hardcoded in the mixin every searchable model shares, the same
        # shape as the `arch_db` special case the fuzzy enumerators carried.
        html_fields = [
            (config["name"], config.get("escaped_twice"))
            for config in mapping.values()
            if config.get("html")
        ]
        if html_fields:
            for data in results_data:
                for html_field, escaped_twice in html_fields:
                    if data[html_field]:
                        if escaped_twice:
                            data[html_field] = re.sub(
                                r"&amp;(?=\w+;)", "&", data[html_field]
                            )
                        data[html_field] = text_from_html(data[html_field], True)
        return results_data
