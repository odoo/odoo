import hashlib
from typing import Any
from urllib.parse import quote

from markupsafe import Markup

from odoo import api, fields, models
from odoo.tools import html_escape as escape


class IrQwebFieldImage(models.AbstractModel):
    """
    Widget options:

    ``class``
        set as attribute on the generated <img> tag
    """

    _inherit = "ir.qweb.field.image"

    def _get_src_urls(
        self, record: Any, field_name: str, options: dict[str, Any]
    ) -> tuple[str, str | None]:
        """Considering the rendering options, returns the src and data-zoom-image urls.

        :return: src, src_zoom urls
        :rtype: tuple[str, str | None]
        """
        max_size = None
        if options.get("resize"):
            max_size = options.get("resize")
        else:
            max_width, max_height = options.get("max_width", 0), options.get(
                "max_height", 0
            )
            if max_width or max_height:
                max_size = f"{max_width}x{max_height}"

        sha = hashlib.sha512(
            str(getattr(record, "write_date", fields.Datetime.now())).encode("utf-8")
        ).hexdigest()[:7]
        max_size = "" if max_size is None else f"/{max_size}"

        if (
            options.get("filename-field")
            and options["filename-field"] in record
            and record[options["filename-field"]]
        ):
            filename = record[options["filename-field"]]
        elif options.get("filename"):
            filename = options["filename"]
        else:
            filename = record.display_name
        filename = (
            (filename or "name")
            .replace("/", "-")
            .replace("\\", "-")
            .replace("..", "--")
        )

        src = f"/web/image/{record._name}/{record.id}/{options.get('preview_image', field_name)}{max_size}/{quote(filename, safe='/:')}?unique={sha}"

        src_zoom = None
        if options.get("zoom") and getattr(record, options["zoom"], None):
            src_zoom = f"/web/image/{record._name}/{record.id}/{options['zoom']}{max_size}/{quote(filename, safe='/:')}?unique={sha}"
        elif options.get("zoom"):
            src_zoom = options["zoom"]

        return src, src_zoom

    @api.model
    def record_to_html(
        self, record: Any, field_name: str, options: dict[str, Any]
    ) -> Markup | bool:
        if options["tagName"] == "img":
            msg = "The root tag of an image field cannot be img. The image goes into the tag as content."
            raise ValueError(msg)

        src = src_zoom = None
        if options.get("qweb_img_raw_data", False):
            value = record[field_name]
            if value is False:
                return False
            src = self._get_src_data_b64(value, options)
        else:
            src, src_zoom = self._get_src_urls(record, field_name, options)

        aclasses = (
            ["img", "img-fluid"]
            if options.get("qweb_img_responsive", True)
            else ["img"]
        )
        aclasses += options.get("class", "").split()
        classes = " ".join(map(escape, aclasses))

        if (
            options.get("alt-field")
            and options["alt-field"] in record
            and record[options["alt-field"]]
        ):
            alt = escape(record[options["alt-field"]])
        elif options.get("alt"):
            alt = options["alt"]
        else:
            alt = escape(record.display_name)

        itemprop = None
        if options.get("itemprop"):
            itemprop = options["itemprop"]

        atts = {}
        atts["src"] = src
        atts["itemprop"] = itemprop
        atts["class"] = classes
        atts["style"] = options.get("style")
        atts["width"] = options.get("width")
        atts["height"] = options.get("height")
        atts["alt"] = alt
        atts["data-zoom"] = "1" if src_zoom else None
        atts["data-zoom-image"] = src_zoom
        atts["data-no-post-process"] = options.get("data-no-post-process")

        atts = self.env["ir.qweb"]._post_processing_att("img", atts)

        img = ["<img"]
        for name, value in atts.items():
            if value:
                img.extend([" ", escape(name), '="', escape(value), '"'])
        img.append("/>")

        return Markup("".join(img))


class IrQwebFieldImage_Url(models.AbstractModel):
    _inherit = "ir.qweb.field.image_url"

    def _get_src_urls(
        self, record: Any, field_name: str, options: dict[str, Any]
    ) -> tuple[str, str | None]:
        image_url = record[options.get("preview_image", field_name)]
        return image_url, options.get("zoom", None)
