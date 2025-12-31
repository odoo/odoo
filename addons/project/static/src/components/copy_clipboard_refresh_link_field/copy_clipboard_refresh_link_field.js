import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import {
    CopyClipboardCharField,
    copyClipboardCharField,
} from "@web/views/fields/copy_clipboard/copy_clipboard_field";

export class ProjectCopyClipboardRefreshLinkField extends CopyClipboardCharField {
    static template = "project.ProjectCopyClipboardRefreshLinkField";

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.notificationService = useService("notification");
        this.orm = useService("orm");
    }

    onRefreshClick() {
        this.dialogService.add(ConfirmationDialog, {
            body: _t("Generating a new link will disable the old one. Do you want to proceed?"),
            confirmLabel: _t("Refresh Link"),
            confirm: async () => {
                const resModel = this.props.record.data.res_model;
                const resId = this.props.record.data.res_id;
                await this.orm.call(resModel, "action_regenerate_access_token", [[resId]]);
                await this.props.record.load();
                this.notificationService.add(_t("Share link refreshed"), { type: "success" });
            },
            cancel: () => {},
        });
    }
}

export const projectCopyClipboardRefreshLinkField = {
    ...copyClipboardCharField,
    component: ProjectCopyClipboardRefreshLinkField,
};

registry.category("fields").add("ProjectCopyClipboardRefreshLink", projectCopyClipboardRefreshLinkField);
