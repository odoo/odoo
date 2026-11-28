import { onWillStart, t, onMounted, useProps } from "@odoo/owl";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander';
import { user } from "@web/core/user";
import { _t } from "@web/core/l10n/translation";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formControllerProps } from "@web/views/form/form_controller";
import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

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
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
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

    async onWillSaveRecord(record) {
        if (
            !this.isProjectManager &&
            record._values.user_id?.id === user.userId &&
            record.data.user_id?.id !== user.userId
        ) {
            return new Promise((resolve) => {
                this.dialogService.add(ConfirmationDialog, {
                    title: _t("Warning"),
                    confirmLabel: _t("Unassign me"),
                    confirmClass: "btn-danger",
                    body: _t(
                        "Unassigning yourself from this project's manager role is only reversible by an administrator, and might lock you out of the project entirely. Are you sure you want to continue?"
                    ),
                    confirm: () => resolve(true),
                    cancel: () => resolve(false),
                });
            });
        }
        return super.onWillSaveRecord(...arguments);
    }

    get isUserProjectManager() {
        return (this.isProjectManager || this.model.root.data.is_user_project_manager);
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () =>
                this.isUserProjectManager && this.model.root.isActive;
        }
        if (actionMenuItems.unarchive.isAvailable) {
            actionMenuItems.unarchive.isAvailable = () =>
                this.isUserProjectManager && !this.model.root.isActive;
        }
        return actionMenuItems;
    }

    get actionMenuItems() {
        const menuItems = super.actionMenuItems;
        if (!this.isUserProjectManager) {
            menuItems.action = [];
        }
        return menuItems;
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
}
