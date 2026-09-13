from odoo import api, fields, models
from odoo.tools.translate import html_translate


class Website(models.Model):
    _inherit = "website"

    name_translated = fields.Char(translate=True)


class TestModel(models.Model):
    _name = "test.model"
    _inherit = [
        "mixin.website.seo.metadata",
        "mixin.website.published",
        "mixin.website.searchable",
    ]
    _description = "Website Model Test"

    name = fields.Char(
        translate=True,
        required=True,
    )
    submodel_ids = fields.One2many(
        comodel_name="test.submodel",
        inverse_name="test_model_id",
        string="Submodels",
    )
    website_description = fields.Html(
        string="Description for the website",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
        default="""<div class="o_test_website_description"><p>A simple website description content.</p></div>""",
    )
    tag_id = fields.Many2one(comodel_name="test.tag")

    @api.model
    def _search_get_detail(self, website, order, options):
        return {
            "model": "test.model",
            "base_domain": [],
            "search_fields": ["name", "submodel_ids.name", "submodel_ids.tag_id.name"],
            "fetch_fields": ["name"],
            "mapping": {
                "name": {"name": "name", "type": "text", "match": True},
                "website_url": {"name": "name", "type": "text", "truncate": False},
            },
            "icon": "fa-regular fa-square-check",
            "order": "name asc, id desc",
        }

    def open_website_url(self):
        self.check_singleton()
        return self.env["website"].get_client_action(f"/test_model/{self.id}")


class TestSubmodel(models.Model):
    _name = "test.submodel"
    _description = "Website Submodel Test"

    name = fields.Char(required=True)
    test_model_id = fields.Many2one(comodel_name="test.model")
    tag_id = fields.Many2one(comodel_name="test.tag")


class TestTag(models.Model):
    _name = "test.tag"
    _description = "Website Tag Test"

    name = fields.Char(required=True)


class TestModelMultiWebsite(models.Model):
    _name = "test.model.multi.website"
    _inherit = [
        "mixin.website.published.multi",
    ]
    _description = "Multi Website Model Test"

    name = fields.Char(required=True)
    # `cascade` is needed as there is demo data for this model which are bound
    # to website 2 (demo website). But some tests are unlinking the website 2,
    # which would fail if the `cascade` is not set. Note that the website 2 is
    # never set on any records in all other modules.
    website_id = fields.Many2one(
        comodel_name="website",
        string="Website",
        ondelete="cascade",
    )


class TestModelExposed(models.Model):
    _name = "test.model.exposed"
    _inherit = [
        "mixin.website.seo.metadata",
        "mixin.website.published",
    ]
    _description = "Website Model Test Exposed"
    _rec_name = "name"

    name = fields.Char()
