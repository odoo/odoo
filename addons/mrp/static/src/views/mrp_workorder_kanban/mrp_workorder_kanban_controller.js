import { useService } from "@web/core/utils/hooks";

import { KanbanController } from "@web/views/kanban/kanban_controller";

export class MrpWorkorderKanbanController extends KanbanController {
    async setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
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
