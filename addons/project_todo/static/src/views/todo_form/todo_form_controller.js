/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { FormController } from "@web/views/form/form_controller";
import { TodoEditableBreadcrumbName } from "@project_todo/components/todo_editable_breadcrumb_name/todo_editable_breadcrumb_name";
import { TodoDoneCheckmark } from "@project_todo/components/todo_done_checkmark/todo_done_checkmark";

import { onWillStart } from "@odoo/owl";

/**
 *  The FormController is overridden to be able to manage the edition of the name of a to-do directly
 *  in the breadcrumb as well as the mark as done button next to it.
 */

export class TodoFormController extends FormController {
    static template = "project_todo.TodoFormView";

    setup() {
        super.setup();
        onWillStart(async () => {
            this.projectAccess = await this.user.hasGroup("project.group_project_user");
        });
    }

    get actionMenuItems() {
        const actionToKeep = ["archive", "unarchive", "duplicate", "delete"];
        const menuItems = super.actionMenuItems;
        const filteredActions =
            menuItems.action?.filter((action) => actionToKeep.includes(action.key)) || [];

        if (this.projectAccess) {
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

Object.assign(TodoFormController.components, {
    TodoEditableBreadcrumbName,
    TodoDoneCheckmark,
});
