import { WebsiteVisitor } from "@website/mail/core/common/website_visitor_model";
import { patchModel } from "@mail/model/export";

const { DateTime } = luxon;

export const websiteVisitorPatch = patchModel(WebsiteVisitor, {
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
});
