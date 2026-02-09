import { useSubEnv } from "@web/owl2/utils";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { EventBus } from "@odoo/owl";

export class TimeOffKanbanController extends KanbanController {
    setup() {
        super.setup();
        useSubEnv({
            timeOffBus: new EventBus(),
        });
    }

    afterExecuteActionButton(clickParams) {
        super.afterExecuteActionButton(clickParams);
        this.env.timeOffBus.trigger("update_dashboard");
    }
}
