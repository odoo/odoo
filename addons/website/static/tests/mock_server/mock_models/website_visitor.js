import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { fields, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class WebsiteVisitor extends models.ServerModel {
    _name = "website.visitor";

    country_id = fields.Many2one({ relation: "res.country", string: "Country" }); // FIXME: somehow not fetched properly
    display_name = fields.Char({ compute: "_compute_display_name" });
    page_visit_history = fields.Char();
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

    /** @param {number[]} ids */
    _to_store(store) {
        /** @type {import("mock_models").ResCountry} */
        const ResCountry = this.env["res.country"];
        /** @type {import("mock_models").ResLang} */
        const ResLang = this.env["res.lang"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];
        /** @type {import("mock_models").Website} */
        const Website = this.env["website"];

        for (const visitor of this) {
            const [data] = this._read_format(visitor.id, ["display_name"]);
            data.country_id = mailDataHelpers.Store.one(ResCountry.browse(visitor.country_id));
            data.page_visit_history = JSON.parse(visitor.page_visit_history || "[]");
            data.lang_id = mailDataHelpers.Store.one(ResLang.browse(visitor.lang_id));
            data.partner_id = mailDataHelpers.Store.one(
                ResPartner.browse(visitor.partner_id),
                makeKwArgs({ fields: ["country_id"] })
            );
            data.website_id = mailDataHelpers.Store.one(Website.browse(visitor.website_id));
            store._add_record_fields(this.browse(visitor.id), data);
        }
    }
}
