import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            ...this.state,
            ratingValue: this.props.composer.message?.rating_value ?? 4,
            starValue: this.props.composer.message?.rating_value ?? 4,
        });
    },

    get allowUpload() {
        return super.allowUpload && !this.props.composer.portalComment;
    },

    editMessage() {
        if (this.props.composer.portalComment) {
            this.savePublisherComment();
            return;
        }
        super.editMessage();
    },

    async savePublisherComment() {
        const data = await rpc("/website/rating/comment", {
            rating_id: this.message.rating.id,
            publisher_comment: this.props.composer.text.trim(),
        });
        this.message.rating = data;
        this.props.onPostCallback();
    },

    onMoveStar(ev) {
        var index = parseInt(ev.currentTarget.getAttribute("index"));
        this.state.starValue = index + 1;
    },

    onClickStar() {
        this.state.ratingValue = this.state.starValue;
    },

    postData(composer) {
        const postData = super.postData(composer);
        if (this.env.displayRating && !this.props.composer.portalComment) {
            postData.extraData.rating_value = this.state.ratingValue;
        }
        return postData;
    },

    async sendMessage() {
        if (!this.env.ratingOptions?.messageId) {
            return super.sendMessage(...arguments);
        }
        this.editMessage();
    },
});
