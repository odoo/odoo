import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as StockPaymentScreen from "@pos_stock/../tests/pos/tours/utils/payment_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("StockPaymentScreenTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Letter Tray", "1", "10"),
            ProductScreen.clickPayButton(),

            // check that ship later button is present
            { trigger: ".payment-buttons button:contains('Ship Later')" },
            // payment line is been in case of mobile as paymentlines are required to manually enter the amount
            {
                isActive: ["mobile"],
                content: "click payment method",
                trigger: `.paymentmethod`,
                run: "click",
            },
            PaymentScreen.enterPaymentLineAmount("Bank", "99"),
            // trying to put 99 as an amount should throw an error. We thus confirm the dialog.
            Dialog.confirm(),
            PaymentScreen.remainingIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("InvoiceShipLaterAccessRight", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.confirmOpeningPopup(),
            ProductScreen.clickHomeCategory(),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickPayButton(),

            PaymentScreen.clickPaymentMethod("Cash"),
            StockPaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
        ].flat(),
});
