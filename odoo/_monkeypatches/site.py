"""Patcher for any change not strictly related to an stdlib module"""

import codecs
import encodings.aliases
import re
import sys

import babel.core

import odoo


def patch_module():
    patch_evented()
    patch_codecs()


odoo.evented = False


def patch_evented():
    """Running mode flags (evented, prefork)

    This should be executed early. It will initialize the `odoo.evented` variable.
    """
    if odoo.evented or not (len(sys.argv) > 1 and sys.argv[1] == "evented"):
        return
    sys.argv.remove("evented")
    odoo.evented = True


def patch_codecs():
    # ---------------------------------------------------------
    # some charset are known by Python under a different name
    # ---------------------------------------------------------

    encodings.aliases.aliases["874"] = "cp874"
    encodings.aliases.aliases["windows_874"] = "cp874"

    # ---------------------------------------------------------
    # alias hebrew iso-8859-8-i and iso-8859-8-e on iso-8859-8
    # https://bugs.python.org/issue18624
    # ---------------------------------------------------------

    iso8859_8 = codecs.lookup("iso8859_8")
    iso8859_8ie_re = re.compile(r"iso[-_]?8859[-_]8[-_]?[ei]", re.IGNORECASE)
    codecs.register(
        lambda charset: iso8859_8 if iso8859_8ie_re.match(charset) else None
    )

    # To remove when corrected in Babel
    babel.core.LOCALE_ALIASES["nb"] = "nb_NO"
