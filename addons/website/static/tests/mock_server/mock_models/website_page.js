import { fields, models } from "@web/../tests/web_test_helpers";

export class WebsitePage extends models.Model {
    _name = "website.page";
    _description = "Page";

    name = fields.Char();
}
