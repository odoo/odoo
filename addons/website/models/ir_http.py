# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
import functools
import logging
import unittest
from zoneinfo import ZoneInfoNotFoundError, ZoneInfo

import werkzeug
from lxml import etree

import odoo
from odoo import api, models
from odoo import SUPERUSER_ID
from odoo.exceptions import AccessError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools.json import scriptsafe as json_scriptsafe
from odoo.tools.safe_eval import safe_eval
from odoo.addons.http_routing.models import ir_http
from odoo.addons.portal.controllers.portal import _build_url_w_params

logger = logging.getLogger(__name__)


def sitemap_qs2dom(qs, route, field='name'):
    """ Convert a query_string (can contains a path) to a domain"""
    if qs and qs.lower() not in route:
        needles = qs.strip('/').split('/')
        # needles will be altered and keep only element which one is not in route
        # diff(from=['shop', 'product'], to=['shop', 'product', 'product']) => to=['product']
        unittest.util.unorderable_list_difference(route.strip('/').split('/'), needles)
        if len(needles) == 1:
            return Domain(field, 'ilike', needles[0])
        else:
            return Domain.FALSE
    return Domain.TRUE


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def routing_map(self, key=None):
        key = self.env.website.id or self.env.context.get('host_id') or None
        return super().routing_map(key=key)

    @classmethod
    def _slug(cls, value: models.BaseModel | tuple[int, str]) -> str:
        try:
            if value.id and value.seo_name:
                return super()._slug((value.id, value.seo_name))
        except AttributeError:
            pass
        return super()._slug(value)

    @classmethod
    def _slug_matching(cls, adapter, endpoint, **kw):
        for arg in kw:
            if isinstance(kw[arg], models.BaseModel):
                kw[arg] = kw[arg].with_context(slug_matching=True)
        qs = request.httprequest.query_string.decode('utf-8')
        return adapter.build(endpoint, kw) + (qs and '?%s' % qs or '')

    @classmethod
    def _url_for(cls, url_from: str, lang_code: str | None = None) -> str:
        ''' Return the url with the rewriting applied.
            Nothing will be done for absolute URL, invalid URL, or short URL from 1 char.

            :param url_from: The URL to convert.
            :param lang_code: Must be the lang `code`. It could also be something
                              else, such as `'[lang]'` (used for url_return).
        '''
        path, sep, qs = (url_from or '').partition('?')

        if not qs:
            path, sep, qs = (url_from or '').partition('#')

        website_id = request.env.website.id or request.env.context['host_id']

        if (
            path
            # don't try to match route if we know that no rewrite has been loaded.
            and request.env['ir.http']._rewrite_len(website_id)
            and (
                len(path) > 1
                and path.startswith('/')
                and '/static/' not in path
                and not path.startswith('/web/')
            )
        ):
            url_from, _ = request.env['ir.http'].url_rewrite(path)
            url_from = url_from if not qs else f"{url_from}{sep}{qs}"

        return super()._url_for(url_from, lang_code)

    @api.ormcache('website_id', cache='routing')
    def _rewrite_len(self, website_id: int) -> int:
        rewrites = self._get_rewrites(website_id)
        return len(rewrites)

    def _get_rewrites(self, website_id):
        domain = (
            Domain('redirect_type', 'in', ('308', '404'))
            & Domain('website_id', 'in', [False, website_id])
        )
        cache = self.env.cr.cache.setdefault('website_rewrites_cache', {})
        rewrites = cache.get(website_id)
        if rewrites is None:
            rewrites = {
                rewrite.url_from: rewrite.sudo(False)
                for rewrite in self.env['website.rewrite'].sudo().search(domain)
            }
            cache[website_id] = rewrites
        return rewrites

    def _generate_routing_rules(self, modules, converters):
        if not request:
            yield from super()._generate_routing_rules(modules, converters)
            return
        website_id = self.env.website.id or self.env.context['host_id']
        logger.debug("_generate_routing_rules for website: %s", website_id)
        rewrites = self._get_rewrites(website_id)
        self._rewrite_len.__cache__.add_value(self, website_id, cache_value=len(rewrites))

        if not rewrites:
            yield from super()._generate_routing_rules(modules, converters)
            return

        for url, endpoint in super()._generate_routing_rules(modules, converters):
            rewrite = rewrites.get(url)
            if rewrite:
                url_to = rewrite.url_to
                if rewrite.redirect_type == '308':
                    logger.debug('Add rule %s for %s' % (url_to, website_id))
                    yield url_to, endpoint  # yield new url

                    if url != url_to:
                        logger.debug('Redirect from %s to %s for website %s' % (url, url_to, website_id))
                        # duplicate the endpoint to only register the redirect_to for this specific url
                        redirect_endpoint = functools.partial(endpoint)
                        functools.update_wrapper(redirect_endpoint, endpoint)
                        _slug_matching = functools.partial(self._slug_matching, endpoint=endpoint)
                        redirect_endpoint.routing = dict(endpoint.routing, redirect_to=_slug_matching)
                        yield url, redirect_endpoint  # yield original redirected to new url
                elif rewrite.redirect_type == '404':
                    logger.debug('Return 404 for %s for website %s' % (url, website_id))
                    continue
            else:
                yield url, endpoint

    @classmethod
    def _get_converters(cls) -> dict[str, type]:
        """ Get the converters list for custom url pattern werkzeug need to
            match Rule. This override adds the website ones.
        """
        return dict(
            super()._get_converters(),
            model=ModelConverter,
        )

    @classmethod
    def _get_public_users(cls):
        public_users = super()._get_public_users()
        website_id = request.env.website.id or request.env.context.get('host_id')
        website = request.env(user=SUPERUSER_ID)['website'].with_context(lang='en_US').browse(website_id)
        if website:
            public_users.append(website.user_id.id)
        return public_users

    @classmethod
    def _auth_method_public(cls, routing: dict):
        """ If no user logged, set the public user of current website, or default
            public user as request uid.
        """
        if not request.session.uid:
            website_id = request.env.context.get('website_id') or request.env.context.get('host_id')
            website = request.env(user=SUPERUSER_ID)['website'].with_context(lang='en_US').browse(website_id)  # sudo
            if website:
                request.update_env(user=website.user_id.id)

        if not request.env.uid:
            super()._auth_method_public(routing)

    @classmethod
    def _match(cls, path):
        def get_current_website_id():
            if force_website_id := request.session.get('force_website_id'):
                if force_website_id in request.env['website'].get_all().ids:
                    return force_website_id
                del request.session['force_website_id']  # it doesn't exist, drop it

            if website_id := request.env.context.get('website_id'):
                if website_id in request.env['website'].get_all().ids:
                    return website_id
            return None

        website_id = get_current_website_id()
        host_id = request.env.context.get('host_id')

        # set website into the context, used by match for the default lang
        if website_id or host_id:
            request.update_context(website_id=website_id or host_id)

        rule, args = super()._match(path)

        if (not rule.endpoint.routing.get('website', False)
            and (website_id or host_id)
        ):
            context = dict(request.env.context)
            context['host_id'] = website_id or host_id
            del context['website_id']
            request.update_env(context=context)

        return rule, args

    @classmethod
    def _pre_dispatch(cls, rule, args):
        super()._pre_dispatch(rule, args)
        website_id = request.env.context.get('website_id') or request.env.context.get('host_id')
        for record in args.values():
            if isinstance(record, models.BaseModel) and 'website_id' in record._fields:
                try:
                    if record.website_id and record.website_id.id != website_id:
                        raise werkzeug.exceptions.NotFound()
                except AccessError:
                    # record.website_id might not be readable as
                    # unpublished `event.event` due to ir.rule, return
                    # 403 instead of using `sudo()` for perfs as this is
                    # low level.
                    raise werkzeug.exceptions.Forbidden()

    @classmethod
    def _get_editor_context(cls):
        ctx = super()._get_editor_context()
        if request.is_frontend_multilang and request.lang == request.env['ir.http']._get_default_lang():
            ctx['edit_translations'] = False
        return ctx

    @classmethod
    def _frontend_pre_dispatch(cls):
        """
        tz, allowed_company_ids, and _get_editor_context() are added in context
        """
        super()._frontend_pre_dispatch()

        if not request.env.context.get('tz') and (tz := request.geoip.location.time_zone):
            with contextlib.suppress(ZoneInfoNotFoundError):
                request.update_context(tz=ZoneInfo(tz).key)

        website = request.env['website'].browse(request.env.context['website_id'])
        user = request.env.user

        # This is mainly to avoid access errors in website controllers
        # where there is no context (eg: /shop), and it's not going to
        # propagate to the global context of the tab. If the company of
        # the website is not in the allowed companies of the user, set
        # the main company of the user.
        context = cls._get_editor_context()
        website_company_id = website.company_id.id
        if user == website.user_id:
            # avoid a read on res_company_user_rel in case of public user
            context['allowed_company_ids'] = [website_company_id]
        elif website_company_id in user._get_company_ids():
            context['allowed_company_ids'] = [website_company_id]
        else:
            context['allowed_company_ids'] = user.company_id.ids

        request.update_context(**context)

    @classmethod
    def _post_dispatch(cls, response):
        super()._post_dispatch(response)

    @api.model
    def _get_default_lang(self):
        website = self.env.website or self.env.website.browse(request.env.context['host_id'])
        if website:
            return self.env['res.lang']._get_data(id=website.default_lang_id.id)
        return super()._get_default_lang()

    @classmethod
    def _get_translation_frontend_modules_name(cls):
        mods = super()._get_translation_frontend_modules_name()
        installed = request.registry._init_modules.union(odoo.tools.config['server_wide_modules'])
        return mods + [mod for mod in installed if 'website' in mod]

    @classmethod
    def _serve_page(cls):
        req_page = request.httprequest.path
        WebsitePage = request.env['website.page'].sudo()
        page_info = WebsitePage._get_page_info(request)

        # redirect to the right url
        if page_info and page_info['url'] != req_page:
            logger.info("Page %r not found, redirecting to existing page %r", req_page, page_info['url'])
            return request.redirect(page_info['url'])

        # redirect without trailing /
        if not page_info and req_page != "/" and req_page.endswith("/"):
            # mimick `_pre_dispatch()` redirect
            path = request.httprequest.path[:-1]
            if request.lang != request.env['ir.http']._get_default_lang():
                path = '/' + request.lang.url_code + path
            if request.httprequest.query_string:
                path += '?' + request.httprequest.query_string.decode('utf-8')
            return request.redirect(path, code=301)

        if page_info:
            if not WebsitePage.env.context.get('website_id'):
                website_id = page_info['website_id'] or request.env['website'].get_current_website(fallback=True).id
                WebsitePage = WebsitePage.with_context(website_id=website_id)
                request.update_context(website_id=website_id)
            return WebsitePage.browse(page_info['id'])._get_response(request)

        return False

    @classmethod
    def _serve_redirect(cls):
        req_page = request.httprequest.path
        req_page_with_qs = request.httprequest.environ['REQUEST_URI']
        domain = (
            Domain('redirect_type', 'in', ('301', '302'))
            # trailing / could have been removed by server_page
            & Domain('url_from', 'in', [req_page_with_qs, req_page.rstrip('/'), req_page + '/'])
            & request.env.website.website_domain()
        )
        return request.env['website.rewrite'].sudo().search(domain, order='url_from DESC', limit=1)

    @classmethod
    def _serve_fallback(cls):
        # serve attachment before
        parent = super()._serve_fallback()
        if parent:  # attachment
            return parent

        # minimal setup to serve frontend pages
        if not request.env.context.get('website_id'):
            request.update_context(website_id=request.env.context.get('host_id'))
        cls._frontend_pre_dispatch()
        cls._handle_debug()

        website_page = cls._serve_page()
        if website_page:
            website_page.flatten()
            return website_page

        redirect = cls._serve_redirect()
        if redirect:
            return request.redirect(
                _build_url_w_params(redirect.url_to, request.params),
                code=redirect.redirect_type,
                local=False)  # safe because only designers can specify redirects

    @classmethod
    def _get_exception_code_values(cls, exception):
        code, values = super()._get_exception_code_values(exception)
        if isinstance(exception, werkzeug.exceptions.NotFound) and request.env.user.has_group('website.group_website_designer'):
            code = 'page_404'
            values['path'] = request.httprequest.path[1:]
        if isinstance(exception, werkzeug.exceptions.Forbidden) and \
           exception.description == "website_visibility_password_required":
            code = 'protected_403'
            values['path'] = request.httprequest.path
        return (code, values)

    @classmethod
    def _get_values_500_error(cls, env, values, exception):
        values = super()._get_values_500_error(env, values, exception)
        if hasattr(exception, 'qweb'):
            qweb_error = exception.qweb
            exception_template = qweb_error.ref
            View = env["ir.ui.view"].sudo()
            view = exception_template and View._get_template_view(exception_template)
            if not view or qweb_error.element and qweb_error.element in view.arch:
                values['view'] = view
            else:
                # There might be 2 cases where the exception code can't be found
                # in the view, either the error is in a child view or the code
                # contains branding (<div t-att-data="request.browse('ok')"/>).
                et = view.with_context(inherit_branding=False)._get_combined_arch()
                node = et.xpath(qweb_error.path) if qweb_error.path else et
                line = node is not None and len(node) > 0 and etree.tostring(node[0], encoding='unicode')
                if line:
                    values['view'] = View._views_get(view.id).filtered(
                        lambda v: line in v.arch
                    )
                    values['view'] = values['view'] and values['view'][0]
        # Needed to show reset template on translated pages (`_prepare_environment` will set it for main lang)
        values['editable'] = request.env.uid and request.env.user.has_group('website.group_website_designer')
        return values

    @api.model
    def _get_error_html(self, code, values):
        irHttp = self
        if code in ('page_404', 'protected_403'):
            website = self.env["website"].get_current_website(fallback=True)
            return code.split('_')[1], website._render_template('website.%s' % code, values)
        return super(IrHttp, irHttp)._get_error_html(code, values)

    @api.model
    def get_frontend_session_info(self):
        website = self.env.website
        session_info = super().get_frontend_session_info()
        geoip_country_code = request.geoip.country_code
        geoip_phone_code = request.env['res.country']._phone_code_for(geoip_country_code) if geoip_country_code else None
        session_info.update({
            'is_website_user': request.env.user.id == website.user_id.id,
            'geoip_country_code': geoip_country_code,
            'geoip_phone_code': geoip_phone_code,
            'lang_url_code': request.lang.url_code,
        })
        if request.env.user.has_group('website.group_website_restricted_editor'):
            session_info.update({
                'website_id': website.id,
                'website_company_id': website.company_id.id,
            })
        session_info['bundle_params']['website_id'] = website.id
        return session_info

    @api.model
    def _is_allowed_cookie(self, cookie_type):
        result = super()._is_allowed_cookie(cookie_type)
        if result and cookie_type == 'optional':
            if not self.env.website.cookies_bar:
                # Cookies bar is disabled on this website
                return True
            accepted_cookie_types = json_scriptsafe.loads(request.cookies.get('website_cookies_bar', '{}'))

            # pre-16.0 compatibility, `website_cookies_bar` was `"true"`.
            # In that case we delete that cookie and let the user choose again.
            if not isinstance(accepted_cookie_types, dict):
                request.future_response.set_cookie('website_cookies_bar', max_age=0)
                return False

            if 'optional' in accepted_cookie_types:
                return accepted_cookie_types['optional']
            return False

        # Pass-through if already forbidden for another reason or a type that
        # is not restricted by the website module.
        return result

    def _get_visitor_from_request(self, force_create=False, force_track_values=None):
        """ Return the visitor as sudo from the request.

        :param force_create: force a visitor creation if no visitor exists
        :param force_track_values: an optional dict to create a track at the
            same time.
        :return: the website visitor if exists or forced, empty recordset
            otherwise.
        """

        # This function can be called in json with mobile app.
        # In case of mobile app, no uid is set on the jsonRequest env.
        # In case of multi db, _env is None on request, and request.env unbound.
        if not (request and request.env and request.env.uid):
            return None

        access_token = self.env['website.visitor']._get_access_token()
        website_id = request.env.website.id or request.env.context.get('host_id')

        if force_create:
            force_track_values = force_track_values or {}
            visitor_id, _ = self.env['website.visitor']._upsert_visitor(
                token_or_partner_id=access_token,
                website_id=website_id,
                lang_id=request.lang.id,
                country_code=request.geoip.country_code,  # GEOIP might return a country code unknown to odoo
                timezone=self.env['website.visitor']._get_visitor_timezone(),
                **force_track_values
            )
            return self.env['website.visitor'].sudo().browse(visitor_id)

        visitor = self.env['website.visitor'].sudo().search_fetch([('access_token', '=', access_token)])

        if not force_create and not self.env.cr.readonly and visitor and not visitor.timezone:
            tz = self.env['website.visitor']._get_visitor_timezone()
            if tz:
                visitor._update_visitor_timezone(tz)

        return visitor


class ModelConverter(ir_http.ModelConverter):

    def to_url(self, value: models.BaseModel) -> str:
        if value.env.context.get('slug_matching'):
            return value.env.context.get('_converter_value', str(value.id))
        return super().to_url(value)

    def generate(self, env, args, dom=None):
        Model = env[self.model]
        # Allow to the current website or the host website directly in route domain
        args['current_website_id'] = env.website.id or env.context.get('host_id')
        domain = safe_eval(self.domain, args)
        domain = Domain(domain)
        if dom:
            domain &= Domain(dom)
        # return record so URL will be the real endpoint URL as the record will go through `slug()`
        # the same way as endpoint URL is retrieved during dispatch (301 redirect), see `to_url()` from ModelConverter
        yield from Model.search(domain)
