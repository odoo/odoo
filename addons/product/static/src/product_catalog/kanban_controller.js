import { KanbanController } from "@web/views/kanban/kanban_controller";
import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";

export class ProductCatalogKanbanController extends KanbanController {
    static template = "ProductCatalogKanbanController";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.orderId = this.props.context.orderId;
        this.orderResModel = this.props.context.product_catalog_order_model;
        this.backToQuotationDebounced = useDebounced(this.backToQuotation, 500)
    }

    // Force the slot for the "Back to Quotation" button to always be shown.
    get canCreate() {
        return true;
    }

    async backToQuotation() {
        // Restore the last form view from the breadcrumbs if breadcrumbs are available.
        // If, for some weird reason, the user reloads the page then the breadcrumbs are
        // lost, and we fall back to the form view ourselves.
        if (this.env.config.breadcrumbs.length > 1) {
            await this.actionService.restore();
        } else {
            await this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: this.orderResModel,
                views: [[false, "form"]],
                view_mode: "form",
                res_id: this.orderId,
            });
        }
    }
}
