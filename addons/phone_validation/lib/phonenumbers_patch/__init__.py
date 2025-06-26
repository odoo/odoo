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

    if parse_version(phonenumbers.__version__) < parse_version('8.12.39'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.36/python/phonenumbers/data/region_CO.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('CO', _local_load_region)

    if parse_version(phonenumbers.__version__) < parse_version('8.13.40'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.40/python/phonenumbers/data/region_IL.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('IL', _local_load_region)

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

    if parse_version(phonenumbers.__version__) < parse_version('8.13.31'):
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.40/python/phonenumbers/data/region_KE.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('KE', _local_load_region)

    # MONKEY PATCHING phonemetadata to fix Brazilian phonenumbers following 2016 changes
    def _hook_load_region_br(code):
        if parse_version(phonenumbers.__version__) < parse_version('8.13.39'):
            # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.39/python/phonenumbers/data/region_BR.py
            _local_load_region(code)
        else:
            phonenumbers.data._load_region(code)
        _region_metadata = phonenumbers.PhoneMetadata._region_metadata
        if 'BR' in _region_metadata:
            _region_metadata['BR'].intl_number_format.append(
                phonenumbers.phonemetadata.NumberFormat(
                    pattern='(\\d{2})(\\d{4})(\\d{4})',
                    format='\\1 9\\2-\\3',
                    leading_digits_pattern=['(?:[14689][1-9]|2[12478]|3[1-578]|5[13-5]|7[13-579][689])'],
                )
            )
    phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('BR', _hook_load_region_br)

    # MONKEY PATCHING phonemetadata to fix Mexican phonenumbers following 2019 changes
    # BEFORE https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.37/python/phonenumbers/data/region_MX.py
    # AFTER  https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.38/python/phonenumbers/data/region_MX.py
    def _hook_load_region_mx(code):
        phonenumbers.data._load_region(code)
        if parse_version(phonenumbers.__version__) > parse_version('8.13.37'):
            _region_metadata = phonenumbers.PhoneMetadata._region_metadata
            if 'MX' in _region_metadata:
                _region_metadata['MX'].intl_number_format.append(
                    phonenumbers.phonemetadata.NumberFormat(
                        pattern='(\\d)(\\d{2})(\\d{4})(\\d{4})',
                        format='\\2 \\3 \\4',
                        leading_digits_pattern=['1(?:33|5[56]|81)']
                    )
                )
                _region_metadata['MX'].intl_number_format.append(
                    phonenumbers.phonemetadata.NumberFormat(
                        pattern='(\\d)(\\d{3})(\\d{3})(\\d{4})',
                        format='\\2 \\3 \\4',
                        leading_digits_pattern=['1']
                    )
                )
    phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('MX', _hook_load_region_mx)
