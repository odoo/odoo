import { Rating } from "@rating/core/common/rating_model";

import { patch } from "@web/core/utils/patch";

patch(Rating.prototype, {
    setup() {
        super.setup(...arguments);
        /** @type {string|undefined} */
        this.publisher_avatar = undefined;
        /** @type {string|undefined} */
        this.publisher_comment = undefined;
        /** @type {string|undefined} */
        this.publisher_datetime = undefined;
        /** @type {number|false|undefined} */
        this.publisher_id = undefined;
        /** @type {string|undefined} */
        this.publisher_name = undefined;
    },
});
