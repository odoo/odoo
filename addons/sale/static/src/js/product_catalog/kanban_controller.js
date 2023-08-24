/** @odoo-module **/

import { KanbanController } from "@web/views/kanban/kanban_controller";
import { onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";


export class ProductCatalogKanbanController extends KanbanController {
    static template = "sale.ProductCatalogKanbanController";

    setup() {
        super.setup();
        this.action = useService("action");
        this.orm = useService("orm");
        this.orderId = this.props.context.order_id;

        onWillStart(async () => {
            // Define the content of the button.
            const orderStateInfo = await this.orm.searchRead(
                "sale.order", [["id", "=", this.orderId]], ["state"]
            );
            const orderIsQuotation = ["draft", "sent"].includes(orderStateInfo[0].state);
            this.buttonString = `Back to ${orderIsQuotation ? "Quotation" : "Order"}`
        })
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
            await this.action.restore();
        } else {
            await this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "sale.order",
                views: [[false, "form"]],
                view_mode: "form",
                res_id: this.orderId,
            });
        }
    }
}
