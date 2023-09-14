/* @odoo-module */

import { Message } from "@mail/core/common/message";
import { convertBrToLineBreak } from "@mail/utils/common/format";

import { patch } from "@web/core/utils/patch";

patch(Message.prototype, {
    setup() {
        super.setup(...arguments);
        this.state.editRating = false;
    },

    onClikEditRating() {
        this.state.editRating = !this.state.editRating;
        if (this.state.editRating) {
            const messageContent = convertBrToLineBreak(
                this.props.message.rating.publisher_comment
            );
            this.store.Composer.insert({
                message: this.props.message,
                textInputContent: messageContent,
                fullFeature: false,
                selection: {
                    start: messageContent.length,
                    end: messageContent.length,
                    direction: "none",
                },
            });
        }
    },

    exitEditRatingMode() {
        this.message.composer = null;
        this.state.editRating = false;
    },

    async deletePublisherComment() {
        const data = await this.rpc("/website/rating/comment", {
            rating_id: this.message.rating.id,
            publisher_comment: "",
        });
        this.store.Message.insert({
            id: this.message.id,
            rating: data,
        });
    },
});
