import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";

registry.category("web_tour.tours").add("GiftCardProgramTour1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramTour2", {
    steps: () =>
        [
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardWithRefundtTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Magnetic Board", "1"), // 1.98
            PosLoyalty.orderTotalIs("1.98"),
            PosLoyalty.finalizeOrder("Cash", "20"),
            ...ProductScreen.clickRefund(),
            TicketScreen.selectOrder("-0001"),
            Order.hasLine({
                withClass: ".selected",
                productName: "Magnetic Board",
            }),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Magnetic Board", "-1.0"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "-1.00"),
            ProductScreen.addOrderline("Gift Card", "1"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1"),
            PosLoyalty.orderTotalIs("0.0"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramPriceNoTaxTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Use gift card
            ProductScreen.addOrderline("Magnetic Board", "1", "1.98", "1.98"),
            PosLoyalty.enterCode("043123456"),
            Dialog.confirm(),
            ProductScreen.clickOrderline("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "-1.00"),
            PosLoyalty.orderTotalIs("0.98"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyPointsGiftcard", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("044123456", 50),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA"),
            ProductScreen.addOrderline("product_a", "1"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.pointsAwardedAre("100"),
            PosLoyalty.finalizeOrder("Cash", "50"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyGiftCardTaxes", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("044123456", 50),
            PosLoyalty.orderTotalIs("50.00"),
            PosLoyalty.finalizeOrder("Cash", "50"),
            ProductScreen.clickDisplayedProduct("Test Product A"),
            PosLoyalty.enterCode("044123456"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.checkTaxAmount("-6.52"),
        ].flat(),
});

registry.category("web_tour.tours").add("PhysicalGiftCardProgramSaleTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("test-card-0000", 125),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("test-card-0001", 100),
            PosLoyalty.clickPhysicalGiftCard("test-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "100"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("new-card-0001", 250),
            PosLoyalty.clickPhysicalGiftCard("new-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "250"),
            PosLoyalty.orderTotalIs("350"),
            PosLoyalty.finalizeOrder("Cash", "350"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramInvoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Test Partner"),
            PosLoyalty.orderTotalIs("50.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_gift_card_no_date", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.createManualGiftCard("test", "42", ""),
            PosLoyalty.finalizeOrder("Cash", "42"),
        ].flat(),
});
