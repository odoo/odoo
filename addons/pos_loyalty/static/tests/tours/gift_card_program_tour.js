import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";

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
            TicketScreen.selectOrder("001"),
            Order.hasLine({
                withClass: ".selected",
                productName: "Magnetic Board",
            }),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.isShown(),
            PaymentScreen.clickBack(),
            ProductScreen.isShown(),
            ProductScreen.clickLine("Magnetic Board", "-1"),
            ProductScreen.selectedOrderlineHas("Magnetic Board", "-1"),
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
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "-1.00"),
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
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("test-card-0001", 100),
            PosLoyalty.clickPhysicalGiftCard("test-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "100"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("new-card-0001", 250),
            PosLoyalty.clickPhysicalGiftCard("new-card-0001"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "250"),
            PosLoyalty.orderTotalIs("350"),
            PosLoyalty.finalizeOrder("Cash", "350"),
        ].flat(),
});

registry.category("web_tour.tours").add("MultiplePhysicalGiftCardProgramSaleTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.clickGiftCardProgram("Gift Cards1"),
            PosLoyalty.createManualGiftCard("test-card-0000", 125),
            PosLoyalty.clickGiftCardProgram("Gift Cards"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.clickGiftCardProgram("Gift Cards2"),
            PosLoyalty.createManualGiftCard("test-card-0001", 125),
            PosLoyalty.clickGiftCardProgram("Gift Cards2"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.clickGiftCardProgram("Gift Cards3"),
            PosLoyalty.createManualGiftCard("test-card-0002", 125),
            PosLoyalty.clickGiftCardProgram("Gift Cards3"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
        ].flat(),
});

registry.category("web_tour.tours").add("GiftCardProgramInvoice", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Test Partner"),
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

registry.category("web_tour.tours").add("test_physical_gift_card_invoiced", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AABBCC Test Partner"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            PosLoyalty.createManualGiftCard("test-card-1234", 125),
            ProductScreen.selectedOrderlineHas("Gift Card", "1.00", "125"),
            PosLoyalty.orderTotalIs("125"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickInvoiceButton(),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("EmptyProductScreenTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.isEmpty(),
            ProductScreen.loadSampleButtonIsThere(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_physical_gift_card", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Gift Card"),

            // Gift card cannot be used as it's already linked to a partner
            PosLoyalty.useExistingLoyaltyCard("gift_card_partner", false),
            // Gift card cannot be used as it's expired
            PosLoyalty.useExistingLoyaltyCard("gift_card_expired", false),
            // Gift card is already sold
            PosLoyalty.useExistingLoyaltyCard("gift_card_sold", false),

            // Use gift_card_generated_but_not_sold - Warning is triggered
            PosLoyalty.enterCode("gift_card_generated_but_not_sold"),
            Dialog.cancel(),

            // Sell the unsold gift card
            PosLoyalty.useExistingLoyaltyCard("gift_card_generated_but_not_sold", true),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "60.00"),
            ProductScreen.clickNumpad("2"), // Cannot edit a physical gift card
            Dialog.confirm(), // Warning is triggered
            PosLoyalty.orderTotalIs("60.00"),
            PosLoyalty.finalizeOrder("Cash", "60"),

            // Use gift_card_valid - No warning should be triggered
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("gift_card_valid"),
            ProductScreen.clickLine("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "-3.20"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Use gift_card_partner - No warning should be triggered
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("gift_card_partner"),
            ProductScreen.clickLine("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "-3.20"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Use gift_card_sold - Warning should be triggered
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("gift_card_sold"),
            ProductScreen.clickLine("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "-6.40"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Use gift_card_generated_but_not_sold - No warning should be triggered
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("gift_card_generated_but_not_sold"),
            ProductScreen.clickLine("Gift Card"),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "-12.80"),
            PosLoyalty.orderTotalIs("0.00"),
            PosLoyalty.finalizeOrder("Cash", "0"),

            // Try to use expired gift card
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            ProductScreen.clickDisplayedProduct("Whiteboard Pen"),
            PosLoyalty.enterCode("gift_card_expired"),
            PosLoyalty.orderTotalIs("9.60"),
            PosLoyalty.finalizeOrder("Cash", "9.60"),

            // Sell a new gift card with a partner
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A powerful PoS man!"),
            ProductScreen.clickDisplayedProduct("Gift Card"),
            ProductScreen.clickNumpad("Price", "9", "9", "9"),
            PosLoyalty.orderTotalIs("999.00"),
            PosLoyalty.finalizeOrder("Cash", "999"),
        ].flat(),
});
