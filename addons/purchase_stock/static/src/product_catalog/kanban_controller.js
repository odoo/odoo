import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanController.prototype, {
    async openSuggestWizard() {
        const action = await this.model.orm.call("purchase.order", "action_display_suggest", [
            this.orderId,
        ]);
        const productIds = this.model.root.records.map((rec) => rec.data.id);
        action.context.default_product_ids = productIds;
        this.actionService.doAction(action);
    },
});
