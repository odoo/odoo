/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import HistoryDialog from '@web_editor/components/history_dialog/history_dialog';
import { useService } from '@web/core/utils/hooks';
import { markup } from '@odoo/owl';
import { escape } from '@web/core/utils/strings';

export const subTaskDeleteConfirmationMessage = _t(
    `Deleting a task will also delete its associated sub-tasks. \
If you wish to preserve the sub-tasks, make sure to unlink them from their parent task beforehand.

Are you sure you want to proceed?`
);

export class ProjectTaskFormController extends FormController {
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
                sequence: 50,
                icon: "fa fa-history",
                description: _t("Restore History"),
                callback: () => this.openHistoryDialog(),
            },
        };
    }

    get deleteConfirmationDialogProps() {
        const deleteConfirmationDialogProps = super.deleteConfirmationDialogProps;
        if (!this.model.root.data.subtask_count) {
            return deleteConfirmationDialogProps;
        }
        return {
            ...deleteConfirmationDialogProps,
            body: subTaskDeleteConfirmationMessage,
        }
    }

    async openHistoryDialog() {
        const record = this.model.root;
        const versionedFieldName = 'description';
        const historyMetadata = record.data["html_field_history_metadata"]?.[versionedFieldName];
        if (!historyMetadata) {
            this.notifications.add(
                escape(_t(
                    "The task description lacks any past content that could be restored at the moment."
                ))
            );
            return;
        }

        this.dialogService.add(
            HistoryDialog,
            {
                title: _t("Task Description History"),
                noContentHelper: markup(
                    `<span class='text-muted fst-italic'>${escape(
                        _t(
                            "The task description was empty at the time."
                        )
                    )}</span>`
                ),
                recordId: this.props.resId,
                recordModel: this.props.resModel,
                versionedFieldName,
                historyMetadata,
                restoreRequested: (html, close) => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Are you sure you want to restore this version ?"),
                        body: _t("Restoring will replace the current content with the selected version. Any unsaved changes will be lost."),
                        confirm: () => {
                            const restoredData = {};
                            restoredData[versionedFieldName] = html;
                            record.update(restoredData);
                            close();
                        },
                        confirmLabel: _t("Restore"),
                    });
                },
            },
        );
    }
}
