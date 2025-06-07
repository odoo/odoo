import contextlib
from unittest.mock import MagicMock, Mock, patch

import werkzeug.urls
from werkzeug.exceptions import NotFound
from werkzeug.test import EnvironBuilder

import odoo.http
from odoo.tests import HOST, HttpCase
from odoo.tools import DotDict, config, frozendict


@contextlib.contextmanager
def MockRequest(
    env, *, path='/mockrequest', routing=True, multilang=True,
    context=frozendict(), cookies=frozendict(), country_code=None,
    website=None, remote_addr=HOST, environ_base=None, url_root=None,
):
    """Mock of the ``http.request``.

    NOTE: If you only use ``request.env`` in your code, you can replace it by
    ``self.env`` and don't need to use this class.
    It is in this module, because website adds properties which are not defined
    in base module.
    """
    lang_code = context.get('lang', env.context.get('lang', 'en_US'))
    env = env(context=dict(context, lang=lang_code))
    if HttpCase.http_port():
        base_url = HttpCase.base_url()
    else:
        base_url = f"http://{HOST}:{config['http_port']}"
    request = Mock(
        # request
        httprequest=Mock(
            host='localhost',
            path=path,
            app=odoo.http.root,
            environ=dict(
                EnvironBuilder(
                    path=path,
                    base_url=base_url,
                    environ_base=environ_base,
                ).get_environ(),
                REMOTE_ADDR=remote_addr,
            ),
            cookies=cookies,
            referrer='',
            remote_addr=remote_addr,
            url_root=url_root,
            args=[],
        ),
        type='http',
        future_response=odoo.http.FutureResponse(),
        params={},
        redirect=env['ir.http']._redirect,
        session=DotDict(
            odoo.http.get_default_session(),
            context={'lang': ''},
            force_website_id=website and website.id,
        ),
        geoip=odoo.http.GeoIP('127.0.0.1'),
        db=env.registry.db_name,
        env=env,
        registry=env.registry,
        cr=env.cr,
        uid=env.uid,
        context=env.context,
        cookies=cookies,
        lang=env['res.lang']._get_data(code=lang_code),
        website=website,
        render=lambda *a, **kw: '<MockResponse>',
    )
    if url_root is not None:
        request.httprequest.url = werkzeug.urls.url_join(url_root, path)
    if website:
        request.website_routing = website.id
    if country_code:
        try:
            request.geoip._city_record = odoo.http.geoip2.models.City(['en'], country={'iso_code': country_code})
        except TypeError:
            request.geoip._city_record = odoo.http.geoip2.models.City({'country': {'iso_code': country_code}})

    # The following code mocks match() to return a fake rule with a fake
    # 'routing' attribute (routing=True) or to raise a NotFound
    # exception (routing=False).
    #
    #   router = odoo.http.root.get_db_router()
    #   rule, args = router.bind(...).match(path)
    #   # arg routing is True => rule.endpoint.routing == {...}
    #   # arg routing is False => NotFound exception
    router = MagicMock()
    match = router.return_value.bind.return_value.match
    if routing:
        match.return_value[0].routing = {
            'type': 'http',
            'website': True,
            'multilang': multilang
        }
    else:
        match.side_effect = NotFound

    def update_context(**overrides):
        request.env = request.env(context=dict(request.context, **overrides))
        request.context = request.env.context

    request.update_context = update_context

    with contextlib.ExitStack() as s:
        odoo.http._request_stack.push(request)
        s.callback(odoo.http._request_stack.pop)
        s.enter_context(patch('odoo.http.root.get_db_router', router))

        yield request
