# -*- coding: utf-8 -*-

import logging
import os
import re
import unicodedata
import werkzeug

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import odoo
from odoo import api, models
from odoo.addons.base.models.ir_http import RequestUID, ModelConverter
from odoo.http import request
from odoo.tools import config, ustr, pycompat

from ..geoipresolver import GeoIPResolver

_logger = logging.getLogger(__name__)

# global resolver (GeoIP API is thread-safe, for multithreaded workers)
# This avoids blowing up open files limit
odoo._geoip_resolver = None


# ------------------------------------------------------------
# Slug API
# ------------------------------------------------------------

def _guess_mimetype(ext=False, default='text/html'):
    exts = {
        '.css': 'text/css',
        '.less': 'text/less',
        '.scss': 'text/scss',
        '.js': 'text/javascript',
        '.xml': 'text/xml',
        '.csv': 'text/csv',
        '.html': 'text/html',
    }
    return ext is not False and exts.get(ext, default) or exts


def slugify_one(s, max_length=0):
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
    slug_str = re.sub(r'[\W_]', ' ', uni).strip().lower()
    slug_str = re.sub(r'[-\s]+', '-', slug_str)
    return slug_str[:max_length] if max_length > 0 else slug_str


def slugify(s, max_length=0, path=False):
    if not path:
        return slugify_one(s, max_length=max_length)
    else:
        res = []
        for u in s.split('/'):
            if slugify_one(u, max_length=max_length) != '':
                res.append(slugify_one(u, max_length=max_length))
        # check if supported extension
        path_no_ext, ext = os.path.splitext(s)
        if ext and ext in _guess_mimetype():
            res[-1] = slugify_one(path_no_ext) + ext
        return '/'.join(res)


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


# ------------------------------------------------------------
# Language tools
# ------------------------------------------------------------

def url_for(path_or_uri, lang=None):
    current_path = request.httprequest.path     # should already be text
    location = pycompat.to_text(path_or_uri).strip()
    force_lang = lang is not None
    url = werkzeug.urls.url_parse(location)

    if not url.netloc and not url.scheme and (url.path or force_lang):
        location = werkzeug.urls.url_join(current_path, location)

        lang = pycompat.to_text(lang or request.context.get('lang') or 'en_US')
        langs = [lg[0] for lg in request.env['ir.http']._get_language_codes()]

        if (len(langs) > 1 or force_lang) and is_multilang_url(location, langs):
            ps = location.split(u'/')
            if ps[1] in langs:
                # Replace the language only if we explicitly provide a language to url_for
                if force_lang:
                    ps[1] = lang
                # Remove the default language unless it's explicitly provided
                elif ps[1] == request.env['ir.http']._get_default_lang().code:
                    ps.pop(1)
            # Insert the context language or the provided language
            elif lang != request.env['ir.http']._get_default_lang().code or force_lang:
                ps.insert(1, lang)
            location = u'/'.join(ps)

    return location


