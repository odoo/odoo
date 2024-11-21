import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalState = useState({
            ratingValue: 4,
            starValue: 4,
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
        const index = parseInt(ev.currentTarget.getAttribute("index"));
        this.portalState.starValue = index + 1;
    },

    onClickStar() {
        this.portalState.ratingValue = this.portalState.starValue;
    },

    get postData() {
        const postData = super.postData;
        if (this.env.displayRating && !this.message) {
            postData.rating_value = this.portalState.ratingValue;
        }
        return postData;
    },
});
