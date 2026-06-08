import { fields, models } from "@web/../tests/web_test_helpers";

export class WebsiteTrack extends models.ServerModel {
    _name = "website.track";
    _description = "Visited Page";
    _order = "visit_datetime desc";

    visitor_id = fields.Many2one({ relation: "website.visitor" });

    page_id = fields.Many2one({ relation: "website.page" });
    url = fields.Char("Url");
    visit_datetime = fields.Datetime("Visit DateTime");
}

export class WebsiteVisitor extends models.ServerModel {
    _name = "website.visitor";

    country_id = fields.Many2one({ relation: "res.country", string: "Country" }); // FIXME: somehow not fetched properly
    display_name = fields.Char({ compute: "_compute_display_name" });
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

    _store_visitor_fields(res) {
        res.one("country_id", ["code"]);
        res.attr("display_name");
        res.one("lang_id", ["name"]);
        res.one("partner_id", (partnerRes) => partnerRes.one("country_id", ["code"]));
        res.one("website_id", "_store_website_fields");
    }
}
