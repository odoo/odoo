import { Composer } from "@mail/core/common/composer";

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.portalState = useState({
            ratingValue: this.defaultRatingValue,
            starValue: this.defaultRatingValue,
        });
    },

    get allowUpload() {
        return super.allowUpload && !this.props.composer.portalComment;
    },

    get defaultRatingValue() {
        return this.message?.rating_id?.rating || this.env.defaultRatingValue || 4;
    },

    get hasValidMessage() {
        return (
            super.hasValidMessage ||
            (this.message && this.message.rating_id) ||
            (!this.message && this.portalState.ratingValue)
        );
    },

    get SEND_TEXT() {
        if (this.props.composer.message && this.env.inPortalRatingComposer) {
            return _t("Save");
        }
        return super.SEND_TEXT;
    },

    get sendButtonAttClass() {
        return {
            ...super.sendButtonAttClass,
            "border-0": this.props.composer.message && !this.env.inPortalRatingComposer,
        };
    },

    get isSendButtonDisabled() {
        return !this.env.allowVoidContent && super.isSendButtonDisabled;
    },

    get showSendButtonText() {
        return super.showSendButtonText || (this.message && this.env.inPortalRatingComposer);
    },

    get inChatterStyle() {
        return super.inChatterStyle || this.env.inPortalRatingComposer;
    },

    get showSendKeybinds() {
        return super.showSendKeybinds && !this.env.inPortalRatingComposer;
    },

    get shouldEditMessage() {
        return super.shouldEditMessage || this.message.rating_id;
    },

    get updateData() {
        const updateData = super.updateData;
        if (this.message.rating_id && this.message.rating_id.rating !== this.portalState.ratingValue) {
            updateData.rating_value = this.portalState.ratingValue;
        }
        return updateData;
    },

    async editMessage() {
        if (this.props.composer.portalComment) {
            this.savePublisherComment();
            return;
        }
        super.editMessage();
    },

    async savePublisherComment() {
        const data = await rpc("/website/rating/comment", {
            rating_id: this.message.rating_id.id,
            publisher_comment: this.props.composer.text.trim(),
        });
        this.store.insert(data);
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
        if (this.env.displayRating) {
            postData.rating_value = this.portalState.ratingValue;
        }
        return postData;
    },

    async sendMessage() {
        if (this.env.inPortalRatingComposer && this.message) {
            this.editMessage();
        }
        return super.sendMessage(...arguments);
    },
});
