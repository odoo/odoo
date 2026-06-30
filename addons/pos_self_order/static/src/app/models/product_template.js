import { ProductTemplate } from "@point_of_sale/app/models/product_template";
import { patch } from "@web/core/utils/patch";

patch(ProductTemplate.prototype, {
    get isConfigurableForSelfOrder() {
        if (this.config.self_ordering_mode !== "kiosk") {
            return this.isConfigurable();
        }
        return this.attribute_line_ids.some(
            (a) =>
                a.product_template_value_ids.length > 1 || a.attribute_id.display_type === "multi"
        );
    },

    showComboSelectionPage() {
        const selectedCombos = [];
        for (const combo of this.combo_ids) {
            const { combo_item_ids } = combo;
            if (
                combo_item_ids.length > 1 ||
                combo.qty_max > 1 ||
                combo_item_ids[0]?.product_id?.isConfigurableForSelfOrder
            ) {
                return { show: true, selectedCombos: [] };
            }
            const item = this.models["product.combo.item"].get(combo_item_ids[0].id);
            selectedCombos.push({
                combo_item_id: item,
                qty: 1,
                configuration: {
                    attribute_custom_values: [],
                    attribute_value_ids: [],
                    price_extra: 0,
                },
            });
        }
        return { show: false, selectedCombos };
    },
});
