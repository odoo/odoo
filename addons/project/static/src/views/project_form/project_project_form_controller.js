import { onWillStart, t, onMounted, useProps, markup } from "@odoo/owl";
import { FormControllerWithHTMLExpander } from "@resource/views/form_with_html_expander/form_controller_with_html_expander";
import { user } from "@web/core/user";
import { formControllerProps } from "@web/views/form/form_controller";
import { ProjectTemplateDropdown } from "../components/project_template_dropdown";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { HistoryDialog } from "@html_editor/components/history_dialog/history_dialog";
import { getHtmlFieldMetadata, setHtmlFieldMetadata } from "@html_editor/fields/html_field";
import { useService } from "@web/core/utils/hooks";

export class ProjectProjectFormController extends FormControllerWithHTMLExpander {
    static components = {
        ...FormControllerWithHTMLExpander.components,
        ProjectTemplateDropdown,
    };
    props = useProps({
        ...formControllerProps,
        focusTitle: t.boolean().optional(false),
    });

    setup() {
        super.setup();
        this.notifications = useService("notification");
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup("project.group_project_manager");
            this.featuresToObserve = await this.orm.call(
                this.modelParams.config.resModel,
                "check_features_enabled",
                []
            );
        });

        if (this.props.focusTitle) {
            onMounted(() => this.rootRef().querySelector("#name_0")?.focus());
        }
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () => this.isProjectManager;
        }
        return {
            ...actionMenuItems,
            openHistoryDialog: {
                sequence: 15,
                icon: "history",
                description: _t("Version History"),
                callback: () => this.openHistoryDialog(),
            },
        };
    }

    /**
     * @override
     */
    async onRecordSaved(record, changes) {
        await super.onRecordSaved(...arguments);
        const updatedFields = Object.keys(this.featuresToObserve).filter(
            (fName) => fName in changes
        );
        if (updatedFields.length) {
            const updatedFeatures = await record.model.orm.call(
                record.resModel,
                "check_features_enabled",
                [updatedFields]
            );
            if (
                Object.entries(updatedFeatures).some(
                    ([fName, value]) => value !== this.featuresToObserve[fName]
                )
            ) {
                this.model.action.doAction("reload_context");
            }
        }
    }

    async openHistoryDialog() {
        const record = this.model.root;
        const versionedFieldName = "description";
        const historyMetadata = record.data["html_field_history_metadata"]?.[versionedFieldName];
        if (!historyMetadata) {
            this.notifications.add(
                _t(
                    "The project description lacks any past content that could be restored at the moment."
                )
            );
            return;
        }

        this.dialogService.add(HistoryDialog, {
            title: _t("Project Description History"),
            noContentHelper: markup`
                        <span class='text-muted fst-italic'>${_t(
                            "The project description was empty at the time."
                        )}</span>`,
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
                        const restoredData = {};
                        const contentMetadata = getHtmlFieldMetadata(
                            record.data[versionedFieldName]
                        );
                        restoredData[versionedFieldName] = setHtmlFieldMetadata(
                            html,
                            contentMetadata
                        );
                        record.update(restoredData);
                        close();
                    },
                    confirmLabel: _t("Restore"),
                });
            },
        });
    }
}
