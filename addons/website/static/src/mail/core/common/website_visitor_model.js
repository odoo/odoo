import { fields, Record } from "@mail/model/export";

export class WebsiteVisitor extends Record {
    static _name = "website.visitor";

    country = fields.One("res.country", {
        /** @this {import("models").WebsiteVisitor} */
        compute() {
            return this.partner_id?.country_id || this.country_id;
        },
    });
    country_id = fields.One("res.country");
    /** @type {string} */
    display_name;
    lang_id = fields.One("res.lang");
    partner_id = fields.One("res.partner");
    website_id = fields.One("website");
}

WebsiteVisitor.register();
