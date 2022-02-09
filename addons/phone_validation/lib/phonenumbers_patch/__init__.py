from odoo.tools.parse_version import parse_version

try:
    import phonenumbers
    # MONKEY PATCHING phonemetadata of Ivory Coast if phonenumbers is too old
    if parse_version(phonenumbers.__version__) < parse_version('8.12.32'):
        def _local_load_region(code):
            __import__("region_%s" % code, globals(), locals(),
                fromlist=["PHONE_METADATA_%s" % code], level=1)
        # loading updated region_CI.py from current directory
        # https://github.com/daviddrysdale/python-phonenumbers/blob/v8.12.32/python/phonenumbers/data/region_CI.py
        phonenumbers.phonemetadata.PhoneMetadata.register_region_loader('CI', _local_load_region)
except ImportError:
    pass
