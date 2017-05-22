# -*- coding: utf-8 -*-

import re
import unicodedata

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

from odoo import api, models
from odoo.addons.base.ir.ir_http import RequestUID, ModelConverter
from odoo.http import request
from odoo.tools import ustr


# ------------------------------------------------------------
# Slug API
# ------------------------------------------------------------

def slugify(s, max_length=None):
    """ Transform a string to a slug that can be used in a url path.
        This method will first try to do the job with python-slugify if present.
        Otherwise it will process string by stripping leading and ending spaces,
        converting unicode chars to ascii, lowering all chars and replacing spaces
        and underscore with hyphen "-".
        :param s: str
        :param max_length: int
        :rtype: str
    """
    s = ustr(s)
    if slugify_lib:
        # There are 2 different libraries only python-slugify is supported
        try:
            return slugify_lib.slugify(s, max_length=max_length)
        except TypeError:
            pass
    uni = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')
    slug_str = re.sub('[\W_]', ' ', uni).strip().lower()
    slug_str = re.sub('[-\s]+', '-', slug_str)

    return slug_str[:max_length]


def slug(value):
    if isinstance(value, models.BaseModel):
        if isinstance(value.id, models.NewId):
            raise ValueError("Cannot slug non-existent record %s" % value)
        # [(id, name)] = value.name_get()
        identifier, name = value.id, value.display_name
    else:
        # assume name_search result tuple
        identifier, name = value
    slugname = slugify(name or '').strip().strip('-')
    if not slugname:
        return str(identifier)
    return "%s-%d" % (slugname, identifier)

# NOTE: as the pattern is used as it for the ModelConverter (ir_http.py), do not use any flags
_UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|/)')


def unslug(s):
    """Extract slug and id from a string.
        Always return un 2-tuple (str|None, int|None)
    """
    m = _UNSLUG_RE.match(s)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))


def unslug_url(s):
    """ From /blog/my-super-blog-1" to "blog/1" """
    parts = s.split('/')
    if parts:
        unslug_val = unslug(parts[-1])
        if unslug_val[1]:
            parts[-1] = str(unslug_val[1])
            return '/'.join(parts)
    return s


class ModelConverter(ModelConverter):

    def __init__(self, url_map, model=False, domain='[]'):
        super(ModelConverter, self).__init__(url_map, model)
        self.domain = domain
        self.regex = _UNSLUG_RE.pattern

    def to_url(self, value):
        return slug(value)

    def to_python(self, value):
        matching = re.match(self.regex, value)
        _uid = RequestUID(value=value, match=matching, converter=self)
        record_id = int(matching.group(2))
        env = api.Environment(request.cr, _uid, request.context)
        if record_id < 0:
            # limited support for negative IDs due to our slug pattern, assume abs() if not found
            if not env[self.model].browse(record_id).exists():
                record_id = abs(record_id)
        return env[self.model].browse(record_id)


class IrHttp(models.AbstractModel):
    _inherit = ['ir.http']

    @classmethod
    def _get_languages(cls):
        return request.env['res.lang'].search([])

    @classmethod
    def _get_language_codes(cls):
        languages = cls._get_languages()
        return [(lang.code, lang.name) for lang in languages]

    @classmethod
    def _get_default_lang(cls):
        lang_code = request.env['ir.values'].sudo().get_default('res.partner', 'lang')
        if lang_code:
            return request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return request.env['res.lang'].search([], limit=1)