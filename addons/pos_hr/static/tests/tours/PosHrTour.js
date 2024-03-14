/** @odoo-module */

import * as PosHr from "@pos_hr/../tests/tours/PosHrTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as Dialog from "@point_of_sale/../tests/tours/helpers/DialogTourMethods";
import * as SelectionPopup from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosHrTour", {
    test: true,
    url: "/pos/ui",
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
            NumberPopup.pressNumpad("8 1"),
            NumberPopup.fillPopupValue("2581"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            // after trying to close the number popup, the error popup should be shown
            // successfully confirming the dialog would imply that the error popup is actually shown
            Dialog.confirm(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee1", { run: "click" }),

            NumberPopup.enterValue("25"),
            NumberPopup.isShown("••"),
            NumberPopup.pressNumpad("8 0"),
            NumberPopup.fillPopupValue("2580"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            Dialog.confirm("Open session"),
            ProductScreen.isShown(),
            PosHr.cashierNameIs("Pos Employee1"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.clickMenuButton(),
            PosHr.clickLockButton(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee2", { run: "click" }),
            NumberPopup.enterValue("12"),
            NumberPopup.isShown("••"),
            NumberPopup.pressNumpad("3 4"),
            NumberPopup.fillPopupValue("1234"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            ProductScreen.isShown(),

            // Create orders and check if the ticket list has the right employee for each order
            // order for employee 2
            ProductScreen.addOrderline("Desk Pad", "1", "2"),
            ProductScreen.totalAmountIs("2.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),

            // order for employee 1
            Chrome.clickMenuButton(),
            PosHr.clickLockButton(),
            PosHr.login("Pos Employee1", "2580"),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "4"),
            ProductScreen.totalAmountIs("4.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),
            TicketScreen.nthRowContains(3, "Pos Employee1", false),

            // order for admin
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "8"),
            ProductScreen.totalAmountIs("8.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(4, "Mitchell Admin", false),
        ].flat(),
});
