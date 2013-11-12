# -*- coding: utf-8 -*-
import fnmatch
import functools
import inspect
import logging
import math
import itertools
import traceback
import urllib
import urlparse

import simplejson
import werkzeug
import werkzeug.exceptions
import werkzeug.wrappers

import openerp
from openerp.exceptions import AccessError, AccessDenied
from openerp.osv import orm, osv, fields
from openerp.tools.safe_eval import safe_eval

from openerp.addons.web import http
from openerp.addons.web.http import request


logger = logging.getLogger(__name__)

def route(routes, *route_args, **route_kwargs):
    def decorator(f):
        new_routes = routes if isinstance(routes, list) else [routes]
        f.cms = True
        f.multilang = route_kwargs.get('multilang', False)
        if f.multilang:
            route_kwargs.pop('multilang')
            for r in list(new_routes):
                new_routes.append('/<string(length=5):lang_code>' + r)
        @http.route(new_routes, *route_args, **route_kwargs)
        @functools.wraps(f, assigned=functools.WRAPPER_ASSIGNMENTS + ('func_name',))
        def wrap(*args, **kwargs):
            request.route_lang = kwargs.get('lang_code', None)
            if not hasattr(request, 'website'):
                request.multilang = f.multilang
                # TODO: Select website, currently hard coded
                request.website = request.registry['website'].browse(
                    request.cr, request.uid, 1, context=request.context)

                if request.route_lang:
                    lang_ok = [lg.code for lg in request.website.language_ids if lg.code == request.route_lang]
                    if not lang_ok:
                        return request.not_found()
                request.website.preprocess_request(request)
            return f(*args, **kwargs)
        return wrap
    return decorator

def url_for(path_or_uri, lang=None, keep_query=None):
    location = path_or_uri.strip()
    url = urlparse.urlparse(location)
    if request and not url.netloc and not url.scheme:
        location = urlparse.urljoin(request.httprequest.path, location)
        langs = request.context.get('langs')
        if location[0] == '/' and (len(langs) > 1 or lang):
            ps = location.split('/')
            lang = lang or request.context.get('lang')
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

def urlplus(url, params):
    if not params:
        return url

    # can't use urlencode because it encodes to (ascii, replace) in p2
    return "%s?%s" % (url, '&'.join(
        k + '=' + urllib.quote_plus(v.encode('utf-8') if isinstance(v, unicode) else str(v))
        for k, v in params.iteritems()
    ))

