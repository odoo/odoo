import { fields, Record } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;

export class WebsiteVisitor extends Record {
    static _name = "website.visitor";
    static id = "id";

    country = fields.One("res.country", {
        /** @this {import("models").WebsiteVisitor} */
        compute() {
            return this.partner_id?.country_id || this.country_id;
        },
    });
    country_id = fields.One("res.country");
    discuss_channel_ids = fields.Many("Thread");
    /** @type {string} */
    display_name;
    lang_id = fields.One("res.lang");
    partner_id = fields.One("Persona");
    website_id = fields.One("website");

    get historyLocalized() {
        const history = [];
        for (const h of this.history_data ?? []) {
            const [label, date] = h;
            const time = deserializeDateTime(date).toLocaleString(DateTime.TIME_24_SIMPLE);
            history.push(`${label} (${time})`);
        }
        return history.join(" → ");
    }
}

WebsiteVisitor.register();
