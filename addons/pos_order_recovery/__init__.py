# -*- coding: utf-8 -*-

from . import models


from odoo import api, SUPERUSER_ID


def _generate_capture_record_from_existing_capture_attachments(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['pos.order.capture']._generate_capture_record_from_existing_capture_attachments()
