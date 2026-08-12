# Part of Odoo. See LICENSE file for full copyright and licensing details.

import bisect
import functools
import json

from odoo import http
from odoo.tools.misc import file_open


@functools.cache
def _load_search_index():
    """Load the inverted search index for Material Symbols icons.

    The index maps each unique token (lowercase word from an icon's name or
    tags) to the list of icon indices that contain it.  Tokens are stored
    sorted so that ``bisect`` can efficiently locate prefix matches.

    :returns: a dict with keys ``t`` (sorted tokens), ``i`` (token → icon
        index list), and ``c`` (compact icon list: ``n`` = name, ``f`` = has_fill).
    """
    with file_open('web/static/src/libs/materialsymbols/search_index.json', 'r') as fh:
        return json.load(fh)


class MaterialSymbols(http.Controller):

    @http.route('/web/material_symbols/search', type='jsonrpc', auth='user', readonly=True)
    def search(self, needle='', variant='outline'):
        """Search the Material Symbols icons by name and tags.

        :param str needle: the search term.  When empty, every icon is returned.
        :param str variant: ``'outline'`` (default) or ``'filled'``.
        :returns: a list of ``{name, variant, source}`` dicts, tags excluded.
        """
        needle = (needle or '').strip().lower()
        if not needle:
            index = _load_search_index()
            icon_list = index['c']
            return [
                {
                    'name': icon['n'],
                    'variant': 'filled' if (variant == 'filled' and icon['f']) else 'outline',
                    'source': 'ms',
                }
                for icon in icon_list
            ]

        index = _load_search_index()
        tokens = index['t']
        inverted = index['i']
        icon_list = index['c']

        # Split needle into words; intersect the icon sets for each word.
        words = needle.split()
        matching_indices: set[int] | None = None

        for word in words:
            # Find all tokens that *start with* this word via binary search.
            lo = bisect.bisect_left(tokens, word)
            hi = bisect.bisect_left(tokens, word + '\uffff')  # sentinel

            word_indices: set[int] = set()
            for token in tokens[lo:hi]:
                word_indices.update(inverted[token])

            if matching_indices is None:
                matching_indices = word_indices
            else:
                matching_indices &= word_indices

            if not matching_indices:
                return []

        return [
            {
                'name': icon_list[idx]['n'],
                'variant': 'filled' if (variant == 'filled' and icon_list[idx]['f']) else 'outline',
                'source': 'ms',
            }
            for idx in sorted(matching_indices or [])
        ]
