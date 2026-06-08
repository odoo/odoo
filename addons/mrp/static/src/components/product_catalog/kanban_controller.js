import { ProductCatalogKanbanController } from "@product/product_catalog/kanban_controller";
import { patch } from "@web/core/utils/patch";
import { _t } from "@web/core/l10n/translation";

patch(ProductCatalogKanbanController.prototype, {
    setOrderStateInfo() {
        if (["mrp.bom", "mrp.production"].includes(this.orderResModel)) {
            return {};
        }
        return super.setOrderStateInfo();
    },

    _defineButtonContent() {
        if (this.orderResModel === "mrp.bom") {
            this.buttonString = _t("Back to BoM");
        } else if (this.orderResModel === "mrp.production") {
            this.buttonString = _t("Back to Production");
        } else {
            super._defineButtonContent();
        }
    },
});
