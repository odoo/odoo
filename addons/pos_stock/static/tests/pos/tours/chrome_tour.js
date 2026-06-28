import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as StockFeedbackScreen from "@pos_stock/../tests/pos/tours/utils/feedback_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as StockPaymentScreen from "@pos_stock/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

const { DateTime } = luxon;
const nextYear = DateTime.now().year + 1;

registry.category("web_tour.tours").add("test_edit_paid_order_stock", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Organizer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickEditPayment(),
            // Add customer
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("Partner Test 1"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            // Ship later case
            ProductScreen.addOrderline("Desk Organizer"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickPartnerButton(),
            PaymentScreen.clickCustomer("APartner Full"),
            // This will set today's date as shipping date
            StockPaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            StockFeedbackScreen.checkTicketData({
                is_shipping_date: true,
            }),
            FeedbackScreen.clickEditPayment(),
            // clicking once will make it empty and on clicking again it will open date picking
            StockPaymentScreen.setShipLaterDate(`${nextYear}-05-30`),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
