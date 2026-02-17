import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("L10nJoEdiPosTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.checkTicketData({
                cssRules: [
                    {
                        css: "div",
                        text: "JoFotara QR code",
                        length: 1,
                    },
                    {
                        css: "div.l10n-jo-edi-pos-qr img.pos-receipt-qrcode",
                        length: 1,
                    },
                ],
            }),
        ].flat(),
});
