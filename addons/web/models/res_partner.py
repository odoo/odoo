import logging
from base64 import b64decode
from typing import Any

from odoo import models
from odoo.libs.facade import Proxy, ProxyAttr, ProxyFunc

_logger = logging.getLogger(__name__)

try:
    import vobject.vcard
except ImportError:
    _logger.warning(
        "`vobject` Python module not found, vcard file generation disabled. Consider installing this module if you want to generate vcard files"
    )
    vobject = None


# vCard PHOTO type values per RFC 2426 (vCard 3.0)
_IMAGE_SIGNATURES = {
    b"\xff\xd8\xff": "JPEG",
    b"\x89PNG": "PNG",
    b"GIF8": "GIF",
    b"BM": "BMP",
}


def _guess_image_vcard_type(data: bytes) -> str:
    """Detect image format from binary data for vCard PHOTO type_param."""
    for signature, vcard_type in _IMAGE_SIGNATURES.items():
        if data[: len(signature)] == signature:
            return vcard_type
    return "JPEG"  # safe default — Odoo stores avatars as JPEG or PNG


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
    _inherit = "res.partner"

    def _build_vcard(self) -> Any:
        """Build the partner's vCard.
        :returns a vobject.vCard object
        """
        if not vobject:
            return False
        vcard = vobject.vCard()
        # Name
        n = vcard.add("n")
        n.value = vobject.vcard.Name(family=self.name or self.complete_name or "")
        # Formatted Name
        fn = vcard.add("fn")
        fn.value = self.name or self.complete_name or ""
        # Address
        adr = vcard.add("adr")
        adr.value = vobject.vcard.Address(
            street=self.street or "", city=self.city or "", code=self.zip or ""
        )
        if self.state_id:
            adr.value.region = self.state_id.name
        if self.country_id:
            adr.value.country = self.country_id.name
        # Email
        if self.email:
            email = vcard.add("email")
            email.value = self.email
            email.type_param = "INTERNET"
        # Telephone numbers
        if self.phone:
            tel = vcard.add("tel")
            tel.type_param = "work"
            tel.value = self.phone
        # URL
        if self.website:
            url = vcard.add("url")
            url.value = self.website
        # Organisation
        if self.commercial_company_name:
            org = vcard.add("org")
            org.value = [self.commercial_company_name]
        if self.function:
            function = vcard.add("title")
            function.value = self.function
        # Photo
        if self.avatar_512:
            photo = vcard.add("photo")
            photo_data = b64decode(self.avatar_512)
            photo.value = photo_data
            photo.encoding_param = "B"
            photo.type_param = _guess_image_vcard_type(photo_data)
        return VComponentProxy(vcard)

    def _get_vcard_file(self) -> bytes | bool:
        vcard = self._build_vcard()
        if vcard:
            return vcard.serialize().encode()
        return False
