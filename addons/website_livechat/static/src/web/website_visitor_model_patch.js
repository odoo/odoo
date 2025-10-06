import { fields } from "@mail/core/common/record";

import { deserializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

import { WebsiteVisitor } from "@website/common/website_visitor_model";

const { DateTime } = luxon;

/** @type {import("models").WebsiteVisitor} */
const websiteVisitorPatch = {
    setup() {
        super.setup();
        /** @type {Array<[string, string]>} */
        this.page_visit_history = [];
        this.discuss_channel_ids = fields.Many("mail.thread");
    },
    /** @returns {string} */
    get pageVisitHistoryText() {
        const history = [];
        for (const h of this.page_visit_history) {
            const [label, date] = h;
            const time = deserializeDateTime(date).toLocaleString(DateTime.TIME_24_SIMPLE);
            history.push(`${label} (${time})`);
        }
        return history.join(" → ");
    },
};
patch(WebsiteVisitor.prototype, websiteVisitorPatch);
