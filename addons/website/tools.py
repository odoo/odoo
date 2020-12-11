# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import contextlib
from unittest.mock import Mock, MagicMock, patch

import werkzeug

import odoo
from odoo.tools.misc import DotDict

def werkzeugRaiseNotFound(*args, **kwargs):
    raise werkzeug.exceptions.NotFound()

@contextlib.contextmanager
def MockRequest(
        env, *, routing=True, multilang=True,
        context=None,
        cookies=None, country_code=None, website=None, sale_order_id=None
):
    router = MagicMock()
    match = router.return_value.bind.return_value.match
    if routing:
        match.return_value[0].routing = {
            'type': 'http',
            'website': True,
            'multilang': multilang
        }
    else:
        match.side_effect = werkzeugRaiseNotFound

    if context is None:
        context = {}
    lang_code = context.setdefault('lang', env.context.get('lang', 'en_US'))

    request = Mock(
        context=context,
        db=None,
        debug=False,
        endpoint=match.return_value[0] if routing else None,
        env=env,
        httprequest=Mock(
            host='localhost',
            path='/hello/',
            app=odoo.http.root,
            environ={'REMOTE_ADDR': '127.0.0.1'},
            cookies=cookies or {},
            referrer='',
        ),
        lang=lang_code,
        redirect=werkzeug.utils.redirect,
        session=DotDict(
            geoip={'country_code': country_code},
            sale_order_id=sale_order_id,
        ),
        website=website
    )

    with contextlib.ExitStack() as s:
        odoo.http._request_stack.push(request)
        s.callback(odoo.http._request_stack.pop)
        s.enter_context(patch('odoo.http.root.get_db_router', router))

        yield request
