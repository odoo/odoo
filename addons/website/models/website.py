# -*- coding: utf-8 -*-
import fnmatch
import functools
import inspect
import logging
import math
import itertools
import urllib
import urlparse

import simplejson
import werkzeug
import werkzeug.exceptions
import werkzeug.wrappers

import openerp
from openerp.osv import orm, osv, fields
from openerp.tools.safe_eval import safe_eval

from openerp.addons.web import http
from openerp.addons.web.http import request, LazyResponse
from ..utils import slugify

logger = logging.getLogger(__name__)

def route(routes, *route_args, **route_kwargs):
    def decorator(f):
        f.cms = True
        f.multilang = route_kwargs.pop('multilang', False)
        return http.route(routes, *route_args, **route_kwargs)(f)
    return decorator

def url_for(path_or_uri, lang=None, keep_query=None):
    location = path_or_uri.strip()
    url = urlparse.urlparse(location)
    if request and not url.netloc and not url.scheme:
        location = urlparse.urljoin(request.httprequest.path, location)
        lang = lang or request.context.get('lang')
        langs = [lg[0] for lg in request.website.get_languages()]
        if location[0] == '/' and len(langs) > 1 and lang != request.website.default_lang_code:
            ps = location.split('/')
            if ps[1] in langs:
                ps[1] = lang
            else:
                ps.insert(1, lang)
            location = '/'.join(ps)
        if keep_query:
            url = urlparse.urlparse(location)
            location = url.path
            params = werkzeug.url_decode(url.query)
            query_params = frozenset(werkzeug.url_decode(request.httprequest.query_string).keys())
            for kq in keep_query:
                for param in fnmatch.filter(query_params, kq):
                    params[param] = request.params[param]
            params = werkzeug.urls.url_encode(params)
            if params:
                location += '?%s' % params

    return location

def slug(value):
    if isinstance(value, orm.browse_record):
        # [(id, name)] = value.name_get()
        id, name = value.id, value[value._rec_name]
    else:
        # assume name_search result tuple
        id, name = value
    return "%s-%d" % (slugify(name), id)

def urlplus(url, params):
    if not params:
        return url

    # can't use urlencode because it encodes to (ascii, replace) in p2
    return "%s?%s" % (url, '&'.join(
        k + '=' + urllib.quote_plus(v.encode('utf-8') if isinstance(v, unicode) else str(v))
        for k, v in params.iteritems()
    ))

def quote_plus(value):
    return urllib.quote_plus(value.encode('utf-8') if isinstance(value, unicode) else str(value))

def preload_records(*args, **kwargs):
    """ This helper allows to check the existence and prefetch one or many browse_records at once.
        If the browse record(s) does not exists in the db it will raise a LazyResponse
    """
    field = kwargs.pop('field', 'name')
    on_error = kwargs.pop('on_error', 'website.404')
    error_code = kwargs.pop('error_code', 404)
    try:
        for arg in args:
            if isinstance(arg, orm.browse_record):
                arg[field]
            elif isinstance(arg, orm.browse_record_list):
                [record[field] for record in arg]
    except:
        lazy_error = request.website.render(on_error, status_code=error_code)
        raise werkzeug.exceptions.HTTPException(response=lazy_error)

