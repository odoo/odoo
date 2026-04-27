import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";
import { onMounted } from "@odoo/owl";

patch(ProductScreen.prototype, {
    setup() {
        super.setup(...arguments);

        onMounted(() => {
            if (this.pos.isChileanCompany() && !this.pos.get_order().partner_id) {
                this.pos.get_order().update({
                    partner_id: this.pos.session._consumidor_final_anonimo_id,
                });
            }
        });
    },
});
