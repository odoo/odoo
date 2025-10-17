import * as ProductScreenPos from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as TipScreen from "@pos_restaurant/../tests/tours/utils/tip_screen_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosResTipScreenTour", {
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
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable("4"),
            // order 2
            ProductScreen.addOrderline("Coca-Cola", "2", "2"),
            ProductScreen.totalAmountIs("4.0"),
            Chrome.clickPlanButton(),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),
            {
                trigger: `.ticket-screen .orders .order-row:contains(Tipping):contains($ 2.00)`,
            },
            Chrome.clickPlanButton(),

            // Create without syncing the draft.
            // order 3
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "3", "2"),
            ProductScreen.totalAmountIs("6.0"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickPlanButton(),
            FloorScreen.clickNewOrder(),
            // order 4
            ProductScreen.addOrderline("Coca-Cola", "4", "2"),
            ProductScreen.totalAmountIs("8.0"),
            ProductScreen.clickControlButton("Guests"),
            NumberPopup.enterValue("2"),
            NumberPopup.isShown("2"),
            Dialog.confirm(),
            ProductScreen.guestNumberIs("2"),
            ProductScreen.clickCloseButton(),
            ProductScreen.setTab("Test"),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),
            {
                trigger: `.ticket-screen .orders .order-row:contains(Tipping):contains($ 6.00)`,
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
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Active"),

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
            Chrome.clickOrders(),

            // finalize order 4 then tip custom amount
            TicketScreen.selectOrderByPrice("8.0"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.totalAmountIs("8.0"),
            ProductScreen.guestNumberIs("2"),
            ProductScreen.clickCloseButton(),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
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
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Tipping"),
            TicketScreen.tipContains("1.00"),
            TicketScreen.settleTips(),
            TicketScreen.selectFilter("Active"),
            {
                trigger: `.ticket-screen .orders .order-row:contains(Ongoing):contains($ 4.00)`,
            },
            // tip order2 during payment
            // tip screen should not show after validating payment screen
            TicketScreen.selectOrderByPrice("4.0"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickTipButton(),

            NumberPopup.enterValue("1"),
            NumberPopup.isShown("1"),
            Dialog.confirm(),
            PaymentScreen.emptyPaymentlines("5.0"),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.isShown(),

            // order 5
            // Click directly on "settle" without selecting a Tip
            ReceiptScreen.clickNextOrder(),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "3", "2"),
            ProductScreen.totalAmountIs("6.0"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            TipScreen.clickSettle(),
            ReceiptScreen.isShown(),
            ReceiptScreen.clickNextOrder(),
            FloorScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_tip_after_payment", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "1", "3"),
            ProductScreen.clickPayButton(false),
            ProductScreen.discardOrderWarningDialog(),
            // case 1: remaining < 0 => increase PaymentLine amount
            PaymentScreen.enterPaymentLineAmount("Bank", "1"),
            PaymentScreen.clickTipButton(),
            {
                content: "click numpad button: 1",
                trigger: ".modal div.numpad button:contains(/^1/)",
                run: "click",
            },
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Bank", "2.00"),
            // case 2: remaining >= 0 and remaining >= tip => don't change PaymentLine amount
            PaymentScreen.clickPaymentlineDelButton("Bank", "2.00"),
            PaymentScreen.enterPaymentLineAmount("Bank", "5"),
            PaymentScreen.clickTipButton(),
            {
                content: "click numpad button: 2",
                trigger: ".modal div.numpad button:contains(/^2/)",
                run: "click",
            },
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Bank", "5.00"),
            // case 3: remaining >= 0 and remaining < tip => increase by the difference
            PaymentScreen.clickPaymentlineDelButton("Bank", "5.00"),
            PaymentScreen.enterPaymentLineAmount("Bank", "5"),
            PaymentScreen.clickTipButton(),
            {
                content: "click numpad button: 3",
                trigger: ".modal div.numpad button:contains(/^3/)",
                run: "click",
            },
            Dialog.confirm(),
            PaymentScreen.selectedPaymentlineHas("Bank", "6.00"),
            Chrome.endTour(),
        ].flat(),
});
