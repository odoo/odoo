# -*- coding: utf-8 -*-
from odoo import fields, models
import logging
import requests

_logger = logging.getLogger(__name__)

NPI_API_URL = "https://npiregistry.cms.hhs.gov/api/"

# Taxonomies searched (NPPES uses "Ophthalmologist"; we also try "Ophthalmology")
NPI_TAXONOMIES = ["Optometrist", "Ophthalmologist", "Ophthalmology"]


class NpiOptometristSearch(models.TransientModel):
    _name = "npi.optometrist.search"
    _description = "NPI Optometrist Search"

    first_name = fields.Char(string="First Name", help="Provider first name (trailing * for wildcard)")
    last_name = fields.Char(string="Last Name", help="Provider last name (trailing * for wildcard)")
    state = fields.Char(string="State", size=2, help="Two-letter state code (e.g., CA, UT)")
    city = fields.Char(string="City")
    postal_code = fields.Char(string="Postal Code")
    limit = fields.Integer(string="Results Limit", default=50, help="Max 200 per request")

    result_ids = fields.Many2many(
        "npi.optometrist.result",
        "npi_search_result_rel",
        "search_id",
        "result_id",
        string="Search Results",
        readonly=True,
    )

    def action_search(self):
        """Call NPPES API for both Optometrists and Ophthalmologists, then combine results."""
        self.ensure_one()
        Result = self.env["npi.optometrist.result"]

        base_params = {
            "version": "2.1",
            "limit": min(max(1, self.limit), 200),
        }
        if self.first_name:
            base_params["first_name"] = self.first_name.strip()
        if self.last_name:
            base_params["last_name"] = self.last_name.strip()
        if self.state:
            base_params["state"] = self.state.strip().upper()[:2]
        if self.city:
            base_params["city"] = self.city.strip()
        if self.postal_code:
            base_params["postal_code"] = self.postal_code.strip()

        if not any([self.first_name, self.last_name, self.state, self.city, self.postal_code]):
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Search Criteria Required",
                    "message": "Enter at least one criterion: name, state, city, or postal code.",
                    "type": "warning",
                    "sticky": True,
                },
            }

        # Split limit across taxonomies (e.g. 50 each for Optometrist and Ophthalmologist)
        limit_per_taxonomy = max(1, min(200, self.limit) // len(NPI_TAXONOMIES))
        self.result_ids.unlink()
        result_records = Result

        for taxonomy_desc in NPI_TAXONOMIES:
            params = dict(base_params, taxonomy_description=taxonomy_desc, limit=limit_per_taxonomy)
            try:
                response = requests.get(NPI_API_URL, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.RequestException as e:
                _logger.exception("NPI API request failed for %s: %s", taxonomy_desc, e)
                continue

            if "Errors" in data and data["Errors"]:
                _logger.warning("NPI API error for %s: %s", taxonomy_desc, data["Errors"])
                continue

            results = data.get("results") or []
            for r in results:
                basic = r.get("basic", {})
                addr_list = r.get("addresses") or []
                primary_addr = next(
                    (a for a in addr_list if a.get("address_purpose") in ("LOCATION", "PRIMARY")),
                    addr_list[0] if addr_list else {}
                )
                taxonomies = r.get("taxonomies") or []
                primary_tax = taxonomies[0] if taxonomies else {}

                name = basic.get("name")
                if not name:
                    first = basic.get("first_name") or ""
                    last = basic.get("last_name") or ""
                    name = f"{first} {last}".strip() or "N/A"

                result_records |= Result.create({
                    "provider_type": taxonomy_desc,
                    "npi_number": r.get("number"),
                    "name": name,
                    "first_name": basic.get("first_name"),
                    "last_name": basic.get("last_name"),
                    "credential": basic.get("credential"),
                    "telephone_number": primary_addr.get("telephone_number") if isinstance(primary_addr, dict) else None,
                    "address_1": primary_addr.get("address_1") if isinstance(primary_addr, dict) else None,
                    "address_2": primary_addr.get("address_2") if isinstance(primary_addr, dict) else None,
                    "city": primary_addr.get("city") if isinstance(primary_addr, dict) else None,
                    "state": primary_addr.get("state") if isinstance(primary_addr, dict) else None,
                    "postal_code": primary_addr.get("postal_code") if isinstance(primary_addr, dict) else None,
                    "taxonomy_code": primary_tax.get("code"),
                    "taxonomy_desc": primary_tax.get("desc"),
                })

        self.result_ids = result_records

        return {
            "type": "ir.actions.act_window",
            "res_model": "npi.optometrist.search",
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class NpiOptometristResult(models.TransientModel):
    _name = "npi.optometrist.result"
    _description = "NPI Eye Care Provider Search Result"

    provider_type = fields.Char(string="Provider Type", readonly=True, help="Optometrist or Ophthalmologist")
    npi_number = fields.Char(string="NPI Number", readonly=True)
    name = fields.Char(string="Name", readonly=True)
    first_name = fields.Char(string="First Name", readonly=True)
    last_name = fields.Char(string="Last Name", readonly=True)
    credential = fields.Char(string="Credential", readonly=True)
    telephone_number = fields.Char(string="Phone", readonly=True)
    address_1 = fields.Char(string="Address 1", readonly=True)
    address_2 = fields.Char(string="Address 2", readonly=True)
    city = fields.Char(string="City", readonly=True)
    state = fields.Char(string="State", readonly=True)
    postal_code = fields.Char(string="Postal Code", readonly=True)
    taxonomy_code = fields.Char(string="Taxonomy Code", readonly=True)
    taxonomy_desc = fields.Char(string="Taxonomy", readonly=True)

    def action_import(self):
        """Create an External Provider from this result and open the External Provider list."""
        self.ensure_one()
        ExternalProvider = self.env["external.provider"]
        # Avoid duplicate NPI
        existing = ExternalProvider.search([("npi", "=", self.npi_number)], limit=1)
        if existing:
            return {
                "type": "ir.actions.act_window",
                "name": "External Provider",
                "res_model": "external.provider",
                "view_mode": "list,form",
                "target": "current",
            }
        name_with_credential = self.name
        if self.credential:
            name_with_credential = f"{self.name} {self.credential}"
        ExternalProvider.create({
            "name": name_with_credential,
            "phone": self.telephone_number or "",
            "email": "",
            "city": (self.city or "").strip(),
            "state": (self.state or "").strip(),
            "npi": self.npi_number or "",
            "company": "",
            "license": "",
            "taxonomy": self.taxonomy_code or self.taxonomy_desc or "",
        })
        return {
            "type": "ir.actions.act_window",
            "name": "External Provider",
            "res_model": "external.provider",
            "view_mode": "list,form",
            "target": "current",
        }
