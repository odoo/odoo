import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";


patch(PaymentScreen.prototype, {

    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.default_partner_ref = 'l10n_pk_res_partner_cash_customer';
    },

    /* Override */
    onMounted() {
        super.onMounted();
        const order = this.currentOrder;
        if (order.company.country_id.code == "PK") {
            this.validateOrderForInvoice();
        }
    },

    async validateOrderForInvoice() {
        const order = this.currentOrder;
        if (!order.to_invoice)
            order.to_invoice = true;
        if (!order.get_partner()) {
            try {
                const partner = await this.getDefaultCustomer(order);
                order.set_partner(partner);
            } catch (error) {
                console.error("Error getting default customer:", error);
            }
        }
    },

    async getDefaultCustomer() {
        const [partner] = await this.pos.data.searchRead(
            "res.partner",
            [["ref", "=", this.default_partner_ref]],
            [],
            { limit: this.limit }
        );
        return partner
    }
});
