from odoo import api, fields, models, Command, _

from lxml import etree

def adapt_arch_to_model(arch, fields_dict):
    """
    Take the generic arch with studio_placeholder tag and replace
    them with fields found in the model
    """
    arch = etree.fromstring(arch, parser=etree.XMLParser(remove_blank_text=True, resolve_entities=False))

    name_placeholders = arch.findall(".//studio_placeholder[@for='name']")
    for name_placeholder in name_placeholders:
        replacement_name = etree.fromstring("<span t-field='record.display_name'/>")
        name_placeholder.getparent().replace(name_placeholder, replacement_name)

    monetary_placeholders = arch.findall(".//studio_placeholder[@for='monetary']")
    monetary_name = next(filter(lambda key: fields_dict[key].type == 'monetary', fields_dict.keys()), False)
    for monetary_placeholder in monetary_placeholders:
        if monetary_name:
            replacement_monetary = etree.fromstring(f"<span class='o_website_monetary' t-field='record.{monetary_name}'/>")
            monetary_placeholder.getparent().replace(monetary_placeholder, replacement_monetary)
        else:
            monetary_placeholder.getparent().remove(monetary_placeholder)

    tags_placeholders = arch.findall(".//studio_placeholder[@for='tags']")
    for tags_placeholder in tags_placeholders:
        tags_name = None
        if 'tag_ids' in fields_dict:
            tags_name = 'tag_ids'
            color_name = 'color'
        elif 'x_studio_tag_ids' in fields_dict:
            tags_name = 'x_studio_tag_ids'
            color_name = 'x_color'
        if tags_name:
            tags_arch = f"""
                    <t t-if="record.{tags_name}" t-foreach="record.{tags_name}" t-as="tag">
                        <span t-field="tag.display_name" t-attf-class="badge o_website_tag #{{'o_tag_color_'+str(tag.{color_name})}}"/>
                    </t>
                """
            tags_class = tags_placeholder.get('class') or ""
            replacement_tags = etree.fromstring(f"<div class='o_website_tags {tags_class}'>{tags_arch}</div>")
            tags_placeholder.getparent().replace(tags_placeholder, replacement_tags)
        else:
            tags_placeholder.getparent().remove(tags_placeholder)

    image_placeholders = arch.findall(".//studio_placeholder[@for='image']")
    image_name = next(filter(lambda key: "image" in key, fields_dict), False)
    for image_placeholder in image_placeholders:
        if image_name:
            image_class = image_placeholder.get('class') or ""
            image_style = image_placeholder.get('style') or ""
            image_arch = f"""
                    <t>
                        <img t-if='record.{image_name}' class='o_website_image {image_class}' style='{image_style}' t-attf-src='data:image/png;base64,{{{{record.{image_name}}}}}'/>
                        <div t-else="" class='o_website_image bg-light {image_class}'/>
                    </t>
                """
            replacement_image = etree.fromstring(image_arch)
            image_placeholder.getparent().replace(image_placeholder, replacement_image)
        else:
            image_placeholder.getparent().remove(image_placeholder)

    html_placeholders = arch.findall(".//studio_placeholder[@for='html']")
    if 'x_studio_website_description' in fields_dict:
        html_name = 'x_studio_website_description'
    else:
        html_name = next(filter(lambda key: fields_dict[key].type == 'html', fields_dict.keys()), False)
    for html_placeholder in html_placeholders:
        if html_name:
            editor_message = _("Drag building blocks to edit the website description of this record.")
            replacement_html = etree.fromstring(f"<div class='o_website_html' t-field='record.{html_name}' data-editor-message='{editor_message}'/>")
            html_placeholder.getparent().replace(html_placeholder, replacement_html)
        else:
            html_placeholder.getparent().remove(html_placeholder)

    return etree.tostring(arch, encoding='utf-8', pretty_print=True)

