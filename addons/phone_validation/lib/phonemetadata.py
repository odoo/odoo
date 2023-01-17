# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

try:
    # import for usage in phonenumbers_patch/region_*.py files
    from phonenumbers.phonemetadata import NumberFormat, PhoneNumberDesc, PhoneMetadata # pylint: disable=unused-import
except ImportError:
    pass
