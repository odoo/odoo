import { Thread } from "@mail/core/common/thread_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const threadPatch = patchModel(Thread, {
    setup() {
        super.setup();
        this.collaborator_ids = fields.Many("res.partner");
    },
});
