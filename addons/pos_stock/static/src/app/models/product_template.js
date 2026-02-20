import { patch } from "@web/core/utils/patch";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

patch(ProductTemplate.prototype, {
    isAllowOnlyOneLot() {
        return this.tracking === "lot" || !this.uom_id || !this.uom_id.is_pos_groupable;
    },

    isTracked() {
        const pickingType = this.models["stock.picking.type"].readAll()[0];

        return (
            ["serial", "lot"].includes(this.tracking) &&
            (pickingType.use_create_lots || pickingType.use_existing_lots)
        );
    },
});
