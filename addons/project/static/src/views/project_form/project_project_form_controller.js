import { onWillStart, t, onMounted, useProps } from "@odoo/owl";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander';
import { user } from "@web/core/user";
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

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () => this.isProjectManager;
        }
        return actionMenuItems;
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
