import { FollowerList } from "@mail/core/web/follower_list";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ProjectFollowerList extends FollowerList {
    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    async onClickRemove(ev, follower) {
        if (follower.is_project_collaborator) {
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
    }
}
