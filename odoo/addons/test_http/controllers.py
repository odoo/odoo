# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from psycopg2.errorcodes import SERIALIZATION_FAILURE
from psycopg2 import OperationalError

from odoo import http

# Force serialization errors. Patched in some tests.
should_fail = None


class SerializationFailureError(OperationalError):
    pgcode = SERIALIZATION_FAILURE


class HttpTest(http.Controller):
    @http.route("/test_http/upload_file", methods=["POST"], type="http", auth="none", csrf=False)
    def upload_file_retry(self, ufile):
        global should_fail  # pylint: disable=W0603
        if should_fail is None:
            raise ValueError("should_fail should be set.")

        data = ufile.read()
        if should_fail:
            should_fail = False  # Fail once
            raise SerializationFailureError()

        return data.decode()
