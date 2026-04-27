/** @odoo-module **/

import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";

export class FSMProductCatalogKanbanController extends ProductCatalogKanbanController {
    static template = "web.KanbanView";
    // changing the template to keep the o-kanban-button-new button

    setup() {
        super.setup();
        this.taskId = this.props.context.fsm_task_id;
    }

    /**
     * @override
     * overriding useless method to prevent wrong orm call
     *
     * **/
    async _defineButtonContent() {}
}
