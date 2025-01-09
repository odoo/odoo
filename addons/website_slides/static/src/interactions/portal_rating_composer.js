import { patch } from "@web/core/utils/patch";
import { RatingPopupComposer } from "@portal_rating/interactions/portal_rating_composer";

patch(RatingPopupComposer.prototype, {
    updateOptions(data) {
        super.updateOptions(...arguments);
        this.options.force_submit_url =
            data.force_submit_url ||
            (this.options.default_message_id && "/slides/mail/update_comment");
    },
});
