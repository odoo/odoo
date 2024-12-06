import { Rating } from "@rating/core/common/rating_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(Rating.prototype, {
    setup() {
        super.setup(...arguments);
        this.publisher_id = Record.one("Persona");
        this.message_id = Record.one("mail.message");
    },
});
