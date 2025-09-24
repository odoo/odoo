import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    _defineButtonContent() {
        if (this.orderResModel !== "account.move") {
            super._defineButtonContent();
        } else if (this.props.context.product_catalog_move_type === "out_invoice") {
            this.buttonString = _t("Back to Invoice");
        } else if (this.props.context.product_catalog_move_type === "in_invoice") {
            this.buttonString = _t("Back to Bill");
        }
    },
});
