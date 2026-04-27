import { PartnerLine } from "@point_of_sale/app/screens/partner_list/partner_line/partner_line";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PartnerLine.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
    },
    get partnerInfos() {
        return this.pos.getPartnerCredit(this.props.partner);
    },
    settleCustomerDue() {
        this.props.close();
        this.pos.settleCustomerDue(this.props.partner);
    },
    payLaterPaymentExists() {
        return this.pos.models["pos.payment.method"].some(
            (pm) =>
                this.pos.config.payment_method_ids.some((m) => m.id === pm.id) &&
                pm.type === "pay_later"
        );
    },
});
