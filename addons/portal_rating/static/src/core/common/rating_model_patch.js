import { fields } from "@mail/model/export";

import { Rating } from "@rating/core/common/rating_model";

import { patch } from "@web/core/utils/patch";

patch(Rating.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|undefined} */
        this.publisher_comment = undefined;
        this.publisher_datetime = fields.Datetime();
        this.publisher_id = fields.One("res.partner");
    },
});
