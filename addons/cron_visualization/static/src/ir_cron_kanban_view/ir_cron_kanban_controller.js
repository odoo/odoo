/** @odoo-module */

import { KanbanController } from "@web/views/kanban/kanban_controller";

import { onWillStart, onWillDestroy } from "@odoo/owl";

export class IrCronKanbanController extends KanbanController {
    setup() {
        super.setup();
        // Every 5 seconds, refresh the kanban view
        this._interval = null;
        onWillStart(async () => {
            this._interval = setInterval(this.refreshData.bind(this), 2500);
        });
        onWillDestroy(() => {
            clearInterval(this._interval);
        });
    }
    async refreshData() {
        await this.model.root.load();
        this.render(true);
    }
}