class WebsiteControllerPageStudio(models.Model):
    _inherit = "website.controller.page"

    use_menu = fields.Boolean(compute="_compute_use_menu_auto_single_page", readonly=False,
        string="Create Website Menu")
    auto_single_page = fields.Boolean(compute="_compute_use_menu_auto_single_page", readonly=False,
        string="Create Single Page", help="If checked, a single page will be created along with your listing page")

    @api.depends_context("default_use_menu", "default_auto_single_page")
    def _compute_use_menu_auto_single_page(self):
        for rec in self:
            if rec.id:
                # the two fields computed here only have sense when creating a new record, they are creation flags that allow for triggering
                # some specific behavior in the create method. Hence, computing those fields when a record already exists doesn't make sense
                # as they would take the value from the context anyway, regardless of the record's reality
                rec.use_menu = False
                rec.auto_single_page = False
            else:
                rec.use_menu = self._context.get("default_use_menu", False)
                rec.auto_single_page = self._context.get("default_auto_single_page", False)

    @api.model_create_multi
    def create(self, vals_list):
        if not self._context.get("website_studio.create_page"):
            return super().create(vals_list)

        Website = self.env["website"]
        for values in list(vals_list):
            if not values.get("model_id", values.get("model_name")):
                continue
            page_type = values.get("page_type")
            name_slugified = values.get("name_slugified")
            model = self.env["ir.model"].browse(values["model_id"])
            if 'x_studio_website_description' not in self.env[model.model]._fields:
                # add a field on the model to store the description
                self.env["ir.model.fields"].create({
                    'name': 'x_studio_website_description',
                    'model_id': model.id,
                    'ttype': 'html',
                    'field_description': _('Website Description'),
                    'copied': True,
                    'sanitize_overridable': True,
                })

            if not values.get("view_id") and page_type and name_slugified:
                template = "website_studio.default_listing" if page_type == "listing" else "website_studio.default_record_page"
                view = self._create_auto_view(template, name_slugified, values.get("website_id"), model)
                values["view_id"] = view.id

            if values.get("auto_single_page"):
                view = self._create_auto_view("website_studio.default_record_page", name_slugified, values.get("website_id"), model)
                sub_vals = dict(values, page_type="single", view_id=view.id, auto_single_page=False, use_menu=False)
                vals_list.append(sub_vals)

            if not values.get("menu_ids") and values.get("use_menu") and "page_name" in values:
                # Fix me: make one menu per website ???
                website = Website.browse(values.get("website_id")) or Website.get_current_website()
                menu_values = {
                    'name': values["page_name"],
                    'url': f"/model/{name_slugified}",
                    'website_id': website.id,
                    'parent_id': website.menu_id.id,
                }
                values["menu_ids"] = [Command.create(menu_values)]

            if not self._get_ir_model_access(model):
                self.env["ir.model.access"].create({
                    "name": "Website integration: public model access",
                    "model_id": model.id,
                    "perm_read": True,
                    "group_id": self.env.ref("website.website_page_controller_expose").id
                })

        return super().create(vals_list)

    @api.model
    def _create_auto_view(self, template, view_key, website_id, model=None):
        template_record = self.env.ref(template)
        key = self.env["website"].get_unique_key(view_key, "website_studio")
        view = template_record.copy({'website_id': website_id, 'key': key})

        arch = template_record.arch.replace(template, key)
        if self._context.get("website_studio.create_page") and model:
            arch = self._replace_arch_placeholders(arch, model)

        view.with_context(lang=None).write({
            'arch': arch,
            'name': view_key,
        })
        return view

    def _replace_arch_placeholders(self, arch, model):
        return adapt_arch_to_model(arch, self.env[model.model]._fields)

    def _get_ir_model_access(self, model):
        return self.env["ir.model.access"].with_context(active_test=False).search([("model_id", "=", model.id), ("group_id", "=", self.env.ref("website.website_page_controller_expose").id)])
