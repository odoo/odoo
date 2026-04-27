from http import HTTPStatus
from urllib.parse import urlencode, quote

from odoo.http import request, route

from odoo.addons.base.models.ir_qweb import keep_query
from odoo.addons.web.controllers import home as web_home
from odoo.addons.web.controllers.utils import ensure_db
from .documents import ShareRoute


class Home(web_home.Home):
    def _web_client_readonly(self):
        """ Force a read/write cursor for documents.access """
        path = request.httprequest.path
        if (
            path.startswith('/odoo/documents')
            and (request.httprequest.args.get('access_token') or path.removeprefix('/odoo/documents/'))
            and request.session.uid
        ):
            return False
        return super()._web_client_readonly()

    @route(readonly=_web_client_readonly)
    def web_client(self, s_action=None, **kw):
        """ Handle direct access to a document with a backend URL (/odoo/documents/<access_token>).

        It redirects to the document either in:
        - the backend if the user is logged and has access to the Documents module
        - or a lightweight version of the backend if the user is logged and has not access
        to the Document module but well to the documents.document model
        - or the document portal otherwise

        Goal: Allow to share directly the backend URL of a document.
        """
        subpath = kw.get('subpath', '')
        access_token = request.params.get('access_token') or subpath.removeprefix('documents/')
        if not subpath.startswith('documents') or not access_token or '/' in access_token:
            return super().web_client(s_action, **kw)

        # This controller should be auth='public' but it actually is
        # auth='none' for technical reasons (see super). Those three
        # lines restore the public behavior.
        ensure_db()
        request.update_env(user=request.session.uid)
        request.env['ir.http']._authenticate_explicit('public')

        # Public/Portal users use the /documents/<access_token> route
        if not request.env.user._is_internal():
            return request.redirect(
                f'/documents/{quote(access_token, safe="")}?{keep_query("*")}',
                HTTPStatus.TEMPORARY_REDIRECT,
            )

        document_sudo = ShareRoute._from_access_token(access_token, follow_shortcut=False)

        if not document_sudo:
            Redirect = request.env['documents.redirect'].sudo()
            if document_sudo := Redirect._get_redirection(access_token):
                return request.redirect(
                    f'/odoo/documents/{quote(document_sudo.access_token, safe="")}?{keep_query("*")}',
                    HTTPStatus.MOVED_PERMANENTLY,
                )

        # We want (1) the webclient renders the webclient template and load
        # the document action. We also want (2) the router rewrites
        # /odoo/documents/<id> to /odoo/documents/<access-token> in the
        # URL.
        # We redirect on /web so this override does kicks in again,
        # super() is loaded and renders the normal home template. We add
        # custom fragments so we can load them inside the router and
        # rewrite the URL.
        query = {}
        if request.session.debug:
            query['debug'] = request.session.debug
        fragment = {
           'action': request.env.ref("documents.document_action").id,
           'menu_id': request.env.ref('documents.menu_root').id,
           'model': 'documents.document',
        }
        if document_sudo:
            fragment.update({
                f'documents_init_{key}': value
                for key, value
                in ShareRoute._documents_get_init_data(document_sudo, request.env.user).items()
            })
        return request.redirect(f'/web?{urlencode(query)}#{urlencode(fragment)}')
