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
    # MONKEY PATCHING phonemetadata of Ivory Coast if phonenumbers is too old
    if parse_version('7.6.1') <= parse_version(phonenumbers.__version__) < parse_version('8.12.32'):
        # loading updated region_CI.py from current directory
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.32/python/phonenumbers/data/region_CI.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('CI', _local_load_region)
    # MONKEY PATCHING phonemetadata of Mauritius if phonenumbers is too old
    if parse_version(phonenumbers.__version__) < parse_version('8.12.13'):
        # loading updated region_MU.py from current directory
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.13.31/python/phonenumbers/data/region_MU.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('MU', _local_load_region)
    # MONKEY PATCHING phonemetadata of Panama if phonenumbers is too old
    if parse_version(phonenumbers.__version__) < parse_version('8.12.43'):
        # region_PA.py in the current directory was copied from external source:
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.43/python/phonenumbers/data/region_PA.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('PA', _local_load_region)
except ImportError:
    pass
