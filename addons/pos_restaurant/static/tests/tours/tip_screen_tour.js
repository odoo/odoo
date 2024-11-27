import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as TipScreen from "@pos_restaurant/../tests/tours/utils/tip_screen_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosResTipScreenTour", {
    checkDelay: 50,
    steps: () =>
        [
            // Create order that is synced when draft.
            // order 1
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "1", "2"),
            ProductScreen.totalAmountIs("2.0"),
            Chrome.clickPlanButton(),
            FloorScreen.orderCountSyncedInTableIs("2", "1"),
            FloorScreen.clickTable("2"),
            ProductScreen.totalAmountIs("2.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            // order 2
            ProductScreen.addOrderline("Coca-Cola", "2", "2"),
            ProductScreen.totalAmountIs("4.0"),
            Chrome.clickPlanButton(),
            Chrome.clickMenuOption("Orders"),
            {
                trigger: `.ticket-screen .orders > .order-row:contains(Tipping):contains($ 2.00)`,
            },
            Chrome.clickPlanButton(),

            // Create without syncing the draft.
            // order 3
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "3", "2"),
            ProductScreen.totalAmountIs("6.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickPlanButton(),
            Chrome.createFloatingOrder(),
            // order 4
            ProductScreen.addOrderline("Coca-Cola", "4", "2"),
            ProductScreen.totalAmountIs("8.0"),
            ProductScreen.clickControlButton("Guests"),
            NumberPopup.enterValue("2"),
            NumberPopup.isShown("2"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("2"),
            ProductScreen.clickCloseButton(),
            Chrome.clickPlanButton(),
            Chrome.clickMenuOption("Orders"),
            {
                trigger: `.ticket-screen .orders > .order-row:contains(Tipping):contains($ 6.00)`,
            },
            // Tip 20% on order1
            TicketScreen.selectOrderByPrice("2.0"),
            TicketScreen.loadSelectedOrder(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("2.0"),
            TipScreen.percentAmountIs("15%", "0.30"),
            TipScreen.percentAmountIs("20%", "0.40"),
            TipScreen.percentAmountIs("25%", "0.50"),
            TipScreen.clickPercentTip("20%"),
            TipScreen.inputAmountIs("0.40"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.clickMenuOption("Orders"),

            // Tip 25% on order3
            TicketScreen.selectOrderByPrice("6.0"),
            TicketScreen.loadSelectedOrder(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("6.0"),
            TipScreen.percentAmountIs("15%", "0.90"),
            TipScreen.percentAmountIs("20%", "1.20"),
            TipScreen.percentAmountIs("25%", "1.50"),
            TipScreen.clickPercentTip("25%"),
            TipScreen.inputAmountIs("1.50"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            Chrome.clickMenuOption("Orders"),

            // finalize order 4 then tip custom amount
            TicketScreen.selectOrderByPrice("8.0"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.totalAmountIs("8.0"),
            ProductScreen.guestNumberIs("2"),
            ProductScreen.clickCloseButton(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("8.0"),
            TipScreen.percentAmountIs("15%", "1.20"),
            TipScreen.percentAmountIs("20%", "1.60"),
            TipScreen.percentAmountIs("25%", "2.00"),
            TipScreen.setCustomTip("1.00"),
            TipScreen.inputAmountIs("1.00"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),

            // settle tips here
            Chrome.clickMenuOption("Orders"),
            TicketScreen.selectFilter("Tipping"),
            TicketScreen.tipContains("1.00"),
            TicketScreen.settleTips(),
            TicketScreen.selectFilter("All active orders"),
            {
                trigger: `.ticket-screen .orders > .order-row:contains(Ongoing):contains($ 4.00)`,
            },
            // tip order2 during payment
            // tip screen should not show after validating payment screen
            TicketScreen.selectOrderByPrice("4.0"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickTipButton(),

            NumberPopup.enterValue("1"),
            NumberPopup.isShown("1"),
            Dialog.confirm(),
            PaymentScreen.emptyPaymentlines("5.0"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.isShown(),

            // order 5
            // Click directly on "settle" without selecting a Tip
            ReceiptScreen.clickNextOrder(),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "3", "2"),
            ProductScreen.totalAmountIs("6.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.clickSettle(),
            {
                ...Dialog.confirm(),
                content:
                    "acknowledge printing error ( because we don't have printer in the test. )",
            },
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            FloorScreen.isShown(),
        ].flat(),
});
