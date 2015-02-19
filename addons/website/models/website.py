# -*- coding: utf-8 -*-
import cStringIO
import contextlib
import datetime
import hashlib
import inspect
import logging
import math
import unicodedata
import os
import re
import time
import urlparse

from PIL import Image
from sys import maxint

import werkzeug
# optional python-slugify import (https://github.com/un33k/python-slugify)
try:
    import slugify as slugify_lib
except ImportError:
    slugify_lib = None

import openerp
from openerp import models, fields, api, _
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

        lang = lang or request.env.context.get('lang')
        langs = [lg[0] for lg in request.website.get_languages()]

        if (len(langs) > 1 or force_lang) and is_multilang_url(location, langs):
            ps = location.split('/')
            if ps[1] in langs:
                # Replace the language only if we explicitly provide a language to url_for
                if force_lang:
                    ps[1] = lang
                # Remove the default language unless it's explicitly provided
                elif ps[1] == request.website.default_lang_code:
                    ps.pop(1)
            # Insert the context language or the provided language
            elif lang != request.website.default_lang_code or force_lang:
                ps.insert(1, lang)
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
        return func.routing.get('website', False) and func.routing.get('multilang', True)
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
    if isinstance(value, models.BaseModel):
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

class website(models.Model):
    @api.multi
    def _get_menu(self):
        Menu = self.env['website.menu']
        for res in self:
            menu_ids = Menu.search([('parent_id', '=', False), ('website_id', '=', res.id)], order='id').ids
            res.menu_id = menu_ids and menu_ids[0] or False

    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco

    name = fields.Char('Website Name')
    domain = fields.Char('Website Domain')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self:self.env['ir.model.data'].sudo().xmlid_to_res_id('base.main_company'))
    language_ids = fields.Many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages')
    default_lang_id = fields.Many2one('res.lang', string="Default language")
    default_lang_code = fields.Char(related='default_lang_id.code', string="Default language code", store=True)
    social_twitter = fields.Char('Twitter Account')
    social_facebook = fields.Char('Facebook Account')
    social_github = fields.Char('GitHub Account')
    social_linkedin = fields.Char('LinkedIn Account')
    social_youtube = fields.Char('Youtube Account')
    social_googleplus = fields.Char('Google+ Account')
    google_analytics_key = fields.Char('Google Analytics Key')
    user_id = fields.Many2one('res.users', string='Public User', default=lambda self:self.env['ir.model.data'].sudo().xmlid_to_res_id('base.public_user'))
    compress_html = fields.Boolean('Compress HTML', default=False)
    cdn_activated = fields.Boolean('Activate CDN for assets', Default=False)
    cdn_url = fields.Char('CDN Base URL', default='//localhost:8069/')
    cdn_filters = fields.Text('CDN Filters', help="URL matching those filters will be rewritten using the CDN Base URL", default='\n'.join(DEFAULT_CDN_FILTERS))
    partner_id = fields.Many2one('res.partner', related='user_id.partner_id', string='Public Partner')
    menu_id = fields.Many2one('website.menu', compute='_get_menu', string='Main Menu')

    # cf. Wizard hack in website_views.xml
    def noop(self, *args, **kwargs):
        pass

    @api.multi
    def write(self, vals):
        self._get_languages.clear_cache(self)
        return super(website, self).write(vals)

    @api.model
    def new_page(self, name, template='website.default_page', ispage=True):
        Imd = self.env['ir.model.data']
        template_module, template_name = template.split('.')

        # completely arbitrary max_length
        page_name = slugify(name, max_length=50)
        page_xmlid = "%s.%s" % (template_module, page_name)

        # find a free xmlid
        inc = 0
        dom = [('key', '=', page_xmlid), '|', ('website_id', '=', False), ('website_id', '=', self.env.context.get('website_id'))]
        while self.env['ir.ui.view'].sudo().with_context(active_test=False).search(dom):
            inc += 1
            page_xmlid = "%s.%s" % (template_module, page_name + (inc and "-%s" % inc or ""))
        page_name += (inc and "-%s" % inc or "")

        # new page
        template_id = Imd.xmlid_to_object(template)
        website_id = self.env.context.get('website_id')
        key = template_module+'.'+page_name
        page = template_id.copy({'website_id': website_id, 'key': key})
        page.write({
            'arch': page.arch.replace(template, page_xmlid),
            'name': page_name,
            'page': ispage,
        })
        return page_xmlid

    @api.model
    def delete_page(self, view_id):
        view_find = self.env['ir.ui.view'].search([
            ('id', '=', view_id),
            "|", ('website_id', '=', self.env.context.get('website_id')), ('website_id', '=', False),
            ('page', '=', True),
            ('type', '=', 'qweb')
        ])
        if view_find:
            view_find.unlink()

    @api.model
    def page_search_dependencies(self, view_id=False):
        dep = {}
        if not view_id:
            return dep

        # search dependencies just for information.
        # It will not catch 100% of dependencies and False positive is more than possible
        # Each module could add dependences in this dict
        View = self.env['ir.ui.view']

        view = View.browse(view_id)
        website_id = self.env.context.get('website_id')
        name = view.key.replace("website.", "")
        fullname = "website.%s" % name

        if view.page:
            # search for page with link
            page_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('arch_db', 'ilike', '/page/%s' % name), ('arch_db', 'ilike', '/page/%s' % fullname)
            ]
            pages = View.search(page_search_dom)
            if pages:
                page_key = _('Page')
                dep[page_key] = []
            for page in pages:
                if page.page:
                    dep[page_key].append({
                        'text': _('Page <b>%s</b> seems to have a link to this page !' % page.key),
                        'link': '/page/%s' % page.key
                    })
                else:
                    dep[page_key].append({
                        'text': _('Template <b>%s (id:%s)</b> seems to have a link to this page !' % (page.key, page.id)),
                        'link': '#'
                    })

            # search for menu with link
            menu_search_dom = [
                '|', ('website_id', '=', website_id), ('website_id', '=', False),
                '|', ('url', 'ilike', '/page/%s' % name), ('url', 'ilike', '/page/%s' % fullname)
            ]

            menus = self.env['website.menu'].search(menu_search_dom)
            if menus:
                menu_key = _('Menu')
                dep[menu_key] = []
            for menu in menus:
                dep[menu_key].append({
                    'text': _('Menu <b>%s</b> seems to have a link to this page !' % menu.name),
                    'link': False
                })

        return dep

    @api.multi
    def page_for_name(self, name, module='website'):
        # whatever
        return '%s.%s' % (module, slugify(name, max_length=50))

    @api.multi
    def page_exists(self, name, module='website'):
        try:
            name = (name or "").replace("/page/website.", "").replace("/page/", "")
            if not name:
                return False
            return self.env["ir.model.data"].xmlid_to_res_model_res_id(module+'.'+name)
        except:
            return False

    @openerp.tools.ormcache(skiparg=3)
    @api.multi
    def _get_languages(self):
        return [(lg.code, lg.name) for lg in self.language_ids]

    @api.model
    def get_cdn_url(self, uri):
        # Currently only usable in a website_enable request context
        if request and request.website and not request.debug:
            cdn_url = request.website.cdn_url
            cdn_filters = (request.website.cdn_filters or '').splitlines()
            for flt in cdn_filters:
                if flt and re.match(flt, uri):
                    return urlparse.urljoin(cdn_url, uri)
        return uri

    @api.multi
    def get_languages(self):
        return self._get_languages()

    @api.multi
    def get_alternate_languages(self, req=None):
        langs = []
        if req is None:
            req = request.httprequest
        default = self.get_current_website().default_lang_code
        uri = req.path
        if req.query_string:
            uri += '?' + req.query_string
        shorts = []
        for code, name in self.get_languages():
            lg_path = ('/' + code) if code != default else ''
            lg = code.split('_')
            shorts.append(lg[0])
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

    @api.model
    @openerp.tools.ormcache(skiparg=4)
    def _get_current_website_id(self, domain_name):
        id = self.search([('name', '=', domain_name)], limit=1).id
        if id:
            return id
        else:
            return self.search([], limit=1).id

    @api.model
    def get_current_website(self):
        domain_name = request.httprequest.environ.get('HTTP_HOST', '').split(':')[0]
        website_id = self._get_current_website_id(domain_name)
        request.context['website_id'] = website_id
        return self.browse(website_id)

    @api.multi
    def is_publisher(self):
        is_website_publisher = self.env['ir.model.access'].check('ir.ui.view', 'write', False)
        return is_website_publisher

    @api.multi
    def is_user(self):
        return self.env['ir.model.access'].check('ir.ui.menu', 'read', False)

    @api.multi
    def get_template(self, template):
        if not isinstance(template, (int, long)) and '.' not in template:
            template = 'website.%s' % template
        View = self.env['ir.ui.view']
        view_id = View.get_view_id(template)
        if not view_id:
            raise NotFound
        return View.browse(view_id)

    def _render(self, cr, uid, ids, template, values=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        return self.pool['ir.ui.view'].render(cr, uid, template, values=values, context=context)

    def render(self, cr, uid, ids, template, values=None, status_code=None, context=None):
        # TODO: remove this. (just kept for backward api compatibility for saas-3)
        return request.render(template, values, uid=uid)

    @api.multi
    def pager(self, url, total, page=1, step=30, scope=5, url_args=None):
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

    @api.model
    def rule_is_enumerable(self, rule):
        """ Checks that it is possible to generate sensible GET queries for
        a given rule (if the endpoint matches its own requirements)

        :type rule: werkzeug.routing.Rule
        :rtype: bool
        """
        endpoint = rule.endpoint
        methods = rule.methods or ['GET']
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
        url_list = []
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
                    for v in converter.generate(query=query, args=val):
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
                if url in url_list:
                    continue
                url_list.append(url)

                yield page

    @api.multi
    def search_pages(self, needle=None, limit=None):
        name = re.sub(r"^/p(a(g(e(/(w(e(b(s(i(t(e(\.)?)?)?)?)?)?)?)?)?)?)?)?", "", needle or "")
        res = []
        for page in self.enumerate_pages(query_string=name):
            if needle in page['loc']:
                res.append(page)
                if len(res) == limit:
                    break
        return res

    @api.multi
    def kanban(self, model, domain, column, template, step=None, scope=None, orderby=None):
        step = step and int(step) or 10
        scope = scope and int(scope) or 5
        orderby = orderby or "name"

        get_args = dict(request.httprequest.args or {})
        model_obj = self.env[model]
        relation = model_obj._columns.get(column)._obj
        relation_obj = self.env[relation]

        get_args.setdefault('kanban', "")
        kanban = get_args.pop('kanban')
        kanban_url = "?%s&kanban=" % werkzeug.url_encode(get_args)

        pages = {}
        for col in kanban.split(","):
            if col:
                col = col.split("-")
                pages[int(col[0])] = int(col[1])

        objects = []
        for group in model_obj.read_group(domain, ["id", column], groupby=column):
            obj = {}

            # browse column
            relation_id = group[column][0]
            obj['column_id'] = relation_obj.browse(relation_id)

            obj['kanban_url'] = kanban_url
            for k, v in pages.items():
                if k != relation_id:
                    obj['kanban_url'] += "%s-%s" % (k, v)

            # pager
            number = model_obj.search_count(group['__domain'])
            obj['page_count'] = int(math.ceil(float(number) / step))
            obj['page'] = pages.get(relation_id) or 1
            if obj['page'] > obj['page_count']:
                obj['page'] = obj['page_count']
            offset = (obj['page']-1) * step
            obj['page_start'] = max(obj['page'] - int(math.floor((scope-1)/2)), 1)
            obj['page_end'] = min(obj['page_start'] + (scope-1), obj['page_count'])

            # view data
            obj['domain'] = group['__domain']
            obj['model'] = model
            obj['step'] = step
            obj['orderby'] = orderby

            # browse objects
            obj['object_ids'] = model_obj.search(group['__domain'], limit=step, offset=offset, order=orderby)

            objects.append(obj)

        values = {
            'objects': objects,
            'range': range,
            'template': template,
        }
        return request.website._render("website.kanban_contain", values)

    @api.multi
    def kanban_col(self, model, domain, page, template, step, orderby):
        html = ""
        model_obj = self.env[model]
        domain = safe_eval(domain)
        step = int(step)
        offset = (int(page)-1) * step
        objects = model_obj.search(domain, limit=step, offset=offset, order=orderby)
        for object_id in objects:
            html += request.website._render(template, {'object_id': object_id})
        return html

    def _image_placeholder(self, response):
        # file_open may return a StringIO. StringIO can be closed but are
        # not context managers in Python 2 though that is fixed in 3
        with contextlib.closing(openerp.tools.misc.file_open(
                os.path.join('web', 'static', 'src', 'img', 'placeholder.png'),
                mode='rb')) as f:
            response.data = f.read()
            return response.make_conditional(request.httprequest)

    @api.model
    def _image(self, model, id, field, response, max_width=maxint, max_height=maxint, cache=None):
        """ Fetches the requested field and ensures it does not go above
        (max_width, max_height), resizing it if necessary.

        Resizing is bypassed if the object provides a $field_big, which will
        be interpreted as a pre-resized version of the base field.

        If the record is not found or does not have the requested field,
        returns a placeholder image via :meth:`~._image_placeholder`.

        Sets and checks conditional response parameters:
        * :mailheader:`ETag` is always set (and checked)
        * :mailheader:`Last-Modified is set iif the record has a concurrency
          field (``__last_update``)

        The requested field is assumed to be base64-encoded image data in
        all cases.
        """
        Model = self.env[model]
        id = int(id)

        ids = Model.search([('id', '=', id)])
        if not ids and 'website_published' in Model._fields:
            ids = Model.sudo().search(
                               [('id', '=', id), ('website_published', '=', True)])
        if not ids:
            return self._image_placeholder(response)

        concurrency = '__last_update'
        [record] = Model.sudo().browse([id]).read([concurrency, field])
        if concurrency in record:
            server_format = openerp.tools.misc.DEFAULT_SERVER_DATETIME_FORMAT
            try:
                response.last_modified = datetime.datetime.strptime(
                    record[concurrency], server_format + '.%f')
            except ValueError:
                # just in case we have a timestamp without microseconds
                response.last_modified = datetime.datetime.strptime(
                    record[concurrency], server_format)

        # Field does not exist on model or field set to False
        if not record.get(field):
            # FIXME: maybe a field which does not exist should be a 404?
            return self._image_placeholder(response)

        response.set_etag(hashlib.sha1(record[field]).hexdigest())
        response.make_conditional(request.httprequest)

        if cache:
            response.cache_control.max_age = cache
            response.expires = int(time.time() + cache)

        # conditional request match
        if response.status_code == 304:
            return response

        if model == 'ir.attachment' and field == 'url' and field in record:
            path = record[field].strip('/')

            # Check that we serve a file from within the module
            if os.path.normpath(path).startswith('..'):
                return self._image_placeholder(response)

            # Check that the file actually exists
            path = path.split('/')
            resource = openerp.modules.get_module_resource(*path)
            if not resource:
                return self._image_placeholder(response)

            data = open(resource, 'rb').read()
        else:
            data = record[field].decode('base64')
        image = Image.open(cStringIO.StringIO(data))
        response.mimetype = Image.MIME[image.format]

        filename = '%s_%s.%s' % (model.replace('.', '_'), id, str(image.format).lower())
        response.headers['Content-Disposition'] = 'inline; filename="%s"' % filename

        if (not max_width) and (not max_height):
            response.data = data
            return response

        w, h = image.size
        max_w = int(max_width) if max_width else maxint
        max_h = int(max_height) if max_height else maxint

        if w < max_w and h < max_h:
            response.data = data
        else:
            size = (max_w, max_h)
            img = image_resize_and_sharpen(image, size, preserve_aspect_ratio=True)
            image_save_for_web(img, response.stream, format=image.format)
            # invalidate content-length computed by make_conditional as
            # writing to response.stream does not do it (as of werkzeug 0.9.3)
            del response.headers['Content-Length']

        return response

    @api.model
    def image_url(self, record, field, size=None):
        """Returns a local url that points to the image field of a given browse record."""
        model = record._name
        sudo_record = record.sudo()
        id = '%s_%s' % (record.id, hashlib.sha1(sudo_record.write_date or sudo_record.create_date or '').hexdigest()[0:7])
        size = '' if size is None else '/%s' % size
        return '/website/image/%s/%s/%s%s' % (model, id, field, size)

class WebsiteMenu(models.Model):
    _name = "website.menu"
    _description = "Website Menu"

    def __defaults_sequence(self):
        menu = self.search_read([(1,"=",1)], ["sequence"], limit=1, order="sequence DESC")
        return menu and menu[0]["sequence"] or 0

    name = fields.Char('Menu', required=True, translate=True)
    url = fields.Char(default='')
    new_window = fields.Boolean('New Window', default=False)
    sequence = fields.Integer(default=__defaults_sequence)
    # TODO: support multiwebsite once done for ir.ui.views
    website_id = fields.Many2one('website', 'Website')
    parent_id = fields.Many2one('website.menu', 'Parent Menu', select=True, ondelete="cascade")
    child_id = fields.One2many('website.menu', 'parent_id', string='Child Menus')
    parent_left = fields.Integer('Parent Left', select=True)
    parent_right = fields.Integer('Parent Right', select=True)

    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

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
            if isinstance(mid, str):
                new_id = self.create({'name': menu['name']}).id
                replace_id(mid, new_id)
        for menu in data['data']:
            self.browse([menu['id']]).write(menu)
        return True


class IrAttachment(models.Model):

    _inherit = "ir.attachment"

    @api.multi
    def _website_url_get(self):
        for attach in self:
            if attach.url:
                attach.website_url = attach.url
            else:
                attach.website_url = self.env['website'].image_url(attach, 'datas')

    @api.multi
    def _datas_big(self):
        if self.env.context and self.env.context.get('bin_size'):
            return False

        for record in self:
            if record.res_model != 'ir.ui.view' or not record.datas: continue
            try:
                record.datas_big = openerp.tools.image_resize_image_big(record.datas)
            except IOError: # apparently the error PIL.Image.open raises
                pass

    website_url = fields.Char(compute='_website_url_get', string="Attachment URL")
    datas_big = fields.Binary (compute='_datas_big', store=True, string="Resized file content")

    @api.multi
    def try_remove(self):
        """ Removes a web-based image attachment if it is used by no view
        (template)

        Returns a dict mapping attachments which would not be removed (if any)
        mapped to the views preventing their removal
        """
        Views = self.env['ir.ui.view']
        attachments_to_remove = []
        # views blocking removal of the attachment
        removal_blocked_by = {}

        for attachment in self:
            # in-document URLs are html-escaped, a straight search will not
            # find them
            url = escape(attachment.website_url)
            view_exist = Views.search(["|", ('arch_db', 'like', '"%s"' % url), ('arch_db', 'like', "'%s'" % url)])

            if view_exist:
                 removal_blocked_by[attachment.id] = [{'id': view_exist.id, 'name':view_exist.name }]
            else:
                attachments_to_remove.append(attachment.id)
        if attachments_to_remove:
            self.browse(attachments_to_remove).unlink()
        return removal_blocked_by

class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        params = {
            'center': '%s, %s %s, %s' % (self.street or '', self.city or '', self.zip or '', self.country_id and self.country_id.name_get()[0][1] or ''),
            'size': "%sx%s" % (height, width),
            'zoom': zoom,
            'sensor': 'false',
        }
        return urlplus('//maps.googleapis.com/maps/api/staticmap' , params)

    @api.multi
    def google_map_link(self, zoom=8):
        params = {
            'q': '%s, %s %s, %s' % (self.street or '', self.city  or '', self.zip or '', self.country_id and self.country_id.name_get()[0][1] or ''),
            'z': 10
        }
        return urlplus('https://maps.google.com/maps' , params)

class ResCompany(models.Model):
    _inherit = "res.company"
    @api.multi
    def google_map_img(self, zoom=8, width=298, height=298):
        partner = self.sudo().partner_id
        return partner and partner.google_map_img(zoom, width, height) or None
    @api.multi
    def google_map_link(self, zoom=8):
        partner = self.sudo().partner_id
        return partner and partner.google_map_link(zoom) or None

class BaseLanguageInstall(models.TransientModel):
    _inherit = "base.language.install"

    website_ids = fields.Many2many('website', string='Websites to translate')

    @api.model
    def default_get(self, fields):
        defaults = super(BaseLanguageInstall, self).default_get(fields)
        website_id = self.env.context.get('params', {}).get('website_id')
        if website_id:
            if 'website_ids' not in defaults:
                defaults['website_ids'] = []
            defaults['website_ids'].append(website_id)
        return defaults

    @api.multi
    def lang_install(self):
        action = super(BaseLanguageInstall, self).lang_install()
        website_ids = [website.id for website in self.website_ids]
        lang_id = self.env['res.lang'].search([('code', '=', self.lang)]).id
        if website_ids and lang_id:
            data = {'language_ids': [(4, lang_id)]}
            self.env['website'].browse(website_ids).write(data)
        params = self.env.context.get('params', {})
        if 'url_return' in params:
            return {
                'url': params['url_return'].replace('[lang]', self.lang),
                'type': 'ir.actions.act_url',
                'target': 'self'
            }
        return action

class WebsiteSeoMetadata(models.Model):
    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    website_meta_title = fields.Char("Website meta title", translate=True)
    website_meta_description = fields.Text("Website meta description", translate=True)
    website_meta_keywords = fields.Char("Website meta keywords", translate=True)


class WebsitePublishedMixin(models.AbstractModel):
    _name = "website.published.mixin"

    website_published = fields.Boolean('Visible in Website', copy=False)
    website_url = fields.Char(compute='_website_url', string='Website URL',
                                    help='The full URL to access the document through the website.')

    @api.multi
    def _website_url(self):
        for res in self:
            res.website_url = '#'

    @api.multi
    def open_website_url(self):
        return {
            'type': 'ir.actions.act_url',
            'url': self.website_url,
            'target': 'self',
        }
