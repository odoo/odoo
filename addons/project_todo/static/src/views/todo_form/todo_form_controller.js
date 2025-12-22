import { onWillStart } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { user } from "@web/core/user";
import { FormControllerWithHTMLExpander } from "@resource/views/form_with_html_expander/form_controller_with_html_expander";

/**
 *  The FormController is overridden to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb as well as the mark as done button next to it.
 */

export class TodoFormController extends FormControllerWithHTMLExpander {
    setup() {
        super.setup();
        onWillStart(async () => {
            this.projectAccess = await user.hasGroup("project.group_project_user");
        });
    }

    get actionMenuItems() {
        const actionToKeep = ["archive", "unarchive", "duplicate", "delete"];
        const menuItems = super.actionMenuItems;
        const filteredActions =
            menuItems.action?.filter((action) => actionToKeep.includes(action.key)) || [];

        if (this.projectAccess && !this.model.root.data.project_id) {
            filteredActions.push({
                description: _t("Convert to Task"),
                callback: () => {
                    this.model.action.doAction(
                        "project_todo.project_task_action_convert_todo_to_task",
                        {
                            props: {
                                resId: this.model.root.resId,
                            },
                        }
                    );
                },
            });
        }
        menuItems.action = filteredActions;
        menuItems.print = [];
        return menuItems;
    }
}
