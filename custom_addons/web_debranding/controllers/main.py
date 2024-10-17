# Copyright 2015-2018,2020 Ivan Yelizariev <https://it-projects.info/team/yelizariev>
# Copyright 2016 Stanislav Krotov <https://it-projects.info/team/ufaks>
# Copyright 2017 Ilmir Karamov <https://it-projects.info/team/ilmir-k>
# Copyright 2017 Nicolas JEUDY <https://github.com/njeudy>
# Copyright 2017 Ildar Nasyrov <https://it-projects.info/team/iledarn>
# Copyright 2018 Kolushov Alexandr <https://it-projects.info/team/KolushovAlexandr>
# License MIT (https://opensource.org/licenses/MIT).
# License OPL-1 (https://www.odoo.com/documentation/user/14.0/legal/licenses/licenses.html#odoo-apps) for derivative work.

import base64
import functools
import io

try:
    from werkzeug.utils import send_file
except ImportError:
    from odoo.tools._vendor.send_file import send_file

import odoo
from odoo import http
from odoo.http import request
from odoo.modules import get_resource_path
from odoo.tools.mimetypes import guess_mimetype

from odoo.addons.web.controllers.binary import Binary


class BinaryCustom(Binary):
    @http.route(
        ["/web/binary/company_logo", "/logo", "/logo.png"], type="http", auth="none"
    )
    def company_logo(self, dbname=None, **kw):
        imgname = "logo"
        imgext = ".png"

        default_logo_module = "web_debranding"
        if request.session.db:
            default_logo_module = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("web_debranding.default_logo_module")
            )

        placeholder = functools.partial(
            get_resource_path, default_logo_module, "static", "img"
        )
        dbname = request.db
        uid = (request.session.uid if dbname else None) or odoo.SUPERUSER_ID

        if not dbname:
            response = http.Stream.from_path(
                placeholder(imgname + imgext)
            ).get_response()
        else:
            try:
                # create an empty registry
                registry = odoo.modules.registry.Registry(dbname)
                with registry.cursor() as cr:
                    company = int(kw["company"]) if kw and kw.get("company") else False
                    if company:
                        cr.execute(
                            """SELECT logo_web, write_date
                                        FROM res_company
                                       WHERE id = %s
                                   """,
                            (company,),
                        )
                    else:
                        cr.execute(
                            """SELECT c.logo_web, c.write_date
                                        FROM res_users u
                                   LEFT JOIN res_company c
                                          ON c.id = u.company_id
                                       WHERE u.id = %s
                                   """,
                            (uid,),
                        )
                    row = cr.fetchone()
                    if row and row[0]:
                        image_base64 = base64.b64decode(row[0])
                        image_data = io.BytesIO(image_base64)
                        mimetype = guess_mimetype(image_base64, default="image/png")
                        imgext = "." + mimetype.split("/")[1]
                        if imgext == ".svg+xml":
                            imgext = ".svg"
                        response = send_file(
                            image_data,
                            request.httprequest.environ,
                            download_name=imgname + imgext,
                            mimetype=mimetype,
                            last_modified=row[1],
                        )
                    else:
                        response = http.Stream.from_path(
                            placeholder("nologo.png")
                        ).get_response()
            except Exception:
                response = http.Stream.from_path(
                    placeholder(imgname + imgext)
                ).get_response()

        return response
