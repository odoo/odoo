import { Thread } from "@mail/core/common/thread_model";
import { fields } from "@mail/model/misc";
import { _t } from "@web/core/l10n/translation";

import { patch } from "@web/core/utils/patch";

/** @type {import("models").Thread} */
const threadPatch = {
    setup() {
        super.setup();
        this.collaborator_ids = fields.Many("res.partner");
    },
    /** @override */
    getFollowerRemovalDialogProps(follower) {
        if (follower.partner_id.in(this.collaborator_ids)) {
            return {
                title: _t("Remove Collaborator"),
                body: _t(
                    "This follower is currently a project collaborator. Removing them will revoke their portal access to the project. Are you sure you want to proceed?"
                ),
                confirmLabel: _t("Remove Collaborator"),
                cancelLabel: _t("Discard"),
            };
        }
        return super.getFollowerRemovalDialogProps(follower);
    },
};
patch(Thread.prototype, threadPatch);
