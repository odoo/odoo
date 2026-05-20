import { GeneratePrinterData } from "@point_of_sale/app/utils/printer/generate_printer_data";
import { patch } from "@web/core/utils/patch";

patch(GeneratePrinterData.prototype, {
    showOldUnitPrice(line) {
        return (
            line.price_type !== "original" &&
            (!this.config.module_pos_discount ||
                line.product_id !== this.config.discount_product_id.id) &&
            line.product_id !== this.config.tip_product_id.id &&
            !line.is_reward_line
        );
    },

    generateLineData() {
        return super.generateLineData(...arguments).map((line) => ({
            ...line,
            show_old_unit_price: this.showOldUnitPrice(line),
        }));
    },
});