def is_multilang_url(local_url, langs=None):
    if not langs:
        langs = [lg[0] for lg in request.env['ir.http']._get_language_codes()]
    spath = local_url.split('/')
    # if a language is already in the path, remove it
    if spath[1] in langs:
        spath.pop(1)
        local_url = '/'.join(spath)

    url = local_url.partition('#')[0].split('?')
    path = url[0]
    query_string = url[1] if len(url) > 1 else None
    router = request.httprequest.app.get_db_router(request.db).bind('')

    def is_multilang_func(func):
        return (func and func.routing.get('website', False) and
                func.routing.get('multilang', func.routing['type'] == 'http'))
    # Try to match an endpoint in werkzeug's routing table
    try:
        func = router.match(path, method='POST', query_args=query_string)[0]
        return is_multilang_func(func)
    except werkzeug.exceptions.MethodNotAllowed:
        func = router.match(path, method='GET', query_args=query_string)[0]
        return is_multilang_func(func)
    except werkzeug.exceptions.NotFound:
        # Consider /static/ files as non-multilang
        static_index = path.find('/static/', 1)
        if static_index != -1 and static_index == path.find('/', 1):
            return False
        return True
    except Exception:
        return False


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

    rerouting_limit = 10

    @classmethod
    def _get_converters(cls):
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super(IrHttp, cls)._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _get_languages(cls):
        return request.env['res.lang'].search([])

    @classmethod
    def _get_language_codes(cls):
        languages = cls._get_languages()
        return [(lang.code, lang.name) for lang in languages]

    @classmethod
    def _get_default_lang(cls):
        lang_code = request.env['ir.default'].sudo().get('res.partner', 'lang')
        if lang_code:
            return request.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return request.env['res.lang'].search([], limit=1)

    @classmethod
    def _get_translation_frontend_modules_domain(cls):
        """ Return a domain to list the domain adding web-translations and
            dynamic resources that may be used frontend views
        """
        return []

    bots = "bot|crawl|slurp|spider|curl|wget|facebookexternalhit".split("|")

    @classmethod
    def is_a_bot(cls):
        # We don't use regexp and ustr voluntarily
        # timeit has been done to check the optimum method
        user_agent = request.httprequest.environ.get('HTTP_USER_AGENT', '').lower()
        try:
            return any(bot in user_agent for bot in cls.bots)
        except UnicodeDecodeError:
            return any(bot in user_agent.encode('ascii', 'ignore') for bot in cls.bots)

    @classmethod
    def get_nearest_lang(cls, lang):
        # Try to find a similar lang. Eg: fr_BE and fr_FR
        short = lang.partition('_')[0]
        short_match = False
        for code, dummy in cls._get_language_codes():
            if code == lang:
                return lang
            if not short_match and code.startswith(short):
                short_match = code
        return short_match

    @classmethod
    def _geoip_setup_resolver(cls):
        # Lazy init of GeoIP resolver
        if odoo._geoip_resolver is not None:
            return
        geofile = config.get('geoip_database')
        try:
            odoo._geoip_resolver = GeoIPResolver.open(geofile) or False
        except Exception as e:
            _logger.warning('Cannot load GeoIP: %s', ustr(e))

    @classmethod
    def _geoip_resolve(cls):
        if 'geoip' not in request.session:
            record = {}
            if odoo._geoip_resolver and request.httprequest.remote_addr:
                record = odoo._geoip_resolver.resolve(request.httprequest.remote_addr) or {}
            request.session['geoip'] = record

    @classmethod
    def _add_dispatch_parameters(cls, func):
        # only called for is_frontend request
        if request.routing_iteration == 1:
            context = dict(request.context)
            path = request.httprequest.path.split('/')
            langs = [lg.code for lg in cls._get_languages()]
            is_a_bot = cls.is_a_bot()
            cook_lang = request.httprequest.cookies.get('frontend_lang')
            nearest_lang = not func and cls.get_nearest_lang(path[1])
            preferred_lang = ((cook_lang if cook_lang in langs else False)
                              or (not is_a_bot and cls.get_nearest_lang(request.lang))
                              or cls._get_default_lang().code)

            request.lang = context['lang'] = nearest_lang or preferred_lang

            # bind modified context
            request.context = context

    @classmethod
    def _dispatch(cls):
        """ Before executing the endpoint method, add website params on request, such as
                - current website (record)
                - multilang support (set on cookies)
                - geoip dict data are added in the session
            Then follow the parent dispatching.
            Reminder :  Do not use `request.env` before authentication phase, otherwise the env
                        set on request will be created with uid=None (and it is a lazy property)
        """
        request.routing_iteration = getattr(request, 'routing_iteration', 0) + 1

        func = None
        routing_error = None
        # locate the controller method
        try:
            if request.httprequest.method == 'GET' and '//' in request.httprequest.path:
                new_url = request.httprequest.path.replace('//', '/') + '?' + request.httprequest.query_string.decode('utf-8')
                return werkzeug.utils.redirect(new_url, 301)
            rule, arguments = cls._find_handler(return_rule=True)
            func = rule.endpoint
            request.is_frontend = func.routing.get('website', False)
        except werkzeug.exceptions.NotFound as e:
            # either we have a language prefixed route, either a real 404
            # in all cases, website processes them
            request.is_frontend = True
            routing_error = e

        request.is_frontend_multilang = (
            request.is_frontend and
            (not func or (func and func.routing.get('multilang', func.routing['type'] == 'http')))
        )

        cls._geoip_setup_resolver()
        cls._geoip_resolve()

        # check authentication level
        try:
            if func:
                cls._authenticate(func.routing['auth'])
            elif request.uid is None and request.is_frontend:
                cls._auth_method_public()
        except Exception as e:
            return cls._handle_exception(e)

        # For website routes (only), add website params on `request`
        cook_lang = request.httprequest.cookies.get('frontend_lang')
        if request.is_frontend:
            request.redirect = lambda url, code=302: werkzeug.utils.redirect(url_for(url), code)

            cls._add_dispatch_parameters(func)

            path = request.httprequest.path.split('/')
            if request.routing_iteration == 1:
                is_a_bot = cls.is_a_bot()
                nearest_lang = not func and cls.get_nearest_lang(path[1])
                url_lang = nearest_lang and path[1]

                # if lang in url but not the displayed or default language --> change or remove
                # or no lang in url, and lang to dispay not the default language --> add lang
                # and not a POST request
                # and not a bot or bot but default lang in url
                if ((url_lang and (url_lang != request.lang or url_lang == cls._get_default_lang().code))
                        or (not url_lang and request.is_frontend_multilang and request.lang != cls._get_default_lang().code)
                        and request.httprequest.method != 'POST') \
                        and (not is_a_bot or (url_lang and url_lang == cls._get_default_lang().code)):
                    if url_lang:
                        path.pop(1)
                    if request.lang != cls._get_default_lang().code:
                        path.insert(1, request.lang)
                    path = '/'.join(path) or '/'
                    routing_error = None
                    redirect = request.redirect(path + '?' + request.httprequest.query_string.decode('utf-8'))
                    redirect.set_cookie('frontend_lang', request.lang)
                    return redirect
                elif url_lang:
                    request.uid = None
                    path.pop(1)
                    routing_error = None
                    return cls.reroute('/'.join(path) or '/')

            if request.lang == cls._get_default_lang().code:
                context = dict(request.context)
                context['edit_translations'] = False
                request.context = context

        if routing_error:
            return cls._handle_exception(routing_error)

        # removed cache for auth public
        result = super(IrHttp, cls)._dispatch()

        if request.is_frontend and cook_lang != request.lang and hasattr(result, 'set_cookie'):
            result.set_cookie('frontend_lang', request.lang)

        return result

    @classmethod
    def reroute(cls, path):
        if not hasattr(request, 'rerouting'):
            request.rerouting = [request.httprequest.path]
        if path in request.rerouting:
            raise Exception("Rerouting loop is forbidden")
        request.rerouting.append(path)
        if len(request.rerouting) > cls.rerouting_limit:
            raise Exception("Rerouting limit exceeded")
        request.httprequest.environ['PATH_INFO'] = path
        # void werkzeug cached_property. TODO: find a proper way to do this
        for key in ('path', 'full_path', 'url', 'base_url'):
            request.httprequest.__dict__.pop(key, None)

        return cls._dispatch()

    @classmethod
    def _postprocess_args(cls, arguments, rule):
        super(IrHttp, cls)._postprocess_args(arguments, rule)

        try:
            _, path = rule.build(arguments)
            assert path is not None
        except odoo.exceptions.MissingError:
            return cls._handle_exception(werkzeug.exceptions.NotFound())
        except Exception as e:
            return cls._handle_exception(e)

        if getattr(request, 'is_frontend_multilang', False) and request.httprequest.method in ('GET', 'HEAD'):
            generated_path = werkzeug.url_unquote_plus(path)
            current_path = werkzeug.url_unquote_plus(request.httprequest.path)
            if generated_path != current_path:
                if request.lang != cls._get_default_lang().code:
                    path = '/' + request.lang + path
                if request.httprequest.query_string:
                    path += '?' + request.httprequest.query_string.decode('utf-8')
                return werkzeug.utils.redirect(path, code=301)
