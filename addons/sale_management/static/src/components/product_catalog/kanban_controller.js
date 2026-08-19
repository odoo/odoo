import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    setOrderStateInfo() {
        if (this.orderResModel === "sale.order.template") {
            return {};
        }
        return super.setOrderStateInfo();
    },

    _defineButtonContent() {
        if (this.orderResModel === "sale.order.template") {
            this.buttonString = _t("Back to Template");
        } else {
            super._defineButtonContent();
        }
    },
});