class website(osv.osv):
    def _get_menu_website(self, cr, uid, ids, context=None):
        # IF a menu is changed, update all websites
        return self.search(cr, uid, [], context=context)
        
    def _get_menu(self, cr, uid, ids, name, arg, context=None):
        root_domain = [('parent_id', '=', False)]
        menus = self.pool.get('website.menu').search(cr, uid, root_domain, order='id', context=context)
        menu = menus and menus[0] or False
        return dict( map(lambda x: (x, menu), ids) )

    def _get_public_user(self, cr, uid, ids, name='public_user', arg=(), context=None):
        ref = self.get_public_user(cr, uid, context=context)
        return dict( map(lambda x: (x, ref), ids) )

    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"
    _columns = {
        'name': fields.char('Domain'),
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
        'public_user': fields.function(_get_public_user, relation='res.users', type='many2one', string='Public User'),
        'menu_id': fields.function(_get_menu, relation='website.menu', type='many2one', string='Main Menu',
            store= {
                'website.menu': (_get_menu_website, ['sequence','parent_id','website_id'], 10)
            })
    }

    def write(self, cr, uid, ids, vals, context=None):
        self._get_languages.clear_cache(self)
        return super(website, self).write(cr, uid, ids, vals, context)

    def new_page(self, cr, uid, name, template='website.default_page', ispage=True, context=None):
        context=context or {}
        # completely arbitrary max_length
        idname = slugify(name, max_length=50)

        imd = self.pool.get('ir.model.data')
        view = self.pool.get('ir.ui.view')

        module, tmp_page = template.split('.')
        view_model, view_id = imd.get_object_reference(cr, uid, module, tmp_page)

        cr.execute('SAVEPOINT new_page')
        try:
            newview_id = view.copy(cr, uid, view_id, context=context)
            newview = view.browse(cr, uid, newview_id, context=context)
            newview.write({
                'arch': newview.arch.replace(template, "%s.%s" % (module, idname)),
                'name': name,
                'page': ispage,
            })
            imd.create(cr, uid, {
                'name': idname,
                'module': module,
                'model': 'ir.ui.view',
                'res_id': newview_id,
                'noupdate': True
            }, context=context)
            cr.execute('RELEASE SAVEPOINT new_page')
            return "%s.%s" % (module, idname)
        except:
            cr.execute("ROLLBACK TO SAVEPOINT new_page")
            raise

    def page_for_name(self, cr, uid, ids, name, module='website', context=None):
        # whatever
        return '%s.%s' % (module, slugify(name, max_length=50))

    def page_exists(self, cr, uid, ids, name, module='website', context=None):
        page = self.page_for_name(cr, uid, ids, name, module=module, context=context)

        try:
            return self.get_template(
                cr, uid, ids, template=page, context=context
            ).exists()
        except:
            return False

    def get_public_user(self, cr, uid, context=None):
        uid = openerp.SUPERUSER_ID
        res = self.pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'public_user')
        return res and res[1] or False

    @openerp.tools.ormcache(skiparg=3)
    def _get_languages(self, cr, uid, id, context=None):
        website = self.browse(cr, uid, id)
        return [(lg.code, lg.name) for lg in website.language_ids]
    def get_languages(self, cr, uid, ids, context=None):
        return self._get_languages(cr, uid, ids[0])

    def get_current_website(self, cr, uid, context=None):
        # TODO: Select website, currently hard coded
        return self.pool['website'].browse(cr, uid, 1, context=context)

    def preprocess_request(self, cr, uid, ids, request, context=None):
        # TODO FP: is_website_publisher and editable in context should be removed
        # for performance reasons (1 query per image to load) but also to be cleaner
        # I propose to replace this by a group 'base.group_website_publisher' on the
        # view that requires it.
        Access = request.registry['ir.model.access']
        is_website_publisher = Access.check(cr, uid, 'ir.ui.view', 'write', False, context)

        lang = request.context['lang']
        is_master_lang = lang == request.website.default_lang_code

        request.redirect = lambda url: werkzeug.utils.redirect(url_for(url))
        request.context.update(
            is_master_lang=is_master_lang,
            editable=is_website_publisher,
            translatable=not is_master_lang,
        )

    def get_template(self, cr, uid, ids, template, context=None):
        IMD = self.pool["ir.model.data"]
        try:
            module, xmlid = template.split('.', 1)
            model, id = IMD.get_object_reference(cr, uid, module, xmlid)
        except ValueError: # catches both unpack errors and gor errors
            module, xmlid = 'website', template
            model, id = IMD.get_object_reference(cr, uid, module, xmlid)
        return self.pool["ir.ui.view"].browse(cr, uid, id, context=context)

    def _render(self, cr, uid, ids, template, values=None, context=None):
        user = self.pool.get("res.users")
        if not context:
            context = {}

        qweb_context = context.copy()

        if values:
            qweb_context.update(values)

        qweb_context.update(
            request=request, # TODO maybe rename to _request to mark this attribute as unsafe
            json=simplejson,
            website=request.website,
            url_for=url_for,
            slug=slug,
            res_company=request.website.company_id,
            user_id=user.browse(cr, uid, uid),
            quote_plus=quote_plus,
        )

        context.update(
            inherit_branding=qweb_context.setdefault('editable', False),
        )

        view = self.get_template(cr, uid, ids, template)

        if 'main_object' not in qweb_context:
            qweb_context['main_object'] = view
        #context['debug'] = True
        result = view.render(qweb_context, engine='website.qweb', context=context)
        return result

    def render(self, cr, uid, ids, template, values=None, status_code=None, context=None):
        def callback(template, values, context):
            return self._render(cr, uid, ids, template, values, context)
        if values is None:
            values = {}
        return LazyResponse(callback, status_code=status_code, template=template, values=values, context=context)

    def pager(self, cr, uid, ids, url, total, page=1, step=30, scope=5, url_args=None, context=None):
        # Compute Pager
        page_count = int(math.ceil(float(total) / step))

        page = max(1, min(int(page), page_count))
        scope -= 1

        pmin = max(page - int(math.floor(scope/2)), 1)
        pmax = min(pmin + scope, page_count)

        if pmax - pmin < scope:
            pmin = pmax - scope if pmax - scope > 0 else 1

        def get_url(page):
            _url = "%spage/%s/" % (url, page)
            if url_args:
                _url = "%s?%s" % (_url, urllib.urlencode(url_args))
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
        methods = rule.methods or ['GET']
        converters = rule._converters.values()

        return (
                'GET' in methods
            and endpoint.exposed == 'http'
            and endpoint.auth in ('none', 'public')
            and getattr(endpoint, 'cms', False)
            # preclude combinatorial explosion by only allowing a single converter
            and len(converters) <= 1
            # ensure all converters on the rule are able to generate values for
            # themselves
            and all(hasattr(converter, 'generate') for converter in converters)
        ) and self.endpoint_is_enumerable(rule)

    def endpoint_is_enumerable(self, rule):
        """ Verifies that it's possible to generate a valid url for the rule's
        endpoint

        :type rule: werkzeug.routing.Rule
        :rtype: bool
        """
        spec = inspect.getargspec(rule.endpoint)

        # if *args bail the fuck out, only dragons can live there
        if spec.varargs:
            return False

        # remove all arguments with a default value from the list
        defaults_count = len(spec.defaults or []) # spec.defaults can be None
        # a[:-0] ~ a[:0] ~ [] -> replace defaults_count == 0 by None to get
        # a[:None] ~ a
        args = spec.args[:(-defaults_count or None)]

        # params with defaults were removed, leftover allowed are:
        # * self (technically should be first-parameter-of-instance-method but whatever)
        # * any parameter mapping to a converter
        return all(
            (arg == 'self' or arg in rule._converters)
            for arg in args)

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
        uid = self.get_public_user(cr, uid, context=context)
        for rule in router.iter_rules():
            if not self.rule_is_enumerable(rule):
                continue

            converters = rule._converters
            filtered = bool(converters)
            if converters:
                # allow single converter as decided by fp, checked by
                # rule_is_enumerable
                [(name, converter)] = converters.items()
                converter_values = converter.generate(
                    request.cr, uid, query=query_string, context=context)
                generated = ({k: v} for k, v in itertools.izip(
                    itertools.repeat(name), converter_values))
            else:
                # force single iteration for literal urls
                generated = [{}]

            for values in generated:
                domain_part, url = rule.build(values, append_unknown=False)
                page = {'name': url, 'url': url}

                if not filtered and query_string and not self.page_matches(cr, uid, page, query_string, context=context):
                    continue
                yield page

    def search_pages(self, cr, uid, ids, needle=None, limit=None, context=None):
        return list(itertools.islice(
            self.enumerate_pages(cr, uid, ids, query_string=needle, context=context),
            limit))

    def page_matches(self, cr, uid, page, needle, context=None):
        """ Checks that a "page" matches a user-provide search string.

        The default implementation attempts to perform a non-contiguous
        substring match of the page's name.

        :param page: {'name': str, 'url': str}
        :param needle: str
        :rtype: bool
        """
        haystack = page['name'].lower()

        needle = iter(needle.lower())
        n = next(needle)
        end = object()

        for char in haystack:
            if char != n: continue

            n = next(needle, end)
            # found all characters of needle in haystack in order
            if n is end:
                return True

        return False

    def kanban(self, cr, uid, ids, model, domain, column, template, step=None, scope=None, orderby=None, context=None):
        step = step and int(step) or 10
        scope = scope and int(scope) or 5
        orderby = orderby or "name"

        get_args = dict(request.httprequest.args or {})
        model_obj = self.pool[model]
        relation = model_obj._columns.get(column)._obj
        relation_obj = self.pool[relation]

        get_args.setdefault('kanban', "")
        kanban = get_args.pop('kanban')
        kanban_url = "?%s&kanban=" % urllib.urlencode(get_args)

        pages = {}
        for col in kanban.split(","):
            if col:
                col = col.split("-")
                pages[int(col[0])] = int(col[1])

        objects = []
        for group in model_obj.read_group(cr, uid, domain, ["id", column], groupby=column):
            obj = {}

            # browse column
            relation_id = group[column][0]
            obj['column_id'] = relation_obj.browse(cr, uid, relation_id)

            obj['kanban_url'] = kanban_url
            for k, v in pages.items():
                if k != relation_id:
                    obj['kanban_url'] += "%s-%s" % (k, v)

            # pager
            number = model_obj.search(cr, uid, group['__domain'], count=True)
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
            object_ids = model_obj.search(cr, uid, group['__domain'], limit=step, offset=offset, order=orderby)
            obj['object_ids'] = model_obj.browse(cr, uid, object_ids)

            objects.append(obj)

        values = {
            'objects': objects,
            'range': range,
            'template': template,
        }
        return request.website._render("website.kanban_contain", values)

    def kanban_col(self, cr, uid, ids, model, domain, page, template, step, orderby, context=None):
        html = ""
        model_obj = self.pool[model]
        domain = safe_eval(domain)
        step = int(step)
        offset = (int(page)-1) * step
        object_ids = model_obj.search(cr, uid, domain, limit=step, offset=offset, order=orderby)
        object_ids = model_obj.browse(cr, uid, object_ids)
        for object_id in object_ids:
            html += request.website._render(template, {'object_id': object_id})
        return html


