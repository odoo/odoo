
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { usePlugin } from "@odoo/owl";
import { ActionPlugin } from "@web/webclient/actions/action_plugin";
import { ORM } from "@web/core/orm_plugin";

export class MrpWorkorderKanbanController extends KanbanController {
    async setup() {
        super.setup();
        this.action = usePlugin(ActionPlugin);
        this.orm = usePlugin(ORM);
    }

    async selectOrdersToPlan() {
        const action = await this.orm.call(this.model.config.resModel, "action_select_mo_to_plan", [false]);
        this.action.doAction(
            action,
            {
                onClose: async () => { await this.model.load(); },
            }
        );
    }
}
