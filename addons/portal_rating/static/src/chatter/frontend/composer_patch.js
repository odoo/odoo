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

    async editMessage() {
        if (this.props.composer.portalComment) {
            await this.savePublisherComment();
            return;
        }
        await super.editMessage();
    },

    async savePublisherComment() {
        if (!this.state.active) {
            return;
        }
        this.state.active = false;
        const data = await rpc("/website/rating/comment", {
            rating_id: this.message.rating_id.id,
            publisher_comment: this.props.composer.composerText.trim(),
        });
        this.message.rating_id = data;
        this.props.onPostCallback();
    },

    get canProcessMessage() {
        return super.canProcessMessage || (this.message && this.message.rating_value);
    },

    get askDeleteFromEdit() {
        return super.askDeleteFromEdit && !this.message.rating_value;
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
