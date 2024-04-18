/** @odoo-module */

import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosHrTour", {
    test: true,
    steps: () =>
        [
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee1"),
            SelectionPopup.has("Pos Employee2"),
            SelectionPopup.has("Mitchell Admin"),
            SelectionPopup.has("Pos Employee1", { run: "click" }),
            NumberPopup.enterValue("25"),
            NumberPopup.isShown("••"),
            NumberPopup.enterValue("81"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            // after trying to close the number popup, the error popup should be shown
            // successfully confirming the dialog would imply that the error popup is actually shown
            Dialog.confirm(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee1", { run: "click" }),

            NumberPopup.enterValue("25"),
            NumberPopup.isShown("••"),
            NumberPopup.enterValue("80"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            Dialog.confirm("Open session"),
            ProductScreen.isShown(),
            PosHr.cashierNameIs("Pos Employee1"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.clickMenuOption("Lock"),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee2", { run: "click" }),
            NumberPopup.enterValue("12"),
            NumberPopup.isShown("••"),
            NumberPopup.enterValue("34"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            ProductScreen.isShown(),

            // Create orders and check if the ticket list has the right employee for each order
            // order for employee 2
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            ProductScreen.totalAmountIs("2.0"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),

            // order for employee 1
            Chrome.clickMenuOption("Lock"),
            PosHr.login("Pos Employee1", "2580"),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "4"),
            ProductScreen.totalAmountIs("4.0"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),
            TicketScreen.nthRowContains(3, "Pos Employee1", false),

            // order for admin
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "8"),
            ProductScreen.totalAmountIs("8.0"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(4, "Mitchell Admin", false),
        ].flat(),
});
