import { FollowerList } from "@mail/core/web/follower_list";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { patch } from "@web/core/utils/patch";

const followerListPatch = {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    },
    /**
     * @param {MouseEvent} ev
     * @param {import("models").Follower} follower
     */
    async onClickRemove(ev, follower) {
        if (follower.partner_id.in(follower.thread.collaborator_ids)) {
            this.dialogService.add(ConfirmationDialog, {
                title: _t("Remove Collaborator"),
                body: _t(
                    "This follower is currently a project collaborator. Removing them will revoke their portal access to the project. Are you sure you want to proceed?"
                ),
                confirmLabel: _t("Remove Collaborator"),
                cancelLabel: _t("Discard"),
                confirm: () => super.onClickRemove(ev, follower),
                cancel: () => {},
            });
        } else {
            super.onClickRemove(ev, follower);
        }
    },
};
patch(FollowerList.prototype, followerListPatch);
