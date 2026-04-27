/** @odoo-module **/

import { onWillDestroy } from "@odoo/owl";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { KanbanController } from "@web/views/kanban/kanban_controller";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        this.catalogKanbanUpdates = [];
        // The `onCatalogUpdated` props provides a callback to be called
        // once all the catalogKanbanUpdates have been resolved
        if (this.props.onCatalogUpdated) {
            onWillDestroy(async () => {
                Promise.all(this.catalogKanbanUpdates).then(() => {
                    this.props.onCatalogUpdated();
                });
            });
        }
    },

    get canCreate() {
        return !this.props.context.from_shop_floor;  // Hide the "Back to Production" button if we are in the shop floor.
    },

    pushCatalogKanbanUpdate(update) {
        this.catalogKanbanUpdates.push(update);
    },
});

patch(ProductCatalogKanbanController, {
    props: {
        ...KanbanController.props,
        onCatalogUpdated: { type: Function, optional: true },
    },
});
