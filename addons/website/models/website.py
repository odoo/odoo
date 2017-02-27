# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import inspect
import logging
import math
import unicodedata
import re
import urlparse
import hashlib
import werkzeug
from werkzeug.exceptions import NotFound

# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

from odoo import api, fields, models
from odoo import tools
from odoo.tools import ustr
from odoo.http import request
from odoo.tools.translate import _

logger = logging.getLogger(__name__)


DEFAULT_CDN_FILTERS = [
    "^/[^/]+/static/",
    "^/web/(css|js)/",
    "^/web/image",
    "^/web/content",
    # retrocompatibility
    "^/website/image/",
]


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


####################################################
# Slug API
####################################################

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


class Website(models.Model):

    _name = "website"  # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"

    def _active_languages(self):
        return self.env['res.lang'].search([]).ids

    def _default_language(self):
        lang_code = self.env['ir.values'].get_default('res.partner', 'lang')
        def_lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        return def_lang.id if def_lang else self._active_languages()[0]

    name = fields.Char('Website Name')
    domain = fields.Char('Website Domain')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.ref('base.main_company').id)
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages', default=_active_languages)
    default_lang_id = fields.Many2one('res.lang', string="Default Language", default=_default_language, required=True)
    default_lang_code = fields.Char(related='default_lang_id.code', string="Default language code", store=True)

    social_twitter = fields.Char('Twitter Account')
    social_facebook = fields.Char('Facebook Account')
    social_github = fields.Char('GitHub Account')
    social_linkedin = fields.Char('LinkedIn Account')
    social_youtube = fields.Char('Youtube Account')
    social_googleplus = fields.Char('Google+ Account')
    google_analytics_key = fields.Char('Google Analytics Key')
    google_management_client_id = fields.Char('Google Client ID')
    google_management_client_secret = fields.Char('Google Client Secret')

    user_id = fields.Many2one('res.users', string='Public User', default=lambda self: self.env.ref('base.public_user').id)
    cdn_activated = fields.Boolean('Activate CDN for assets')
    cdn_url = fields.Char('CDN Base URL', default='')
    cdn_filters = fields.Text('CDN Filters', default=lambda s: '\n'.join(DEFAULT_CDN_FILTERS), help="URL matching those filters will be rewritten using the CDN Base URL")
    partner_id = fields.Many2one(related='user_id.partner_id', relation='res.partner', string='Public Partner')
    menu_id = fields.Many2one('website.menu', compute='_compute_menu', string='Main Menu')
    favicon = fields.Binary(string="Website Favicon", help="This field holds the image used to display a favicon on the website.")

    @api.multi
    def _compute_menu(self):
        Menu = self.env['website.menu']
        for website in self:
            website.menu_id = Menu.search([('parent_id', '=', False), ('website_id', '=', website.id)], order='id', limit=1).id

    # cf. Wizard hack in website_views.xml
    def noop(self, *args, **kwargs):
        pass

    @api.multi
    def write(self, values):
        self._get_languages.clear_cache(self)
        return super(Website, self).write(values)

    #----------------------------------------------------------
    # Page Management
    #----------------------------------------------------------

    @api.model
    def new_page(self, name, template='website.default_page', ispage=True):
        """ Create a new website page, and assign it a xmlid based on the given one
            :param name : the name of the page
            :param template : potential xml_id of the page to create
        """
        template_module, dummy = template.split('.')
        website_id = self._context.get('website_id')

        # completely arbitrary max_length
        page_name = slugify(name, max_length=50)
        page_xmlid = "%s.%s" % (template_module, page_name)

        # find a free xmlid
        inc = 0
        domain_static = [('website_id', '=', False), ('website_id', '=', website_id)]
        while self.env['ir.ui.view'].with_context(active_test=False).sudo().search([('key', '=', page_xmlid), '|'] + domain_static):
            inc += 1
            page_xmlid = "%s.%s" % (template_module, page_name + ("-%s" % inc if inc else ""))
        page_name += (inc and "-%s" % inc or "")

        # new page
        template_record = self.env.ref(template)
        key = '%s.%s' % (template_module, page_name)
        page = template_record.copy({'website_id': website_id, 'key': key})
        page.with_context(lang=None).write({
            'arch': page.arch.replace(template, page_xmlid),
            'name': page_name,
            'page': ispage,
        })
        return page_xmlid

    def key_to_view_id(self, view_id):
        return self.env['ir.ui.view'].search([
            ('id', '=', view_id),
            '|', ('website_id', '=', self._context.get('website_id')), ('website_id', '=', False),
            ('page', '=', True),
            ('type', '=', 'qweb')
        ])

    @api.model
    def delete_page(self, view_id):
        """ Delete a page, given its identifier
            :param view_id : ir.ui.view identifier
        """
        view = self.key_to_view_id(view_id)
        if view:
            view.unlink()

    @api.model
    def rename_page(self, view_id, new_name):
        """ Change the name of the given page
            :param view_id : id of the view to rename
            :param new_name : name to use
        """
        view = self.key_to_view_id(view_id)
        if view:
            # slugify the new name and prefix by module if
            # not already done by end user
            new_name = slugify(new_name, max_length=50)
            prefix = view.key.split('.')[0]
            if not new_name.startswith(prefix):
                new_name = "%s.%s" % (prefix, new_name)

            view.write({
                'key': new_name,
                'arch_db': view.arch_db.replace(view.key, new_name, 1)
            })
            return new_name
        return False

    @api.model
    def page_search_dependencies(self, view_id=False):
        """ Search dependencies just for information. It will not catch 100%
            of dependencies and False positive is more than possible
            Each module could add dependences in this dict
            :returns a dictionnary where key is the 'categorie' of object related to the given
                view, and the value is the list of text and link to the resource using given page
        """
        dependencies = {}
        if not view_id:
            return dependencies

        view = self.env['ir.ui.view'].browse(view_id)
        website_id = self._context.get('website_id')
        name = view.key.replace("website.", "")
        fullname = "website.%s" % name

        if view.page:
            # search for page with link
            page_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('arch_db', 'ilike', '/page/%s' % name), ('arch_db', 'ilike', '/page/%s' % fullname)
            ]

            page_key = _('Page')
            pages = self.env['ir.ui.view'].search(page_search_dom)
            for page in pages:
                dependencies.setdefault(page_key, [])
                if page.page:
                    dependencies[page_key].append({
                        'text': _('Page <b>%s</b> contains a link to this page') % page.key,
                        'link': '/page/%s' % page.key
                    })
                else:
                    dependencies[page_key].append({
                        'text': _('Template <b>%s (id:%s)</b> contains a link to this page') % (page.key, page.id),
                        'link': '#'
                    })

            # search for menu with link
            menu_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('url', 'ilike', '/page/%s' % name), ('url', 'ilike', '/page/%s' % fullname)
            ]

            menu_key = _('Menu')
            menus = self.env['website.menu'].search(menu_search_dom)
            for menu in menus:
                dependencies.setdefault(menu_key, []).append({
                    'text': _('This page is in the menu <b>%s</b>') % menu.name,
                    'link': False
                })

        return dependencies

    @api.model
    def page_exists(self, name, module='website'):
        try:
            name = (name or "").replace("/page/website.", "").replace("/page/", "")
            if not name:
                return False
            return self.env.ref('%s.%s' % module, name)
        except:
            return False

    #----------------------------------------------------------
    # Languages
    #----------------------------------------------------------

    @api.multi
    def get_languages(self):
        self.ensure_one()
        return self._get_languages()

    @tools.cache('self.id')
    def _get_languages(self):
        return [(lg.code, lg.name) for lg in self.language_ids]

    @api.multi
    def get_alternate_languages(self, req=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website().default_lang_code
        shorts = []

        def get_url_localized(router, lang):
            arguments = dict(request.endpoint_arguments)
            for key, val in arguments.items():
                if isinstance(val, models.BaseModel):
                    arguments[key] = val.with_context(lang=lang)
            return router.build(request.endpoint, arguments)

        router = request.httprequest.app.get_db_router(request.db).bind('')
        for code, dummy in self.get_languages():
            lg_path = ('/' + code) if code != default else ''
            lg_codes = code.split('_')
            shorts.append(lg_codes[0])
            uri = get_url_localized(router, code) if request.endpoint else request.httprequest.path
            if req.query_string:
                uri += '?' + req.query_string
            lang = {
                'hreflang': ('-'.join(lg_codes)).lower(),
                'short': lg_codes[0],
                'href': req.url_root[0:-1] + lg_path + uri,
            }
            langs.append(lang)
        for lang in langs:
            if shorts.count(lang['short']) == 1:
                lang['hreflang'] = lang['short']
        return langs

    #----------------------------------------------------------
    # Utilities
    #----------------------------------------------------------

    @api.model
    def get_current_website(self):
        domain_name = request.httprequest.environ.get('HTTP_HOST', '').split(':')[0]
        website_id = self._get_current_website_id(domain_name)
        request.context = dict(request.context, website_id=website_id)
        return self.browse(website_id)

    @tools.cache('domain_name')
    def _get_current_website_id(self, domain_name):
        """ Reminder : cached method should be return record, since they will use a closed cursor. """
        website = self.search([('domain', '=', domain_name)], limit=1)
        if not website:
            website = self.search([], limit=1)
        return website.id

    @api.model
    def is_publisher(self):
        return self.env['ir.model.access'].check('ir.ui.view', 'write', False)

    @api.model
    def is_user(self):
        return self.env['ir.model.access'].check('ir.ui.menu', 'read', False)

    @api.model
    def get_template(self, template):
        View = self.env['ir.ui.view']
        if isinstance(template, (int, long)):
            view_id = template
        else:
            if '.' not in template:
                template = 'website.%s' % template
            view_id = View.get_view_id(template)
        if not view_id:
            raise NotFound
        return View.browse(view_id)

    @api.model
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
        """ Generate a dict with required value to render `website.pager` template. This method compute
            url, page range to display, ... in the pager.
            :param url : base url of the page link
            :param total : number total of item to be splitted into pages
            :param page : current page
            :param step : item per page
            :param scope : number of page to display on pager
            :param url_args : additionnal parameters to add as query params to page url
            :type url_args : dict
            :returns dict
        """
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
                {'url': get_url(page), 'num': page} for page in xrange(pmin, pmax+1)
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
        return all((arg in rule._converters) for arg in args)

    @api.multi
    def enumerate_pages(self, query_string=None):
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
            gd = lambda x: hasattr(x[1], 'domain') and (x[1].domain != '[]')
            convitems.sort(lambda x, y: cmp(gd(x), gd(y)))
            for (i, (name, converter)) in enumerate(convitems):
                newval = []
                for val in values:
                    query = i == len(convitems)-1 and query_string
                    for value_dict in converter.generate(query=query, args=val):
                        newval.append(val.copy())
                        value_dict[name] = value_dict['loc']
                        del value_dict['loc']
                        newval[-1].update(value_dict)
                values = newval

            for value in values:
                domain_part, url = rule.build(value, append_unknown=False)
                page = {'loc': url}
                for key, val in value.items():
                    if key.startswith('__'):
                        page[key[2:]] = val
                if url in ('/sitemap.xml',):
                    continue
                if url in url_set:
                    continue
                url_set.add(url)

                yield page

    @api.multi
    def search_pages(self, needle=None, limit=None):
        name = re.sub(r"^/p(a(g(e(/(w(e(b(s(i(t(e(\.)?)?)?)?)?)?)?)?)?)?)?)?", "", needle or "")
        name = slugify(name, max_length=50)
        res = []
        for page in self.enumerate_pages(query_string=name):
            res.append(page)
            if len(res) == limit:
                break
        return res

    @api.model
    def image_url(self, record, field, size=None):
        """ Returns a local url that points to the image field of a given browse record. """
        sudo_record = record.sudo()
        sha = hashlib.sha1(getattr(sudo_record, '__last_update')).hexdigest()[0:7]
        size = '' if size is None else '/%s' % size
        return '/web/image/%s/%s/%s%s?unique=%s' % (record._name, record.id, field, size, sha)

    @api.model
    def get_cdn_url(self, uri):
        # Currently only usable in a website_enable request context
        if request and request.website and not request.debug and request.website.user_id.id == request.uid:
            cdn_url = request.website.cdn_url
            cdn_filters = (request.website.cdn_filters or '').splitlines()
            for flt in cdn_filters:
                if flt and re.match(flt, uri):
                    return urlparse.urljoin(cdn_url, uri)
        return uri


class Menu(models.Model):

    _name = "website.menu"
    _description = "Website Menu"

    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

    def _default_sequence(self):
        menu = self.search([], limit=1, order="sequence DESC")
        return menu.sequence or 0

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char('Url', default='')
    new_window = fields.Boolean('New Window')
    sequence = fields.Integer(default=_default_sequence)
    website_id = fields.Many2one('website', 'Website')  # TODO: support multiwebsite once done for ir.ui.views
    parent_id = fields.Many2one('website.menu', 'Parent Menu', index=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_left = fields.Integer('Parent Left', index=True)
    parent_right = fields.Integer('Parent Rigth', index=True)

    # would be better to take a menu_id as argument
    @api.model
    def get_tree(self, website_id, menu_id=None):
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
            menu = self.browse(menu_id)
        else:
            menu = self.env['website'].browse(website_id).menu_id
        return make_tree(menu)

    @api.model
    def save(self, website_id, data):
        def replace_id(old_id, new_id):
            for menu in data['data']:
                if menu['id'] == old_id:
                    menu['id'] = new_id
                if menu['parent_id'] == old_id:
                    menu['parent_id'] = new_id
        to_delete = data['to_delete']
        if to_delete:
            self.browse(to_delete).unlink()
        for menu in data['data']:
            mid = menu['id']
            if isinstance(mid, basestring):
                new_menu = self.create({'name': menu['name']})
                replace_id(mid, new_menu.id)
        for menu in data['data']:
            self.browse(menu['id']).write(menu)
        return True


class SeoMetadata(models.AbstractModel):

    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)


class WebsitePublishedMixin(models.AbstractModel):

    _name = "website.published.mixin"

    website_published = fields.Boolean('Visible in Website', copy=False)
    website_url = fields.Char('Website URL', compute='_compute_website_url', help='The full URL to access the document through the website.')

    @api.multi
    def _compute_website_url(self):
        for record in self:
            record.website_url = '#'

    @api.multi
    def website_publish_button(self):
        self.ensure_one()
        if self.env.user.has_group('website.group_website_publisher') and self.website_url != '#':
            return self.open_website_url()
        return self.write({'website_published': not self.website_published})

    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }
