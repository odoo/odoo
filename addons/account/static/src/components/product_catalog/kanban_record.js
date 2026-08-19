import { useSubEnv } from "@web/owl2/utils";
import { ProductCatalogKanbanRecord } from "@product/product_catalog/kanban_record";
import { patch } from "@web/core/utils/patch";

patch(ProductCatalogKanbanRecord.prototype, {
    setup() {
        super.setup();

        useSubEnv({
            ...this.env,
            selectedSectionId: this.env.searchModel.selectedSectionId,
        });
    },

    _getUpdateCatalogQuantityParams() {
        return {
            ...super._getUpdateCatalogQuantityParams(),
            section_id: this.env.selectedSectionId ?? this.env.searchModel.selectedSectionId,
        };
    },


    async _onQuantityChange() {
        const update_values = await super._onQuantityChange();

        if (update_values.subtotal !== undefined) {
            const parsedSubtotal = parseFloat(update_values.subtotal);
            const previousSubtotal = this.productCatalogData.subtotal ?? 0;
            const subtotalDelta = parsedSubtotal - previousSubtotal;

            this.productCatalogData.subtotal = parsedSubtotal;

            if (subtotalDelta) {
                this.notifySectionSubtotalChange(subtotalDelta);
            }
        }

        return update_values;
    },

    notifySectionSubtotalChange(subtotalDelta) {
        this.env.searchModel.trigger("section-subtotal-change", {
            sectionId: this.env.selectedSectionId,
            subtotalDelta: subtotalDelta,
        });
    },
});
