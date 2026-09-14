/** @odoo-module native */
import { useFocusTitle } from "@project/utils/project_utils";
import { _t } from "@web/core/translation";
import { useService } from "@web/core/utils/hooks";
import { FormControllerWithHTMLExpander } from "@web/views/form_with_html_expander/form_controller_with_html_expander";
import { prepareStaticActionMenuItems } from "@web/views/view_utils";

import { ProjectTaskTemplateDropdown } from "../components/project_task_template_dropdown.js";
import { openDescriptionHistoryDialog } from "./description_history.js";

export const subTaskDeleteConfirmationMessage = _t(
    `Deleting a task will also delete its associated sub-tasks. \
If you wish to preserve the sub-tasks, make sure to unlink them from their parent task beforehand.

Are you sure you want to proceed?`,
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
            useFocusTitle(this.rootRef);
        }
    }

    /** @override */
    getStaticActionMenuItems() {
        return {
            ...super.getStaticActionMenuItems(),
            ...prepareStaticActionMenuItems({
                versionHistory: { callback: () => this.openHistoryDialog() },
            }),
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
        };
    }

    async openHistoryDialog() {
        openDescriptionHistoryDialog({
            record: this.model.root,
            resModel: this.props.resModel,
            dialogService: this.dialogService,
            notificationService: this.notifications,
            title: _t("Task Description History"),
            emptyLabel: _t("The task description was empty at the time."),
            noHistoryMessage: _t(
                "The task description lacks any past content that could be restored at the moment.",
            ),
        });
    }
}
