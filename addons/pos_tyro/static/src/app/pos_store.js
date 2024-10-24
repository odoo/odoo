import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async set_tyro_surcharge(amount, surchargeProduct) {
        const currentOrder = this.get_order();
        const line = currentOrder.lines.find((line) => line.product_id.id === surchargeProduct.id);

        if (line) {
            line.set_unit_price(amount);
        } else {
            await this.addLineToCurrentOrder(
                {
                    product_id: surchargeProduct,
                    price_unit: amount,
                    product_tmpl_id: surchargeProduct.product_tmpl_id,
                },
                {}
            );
        }
    },
});
