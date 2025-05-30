import { PortalChatter } from "@portal/chatter/frontend/portal_chatter";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(PortalChatter.prototype, {
    /**
     * Update review count on review tab in courses
     *
     * @override
     * @private
     */
    async _reloadChatterContent(data) {
        super._reloadChatterContent(...arguments);
        if (this.props.resModel === "slide.channel") {
            document.querySelector("#review-tab").textContent = _t(
                "Reviews (%s)",
                data.rating_count || data["mail.thread"][0].rating_count
            );
        }
    },
});
