# -*- coding: utf-8 -*-
import inspect
import logging
import math
import unicodedata
import re
import urlparse
import hashlib

from sys import maxint

import werkzeug
# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import openerp
from openerp.tools.translate import _
from openerp.osv import orm, osv, fields
from openerp.tools import html_escape as escape, ustr, image_resize_and_sharpen, image_save_for_web
from openerp.tools.safe_eval import safe_eval
from openerp.addons.web.http import request
from werkzeug.exceptions import NotFound

logger = logging.getLogger(__name__)

def url_for(path_or_uri, lang=None):
    if isinstance(path_or_uri, unicode):
        path_or_uri = path_or_uri.encode('utf-8')
    current_path = request.httprequest.path
    if isinstance(current_path, unicode):
        current_path = current_path.encode('utf-8')
    location = path_or_uri.strip()
    force_lang = lang is not None
    url = urlparse.urlparse(location)

    if request and not url.netloc and not url.scheme and (url.path or force_lang):
        location = urlparse.urljoin(current_path, location)

        lang = lang or request.context.get('lang')
        langs = [lg[0] for lg in request.website.get_languages()]

        if (len(langs) > 1 or force_lang) and is_multilang_url(location, langs):
            ps = location.split('/')
            if ps[1] in langs:
                # Replace the language only if we explicitly provide a language to url_for
                if force_lang:
                    ps[1] = lang.encode('utf-8')
                # Remove the default language unless it's explicitly provided
                elif ps[1] == request.website.default_lang_code:
                    ps.pop(1)
            # Insert the context language or the provided language
            elif lang != request.website.default_lang_code or force_lang:
                ps.insert(1, lang.encode('utf-8'))
            location = '/'.join(ps)

    return location.decode('utf-8')

def is_multilang_url(local_url, langs=None):
    if not langs:
        langs = [lg[0] for lg in request.website.get_languages()]
    spath = local_url.split('/')
    # if a language is already in the path, remove it
    if spath[1] in langs:
        spath.pop(1)
        local_url = '/'.join(spath)
    try:
        # Try to match an endpoint in werkzeug's routing table
        url = local_url.split('?')
        path = url[0]
        query_string = url[1] if len(url) > 1 else None
        router = request.httprequest.app.get_db_router(request.db).bind('')
        # Force to check method to POST. Odoo uses methods : ['POST'] and ['GET', 'POST']
        func = router.match(path, method='POST', query_args=query_string)[0]
        return (func.routing.get('website', False) and
                func.routing.get('multilang', func.routing['type'] == 'http'))
    except Exception:
        return False

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
    slug = re.sub('[\W_]', ' ', uni).strip().lower()
    slug = re.sub('[-\s]+', '-', slug)

    return slug[:max_length]

def slug(value):
    if isinstance(value, orm.browse_record):
        # [(id, name)] = value.name_get()
        id, name = value.id, value.display_name
    else:
        # assume name_search result tuple
        id, name = value
    slugname = slugify(name or '').strip().strip('-')
    if not slugname:
        return str(id)
    return "%s-%d" % (slugname, id)


# NOTE: as the pattern is used as it for the ModelConverter (ir_http.py), do not use any flags
_UNSLUG_RE = re.compile(r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)(?=$|/)')

DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    # retrocompatibility
    "^/website/image/",
]

def unslug(s):
    """Extract slug and id from a string.
        Always return un 2-tuple (str|None, int|None)
    """
    m = _UNSLUG_RE.match(s)
    if not m:
        return None, None
    return m.group(1), int(m.group(2))

def urlplus(url, params):
    return werkzeug.Href(url)(params or None)

