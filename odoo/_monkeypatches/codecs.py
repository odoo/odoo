import codecs
import encodings.aliases
import re

import babel.core


def patch_codecs():
    # ---------------------------------------------------------
    # some charset are known by Python under a different name
    # ---------------------------------------------------------

    encodings.aliases.aliases['874'] = 'cp874'
    encodings.aliases.aliases['windows_874'] = 'cp874'

    # ---------------------------------------------------------
    # alias hebrew iso-8859-8-i and iso-8859-8-e on iso-8859-8
    # https://bugs.python.org/issue18624
    # ---------------------------------------------------------

    iso8859_8 = codecs.lookup('iso8859_8')
    iso8859_8ie_re = re.compile(r'iso[-_]?8859[-_]8[-_]?[ei]', re.IGNORECASE)
    codecs.register(lambda charset: iso8859_8 if iso8859_8ie_re.match(charset) else None)

    # To remove when corrected in Babel
    babel.core.LOCALE_ALIASES['nb'] = 'nb_NO'
