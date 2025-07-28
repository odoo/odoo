import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { RatingPopupComposer } from "@portal_rating/interactions/portal_rating_composer";

patch(RatingPopupComposer.prototype, {
    updateOptions(data) {
        super.updateOptions(...arguments);
        this.options.force_submit_url =
            data.force_submit_url ||
            (this.options.default_message_id && "/mail/message/update_content");
    },

    reloadRatingPopupComposer() {
        super.reloadRatingPopupComposer(...arguments);
        if (this.options.res_model !== "slide.channel") {
            return;
        }
        const reviewEl = document.querySelector("#review-tab");
        if (reviewEl) {
            reviewEl.textContent = this.rating_count
                ? _t("Reviews (%s)", this.rating_count)
                : _t("Reviews");
        }
    },
});
