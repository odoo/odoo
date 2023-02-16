/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { TodoFormController } from "@note/views/project_task_form/todo_form_controller";
const { onWillStart } = owl;
import { omit } from "@web/core/utils/objects";

/** TodoFormController is overrided to add the action to convert a to-do to a (non-private) task */

export class TodoFormControllerWithConversion extends TodoFormController {
    setup() {
        super.setup();

        onWillStart(async () => {
            this.conversion_view_id = await this.model.orm.call(
                'project.task',
                'get_conversion_view_id',
                [[]]
            );
            this.has_project_access = await this.model.orm.call(
                'project.task',
                'current_user_has_project_access',
                [[]]
            );
        });
    }

    get actionMenuItems() {
        // Restrict to-do actions to static one and Convert to Task (if user has access to Project)
        const staticActionItems = Object.entries(this.getStaticActionMenuItems())
            .filter(([key, item]) => item.isAvailable === undefined || item.isAvailable())
            .sort(([k1, item1], [k2, item2]) => (item1.sequence || 0) - (item2.sequence || 0))
            .map(([key, item]) => Object.assign({ key }, omit(item, "isAvailable", "sequence")));
        const menuItems = {
            action: staticActionItems,
        };

        if (this.has_project_access) {
            menuItems.action.push({
                description: _lt("Convert to Task"),
                callback: () => {
                    this.model.actionService.doAction({
                        type: 'ir.actions.act_window',
                        name: _lt('Convert to task'),
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
