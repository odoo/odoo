
import { fields, models } from "@web/../tests/web_test_helpers";

export class WebsiteVisitor extends models.ServerModel {
    _name = "website.visitor";

    country_id = fields.Many2one({ relation: "res.country", string: "Country" }); // FIXME: somehow not fetched properly
    display_name = fields.Char({ compute: "_compute_display_name" });
    history = fields.Char();
    lang_id = fields.Many2one({ relation: "res.lang", string: "Language" }); // FIXME: somehow not fetched properly
    partner_id = fields.Many2one({ relation: "res.partner", string: "Contact" }); // FIXME: somehow not fetched properly
    website_id = fields.Many2one({ relation: "website", string: "Website" });

    _compute_display_name() {
        for (const record of this) {
            record.display_name =
                this.env["res.partner"].browse(record.partner_id)[0]?.name ||
                `Website Visitor #${record.id}`;
        }
    }
}
