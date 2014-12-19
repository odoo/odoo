import os
import time
import hashlib
import datetime
import cStringIO
from PIL import Image
from sys import maxint

import openerp
from openerp.osv import osv
from openerp.addons.web.http import request
from openerp.tools import image_resize_and_sharpen, image_save_for_web


class website(osv.osv):
    _inherit = "website"

    def _image(self, cr, uid, model, id, field, response, max_width=maxint, max_height=maxint, cache=None, context=None):
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
        Model = self.pool[model]
        id = int(id)

        ids = Model.search(cr, uid,
                           [('id', '=', id)], context=context)
        if not ids and 'website_published' in Model._fields:
            ids = Model.search(cr, openerp.SUPERUSER_ID,
                               [('id', '=', id), ('website_published', '=', True)], context=context)
        if not ids:
            return self._image_placeholder(response)

        concurrency = '__last_update'
        [record] = Model.read(cr, openerp.SUPERUSER_ID, [id],
                              [concurrency, field],
                              context=context)

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

        if model == 'ir.attachment' and field == 'url':
            path = record.get(field).strip('/')

            # Check that we serve a file from within the module
            if os.path.normpath(path).startswith('..'):
                return self._image_placeholder(response)

            # Check that the file actually exists
            path = path.split('/')
            resource = openerp.modules.get_module_resource(path[0], *path[1:])
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
