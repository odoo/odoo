/** @odoo-module */

import { FormController } from '@web/views/form/form_controller';
import { DeleteSubtasksConfirmationDialog } from "@project/components/delete_subtasks_confirmation_dialog/delete_subtasks_confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import HistoryDialog from '@web_editor/components/history_dialog/history_dialog';

export class ProjectTaskFormController extends FormController {
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

    deleteRecord() {
        if (!this.model.root.data.subtask_count) {
            return super.deleteRecord();
        }
        this.dialogService.add(DeleteSubtasksConfirmationDialog, {
            confirm: async () => {
                await this.model.root.delete();
                if (!this.model.root.resId) {
                    this.env.config.historyBack();
                }
            },
        });
    }

    async openHistoryDialog() {
        const record = this.model.root;
        const versionedFieldName = 'description';
        const historyMetadata = record.data["html_field_history_metadata"]?.[versionedFieldName];
        if (!historyMetadata) {
            return;
        }

        this.dialogService.add(
            HistoryDialog,
            {
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
