/* @odoo-module */

import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";
import { useState } from "@odoo/owl";

const Labels = {
    0: "",
    1: "I hate it",
    2: "I don't like it",
    3: "It's okay",
    4: "I like it",
    5: "I love it",
};

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.state = useState({
            ...this.state,
            ratingValue: 0,
            starValue: 4.0,
            rateText: undefined,
        });
    },

    editMessage() {
        if (!this.props.composer.fullFeature) {
            this.savePublisherComment();
            return;
        }
        super.editMessage();
    },

    async savePublisherComment() {
        const data = await this.rpc("/website/rating/comment", {
            rating_id: this.message.rating.id,
            publisher_comment: this.props.composer.textInputContent.trim(),
        });
        this.store.Message.insert({
            id: this.message.id,
            rating: data,
        });
        this.props.onPostCallback();
    },

    onMoveStar(ev) {
        var index = parseInt(ev.currentTarget.getAttribute("index"));
        Object.assign(this.state, {
            starValue: index + 1,
            rateText: _t(Labels[index + 1]),
        });
    },

    onLeaveStar() {
        this.state.rateText = undefined;
    },

    onClickStar() {
        this.state.ratingValue = this.state.starValue;
    },

    get starValInteger() {
        return Math.floor(this.state.starValue);
    },

    get starValDecimal() {
        return this.state.starValue - this.starValInteger;
    },

    get emptyStar() {
        return 5 - (this.starValInteger + Math.ceil(this.starValDecimal));
    },

    postData() {
        const postData = super.postData();
        if (this.state.ratingValue) {
            postData["ratingValue"] = this.state.ratingValue;
        }
        return postData;
    },
});
