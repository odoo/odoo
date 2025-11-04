import { Composer } from "@mail/core/common/composer";

import { patch } from "@web/core/utils/patch";
import { rpc } from "@web/core/network/rpc";
import { useState } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";

const MAX_STAR_RATING = 5;
const DEFAULT_STAR_RATING = 4;

patch(Composer.prototype, {
    setup() {
        super.setup(...arguments);
        this.MAX_STAR_RATING = MAX_STAR_RATING;
        this.portalState = useState({
            hoveredRatingValue: undefined,
            ratingValue: DEFAULT_STAR_RATING,
            /** @deprecated: use 'hoveredRatingValue' instead */
            get starValue() {
                return this.hoveredRatingValue;
            },
            /** @deprecated: use 'hoveredRatingValue' instead */
            set starValue(val) {
                this.hoveredRatingValue = val;
            },
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

    get visibleRatingValue() {
        return this.portalState.hoveredRatingValue ?? this.portalState.ratingValue;
    },

    onMoveStar(ev) {
        this.handleStar(ev, { hovered: !isMobileOS() });
    },

    handleStar(ev, { hovered } = {}) {
        const index = parseInt(ev.currentTarget.getAttribute("index"));
        if (Number.isNaN(index) || index < 0 || index > MAX_STAR_RATING - 1) {
            if (hovered) {
                this.portalState.hoveredRatingValue = undefined;
            }
            return;
        }
        if (hovered) {
            this.portalState.hoveredRatingValue = index + 1;
        } else {
            this.portalState.ratingValue = index + 1;
        }
    },

    onClickStar(ev) {
        this.handleStar(ev);
    },

    onMouseLeaveStar(ev) {
        if (!isMobileOS()) {
            this.handleStar(ev, { hovered: true });
        }
    },

    get postData() {
        const postData = super.postData;
        if (this.env.displayRating && !this.message) {
            postData.rating_value = this.portalState.ratingValue;
        }
        this.portalState.ratingValue = DEFAULT_STAR_RATING;
        return postData;
    },
});
