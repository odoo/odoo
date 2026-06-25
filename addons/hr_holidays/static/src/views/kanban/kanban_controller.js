import { plugin, providePlugins } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";
import { TimeOffPlugin } from "../time_off_plugin";

export class TimeOffKanbanController extends KanbanController {
    setup() {
        super.setup();

        providePlugins([TimeOffPlugin]);

        this.timeOffPlugin = plugin(TimeOffPlugin);
    }

    afterExecuteActionButton(clickParams) {
        super.afterExecuteActionButton(clickParams);

        this.timeOffPlugin.updateDashboard();
    }
}
