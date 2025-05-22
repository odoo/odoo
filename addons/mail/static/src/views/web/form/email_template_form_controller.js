import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { escape } from "@web/core/utils/strings";
import { FormController } from "@web/views/form/form_controller";
import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { markup } from "@odoo/owl";

export class EmailTemplateFormController extends FormController {
    setup() {
        super.setup();
        this.notifications = useService("notification");
    }

    /**
     * @override
     */
    getStaticActionMenuItems() {
        return {
            ...super.getStaticActionMenuItems(),
            openHistoryDialog: {
                sequence: 15,
                icon: "fa fa-history",
                description: _t("Version History"),
                callback: this.openHistoryDialog.bind(this),
            },
        };
    }

    async openHistoryDialog() {
        const record = this.model.root;
        const versionedFieldName = "body_html";
        const historyMetadata = record.data["html_field_history_metadata"]?.[versionedFieldName];
        if (!historyMetadata) {
            this.notifications.add(
                escape(
                    _t(
                        "The template body lacks any past content that could be restored at the moment."
                    )
                )
            );
            return;
        }

        this.dialogService.add(HistoryDialog, {
            title: _t("Email Template History"),
            noContentHelper: markup(
                `<span class='text-muted fst-italic'>${escape(
                    _t("The template body was empty at the time.")
                )}</span>`
            ),
            recordId: record.resId,
            recordModel: this.props.resModel,
            versionedFieldName,
            historyMetadata,
            restoreRequested: (html, close) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Are you sure you want to restore this version ?"),
                    body: _t(
                        "Restoring will replace the current content with the selected version. Any unsaved changes will be lost."
                    ),
                    confirm: () => {
                        record.update({ [versionedFieldName]: html });
                        close();
                    },
                    confirmLabel: _t("Restore"),
                });
            },
        });
    }
}