class website(osv.osv):
    _name = "website" # Avoid website.website convention for conciseness (for new api). Got a special authorization from xmo and rco
    _description = "Website"
    _columns = {
        'name': fields.char('Domain'),
        'company_id': fields.many2one('res.company', string="Company"),
        'language_ids': fields.many2many('res.lang', 'website_lang_rel', 'website_id', 'lang_id', 'Languages'),
        'default_lang_id': fields.many2one('res.lang', string="Default language"),
        'social_twitter': fields.char('Twitter Account'),
        'social_facebook': fields.char('Facebook Account'),
        'social_github': fields.char('GitHub Account'),
        'social_linkedin': fields.char('LinkedIn Account'),
        'social_youtube': fields.char('Youtube Account'),
        'social_googleplus': fields.char('Google+ Account'),
    }

    public_user = None

    def get_public_user(self, cr, uid, context=None):
        if not self.public_user:
            uid = openerp.SUPERUSER_ID
            ref = self.pool['ir.model.data'].get_object_reference(cr, uid, 'website', 'public_user')
            self.public_user = self.pool[ref[0]].browse(cr, uid, ref[1])
        return self.public_user

    def preprocess_request(self, cr, uid, ids, request, context=None):
        def redirect(url):
            return werkzeug.utils.redirect(url_for(url))
        request.redirect = redirect

        is_public_user = request.uid == self.get_public_user(cr, uid, context).id

        # Select current language
        if hasattr(request, 'route_lang'):
            lang = request.route_lang
        else:
            lang = request.params.get('lang', None) or request.httprequest.cookies.get('lang', None)
        if lang not in [lg.code for lg in request.website.language_ids]:
            lang = request.website.default_lang_id.code

        is_master_lang = lang == request.website.default_lang_id.code
        request.context.update({
            'lang': lang,
            'lang_selected': [lg for lg in request.website.language_ids if lg.code == lang],
            'langs': [lg.code for lg in request.website.language_ids],
            'multilang': request.multilang,
            'is_public_user': is_public_user,
            'is_master_lang': is_master_lang,
            'editable': not is_public_user,
            'translatable': not is_public_user and not is_master_lang and request.multilang,
        })

    def render(self, cr, uid, ids, template, values=None, context=None):
        view = self.pool.get("ir.ui.view")
        IMD = self.pool.get("ir.model.data")
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
            res_company=request.website.company_id,
            user_id=user.browse(cr, uid, uid),
        )

        context.update(
            inherit_branding=qweb_context.setdefault('editable', False),
        )

        view_ref = None
        # check if xmlid of the template exists
        try:
            module, xmlid = template.split('.', 1)
            view_ref = IMD.get_object_reference(cr, uid, module, xmlid)
        except ValueError: # catches both unpack errors and gor errors
            module, xmlid = 'website', template
            try:
                view_ref = IMD.get_object_reference(cr, uid, module, xmlid)
            except ValueError:
                return self.error(cr, uid, 404, qweb_context, context=context)

        if 'main_object' not in qweb_context:
            try:
                main_object = self.pool[view_ref[0]].browse(cr, uid, view_ref[1])
                qweb_context['main_object'] = main_object
            except Exception:
                pass

        try:
            return view.render(
                cr, uid, "%s.%s" % (module, xmlid), qweb_context,
                engine='website.qweb', context=context)
        except (AccessError, AccessDenied), err:
            logger.error(err)
            qweb_context['error'] = err[1]
            logger.warn("Website Rendering Error.\n\n%s" % traceback.format_exc())
            return self.error(cr, uid, 401, qweb_context, context=context)
        except Exception, e:
            qweb_context['template'] = getattr(e, 'qweb_template', '')
            node = getattr(e, 'qweb_node', None)
            qweb_context['node'] = node and node.toxml()
            qweb_context['expr'] = getattr(e, 'qweb_eval', '')
            qweb_context['traceback'] = traceback.format_exc()
            logger.exception("Website Rendering Error.\n%(template)s\n%(expr)s\n%(node)s" % qweb_context)
            return self.error(cr, uid, 500 if qweb_context['editable'] else 404,
                              qweb_context, context=context)

    def error(self, cr, uid, code, qweb_context, context=None):
        View = request.registry['ir.ui.view']
        return werkzeug.wrappers.Response(
            View.render(cr, uid, 'website.%d' % code, qweb_context),
            status=code,
            content_type='text/html;charset=utf-8')

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

        return (
                'GET' in methods
            and endpoint.exposed == 'http'
            and endpoint.auth in ('none', 'public')
            and getattr(endpoint, 'cms', False)
            # ensure all converters on the rule are able to generate values for
            # themselves
            and all(hasattr(converter, 'generate')
                    for converter in rule._converters.itervalues())
        ) and self.endpoint_is_enumerable(rule)

    def endpoint_is_enumerable(self, rule):
        """ Verifies that it's possible to generate a valid url for the rule's
        endpoint

        :type rule: werkzeug.routing.Rule
        :rtype: bool
        """

        # apparently the decorator package makes getargspec work correctly
        # on functions it decorates. That's not the case for
        # @functools.wraps, so hack around to get the original function
        # (and hope a single decorator was applied or we're hosed)
        # FIXME: this is going to blow up if we want/need to use multiple @route (with various configurations) on a method
        undecorated_func = rule.endpoint.func_closure[0].cell_contents

        # If this is ever ported to py3, use signatures, it doesn't suck as much
        spec = inspect.getargspec(undecorated_func)

        # if *args or **kwargs, just bail the fuck out, only dragons can
        # live there
        if spec.varargs or spec.keywords:
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

    def list_pages(self, cr, uid, ids, context=None):
        """ Available pages in the website/CMS. This is mostly used for links
        generation and can be overridden by modules setting up new HTML
        controllers for dynamic pages (e.g. blog).

        By default, returns template views marked as pages.

        :returns: a list of mappings with two keys: ``name`` is the displayable
                  name of the resource (page), ``url`` is the absolute URL
                  of the same.
        :rtype: list({name: str, url: str})
        """

        router = request.httprequest.app.get_db_router(request.db)

        for rule in router.iter_rules():
            if not self.rule_is_enumerable(rule):
                continue

            generated = map(dict, itertools.product(*(
                itertools.izip(itertools.repeat(name), converter.generate())
                for name, converter in rule._converters.iteritems()
            )))

            for values in generated:
                # rule.build returns (domain_part, rel_url)
                url = rule.build(values, append_unknown=False)[1]
                yield {'name': url, 'url': url }

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
        return request.website.render("website.kanban_contain", values)

    def kanban_col(self, cr, uid, ids, model, domain, page, template, step, orderby, context=None):
        html = ""
        model_obj = self.pool[model]
        domain = safe_eval(domain)
        step = int(step)
        offset = (int(page)-1) * step
        object_ids = model_obj.search(cr, uid, domain, limit=step, offset=offset, order=orderby)
        object_ids = model_obj.browse(cr, uid, object_ids)
        for object_id in object_ids:
            html += request.website.render(template, {'object_id': object_id})
        return html

    def get_menu(self, cr, uid, ids, context=None):
        return self.pool['website.menu'].get_menu(cr, uid, ids[0], context=context)

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
    }
    _parent_store = True
    _parent_order = 'sequence, name'
    _order = "parent_left"

    def get_menu(self, cr, uid, website_id, context=None):
        root_domain = [('parent_id', '=', False)] # ('website_id', '=', website_id),
        menu_ids = self.search(cr, uid, root_domain, context=context)
        menu = self.browse(cr, uid, menu_ids, context=context)
        return menu[0]

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
        menu = self.get_menu(cr, uid, website_id, context=context)
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
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).parent_id
        return partner and partner.google_map_img(zoom, width, height, context=context) or None
    def google_map_link(self, cr, uid, ids, zoom=8, context=None):
        partner = self.browse(cr, openerp.SUPERUSER_ID, ids[0], context=context).parent_id
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
