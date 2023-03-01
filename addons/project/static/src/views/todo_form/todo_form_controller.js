/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { TodoFormController } from "@note/views/todo_form/todo_form_controller";
const { onWillStart } = owl;

/** TodoFormController is overridden to add the action to convert a to-do to a (non-private) task */

export class TodoFormControllerWithConversion extends TodoFormController {
    setup() {
        super.setup();

        onWillStart(async () => {
            this.conversion_view_id = await this.model.orm.call(
                'project.task',
                'get_conversion_view_id',
                [],
            );
            this.has_project_access = await this.model.orm.call(
                'project.task',
                'current_user_has_project_access',
                [],
            );
        });
    }

    get actionMenuItems() {
        // Restrict to-do actions to static one and Convert to Task (if user has access to Project)
        const menuItems = super.actionMenuItems;

        if (this.has_project_access) {
            menuItems.action.push({
                description: _lt("Convert to Task"),
                callback: () => {
                    this.model.actionService.doAction({
                        type: 'ir.actions.act_window',
                        name: _lt('Convert to Task'),
                        target: 'new',
                        res_model: 'project.task',
                        res_id: this.model.root.data.id,
                        views: [[this.conversion_view_id, "form"]],
                    });
                }
            });
        }

        return menuItems;
    }
}
