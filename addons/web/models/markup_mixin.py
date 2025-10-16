from datetime import timezone

from odoo import api, fields, models
from odoo.tools.json import scriptsafe as json_safe


class WebMarkupDataMixin(models.AbstractModel):
    _name = 'web.markup_data.mixin'
    _description = 'Structured Data Markup Mixin'

    @api.model
    def _md_payload(self, schema_type, **fields):
        payload = {
            '@context': 'https://schema.org',
            '@type': schema_type,
        }
        for key, value in fields.items():
            if value is None or value is False:
                continue
            if isinstance(value, (list, tuple, set)) and len(value) == 0:
                continue
            payload[key] = value
        return payload

    @api.model
    def _md_image_object(self, url):
        if not url:
            return False
        return self._md_payload('ImageObject', url=url)

    @api.model
    def _md_organization(self, *, name, url=None, logo=None):
        payload = self._md_payload('Organization', name=name)
        if url:
            payload['url'] = url
        if logo:
            payload['logo'] = self._md_image_object(logo) if isinstance(logo, str) else logo
        return payload

    @api.model
    def _md_postal_address(
        self,
        *,
        street_address=None,
        locality=None,
        region=None,
        postal_code=None,
        country=None,
    ):
        return self._md_payload(
            'PostalAddress',
            streetAddress=street_address,
            addressLocality=locality,
            addressRegion=region,
            postalCode=postal_code,
            addressCountry=country,
        )

    @api.model
    def _md_person(self, *, name, email=None):
        payload = self._md_payload('Person', name=name)
        if email:
            payload['email'] = email
        return payload

    @api.model
    def _md_collection_page(self, *, name, url, has_part=None):
        return self._md_payload(
            'CollectionPage',
            name=name,
            url=url,
            hasPart=has_part,
        )

    @api.model
    def _md_place(self, *, name=None, address=None):
        return self._md_payload('Place', name=name, address=address)

    @api.model
    def _md_list_item(self, *, position, name, item=None):
        if not name:
            return False
        entry = {
            '@type': 'ListItem',
            'position': position,
            'name': name,
        }
        if item:
            entry['item'] = item
        return entry

    @api.model
    def _md_speakable(self, xpaths=None):
        if not xpaths:
            return False
        return {
            '@type': 'SpeakableSpecification',
            'xpath': list(xpaths),
        }

    @api.model
    def _md_datetime(self, dt):
        if not dt:
            return False
        as_datetime = fields.Datetime.to_datetime(dt)
        if not as_datetime.tzinfo:
            as_datetime = as_datetime.replace(tzinfo=timezone.utc)
        return as_datetime.isoformat()

    @api.model
    def _md_breadcrumb_list(self, items):
        elements = []
        for idx, (name, url) in enumerate(items, start=1):
            list_item = self._md_list_item(position=idx, name=name, item=url)
            if list_item:
                elements.append(list_item)
        if not elements:
            return False
        return self._md_payload('BreadcrumbList', itemListElement=elements)

    def _get_md_payload(self, website):
        """Return the Schema.org payload representing the record on the given website.

        Subclasses are expected to override this method and return a dictionary (or False)
        describing the structured data payload for a single record.

        Returns:
            dict | bool: A dictionary representing the structured data payload, or False if not
                         applicable.
        """
        self.ensure_one()
        return False

    def _get_md_payloads(self, website):
        """Return the structured data payload(s) for the current recordset.

        Returns:
            dict | bool: A dictionary representing the structured data payload(s) if available,
                         or False if no payloads are applicable.
        """
        payloads = []
        for record in self:
            payload = record._get_md_payload(website)
            if payload:
                payloads.append(payload)

        if not payloads:
            return False
        if len(payloads) == 1:
            return payloads[0]
        return payloads

    def _get_md_json(self, website, indent=2):
        """Return a JSON representation of the structured data payload(s).

        Returns:
            str | bool: A JSON string representing the structured data payload(s), or False if no
                        payloads are applicable.
        """
        payload = self._get_md_payloads(website)
        if not payload:
            return False
        return json_safe.dumps(payload, indent=indent)
