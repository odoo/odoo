import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.collaborator_ids = fields.Many("res.partner");
    },
};
patch(Thread.prototype, threadPatch);
