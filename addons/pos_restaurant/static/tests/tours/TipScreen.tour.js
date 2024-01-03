/** @odoo-module */

import * as ProductScreenPos from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/helpers/ProductScreenTourMethods";
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as PaymentScreen from "@point_of_sale/../tests/tours/helpers/PaymentScreenTourMethods";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/helpers/ReceiptScreenTourMethods";
import * as FloorScreen from "@pos_restaurant/../tests/tours/helpers/FloorScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as TipScreen from "@pos_restaurant/../tests/tours/helpers/TipScreenTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosResTipScreenTour", {
    test: true,
    steps: () =>
        [
            // Create order that is synced when draft.
            // order 1
            Dialog.confirm("Open session"),
            FloorScreen.clickTable("2"),
            ProductScreen.addOrderline("Minute Maid", "1", "2"),
            ProductScreen.totalAmountIs("2.0"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("2", "1"),
            FloorScreen.clickTable("2"),
            ProductScreen.totalAmountIs("2.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            // order 2
            ProductScreen.addOrderline("Coca-Cola", "2", "2"),
            ProductScreen.totalAmountIs("4.0"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("2", "2"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains("2", "Tipping"),
            TicketScreen.clickDiscard(),

            // Create without syncing the draft.
            // order 3
            FloorScreen.clickTable("5"),
            ProductScreen.addOrderline("Minute Maid", "3", "2"),
            ProductScreen.totalAmountIs("6.0"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            TipScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.clickNewTicket(),
            // order 4
            ProductScreen.addOrderline("Coca-Cola", "4", "2"),
            ProductScreen.totalAmountIs("8.0"),
            FloorScreen.backToFloor(),
            FloorScreen.orderCountSyncedInTableIs("5", "4"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains("4", "Tipping"),

            // Tip 20% on order1
            TicketScreen.selectOrder("-0001"),
            TicketScreen.loadSelectedOrder(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("2.0"),
            TipScreen.percentAmountIs("15%", "0.30"),
            TipScreen.percentAmountIs("20%", "0.40"),
            TipScreen.percentAmountIs("25%", "0.50"),
            TipScreen.clickPercentTip("20%"),
            TipScreen.inputAmountIs("0.40"),
            FloorScreen.backToFloor(),
            FloorScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),

            // Tip 25% on order3
            TicketScreen.selectOrder("-0003"),
            TicketScreen.loadSelectedOrder(),
            TipScreen.isShown(),
            TipScreen.totalAmountIs("6.0"),
            TipScreen.percentAmountIs("15%", "0.90"),
            TipScreen.percentAmountIs("20%", "1.20"),
            TipScreen.percentAmountIs("25%", "1.50"),
            TipScreen.clickPercentTip("25%"),
            TipScreen.inputAmountIs("1.50"),
            FloorScreen.backToFloor(),
            FloorScreen.isShown(),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),

            // finalize order 4 then tip custom amount
            TicketScreen.selectOrder("-0004"),
            TicketScreen.loadSelectedOrder(),
            ProductScreen.isShown(),
            ProductScreen.totalAmountIs("8.0"),
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
            FloorScreen.backToFloor(),
            FloorScreen.isShown(),

            // settle tips here
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.selectFilter("Tipping"),
            TicketScreen.tipContains("1.00"),
            TicketScreen.settleTips(),
            TicketScreen.selectFilter("All active orders"),
            TicketScreen.nthRowContains(2, "Ongoing"),

            // tip order2 during payment
            // tip screen should not show after validating payment screen
            TicketScreen.selectOrder("-0002"),
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
