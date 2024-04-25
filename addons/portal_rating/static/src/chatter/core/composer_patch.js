import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            ...this.state,
            ratingValue: 4,
            starValue: 4,
        });
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
        if (this.env.displayRating && !this.message) {
            postData.options.rating_value = this.state.ratingValue;
        }
        return postData;
    },
});
