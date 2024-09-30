import { fields } from "@mail/model/export";

import { Rating } from "@rating/core/common/rating_model";

import { patch } from "@web/core/utils/patch";

const ratingPatch = {
    setup() {
        super.setup(...arguments);
        /** @type {string} */
        this.publisher_comment;
        this.publisher_datetime = fields.Datetime()
        this.publisher_id = fields.One("res.partner");
    },
};
patch(Rating.prototype, ratingPatch);
