# Copyright 2020 Eugene Molotov <https://it-projects.info/team/em230418>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import base64

import odoo
from odoo import http
from odoo.http import request
from odoo.tools import image_process

from odoo.addons.web.controllers.main import Binary


class BinaryExtended(Binary):
    def _content_image(
        self,
        xmlid=None,
        model="ir.attachment",
        id=None,  # pylint: disable=redefined-builtin
        field="datas",
        filename_field="name",
        unique=None,
        filename=None,
        mimetype=None,
        download=None,
        width=0,
        height=0,
        crop=False,
        quality=0,
        access_token=None,
        placeholder="placeholder.png",
        **kwargs
    ):
        status, headers, image_base64 = request.env["ir.http"].binary_content(
            xmlid=xmlid,
            model=model,
            id=id,
            field=field,
            unique=unique,
            filename=filename,
            filename_field=filename_field,
            download=download,
            mimetype=mimetype,
            default_mimetype="image/png",
            access_token=access_token,
        )

        if status in [301, 302, 304] or (
            status != 200 and download
        ):  # em230418: added 302 only
            return request.env["ir.http"]._response_by_status(
                status, headers, image_base64
            )
        if not image_base64:
            # Since we set a placeholder for any missing image, the status must be 200. In case one
            # wants to configure a specific 404 page (e.g. though nginx), a 404 status will cause
            # troubles.
            status = 200
            image_base64 = base64.b64encode(self.placeholder(image=placeholder))
            if not (width or height):
                width, height = odoo.tools.image_guess_size_from_field_name(field)

        image_base64 = image_process(
            image_base64,
            size=(int(width), int(height)),
            crop=crop,
            quality=int(quality),
        )

        content = base64.b64decode(image_base64)
        headers = http.set_safe_image_headers(headers, content)
        response = request.make_response(content, headers)
        response.status_code = status
        return response
