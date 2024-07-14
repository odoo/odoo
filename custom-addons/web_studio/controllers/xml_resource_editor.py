from lxml import etree

from odoo import http
from odoo.http import request

class WebStudioController(http.Controller):

    @http.route("/web_studio/get_xml_editor_resources", type="json", auth="user")
    def get_xml_editor_resources(self, key):
        views = request.env["ir.ui.view"].with_context(no_primary_children=True, __views_get_original_hierarchy=[]).get_related_views(key)
        views = views.read(['name', 'id', 'key', 'xml_id', 'arch', 'active', 'inherit_id'])

        main_view = None
        for view in views:
            arch = view["arch"]
            root = etree.fromstring(arch)

            called_xml_ids = []
            for el in root.xpath("//*[@t-call]"):
                tcall = el.get("t-call")
                if "{" in tcall:
                    continue
                called_xml_ids.append(tcall)

                if main_view is None and el.xpath("ancestor::t[@t-foreach='docs']"):
                    main_view = tcall

            if called_xml_ids:
                view["called_xml_ids"] = called_xml_ids

        return {
            "main_view_key": main_view or key,
            "views": views,
        }
