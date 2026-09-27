import { useSubEnv } from "@web/owl2/utils";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogAccountMoveLine } from "./account_move_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();

        useSubEnv({
            ...this.env,
            selectedSectionId: this.env.searchModel.selectedSectionId,
        });
    },

    get orderLineComponent() {
        if (this.env.orderResModel === "account.move") {
            return ProductCatalogAccountMoveLine;
        }
        return super.orderLineComponent;
    },

    _getUpdateQuantityAndGetPriceParams() {
        return {
            ...super._getUpdateQuantityAndGetPriceParams(),
            section_id: this.env.selectedSectionId ?? this.env.searchModel.selectedSectionId,
        };
    },

    addProduct(qty = 1) {
        if (this.productCatalogData.quantity === 0 && qty < this.productCatalogData.min_qty) {
            qty = this.productCatalogData.min_qty; // Take seller's minimum if trying to add less
        }
        super.addProduct(qty);
    },

    _updateProductCatalogData(result) {
        super._updateProductCatalogData(result);

        if (result.subtotal !== undefined) {
            const parsedSubtotal = parseFloat(result.subtotal);
            const previousSubtotal = this.productCatalogData.subtotal ?? 0;
            const subtotalDelta = parsedSubtotal - previousSubtotal;

            this.productCatalogData.subtotal = parsedSubtotal;

            if (subtotalDelta) {
                this.notifySectionSubtotalChange(subtotalDelta);
            }
        }
    },

    notifySectionSubtotalChange(subtotalDelta) {
        this.env.searchModel.trigger("section-subtotal-change", {
            sectionId: this.env.selectedSectionId,
            subtotalDelta: subtotalDelta,
        });
    },
});