class website(osv.osv):
    def _get_menu(self, cr, uid, ids, name, arg, context=None):
        res = {}
        menu_obj = self.pool.get('website.menu')
        for id in ids:
            menu_ids = menu_obj.search(cr, uid, [('parent_id', '=', False), ('website_id', '=', id)], order='id', context=context)
            res[id] = menu_ids and menu_ids[0] or False
        return res

    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"
    _columns = {
        'name': fields.char('Website Name'),
        'domain': fields.char('Website Domain'),
        'company_id': fields.many2one('res.company', string="Company"),
        'language_ids': fields.many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages'),
        'default_lang_id': fields.many2one('res.lang', string="Default language"),
        'default_lang_code': fields.related('default_lang_id', 'code', type="char", string="Default language code", store=True),
        'social_twitter': fields.char('Twitter Account'),
        'social_facebook': fields.char('Facebook Account'),
        'social_github': fields.char('GitHub Account'),
        'social_linkedin': fields.char('LinkedIn Account'),
        'social_youtube': fields.char('Youtube Account'),
        'social_googleplus': fields.char('Google+ Account'),
        'google_analytics_key': fields.char('Google Analytics Key'),
        'user_id': fields.many2one('res.users', string='Public User'),
        'compress_html': fields.boolean('Compress HTML'),
        'cdn_activated': fields.boolean('Activate CDN for assets'),
        'cdn_url': fields.char('CDN Base URL'),
        'cdn_filters': fields.text('CDN Filters', help="URL matching those filters will be rewritten using the CDN Base URL"),
        'partner_id': fields.related('user_id','partner_id', type='many2one', relation='res.partner', string='Public Partner'),
        'menu_id': fields.function(_get_menu, relation='website.menu', type='many2one', string='Main Menu')
    }
    _defaults = {
        'user_id': lambda self,cr,uid,c: self.pool['ir.model.data'].xmlid_to_res_id(cr, openerp.SUPERUSER_ID, 'base.public_user'),
        'company_id': lambda self,cr,uid,c: self.pool['ir.model.data'].xmlid_to_res_id(cr, openerp.SUPERUSER_ID,'base.main_company'),
        'compress_html': False,
        'cdn_activated': False,
        'cdn_url': '',
        'cdn_filters': '\n'.join(DEFAULT_CDN_FILTERS),
    }

    # cf. Wizard hack in website_views.xml
    def noop(self, *args, **kwargs):
        pass

    def write(self, cr, uid, ids, vals, context=None):
        self._get_languages.clear_cache(self)
        return super(website, self).write(cr, uid, ids, vals, context)

    def new_page(self, cr, uid, name, template='website.default_page', ispage=True, context=None):
        context = context or {}
        imd = self.pool.get('ir.model.data')
        view = self.pool.get('ir.ui.view')
        template_module, template_name = template.split('.')

        # completely arbitrary max_length
        page_name = slugify(name, max_length=50)
        page_xmlid = "%s.%s" % (template_module, page_name)

        # find a free xmlid
        inc = 0
        dom = [('website_id', '=', False), ('website_id', '=', context.get('website_id'))]
        while view.search(cr, openerp.SUPERUSER_ID, [('key', '=', page_xmlid), '|'] + dom, context=dict(context or {}, active_test=False)):
            inc += 1
            page_xmlid = "%s.%s" % (template_module, page_name + (inc and "-%s" % inc or ""))
        page_name += (inc and "-%s" % inc or "")

        # new page
        _, template_id = imd.get_object_reference(cr, uid, template_module, template_name)
        website_id = context.get('website_id')
        key = template_module+'.'+page_name
        page_id = view.copy(cr, uid, template_id, {'website_id': website_id, 'key': key}, context=context)
        page = view.browse(cr, uid, page_id, context=dict(context, lang=None))
        page.write({
            'arch': page.arch.replace(template, page_xmlid),
            'name': page_name,
            'page': ispage,
        })
        return page_xmlid

    def key_to_view_id(self, cr, uid, view_id, context=None):
        View = self.pool.get('ir.ui.view')
        return View.search(cr, uid, [
            ('id', '=', view_id),
            "|", ('website_id', '=', context.get('website_id')), ('website_id', '=', False),
            ('page', '=', True),
            ('type', '=', 'qweb')
        ], context=context)

    def delete_page(self, cr, uid, view_id, context=None):
        if context is None:
            context = {}
        View = self.pool.get('ir.ui.view')
        view_find = self.key_to_view_id(cr, uid, view_id, context=context)
        if view_find:
            View.unlink(cr, uid, view_find, context=context)

    def rename_page(self, cr, uid, view_id, new_name, context=None):
        if context is None:
            context = {}
        View = self.pool.get('ir.ui.view')
        view_find = self.key_to_view_id(cr, uid, view_id, context=context)
        if view_find:
            v = View.browse(cr, uid, view_find, context=context)

            new_name = slugify(new_name, max_length=50)
            # Prefix by module if not already done by end user
            prefix = v.key.split('.')[0]
            if not new_name.startswith(prefix):
                new_name = "%s.%s" % (prefix, new_name)

            View.write(cr, uid, view_find, {
                'key': new_name,
                'arch_db': v.arch_db.replace(v.key, new_name, 1)
            })
            return new_name

    def page_search_dependencies(self, cr, uid, view_id=False, context=None):
        dep = {}
        if not view_id:
            return dep

        # search dependencies just for information.
        # It will not catch 100% of dependencies and False positive is more than possible
        # Each module could add dependences in this dict
        if context is None:
            context = {}
        View = self.pool.get('ir.ui.view')
        Menu = self.pool.get('website.menu')

        view = View.browse(cr, uid, view_id, context=context)
        website_id = context.get('website_id')
        name = view.key.replace("website.", "")
        fullname = "website.%s" % name

        if view.page:
            # search for page with link
            page_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('arch_db', 'ilike', '/page/%s' % name), ('arch_db', 'ilike', '/page/%s' % fullname)
            ]
            pages = View.search(cr, uid, page_search_dom, context=context)
            if pages:
                page_key = _('Page')
                dep[page_key] = []
            for page in View.browse(cr, uid, pages, context=context):
                if page.page:
                    dep[page_key].append({
                        'text': _('Page <b>%s</b> seems to have a link to this page !') % page.key,
                        'link': '/page/%s' % page.key
                    })
                else:
                    dep[page_key].append({
                        'text': _('Template <b>%s (id:%s)</b> seems to have a link to this page !') % (page.key, page.id),
                        'link': '#'
                    })

            # search for menu with link
            menu_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('url', 'ilike', '/page/%s' % name), ('url', 'ilike', '/page/%s' % fullname)
            ]

            menus = Menu.search(cr, uid, menu_search_dom, context=context)
            if menus:
                menu_key = _('Menu')
                dep[menu_key] = []
            for menu in Menu.browse(cr, uid, menus, context=context):
                dep[menu_key].append({
                    'text': _('Menu <b>%s</b> seems to have a link to this page !') % menu.name,
                    'link': False
                })

        return dep

    def page_for_name(self, cr, uid, ids, name, module='website', context=None):
        # whatever
        return '%s.%s' % (module, slugify(name, max_length=50))

    def page_exists(self, cr, uid, ids, name, module='website', context=None):
        try:
            name = (name or "").replace("/page/website.", "").replace("/page/", "")
            if not name:
                return False
            return self.pool["ir.model.data"].get_object_reference(cr, uid, module, name)
        except:
            return False

    @openerp.tools.ormcache('id')
    def _get_languages(self, cr, uid, id, context=None):
        website = self.browse(cr, uid, id)
        return [(lg.code, lg.name) for lg in website.language_ids]

    def get_cdn_url(self, cr, uid, uri, context=None):
        # Currently only usable in a website_enable request context
        if request and request.website and not request.debug and request.website.user_id.id == request.uid:
            cdn_url = request.website.cdn_url
            cdn_filters = (request.website.cdn_filters or '').splitlines()
            for flt in cdn_filters:
                if flt and re.match(flt, uri):
                    return urlparse.urljoin(cdn_url, uri)
        return uri

    def get_languages(self, cr, uid, ids, context=None):
        return self._get_languages(cr, uid, ids[0])

    def get_alternate_languages(self, cr, uid, ids, req=None, context=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website(cr, uid, context=context).default_lang_code
        shorts = []

        def get_url_localized(router, lang):
            arguments = dict(request.endpoint_arguments)
            for k, v in arguments.items():
                if isinstance(v, orm.browse_record):
                    arguments[k] = v.with_context(lang=lang)
            return router.build(request.endpoint, arguments)
        router = request.httprequest.app.get_db_router(request.db).bind('')
        for code, name in self.get_languages(cr, uid, ids, context=context):
            lg_path = ('/' + code) if code != default else ''
            lg = code.split('_')
            shorts.append(lg[0])
            uri = request.endpoint and get_url_localized(router, code) or request.httprequest.path
            if req.query_string:
                uri += '?' + req.query_string
            lang = {
                'hreflang': ('-'.join(lg)).lower(),
                'short': lg[0],
                'href': req.url_root[0:-1] + lg_path + uri,
            }
            langs.append(lang)
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']
        return langs

    @openerp.tools.ormcache('domain_name')
    def _get_current_website_id(self, cr, uid, domain_name, context=None):
        ids = self.search(cr, uid, [('domain', '=', domain_name)], limit=1, context=context)
        return ids and ids[0] or self.search(cr, uid, [], limit=1)[0]

    def get_current_website(self, cr, uid, context=None):
        domain_name = request.httprequest.environ.get('HTTP_HOST', '').split(':')[0]
        website_id = self._get_current_website_id(cr, uid, domain_name)
        request.context['website_id'] = website_id
        return self.browse(cr, uid, website_id, context=context)

    def is_publisher(self, cr, uid, ids, context=None):
        Access = self.pool['ir.model.access']
        is_website_publisher = Access.check(cr, uid, 'ir.ui.view', 'write', False, context=context)
        return is_website_publisher

    def is_user(self, cr, uid, ids, context=None):
        Access = self.pool['ir.model.access']
        return Access.check(cr, uid, 'ir.ui.menu', 'read', False, context=context)

    def get_template(self, cr, uid, ids, template, context=None):
        View = self.pool['ir.ui.view']
        if isinstance(template, (int, long)):
            view_id = template
        else:
            if '.' not in template:
                template = 'website.%s' % template
            view_id = View.get_view_id(cr, uid, template, context=context)
        if not view_id:
            raise NotFound
        return View.browse(cr, uid, view_id, context=context)

    def _render(self, cr, uid, ids, template, values=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        return self.pool['ir.ui.view'].render(cr, uid, template, values=values, context=context)

    def render(self, cr, uid, ids, template, values=None, status_code=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        return request.render(template, values, uid=uid)

    def pager(self, cr, uid, ids, url, total, page=1, step=30, scope=5, url_args=None, context=None):
        # Compute Pager
        page_count = int(math.ceil(float(total) / step))

        page = max(1, min(int(page if str(page).isdigit() else 1), page_count))
        scope -= 1

        pmin = max(page - int(math.floor(scope/2)), 1)
        pmax = min(pmin + scope, page_count)

        if pmax - pmin < scope:
            pmin = pmax - scope if pmax - scope > 0 else 1

        def get_url(page):
            _url = "%s/page/%s" % (url, page) if page > 1 else url
            if url_args:
                _url = "%s?%s" % (_url, werkzeug.url_encode(url_args))
            return _url

        return {
            "page_count": page_count,
            "offset": (page - 1) * step,
            "page": {
                'url': get_url(page),
                'num': page
            },
            "page_start": {
                'url': get_url(pmin),
                'num': pmin
            },
            "page_previous": {
                'url': get_url(max(pmin, page - 1)),
                'num': max(pmin, page - 1)
            },
            "page_next": {
                'url': get_url(min(pmax, page + 1)),
                'num': min(pmax, page + 1)
            },
            "page_end": {
                'url': get_url(pmax),
                'num': pmax
            },
            "pages": [
                {'url': get_url(page), 'num': page}
                for page in xrange(pmin, pmax+1)
            ]
        }

    def rule_is_enumerable(self, rule):
        """ Checks that it is possible to generate sensible GET queries for
        a given rule (if the endpoint matches its own requirements)

        :type rule: werkzeug.routing.Rule
        :rtype: bool
        """
        endpoint = rule.endpoint
        methods = endpoint.routing.get('methods') or ['GET']

        converters = rule._converters.values()
        if not ('GET' in methods
            and endpoint.routing['type'] == 'http'
            and endpoint.routing['auth'] in ('none', 'public')
            and endpoint.routing.get('website', False)
            and all(hasattr(converter, 'generate') for converter in converters)
            and endpoint.routing.get('website')):
            return False

        # dont't list routes without argument having no default value or converter
        spec = inspect.getargspec(endpoint.method.original_func)

        # remove self and arguments having a default value
        defaults_count = len(spec.defaults or [])
        args = spec.args[1:(-defaults_count or None)]

        # check that all args have a converter
        return all( (arg in rule._converters) for arg in args)

    def enumerate_pages(self, cr, uid, ids, query_string=None, context=None):
        """ Available pages in the website/CMS. This is mostly used for links
        generation and can be overridden by modules setting up new HTML
        controllers for dynamic pages (e.g. blog).

        By default, returns template views marked as pages.

        :param str query_string: a (user-provided) string, fetches pages
                                 matching the string
        :returns: a list of mappings with two keys: ``name`` is the displayable
                  name of the resource (page), ``url`` is the absolute URL
                  of the same.
        :rtype: list({name: str, url: str})
        """
        router = request.httprequest.app.get_db_router(request.db)
        # Force enumeration to be performed as public user
        url_set = set()
        for rule in router.iter_rules():
            if not self.rule_is_enumerable(rule):
                continue

            converters = rule._converters or {}
            if query_string and not converters and (query_string not in rule.build([{}], append_unknown=False)[1]):
                continue
            values = [{}]
            convitems = converters.items()
            # converters with a domain are processed after the other ones
            gd = lambda x: hasattr(x[1], 'domain') and (x[1].domain <> '[]')
            convitems.sort(lambda x, y: cmp(gd(x), gd(y)))
            for (i,(name, converter)) in enumerate(convitems):
                newval = []
                for val in values:
                    query = i==(len(convitems)-1) and query_string
                    for v in converter.generate(request.cr, uid, query=query, args=val, context=context):
                        newval.append( val.copy() )
                        v[name] = v['loc']
                        del v['loc']
                        newval[-1].update(v)
                values = newval

            for value in values:
                domain_part, url = rule.build(value, append_unknown=False)
                page = {'loc': url}
                for key,val in value.items():
                    if key.startswith('__'):
                        page[key[2:]] = val
                if url in ('/sitemap.xml',):
                    continue
                if url in url_set:
                    continue
                url_set.add(url)

                yield page

    def search_pages(self, cr, uid, ids, needle=None, limit=None, context=None):
        name = re.sub(r"^/p(a(g(e(/(w(e(b(s(i(t(e(\.)?)?)?)?)?)?)?)?)?)?)?)?", "", needle or "")
        res = []
        for page in self.enumerate_pages(cr, uid, ids, query_string=name, context=context):
            if needle in page['loc']:
                res.append(page)
                if len(res) == limit:
                    break
        return res

    def image_url(self, cr, uid, record, field, size=None, context=None):
        """Returns a local url that points to the image field of a given browse record."""
        sudo_record = record.sudo()
        sha = hashlib.sha1(getattr(sudo_record, '__last_update')).hexdigest()[0:7]
        size = '' if size is None else '/%s' % size
        return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

class website_menu(osv.osv):
    _name = "website.menu"
    _description = "Website Menu"
    _columns = {
        'name': fields.char('Menu', required=True, translate=True),
        'url': fields.char('Url'),
        'new_window': fields.boolean('New Window'),
        'sequence': fields.integer('Sequence'),
        # TODO: support multiwebsite once done for ir.ui.views
        'website_id': fields.many2one('website', 'Website'),
        'parent_id': fields.many2one('website.menu', 'Parent Menu', select=True, ondelete="cascade"),
        'child_id': fields.one2many('website.menu', 'parent_id', string='Child Menus'),
        'parent_left': fields.integer('Parent Left', select=True),
        'parent_right': fields.integer('Parent Right', select=True),
    }

    def __defaults_sequence(self, cr, uid, context):
        menu = self.search_read(cr, uid, [(1,"=",1)], ["sequence"], limit=1, order="sequence DESC", context=context)
        return menu and menu[0]["sequence"] or 0

    _defaults = {
        'url': '',
        'sequence': __defaults_sequence,
        'new_window': False,
    }
    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

    # would be better to take a menu_id as argument
    def get_tree(self, cr, uid, website_id, menu_id=None, context=None):
        def make_tree(node):
            menu_node = dict(
                id=node.id,
                name=node.name,
                url=node.url,
                new_window=node.new_window,
                sequence=node.sequence,
                parent_id=node.parent_id.id,
                children=[],
            )
            for child in node.child_id:
                menu_node['children'].append(make_tree(child))
            return menu_node
        if menu_id:
            menu = self.browse(cr, uid, menu_id, context=context)
        else:
            menu = self.pool.get('website').browse(cr, uid, website_id, context=context).menu_id
        return make_tree(menu)

    def save(self, cr, uid, website_id, data, context=None):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        to_delete = data['to_delete']
        if to_delete:
            self.unlink(cr, uid, to_delete, context=context)
        for menu in data['data']:
            mid = menu['id']
            if isinstance(mid, basestring):
                new_id = self.create(cr, uid, {'name': menu['name']}, context=context)
                replace_id(mid, new_id)
        for menu in data['data']:
            self.write(cr, uid, [menu['id']], menu, context=context)
        return True


class ir_attachment(osv.osv):
    _inherit = "ir.attachment"

    _columns = {
        'website_url': fields.related("local_url", string="Attachment URL", type='char', deprecated=True), # related for backward compatibility with saas-6
    }

class res_partner(osv.osv):
    _inherit = "res.partner"

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'center': '%s, %s %s, %s' % (partner.street or '', partner.city or '', partner.zip or '', partner.country_id and partner.country_id.name_get()[0][1] or ''),
            'size': "%sx%s" % (height, width),
            'zoom': zoom,
            'sensor': 'false',
        }
        return urlplus('//maps.googleapis.com/maps/api/staticmap' , params)

    def google_map_link(self, cr, uid, ids, zoom=10, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'q': '%s, %s %s, %s' % (partner.street or '', partner.city  or '', partner.zip or '', partner.country_id and partner.country_id.name_get()[0][1] or ''),
            'z': zoom,
        }
        return urlplus('https://maps.google.com/maps' , params)

class res_company(osv.osv):
    _inherit = "res.company"
    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_img(zoom, width, height, context=context) or None
    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_link(zoom, context=context) or None

class base_language_install(osv.osv_memory):
    _inherit = "base.language.install"
    _columns = {
        'website_ids': fields.many2many('website', string='Websites to translate'),
    }

    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        defaults = super(base_language_install, self).default_get(cr, uid, fields, context)
        website_id = context.get('params', {}).get('website_id')
        if website_id:
            if 'website_ids' not in defaults:
                defaults['website_ids'] = []
            defaults['website_ids'].append(website_id)
        return defaults

    def lang_install(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action = super(base_language_install, self).lang_install(cr, uid, ids, context)
        language_obj = self.browse(cr, uid, ids)[0]
        website_ids = [website.id for website in language_obj['website_ids']]
        lang_id = self.pool['res.lang'].search(cr, uid, [('code', '=', language_obj['lang'])])
        if website_ids and lang_id:
            data = {'language_ids': [(4, lang_id[0])]}
            self.pool['website'].write(cr, uid, website_ids, data)
        params = context.get('params', {})
        if 'url_return' in params:
            return {
                'url': params['url_return'].replace('[lang]', language_obj['lang']),
                'type': 'ir.actions.act_url',
                'target': 'self'
            }
        return action

class website_seo_metadata(osv.Model):
    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    _columns = {
        'website_meta_title': fields.char("Website meta title", translate=True),
        'website_meta_description': fields.text("Website meta description", translate=True),
        'website_meta_keywords': fields.char("Website meta keywords", translate=True),
    }


class website_published_mixin(osv.AbstractModel):
    _name = "website.published.mixin"

    _website_url_proxy = lambda self, *a, **kw: self._website_url(*a, **kw)

    _columns = {
        'website_published': fields.boolean('Visible in Website', copy=False),
        'website_url': fields.function(_website_url_proxy, type='char', string='Website URL',
                                       help='The full URL to access the document through the website.'),
    }

    def _website_url(self, cr, uid, ids, field_name, arg, context=None):
        return dict.fromkeys(ids, '#')

    def website_publish_button(self, cr, uid, ids, context=None):
        for i in self.browse(cr, uid, ids, context):
            if self.pool['res.users'].has_group(cr, uid, 'base.group_website_publisher') and i.website_url != '#':
                return self.open_website_url(cr, uid, ids, context)
            i.write({'website_published': not i.website_published})
        return True

    def open_website_url(self, cr, uid, ids, context=None):
        return {
            'type': 'ir.actions.act_url',
            'url': self.browse(cr, uid, ids[0]).website_url,
            'target': 'self',
        }
