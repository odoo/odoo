/** @odoo-module native */
import { onWillStart } from "@odoo/owl";
import { useFocusTitle } from "@project/utils/project_utils";
import { user } from "@web/core/user";
import { FormControllerWithHTMLExpander } from "@web/views/form_with_html_expander/form_controller_with_html_expander";

import { ProjectTemplateDropdown } from "../components/project_template_dropdown.js";

export class ProjectProjectFormController extends FormControllerWithHTMLExpander {
    static template = "project.ProjectFormView";
    static components = {
        ...FormControllerWithHTMLExpander.components,
        ProjectTemplateDropdown,
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
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup(
                "project.group_project_manager",
            );
            this.featuresToObserve = await this.orm.call(
                this.props.resModel,
                "get_features_enabled",
                [],
            );
        });

        if (this.props.focusTitle) {
            useFocusTitle(this.rootRef);
        }
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (!this.isProjectManager) {
            ["duplicate", "archive", "unarchive"].forEach(
                (item) => delete actionMenuItems[item],
            );
        }
        return actionMenuItems;
    }

    /** @override */
    async onRecordSaved(record, changes) {
        await super.onRecordSaved(...arguments);
        const updatedFields = Object.keys(this.featuresToObserve).filter(
            (fName) => fName in changes,
        );
        if (updatedFields.length) {
            const updatedFeatures = await record.model.orm.call(
                record.resModel,
                "get_features_enabled",
                [updatedFields],
            );
            if (
                Object.entries(updatedFeatures).some(
                    ([fName, value]) => value !== this.featuresToObserve[fName],
                )
            ) {
                this.actionService.doAction("reload_context");
            }
        }
    }
}
