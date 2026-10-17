import { Rating } from "@rating/core/common/rating_model";
import { patchModel } from "@mail/model/export";

export const ratingPatch = patchModel(Rating, {
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
