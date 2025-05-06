import { onWillStart, useEffect } from "@odoo/owl";
import { user } from "@web/core/user";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander'
import { ProjectTemplateDropdown } from "../components/project_template_dropdown";

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
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });

        if (this.props.focusTitle) {
            useEffect(
                (el) => {
                    if (el) {
                        const title = this.rootRef.el.querySelector("#name_0");
                        if (title) {
                            title.focus();
                        }
                    }
                },
                () => [this.rootRef.el]
            );
        }
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () => this.isProjectManager;
        }
        return actionMenuItems;
    }
}
