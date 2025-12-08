import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSaleLoyaltyTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_sale_loyalty_ignored_in_pos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.totalAmountIs(90),
        ].flat(),
});
registry.category("web_tour.tours").add("test_sale_order_loyalty_card_can_be_used_in_pos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Pad"),
            PosLoyalty.enterCode("LOYALTY123"),
            ProductScreen.customerIsSelected("partner_a"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});
