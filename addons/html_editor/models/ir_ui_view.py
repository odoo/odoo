import copy
import logging
import uuid

from lxml import etree, html

from odoo import _, api, models
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

from odoo.addons.base.models.ir_ui_view import MOVABLE_BRANDING

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

EDITING_ATTRIBUTES = MOVABLE_BRANDING | {
    "data-oe-type",
    "data-oe-expression",
    "data-oe-translation-id",
    "data-note-id",
}


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    def _get_cleaned_non_editing_attributes(self, attributes):
        attributes = {k: v for k, v in attributes if k not in EDITING_ATTRIBUTES}
        if "class" in attributes:
            classes = attributes["class"].split()
            attributes["class"] = " ".join([c for c in classes if c != "o_editable"])
        if attributes.get("contenteditable") == "true":
            del attributes["contenteditable"]
        return attributes

    @api.model
    def extract_embedded_fields(self, arch):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    @api.model
    def extract_oe_structures(self, arch):
        return arch.xpath(
            '//*[hasclass("oe_structure")][contains(@id, "oe_structure")]'
        )

    @api.model
    def get_default_lang_code(self):
        return False

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get("data-oe-model")]
        field = el.get("data-oe-field")

        model = "ir.qweb.field." + el.get("data-oe-type")
        converter = self.env[model] if model in self.env else self.env["ir.qweb.field"]

        try:
            value = converter.from_html(Model, Model._fields[field], el)
            if value is not None:
                record = Model.browse(int(el.get("data-oe-id")))
                if not self.env.context.get("lang") and self.get_default_lang_code():
                    record.with_context(lang=self.get_default_lang_code()).write(
                        {field: value}
                    )
                else:
                    record.write({field: value})

                if callable(Model._fields[field].translate):
                    self._copy_custom_snippet_translations(record, field)

        except (ValueError, TypeError) as err:
            _debug.logic("snippet_save_refused", reason="bad_values", view=self.id)
            raise ValidationError(
                _(
                    "Invalid field value for %(field_name)s: %(value)s",
                    field_name=Model._fields[field].string,
                    value=el.text_content().strip(),
                )
            ) from err

    def save_oe_structure(self, el):
        self.check_singleton()

        if el.get("id") in self.key:
            return False

        arch = etree.Element("data")
        xpath = etree.Element(
            "xpath",
            expr=f"//*[hasclass('oe_structure')][@id='{el.get('id')}']",
            position="replace",
        )
        arch.append(xpath)
        attributes = self._get_cleaned_non_editing_attributes(el.attrib.items())
        structure = etree.Element(el.tag, attrib=attributes)
        structure.text = el.text
        xpath.append(structure)
        for child in el.iterchildren(tag=etree.Element):
            structure.append(copy.deepcopy(child))

        vals = {
            "inherit_id": self.id,
            "name": f"{self.name} ({el.get('id')})",
            "arch": etree.tostring(arch, encoding="unicode"),
            "key": f"{self.key}_{el.get('id')}",
            "type": "qweb",
            "mode": "extension",
        }
        vals.update(self._save_oe_structure_hook())
        oe_structure_view = self.env["ir.ui.view"].create(vals)
        self._copy_custom_snippet_translations(oe_structure_view, "arch_db")

        return True

    @api.model
    def _copy_custom_snippet_translations(self, record, html_field):
        lang_value = record[html_field]
        if not lang_value:
            return

        try:
            tree = html.fromstring(lang_value)
        except etree.ParserError as e:
            raise ValidationError(str(e)) from e

        for custom_snippet_el in tree.xpath('//*[hasclass("s_custom_snippet")]'):
            custom_snippet_name = custom_snippet_el.get("data-name")
            custom_snippet_view = self.search(  # noqa: E8507 - one lookup per custom snippet in the arch
                [("name", "=", custom_snippet_name)], limit=1
            )
            if custom_snippet_view:
                self._copy_field_terms_translations(
                    custom_snippet_view, "arch_db", record, html_field
                )

    @api.model
    def _copy_field_terms_translations(
        self, records_from, name_field_from, record_to, name_field_to
    ):
        record_to.check_access("write")
        field_from = records_from._fields[name_field_from]
        field_to = record_to._fields[name_field_to]
        record_to._check_field_access(field_to, "write")

        if not callable(field_from.translate):
            raise TypeError(
                f"'translate' property of field {field_from!r} is not callable"
            )
        if not callable(field_to.translate):
            raise TypeError(
                f"'translate' property of field {field_to!r} is not callable"
            )
        if not field_to.store:
            raise ValueError(f"Field {field_to!r} is not stored")

        if not record_to[name_field_to] or not any(
            records_from.mapped(name_field_from)
        ):
            return

        lang_env = self.env.lang or "en_US"
        langs = {lang for lang, _ in self.env["res.lang"].get_installed()}

        records_from.flush_model([name_field_from])
        records_from = records_from.with_context(check_translations=True)
        record_to = record_to.with_context(check_translations=True)
        existing_translation_dictionary = field_to.get_translation_dictionary(
            record_to[name_field_to],
            {
                lang: record_to.with_context(prefetch_langs=True, lang=lang)[
                    name_field_to
                ]
                for lang in langs
                if lang != lang_env
            },
        )
        extra_translation_dictionary = {}
        for record_from in records_from:
            extra_translation_dictionary.update(
                field_from.get_translation_dictionary(
                    record_from[name_field_from],
                    {
                        lang: record_from.with_context(prefetch_langs=True, lang=lang)[
                            name_field_from
                        ]
                        for lang in langs
                        if lang != lang_env
                    },
                )
            )
        for term, extra_translation_values in extra_translation_dictionary.items():
            existing_translation_values = existing_translation_dictionary.setdefault(
                term, {}
            )
            for lang, extra_translation in extra_translation_values.items():
                if existing_translation_values.get(lang, term) == term:
                    existing_translation_values[lang] = extra_translation
        translation_dictionary = existing_translation_dictionary

        langs.add("en_US")

        stored_translation = field_to._get_stored_translations(record_to) or {}
        for lang in langs:
            lang_ = f"_{lang}" if f"_{lang}" in stored_translation else lang
            stored_translation[lang_] = field_to.translate(
                lambda term, lang=lang: translation_dictionary.get(term, {}).get(lang),
                record_to[name_field_to],
            )
            if not self.env.context.get("delay_translations") and lang_.startswith("_"):
                stored_translation[lang] = stored_translation.pop(lang_)

        field_to._update_cache(
            record_to.with_context(prefetch_langs=True), stored_translation, dirty=True
        )
        record_to = record_to.with_context(check_translations=False)
        record_to[name_field_to] = record_to[name_field_to]

    @api.model
    def _save_oe_structure_hook(self):
        return {}

    @api.model
    def _are_archs_equal(self, arch1, arch2):
        if arch1.tag != arch2.tag:
            return False
        if arch1.text != arch2.text:
            return False
        if arch1.tail != arch2.tail:
            return False
        if arch1.attrib != arch2.attrib:
            return False
        if len(arch1) != len(arch2):
            return False
        return all(map(self._are_archs_equal, arch1, arch2, strict=True))

    @api.model
    def _get_allowed_root_attrs(self):
        return ["style", "class", "target", "href"]

    def replace_arch_section(self, section_xpath, replacement, replace_tail=False):
        self.check_singleton()
        arch = etree.fromstring(self.arch.encode("utf-8"))
        if not section_xpath:
            root = arch
        else:
            matches = arch.xpath(section_xpath)
            if len(matches) != 1:
                raise UserError(
                    _(
                        "Could not find a unique section to update (the page may have "
                        "changed since you started editing it, please reload)."
                    )
                )
            [root] = matches

        root.text = replacement.text

        for attribute in self._get_allowed_root_attrs():
            if attribute in replacement.attrib:
                root.attrib[attribute] = replacement.attrib[attribute]
            elif attribute in root.attrib:
                del root.attrib[attribute]

        if replace_tail:
            root.tail = replacement.tail
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @api.model
    def to_field_ref(self, el):
        attributes = {
            k: v for k, v in el.attrib.items() if not k.startswith("data-oe-")
        }
        attributes["t-field"] = el.get("data-oe-expression")

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    @api.model
    def to_empty_oe_structure(self, el):
        out = html.html_parser.makeelement(el.tag, attrib=el.attrib)
        out.tail = el.tail
        return out

    @api.model
    def _set_noupdate(self):
        self.sudo().mapped("model_data_id").write({"noupdate": True})

    def save(self, value, xpath=None):
        self.check_singleton()

        arch_section = html.fromstring(value, parser=html.HTMLParser(encoding="utf-8"))

        if xpath is None:
            self.save_embedded_field(arch_section)
            return

        for el in self.extract_embedded_fields(arch_section):
            self.save_embedded_field(el)

            el.getparent().replace(el, self.to_field_ref(el))

        for el in self.extract_oe_structures(arch_section):
            if self.save_oe_structure(el):
                empty = self.to_empty_oe_structure(el)
                if el == arch_section:
                    arch_section = empty
                else:
                    el.getparent().replace(el, empty)

        if self.key in {
            "website.footer_copyright_company_name",
            "website.template_footer_mega",
            "website.template_footer_mega_columns",
            "website.template_footer_mega_links",
        }:
            ancestor = self.inherit_id.inherit_id.inherit_id
            if not ancestor:
                # The website footer inheritance chain this shim expects is
                # shallower than usual (e.g. a customized/truncated chain);
                # skip the mega-footer column-class fixup rather than crash
                # on `ancestor.arch` (False on an empty recordset).
                _logger.warning(
                    "Skipping mega-footer column-class fixup for %s: "
                    "inherit_id chain is shorter than expected.",
                    self.key,
                )
            else:
                arch = etree.fromstring(ancestor.arch.encode("utf-8"))
                has_change = False
                for node in arch.xpath(
                    "//div[hasclass('o_footer_copyright')]//div[hasclass('col-sm')]"
                ):
                    if "col-md" not in node.get("class"):
                        node.set("class", node.get("class") + " col-md")
                        has_change = True
                if has_change:
                    ancestor.with_context(no_cow=True).write(
                        {"arch": etree.tostring(arch, encoding="unicode")}
                    )

        new_arch = self.replace_arch_section(xpath, arch_section)
        old_arch = etree.fromstring(self.arch.encode("utf-8"))
        if not self._are_archs_equal(old_arch, new_arch):
            self._set_noupdate()
            self.write({"arch": etree.tostring(new_arch, encoding="unicode")})
            self._copy_custom_snippet_translations(self, "arch_db")

    @api.model
    def _view_get_inherited_children(self, view):
        if self.env.context.get("no_primary_children", False):
            original_hierarchy = self.env.context.get(
                "__views_get_original_hierarchy", []
            )
            return view.inherit_children_ids.filtered(
                lambda extension: (
                    extension.mode != "primary" or extension.id in original_hierarchy
                )
            )
        return view.inherit_children_ids

    @api.model
    def _views_get(
        self, view_id, get_children=True, bundles=False, root=True, visited=None
    ):
        try:
            if isinstance(view_id, models.BaseModel):
                view = view_id
            else:
                view = self._get_template_view(view_id)
        except MissingError:
            _logger.warning("Could not find view object with view_id '%s'", view_id)
            return self.env["ir.ui.view"]

        if visited is None:
            visited = []
        original_hierarchy = self.env.context.get("__views_get_original_hierarchy", [])
        while root and view.inherit_id:
            original_hierarchy.append(view.id)
            view = view.inherit_id

        views_to_return = view

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._get_template_view(
                    child.get("t-call", child.get("t-call-assets"))
                )
            except MissingError:
                continue
            if (
                called_view
                and called_view not in views_to_return
                and called_view.id not in visited
            ):
                views_to_return += self._views_get(
                    called_view,
                    get_children=get_children,
                    bundles=bundles,
                    visited=visited + views_to_return.ids,
                )

        if not get_children:
            return views_to_return

        extensions = self._view_get_inherited_children(view)

        for extension in extensions.sorted(key=lambda v: v.id):
            if extension.id not in visited:
                for ext_view in self._views_get(
                    extension,
                    get_children=extension.active,
                    root=False,
                    visited=visited + views_to_return.ids,
                ):
                    if ext_view not in views_to_return:
                        views_to_return += ext_view
        return views_to_return

    @api.model
    def get_related_views(self, key, bundles=False):
        user_groups = set(self.env.user.group_ids)
        new_context = {
            **self.env.context,
            "active_test": False,
        }
        new_context.pop("lang", None)
        View = self.with_context(new_context)
        views = View._views_get(key, bundles=bundles)
        return views.filtered(
            lambda v: not v.group_ids or len(user_groups.intersection(v.group_ids))
        )

    @api.model
    def _get_snippet_addition_view_key(self, template_key, key):
        return f"{template_key}.{key}"

    @api.model
    def _snippet_save_view_values_hook(self):
        return {}

    def _find_available_name(self, name, used_names):
        attempt = 1
        candidate_name = name
        while candidate_name in used_names:
            attempt += 1
            candidate_name = f"{name} ({attempt})"
        return candidate_name

    @api.model
    def save_snippet(self, name, arch, template_key, snippet_key, thumbnail_url):
        app_name = template_key.split(".")[0]
        snippet_key = f"{snippet_key}_{uuid.uuid4().hex}"
        full_snippet_key = f"{app_name}.{snippet_key}"

        current_website = self.env["website"].browse(self.env.context.get("website_id"))
        website_domain = Domain(current_website.website_domain())
        used_names = self.search(
            Domain("name", "=like", f"{name}%") & website_domain
        ).mapped("name")
        name = self._find_available_name(name, used_names)

        arch_tree = html.fromstring(arch)
        attributes = self._get_cleaned_non_editing_attributes(arch_tree.attrib.items())
        for attr in list(arch_tree.attrib):
            if attr in attributes:
                arch_tree.attrib[attr] = attributes[attr]
            else:
                del arch_tree.attrib[attr]
        xml_arch = etree.tostring(arch_tree, encoding="utf-8")
        new_snippet_view_values = {
            "name": name,
            "key": full_snippet_key,
            "type": "qweb",
            "arch": xml_arch,
        }
        new_snippet_view_values.update(self._snippet_save_view_values_hook())
        custom_snippet_view = self.create(new_snippet_view_values)
        model = self.env.context.get("model")
        field = self.env.context.get("field")
        if field == "arch":
            field = "arch_db"
        res_id = self.env.context.get("resId")
        if model and field and res_id:
            self._copy_field_terms_translations(
                self.env[model].browse(int(res_id)),
                field,
                custom_snippet_view,
                "arch_db",
            )

        custom_section = self.search([("key", "=", template_key)])
        snippet_addition_view_values = {
            "name": name + " Block",
            "key": self._get_snippet_addition_view_key(template_key, snippet_key),
            "inherit_id": custom_section.id,
            "type": "qweb",
            "arch": f"""
                <data inherit_id="{template_key}">
                    <xpath expr="//snippets[@id='snippet_custom']" position="inside">
                        <t t-snippet="{full_snippet_key}" t-thumbnail="{thumbnail_url}"/>
                    </xpath>
                </data>
            """,
        }
        snippet_addition_view_values.update(self._snippet_save_view_values_hook())
        self.create(snippet_addition_view_values)
        return name

    @api.model
    def rename_snippet(self, name, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split(".")[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([("key", "=", custom_key)])
        if snippet_addition_view:
            snippet_addition_view.name = name + " Block"
        snippet_view.name = name

    @api.model
    def remove_snippet(self, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split(".")[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([("key", "=", custom_key)])
        (snippet_addition_view | snippet_view).unlink()
