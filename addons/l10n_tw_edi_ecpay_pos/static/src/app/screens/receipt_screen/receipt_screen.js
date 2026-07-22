import { patch } from "@web/core/utils/patch";
import { EcpayCertificateReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_certificate_receipt";
import { EcpayTransactionReceipt } from "@l10n_tw_edi_ecpay_pos/app/components/order_receipt/ecpay_transaction_receipt";
import { ReceiptScreen } from "@point_of_sale/app/screens/receipt_screen/receipt_screen";

patch(ReceiptScreen, {
    components: { ...ReceiptScreen.components, EcpayCertificateReceipt, EcpayTransactionReceipt },
});
