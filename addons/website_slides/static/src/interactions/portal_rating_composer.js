import { RatingPopupComposer } from "@portal_rating/interactions/portal_rating_composer";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(RatingPopupComposer.prototype, {
    start() {
        super.start(...arguments);
        if (this.options?.res_model !== "slide.channel") {
            return;
        }
        // When the review is emptied in the chatter, display the button as it cannot be edited in the chatter anymore.
        this.addListener(this.env.bus, "WEBSITE_SLIDES:CHANNEL_DELETE_MESSAGE", ({ detail }) => {
            // this.documentId can be a string representing a number
            if (detail.id === Number(this.documentId)) {
                this.isBtnDisplayed = true;
                this.updateContent();
            }
        });
    },

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
