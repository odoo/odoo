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
                result[attach.id] = '/web/image/%s?unique=%s' % (attach.id, attach.checksum)
        return result

    _columns = {
        'local_url': fields.function(_local_url_get, string="Attachment URL", type='char'),
    }
