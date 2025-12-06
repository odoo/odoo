import RatingPopupComposer from "@portal_rating/js/portal_rating_composer";
import { _t } from "@web/core/l10n/translation";

RatingPopupComposer.include({
    _update_options: function (data) {
        this._super(...arguments);
        this.options.force_submit_url =
            data.force_submit_url ||
            (this.options.default_message_id && "/slides/mail/update_comment");
    },
    _reloadRatingPopupComposer: function () {
        if (this.options.res_model !== "slide.channel") {
            return this._super(...arguments);
        }
        const reviewEl = document.querySelector("#review-tab");
        if (reviewEl) {
            reviewEl.textContent = this.rating_count
                ? _t("Reviews (%s)", this.rating_count)
                : _t("Reviews");
        }
        const editedMessage = this.options["mail.message"]?.[0];
        // Only update the modal when editing the logged user message
        if (!editedMessage || this.options.partner_id === editedMessage.author?.id) {
            return this._super(...arguments);
        }
    },
});
