import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogAccountMoveLine } from "./account_move_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();
    },

    get orderLineComponent() {
        if (this.orderLineProps.orderResModel === "account.move") {
            return ProductCatalogAccountMoveLine;
        }
        return super.orderLineComponent;
    },

    _getUpdateQuantityAndGetPriceParams() {
        return {
            ...super._getUpdateQuantityAndGetPriceParams(),
            section_id: this.env.searchModel.selectedSection?.sectionId,
        };
    },

    addProduct(qty = 1) {
        if (this.productCatalogData.quantity === 0 && qty < this.productCatalogData.min_qty) {
            qty = this.productCatalogData.min_qty; // Take seller's minimum if trying to add less
        }
        super.addProduct(qty);
    },

    updateQuantity(quantity, debounce = true) {
        const lineCountChange = (quantity > 0) - (this.productCatalogData.quantity > 0);
        if (lineCountChange !== 0) {
            this.notifyLineCountChange(lineCountChange);
        }

        super.updateQuantity(quantity, debounce);
    },

    notifyLineCountChange(lineCountChange) {
        this.env.searchModel.trigger("section-line-count-change", {
            sectionId: this.env.searchModel.selectedSection?.sectionId,
            lineCountChange: lineCountChange,
        });
    },
});
