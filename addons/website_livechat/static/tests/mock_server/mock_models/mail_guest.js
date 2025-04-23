import { mailModels } from "@mail/../tests/mail_test_helpers";
import { fields } from "@web/../tests/web_test_helpers";

export class MailGuest extends mailModels.MailGuest {
    visitor_id = fields.One2many({
        relation: "website.visitor",
    });
    website_name = fields.Char({
        related: "visitor_id.website_id.name",
    });
    lang_name = fields.Char({
        related: "visitor_id.lang_id.name",
    })
    is_connected = fields.Boolean({
        related: "visitor_id.is_connected",
    });
    history = fields.Char({
        related: "visitor_id.history"
    });
    country_id = fields.Many2one({
        relation: "res.country",
        related: "visitor_id.country_id",
    });

    get default_fields() {
        return [...super.default_fields, "website_name", "lang_name", "is_connected","history", "country_id"];
    }
}
