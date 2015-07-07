# -*- coding: utf-8 -*-
import openerp
from openerp.osv import osv, fields

import contextlib
from sys import maxint
from openerp.addons.web.http import request
import datetime
import hashlib
import time
import os

from openerp.tools import html_escape as escape, ustr, image_resize_and_sharpen, image_save_for_web
from PIL import Image
import cStringIO

import logging
logger = logging.getLogger(__name__)


class ir_attachment(osv.osv):

    _inherit = "ir.attachment"

    def _local_url_get(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for attach in self.browse(cr, uid, ids, context=context):
            if attach.url:
                result[attach.id] = attach.url
            else:
                result[attach.id] = self.image_url(cr, uid, attach, 'datas')
        return result

    _columns = {
        'local_url': fields.function(_local_url_get, string="Attachment URL", type='char'),
    }

    def _image_placeholder(self, response):
        # file_open may return a StringIO. StringIO can be closed but are
        # not context managers in Python 2 though that is fixed in 3
        with contextlib.closing(openerp.tools.misc.file_open(
                os.path.join('web', 'static', 'src', 'img', 'placeholder.png'),
                mode='rb')) as f:
            response.data = f.read()
            return response.make_conditional(request.httprequest)

    def _image(self, cr, uid, model, id_or_ids, field, response, max_width=maxint, max_height=maxint, cache=None, context=None):
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
        ids = isinstance(id_or_ids, (list, tuple)) and id_or_ids or [int(id_or_ids)]
        ids = Model.search(cr, uid, [('id', 'in', ids)], context=context)

        if not ids:
            return self._image_placeholder(response)

        concurrency = '__last_update'
        [record] = Model.read(cr, openerp.SUPERUSER_ID, ids, [concurrency, field], context=context)

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

        filename = '%s_%s.%s' % (model.replace('.', '_'), ids[0], str(image.format).lower())
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

    def image_url(self, cr, uid, record, field, size=None, context=None):
        """Returns a local url that points to the image field of a given browse record."""
        model = record._name
        sudo_record = record.sudo()
        id = '%s_%s' % (record.id, hashlib.sha1(sudo_record.write_date or sudo_record.create_date or '').hexdigest()[0:7])
        size = '' if size is None else '/%s' % size
        return '/web_editor/image/%s/%s/%s%s' % (model, id, field, size)
