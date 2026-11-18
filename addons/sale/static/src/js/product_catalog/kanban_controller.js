import { onWillUnmount } from "@odoo/owl";
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanController.prototype, {
    setup() {
        super.setup();
        // The catalog updates the lines one request at a time: their changes are logged at once
        // when leaving it, whichever way the user leaves
        onWillUnmount(() => this.logLineChanges());
    },

    async onWillStart() {
        await super.onWillStart();
        // The order, even when the catalog is opened from another record (e.g. a field service
        // intervention, which doesn't fetch the order state)
        this.catalogOrderId = this.props.context.product_catalog_order_id;
        if (
            this.orderResModel === "sale.order"
            && this.catalogOrderId
            && this.orderStateInfo?.state !== "draft"  // Not logged on drafts
        ) {
            this.lineChangesValues = await this.orm.call(
                "sale.order",
                "get_catalog_line_changes_values",
                [[this.catalogOrderId]]
            );
        }
    },

    async backToQuotation() {
        // Before going back, so that the order shows the message
        await this.logLineChanges();
        return super.backToQuotation();
    },

    async logLineChanges() {
        const lineChangesValues = this.lineChangesValues;
        if (!lineChangesValues) {
            return;
        }
        this.lineChangesValues = null;
        await this.orm.call(
            "sale.order",
            "log_catalog_line_changes",
            [[this.catalogOrderId], lineChangesValues]
        );
    },
});
