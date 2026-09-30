import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";
import { useService } from '@web/core/utils/hooks';
import { markup, useEffect } from "@odoo/owl";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander';
import { getHtmlFieldMetadata, setHtmlFieldMetadata } from "@html_editor/fields/html_field";

import { ProjectTaskTemplateDropdown } from "../components/project_task_template_dropdown";

export const subTaskDeleteConfirmationMessage = _t(
    `Deleting a task will also delete its associated sub-tasks. \
If you wish to preserve the sub-tasks, make sure to unlink them from their parent task beforehand.

Are you sure you want to proceed?`
);

export class ProjectTaskFormController extends FormControllerWithHTMLExpander {
    static template = "project.ProjectTaskFormView";
    static components = {
        ...FormControllerWithHTMLExpander.components,
        ProjectTaskTemplateDropdown,
    };

    static props = {
        ...FormControllerWithHTMLExpander.props,
        focusTitle: {
            type: Boolean,
            optional: true,
        },
    };
    static defaultProps = {
        ...FormControllerWithHTMLExpander.defaultProps,
        focusTitle: false,
    };

    setup() {
        super.setup();
        this.notifications = useService("notification");

        if (this.props.focusTitle) {
            useEffect(
                () => {
                    if (this.rootRef) {
                        const title = this.rootRef.el.querySelector("#name_0");
                        if (title) {
                            title.focus();
                        }
                    }
                },
                () => []
            );
        }
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
                _t(
                    "The task description lacks any past content that could be restored at the moment."
                )
            );
            return;
        }

        this.dialogService.add(
            HistoryDialog,
            {
                title: _t("Task Description History"),
                noContentHelper: markup`
                    <span class='text-muted fst-italic'>${_t(
                        "The task description was empty at the time."
                    )}</span>`,
                recordId: record.resId,
                recordModel: this.props.resModel,
                versionedFieldName,
                historyMetadata,
                restoreRequested: (html, close) => {
                    this.dialogService.add(ConfirmationDialog, {
                        title: _t("Are you sure you want to restore this version ?"),
                        body: _t("Restoring will replace the current content with the selected version. Any unsaved changes will be lost."),
                        confirm: () => {
                            const restoredData = {};
                            const contentMetadata = getHtmlFieldMetadata(record.data[versionedFieldName]);
                            restoredData[versionedFieldName] = setHtmlFieldMetadata(html, contentMetadata);
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
