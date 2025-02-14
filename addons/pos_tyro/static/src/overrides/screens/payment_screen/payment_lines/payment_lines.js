import { patch } from "@web/core/utils/patch";
import { PaymentScreenPaymentLines } from "@point_of_sale/app/screens/payment_screen/payment_lines/payment_lines";

patch(PaymentScreenPaymentLines, {
    props: {
        ...PaymentScreenPaymentLines.props,
        refundLines: { type: Array, optional: true },
        selectRefundLine: Function,
    },
});
