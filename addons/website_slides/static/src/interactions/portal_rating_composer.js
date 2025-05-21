import { RatingPopupComposer } from "@portal_rating/interactions/portal_rating_composer";
import { patch } from "@web/core/utils/patch";

patch(RatingPopupComposer.prototype, {
    setup() {
        super.setup(...arguments);
        // When the review is emptied in the chatter, display the button as it cannot be edited in the chatter anymore.
        this.deleteMessageEvent = "WEBSITE_SLIDES:CHANNEL_DELETE_MESSAGE";
        this.deleteMessageListener = ({ detail }) => {
            if (detail.id === this.documentId) {
                this.isBtnDisplayed = true;
                this.updateContent();
            }
        };
        this.env.bus.addEventListener(this.deleteMessageEvent, this.deleteMessageListener);
    },

    updateOptions(data) {
        super.updateOptions(...arguments);
        this.options.force_submit_url =
            data.force_submit_url ||
            (this.options.default_message_id && "/mail/message/update_content");
    },

    destroy() {
        super.destroy();
        this.env.bus.removeEventListener(this.deleteMessageEvent, this.deleteMessageListener);
    },
});