class website_menu(osv.osv):
    _name = "website.menu"
    _description = "Website Menu"
    _columns = {
        'name': fields.char('Menu', size=64, required=True, translate=True),
        'url': fields.char('Url', required=True, translate=True),
        'new_window': fields.boolean('New Window'),
        'sequence': fields.integer('Sequence'),
        # TODO: support multiwebsite once done for ir.ui.views
        'website_id': fields.many2one('website', 'Website'),
        'parent_id': fields.many2one('website.menu', 'Parent Menu', select=True, ondelete="cascade"),
        'child_id': fields.one2many('website.menu', 'parent_id', string='Child Menus'),
        'parent_left': fields.integer('Parent Left', select=True),
        'parent_right': fields.integer('Parent Right', select=True),
    }
    _defaults = {
        'url': '',
        'sequence': 0,
        'new_window': False,
    }
    _parent_store = True
    _parent_order = 'sequence'
    _order = "sequence"

    # would be better to take a menu_id as argument
    def get_tree(self, cr, uid, website_id, context=None):
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
            if isinstance(mid, str):
                new_id = self.create(cr, uid, {'name': menu['name']}, context=context)
                replace_id(mid, new_id)
        for menu in data['data']:
            self.write(cr, uid, [menu['id']], menu, context=context)
        return True

