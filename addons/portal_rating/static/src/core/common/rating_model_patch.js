import { Rating } from "@rating/core/common/rating_model";
import { fields } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

const ratingPatch = {
    setup() {
        super.setup(...arguments);
        this.publisher_id = fields.One("Persona");
        this.message_id = fields.One("mail.message", { inverse: "rating_id" });
    },
};
patch(Rating.prototype, ratingPatch);
