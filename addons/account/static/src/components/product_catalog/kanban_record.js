/** @odoo-module native */
import {
    ProductCatalogKanbanRecord,
    productCatalogOrderLines,
} from "@product/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";

import { ProductCatalogAccountMoveLine } from "./account_move_line.js";

productCatalogOrderLines.add("account.move", ProductCatalogAccountMoveLine);

patch(ProductCatalogKanbanRecord.prototype, {
    get sectionIdOfPendingUpdate() {
        return this._sectionIdOfPendingUpdate === undefined
            ? this.env.searchModel.selectedSection.sectionId
            : this._sectionIdOfPendingUpdate;
    },

    _getUpdateQuantityAndGetPriceParams() {
        return {
            ...super._getUpdateQuantityAndGetPriceParams(),
            section_id: this.sectionIdOfPendingUpdate,
        };
    },

    addProduct(qty = 1) {
        if (
            this.productCatalogData.quantity === 0 &&
            qty < this.productCatalogData.min_qty
        ) {
            qty = this.productCatalogData.min_qty;
        }
        super.addProduct(qty);
    },

    updateQuantity(quantity) {
        this._sectionIdOfPendingUpdate = this.env.searchModel.selectedSection.sectionId;
        if (!this.productCatalogData.readOnly) {
            const lineCountChange =
                (quantity > 0) - (this.productCatalogData.quantity > 0);
            if (lineCountChange !== 0) {
                this.notifyLineCountChange(lineCountChange);
            }
        }

        super.updateQuantity(quantity);
    },

    notifyLineCountChange(lineCountChange) {
        this.env.searchModel.trigger("section-line-count-change", {
            sectionId: this.sectionIdOfPendingUpdate,
            lineCountChange: lineCountChange,
        });
    },
});