class ir_attachment(osv.osv):
    _inherit = "ir.attachment"
    def _website_url_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.type == 'url':
                result[attach.id] = attach.url
            else:
                result[attach.id] = urlplus('/website/image', {
                    'model': 'ir.attachment',
                    'field': 'datas',
                    'id': attach.id,
                    'max_width': 1024,
                    'max_height': 768,
                })
        return result
    _columns = {
        'website_url': fields.function(_website_url_get, string="Attachment URL", type='char')
    }

class res_partner(osv.osv):
    _inherit = "res.partner"

    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'center': '%s, %s %s, %s' % (partner.street, partner.city, partner.zip, partner.country_id and partner.country_id.name_get()[0][1] or ''),
            'size': "%sx%s" % (height, width),
            'zoom': zoom,
            'sensor': 'false',
        }
        return urlplus('http://maps.googleapis.com/maps/api/staticmap' , params)

    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, uid, ids[0], context=context)
        params = {
            'q': '%s, %s %s, %s' % (partner.street, partner.city, partner.zip, partner.country_id and partner.country_id.name_get()[0][1] or ''),
        }
        return urlplus('https://maps.google.be/maps' , params)

class res_company(osv.osv):
    _inherit = "res.company"
    def google_map_img(self, cr, uid, ids, zoom=8, width=298, height=298, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_img(zoom, width, height, context=context) or None
    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).partner_id
        return partner and partner.google_map_link(zoom, context=context) or None

class base_language_install(osv.osv):
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

class SeoMetadata(osv.Model):
    _name = 'website.seo.metadata'
    _description = 'SEO metadata'

    _columns = {
        'website_meta_title': fields.char("Website meta title", size=70, translate=True),
        'website_meta_description': fields.text("Website meta description", size=160, translate=True),
        'website_meta_keywords': fields.char("Website meta keywords", translate=True),
    }
