/** @odoo-module */

import { useSubEnv } from "@odoo/owl";
import { KanbanController } from "@web/views/kanban/kanban_controller";

export class TimesheetTimerKanbanController extends KanbanController {
    setup() {
        super.setup();
        useSubEnv({
            config: {
                ...this.env.config,
                disableSearchBarAutofocus: true,
            },
        });
    }
}
