# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from base64 import b64decode

import werkzeug.urls

from odoo import models
from odoo.tools.facade import Proxy, ProxyAttr, ProxyFunc

_logger = logging.getLogger(__name__)

try:
    import vobject.vcard
except ImportError:
    _logger.warning("`vobject` Python module not found, vcard file generation disabled. Consider installing this module if you want to generate vcard files")
    vobject = None


if vobject is not None:

    class VBaseProxy(Proxy):
        _wrapped__ = vobject.base.VBase

        encoding_param = ProxyAttr()
        type_param = ProxyAttr()
        value = ProxyAttr(None)

    class VCardContentsProxy(Proxy):
        _wrapped__ = dict

        __delitem__ = ProxyFunc()
        __contains__ = ProxyFunc()
        get = ProxyFunc(lambda lines: [VBaseProxy(line) for line in lines])

    class VComponentProxy(Proxy):
        _wrapped__ = vobject.base.Component

        add = ProxyFunc(VBaseProxy)
        contents = ProxyAttr(VCardContentsProxy)
        serialize = ProxyFunc()


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'web.markup_data.mixin']

    def _get_md_payload(self, website):
        self.ensure_one()
        name = self.display_name or self.name
        if not name:
            return False

        base_url = website.get_base_url()
        website_url = self.website or ''
        if website_url and not website_url.startswith(("http://", "https://")):
            website_url = werkzeug.urls.join(base_url, website_url)

        image_path = website.image_url(self, 'image_512')
        image_url = f'{base_url}{image_path}' if image_path else None

        payload = self._md_organization(
            name=name,
            url=website_url or base_url,
            logo=image_url,
        )

        phones = [phone for phone in (self.phone, self.mobile) if phone]
        if phones:
            payload['telephone'] = ' / '.join(phones)
        if self.email:
            payload['email'] = self.email

        street = self.street.strip() if self.street else None
        postal_code = self.zip.strip() if self.zip else None
        city = self.city.strip() if self.city else None
        region = self.state_id.name if self.state_id else None
        country = self.country_id.name if self.country_id else None
        if any((street, postal_code, city, region, country)):
            payload['address'] = self._md_postal_address(
                street_address=street,
                postal_code=postal_code,
                locality=city,
                region=region,
                country=country,
            )

        return payload

    def _build_vcard(self):
        """ Build the partner's vCard.
            :returns a vobject.vCard object
        """
        if not vobject:
            return False
        vcard = vobject.vCard()
        # Name
        n = vcard.add('n')
        n.value = vobject.vcard.Name(family=self.name or self.complete_name or '')
        # Formatted Name
        fn = vcard.add('fn')
        fn.value = self.name or self.complete_name or ''
        # Address
        adr = vcard.add('adr')
        adr.value = vobject.vcard.Address(street=self.street or '', city=self.city or '', code=self.zip or '')
        if self.state_id:
            adr.value.region = self.state_id.name
        if self.country_id:
            adr.value.country = self.country_id.name
        # Email
        if self.email:
            email = vcard.add('email')
            email.value = self.email
            email.type_param = 'INTERNET'
        # Telephone numbers
        if self.phone:
            tel = vcard.add('tel')
            tel.type_param = 'work'
            tel.value = self.phone
        # URL
        if self.website:
            url = vcard.add('url')
            url.value = self.website
        # Organisation
        if self.commercial_company_name:
            org = vcard.add('org')
            org.value = [self.commercial_company_name]
        if self.function:
            function = vcard.add('title')
            function.value = self.function
        # Photo
        photo = vcard.add('photo')
        photo.value = b64decode(self.avatar_512)
        photo.encoding_param = 'B'
        photo.type_param = 'JPG'
        return VComponentProxy(vcard)

    def _get_vcard_file(self):
        vcard = self._build_vcard()
        if vcard:
            return vcard.serialize().encode()
        return False
