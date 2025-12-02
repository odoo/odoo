import { deserializeDateTime } from "@web/core/l10n/dates";
import { patch } from "@web/core/utils/patch";

import { WebsiteVisitor } from "@website/common/website_visitor_model";

const { DateTime } = luxon;

patch(WebsiteVisitor.prototype, {
    setup() {
        super.setup();
        this.page_visit_history = [];
    },
    get pageVisitHistoryText() {
        const history = [];
        for (const h of this.page_visit_history) {
            const [label, date] = h;
            const time = deserializeDateTime(date).toLocaleString(DateTime.TIME_24_SIMPLE);
            history.push(`${label} (${time})`);
        }
        return history.join(" → ");
    },
});
