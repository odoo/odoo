import { patch } from "@web/core/utils/patch";

import { WebsiteVisitor } from "@website/mail/core/common/website_visitor_model";

const { DateTime } = luxon;

/** @type {import("models").WebsiteVisitor} */
const websiteVisitorPatch = {
    /** @returns {string} */
    get pageVisitHistoryText() {
        return this.last_track_ids
            .map(
                (track) =>
                    `${track.page_id.name} (${track.visit_datetime.toLocaleString(
                        DateTime.TIME_24_SIMPLE
                    )})`
            )
            .join(" → ");
    },
};
patch(WebsiteVisitor.prototype, websiteVisitorPatch);
