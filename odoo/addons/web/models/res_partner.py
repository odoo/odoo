# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from base64 import b64decode

from odoo import models

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, vcard file generation disabled. Consider installing this module if you want to generate vcard files")
    vobject = None


class ResPartner(models.Model):
    _inherit = 'res.partner'

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
        if self.title:
            n.value.prefix = self.title.name
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
        if self.mobile:
            tel = vcard.add('tel')
            tel.type_param = 'cell'
            tel.value = self.mobile
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
        return vcard

    def _get_vcard_file(self):
        vcard = self._build_vcard()
        if vcard:
            return vcard.serialize().encode()
        return False
