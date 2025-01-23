# ruff: noqa: F401, PLC0415
# ignore import not at top of the file
import os
import time
from .evented import patch_evented


modules = {}


def set_timezone_utc():
    os.environ['TZ'] = 'UTC'  # Set the timezone
    if hasattr(time, 'tzset'):
        time.tzset()


def register(patched_modules):
    modules.update(patched_modules)
    for patched_module in patched_modules.values():
        patched_module._patched = True


def patch_all():
    patch_evented()
    set_timezone_utc()

    from .codecs import patch_codecs
    patch_codecs()
    from .mimetypes import patch_mimetypes
    patch_mimetypes()
    from .pytz import patch_pytz
    patch_pytz()
    from .literal_eval import patch_literal_eval
    patch_literal_eval()
    from .num2words import patch_num2words
    patch_num2words()
    from .stdnum import patch_stdnum
    patch_stdnum()
    from .zeep import patch_zeep
    patch_zeep()
    from .win32 import patch_win32
    patch_win32()
    from .csv import patch_csv
    patch_csv()
    from .re import patch_re
    patch_re()
    from .xlsxwriter import patch_xlsxwriter
    patch_xlsxwriter()
    from .xlwt import patch_xlwt
    patch_xlwt()
