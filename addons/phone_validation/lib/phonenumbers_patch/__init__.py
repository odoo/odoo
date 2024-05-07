# -*- coding: utf-8 -*-
# Copyright (C) 2009 The Libphonenumber Authors

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# https://github.com/google/libphonenumber

from odoo.tools.parse_version import parse_version


def _local_load_region(code):
    __import__("region_%s" % code, globals(), locals(),
        fromlist=["PHONE_METADATA_%s" % code], level=1)

try:
    import phonenumbers
except ImportError:
    pass
else:
    # Over time, phone number formats change. The following monkey patches ensure phone number parsing stays up to date:
    # The most common type of patch occurs when the phonenumbers library is updated, but Odoo is still using an older version.
    # In such cases, we need to:
    # 1. Grab the newest metadata describing the phone number for a certain country.
    # 2. Create/update a metadata file in the current directory (e.g., files named like region_SN for the Senegal patch).
    # 3. Load the metadata file. Please add a reference to the upstream from which the update was taken.

    if parse_version('7.6.1') <= parse_version(phonenumbers.__version__) < parse_version('8.12.32'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.32/python/phonenumbers/data/region_CI.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('CI', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.13.32'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.32/python/phonenumbers/data/region_MA.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('MA', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.12.13'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.31/python/phonenumbers/data/region_MU.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('MU', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.12.43'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.43/python/phonenumbers/data/region_PA.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('PA', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.12.29'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.57/python/phonenumbers/data/region_SN.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('SN', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.12.39'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.36/python/phonenumbers/data/region_CO.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('CO', _local_load_region)
