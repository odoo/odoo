import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    get stateFiels() {
        return this.orderResModel === "account.move" ? ["state", "move_type"] : super.stateFiels;
    },

    _defineButtonContent() {
        if (this.orderStateInfo.move_type === "out_invoice") {
            this.buttonString = _t("Back to Invoice");
        } else if (this.orderStateInfo.move_type === "in_invoice") {
            this.buttonString = _t("Back to Bill");
        } else {
            super._defineButtonContent();
        }
    },
});
