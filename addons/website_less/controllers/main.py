import werkzeug
from openerp.http import request
from openerp.addons.web import http
from openerp.addons.website.controllers.main import Website
from openerp.addons.base.ir.ir_qweb import QWebTemplateNotFound
from openerp.addons.website_less.ir_qweb import AssetsBundle
from openerp.addons.web.controllers.main import Home, make_conditional, BUNDLE_MAXAGE


class Home_less(Home):

    @http.route([
        '/web/js/<xmlid>',
        '/web/js/<xmlid>/<version>',
    ], type='http', auth='public')
    def js_bundle(self, xmlid, version=None, **kw):
        try:
            bundle = AssetsBundle(xmlid)
        except QWebTemplateNotFound:
            return request.not_found()

        response = request.make_response(bundle.js(), [('Content-Type', 'application/javascript')])
        return make_conditional(response, bundle.last_modified, max_age=BUNDLE_MAXAGE)

    @http.route([
        '/web/css/<xmlid>',
        '/web/css/<xmlid>/<version>',
    ], type='http', auth='public')
    def css_bundle(self, xmlid, version=None, **kw):
        try:
            bundle = AssetsBundle(xmlid)
        except QWebTemplateNotFound:
            return request.not_found()

        response = request.make_response(bundle.css(), [('Content-Type', 'text/css')])
        return make_conditional(response, bundle.last_modified, max_age=BUNDLE_MAXAGE)


class Website_less(Website):
    #------------------------------------------------------
    # Themes
    #------------------------------------------------------

    def get_view_ids(self, xml_ids):
        ids = []
        imd = request.registry['ir.model.data']
        for xml_id in xml_ids:
            if "." in xml_id:
                xml = xml_id.split(".")
                view_model, id = imd.get_object_reference(request.cr, request.uid, xml[0], xml[1])
            else:
                id = int(xml_id)
            ids.append(id)
        return ids

    @http.route(['/website/theme_customize_get'], type='json', auth="public", website=True)
    def theme_customize_get(self, xml_ids):
        view = request.registry["ir.ui.view"]
        enable = []
        disable = []
        ids = self.get_view_ids(xml_ids)
        context = dict(request.context or {}, active_test=True)
        for v in view.browse(request.cr, request.uid, ids, context=context):
            if v.active:
                enable.append(v.xml_id)
            else:
                disable.append(v.xml_id)
        return [enable, disable]

    @http.route(['/website/theme_customize'], type='json', auth="public", website=True)
    def theme_customize(self, enable, disable):
        """ enable or Disable lists of ``xml_id`` of the inherit templates
        """
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        view = pool["ir.ui.view"]
        context = dict(request.context or {}, active_test=True)

        def set_active(ids, active):
            if ids:
                view.write(cr, uid, self.get_view_ids(ids), {'active': active}, context=context)

        set_active(disable, False)
        set_active(enable, True)

        return True

    @http.route(['/website/theme_customize_reload'], type='http', auth="public", website=True)
    def theme_customize_reload(self, href, enable, disable):
        self.theme_customize(enable and enable.split(",") or [], disable and disable.split(",") or [])
        return request.redirect(href + ("&theme=true" if "#" in href else "#theme=true"))

    @http.route(['/website/multi_render'], type='json', auth="public", website=True)
    def multi_render(self, ids_or_xml_ids, values=None):
        res = {}
        for id_or_xml_id in ids_or_xml_ids:
            res[id_or_xml_id] = request.registry["ir.ui.view"].render(request.cr, request.uid,
                id_or_xml_id, values=values, engine='ir.qweb', context=request.context)
        return res

    @http.route([
        '/website/image',
        '/website/image/<xmlid>',
        '/website/image/<xmlid>/<field>',
        '/website/image/<xmlid>/<int:max_width>x<int:max_height>',
        '/website/image/<xmlid>/<field>/<int:max_width>x<int:max_height>',
        '/website/image/<model>/<id>/<field>',
        '/website/image/<model>/<id>/<field>/<int:max_width>x<int:max_height>',
    ], auth="public", website=True)
    def website_image(self, model=None, id=None, field=None, xmlid=None, max_width=None, max_height=None):
        """ Fetches the requested field and ensures it does not go above
        (max_width, max_height), resizing it if necessary.

        If the record is not found or does not have the requested field,
        returns a placeholder image via :meth:`~.placeholder`.

        Sets and checks conditional response parameters:
        * :mailheader:`ETag` is always set (and checked)
        * :mailheader:`Last-Modified is set iif the record has a concurrency
          field (``__last_update``)

        The requested field is assumed to be base64-encoded image data in
        all cases.

        xmlid can be used to load the image. But the field image must by base64-encoded
        """
        if xmlid and "." in xmlid:
            try:
                record = request.env['ir.model.data'].xmlid_to_object(xmlid)
                model, id = record._name, record.id
            except:
                raise werkzeug.exceptions.NotFound()
                env.ref
            if model == 'ir.attachment' and not field:
                if record.sudo().type == 'url':
                    field = "url"
                else:
                    field = "datas"
        elif model and id and field:
            idsha = id.split('_')
            try:
                id = idsha[0]
            except IndexError:
                raise werkzeug.exceptions.NotFound()
        else:
            raise werkzeug.exceptions.NotFound()

        response = werkzeug.wrappers.Response()
        return request.registry['website']._image(
                    request.cr, request.uid, model, id, field, response, max_width, max_height)
