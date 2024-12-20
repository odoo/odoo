import { onWillStart } from "@odoo/owl";
import { user } from "@web/core/user";
import { FormControllerWithHTMLExpander } from '@resource/views/form_with_html_expander/form_controller_with_html_expander'

export class ProjectProjectFormController extends FormControllerWithHTMLExpander {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.isProjectManager = await user.hasGroup('project.group_project_manager');
        });
    }

    getStaticActionMenuItems() {
        const actionMenuItems = super.getStaticActionMenuItems(...arguments);
        if (actionMenuItems.archive.isAvailable) {
            actionMenuItems.archive.isAvailable = () => this.isProjectManager;
        }
        return actionMenuItems;
    }
}
