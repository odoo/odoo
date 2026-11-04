/** @odoo-module */
import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    async _defineButtonContent() {
        const fields = this.orderResModel === "account.move" ? ["state", "move_type"] : ["state"];
        const orderStateInfo = await this.orm.searchRead(
            this.orderResModel,
            [["id", "=", this.orderId]],
            fields,
        );
        if (orderStateInfo[0]?.move_type === "out_invoice") {
            this.buttonString = _t("Back to Invoice");
        } else if (orderStateInfo[0]?.move_type === "in_invoice") {
            this.buttonString = _t("Back to Bill");
        } else {
            super._defineButtonContent();
        }
    },
});
