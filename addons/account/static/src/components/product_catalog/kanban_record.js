import { useSubEnv } from "@web/owl2/utils";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { ProductCatalogAccountMoveLine } from "./account_move_line";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();

        this._pendingSectionUpdate = null;

        useSubEnv({
            ...this.env,
            selectedSectionId: this.env.searchModel.selectedSection.sectionId,
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
            section_id: this.env.selectedSectionId ?? this.env.searchModel.selectedSection.sectionId,
        };
    },

    addProduct(qty = 1) {
        if (this.productCatalogData.quantity === 0 && qty < this.productCatalogData.min_qty) {
            qty = this.productCatalogData.min_qty; // Take seller's minimum if trying to add less
        }
        super.addProduct(qty);
    },

    updateQuantity(quantity) {
        const lineCountChange = (quantity > 0) - (this.productCatalogData.quantity > 0);

        const oldSubtotal = this.productCatalogData.quantity * this.productCatalogData.price;

        super.updateQuantity(quantity);

        this._pendingSectionUpdate = {
            oldSubtotal,
            lineCountChange,
        };
    },

    async _onQuantityChange() {
        await super._onQuantityChange();

        if (this._pendingSectionUpdate) {
            const newSubtotal = this.productCatalogData.quantity * this.productCatalogData.price;

            const subtotalDelta =
                newSubtotal - this._pendingSectionUpdate.oldSubtotal;

            this.notifySectionUpdate({
                lineCountChange: this._pendingSectionUpdate.lineCountChange,
                subtotalDelta,
            });

            this._pendingSectionUpdate = null;
        }
    },

    notifySectionUpdate({lineCountChange, subtotalDelta}) {
        this.env.searchModel.trigger('section-line-count-change', {
            sectionId: this.env.selectedSectionId,
            lineCountChange: lineCountChange,
            subtotalDelta: subtotalDelta,
        });
    },
})
