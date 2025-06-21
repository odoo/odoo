/** @odoo-module */

import * as PosHr from "@pos_hr/../tests/tours/PosHrTourMethods";
import * as ProductScreen from "@point_of_sale/../tests/tours/helpers/ProductScreenTourMethods";
import * as TicketScreen from "@point_of_sale/../tests/tours/helpers/TicketScreenTourMethods";
import * as Chrome from "@point_of_sale/../tests/tours/helpers/ChromeTourMethods";
import * as ErrorPopup from "@point_of_sale/../tests/tours/helpers/ErrorPopupTourMethods";
import * as NumberPopup from "@point_of_sale/../tests/tours/helpers/NumberPopupTourMethods";
import * as SelectionPopup from "@point_of_sale/../tests/tours/helpers/SelectionPopupTourMethods";
import { registry } from "@web/core/registry";
import { negate } from "../../../../point_of_sale/static/tests/tours/helpers/utils";

registry.category("web_tour.tours").add("PosHrTour", {
    test: true,
    url: "/pos/ui",
    steps: () =>
        [
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.isShown(),
            SelectionPopup.hasSelectionItem("Pos Employee1"),
            SelectionPopup.hasSelectionItem("Pos Employee2"),
            SelectionPopup.hasSelectionItem("Mitchell Admin"),
            SelectionPopup.clickItem("Pos Employee1"),
            NumberPopup.isShown(),
            NumberPopup.enterValue("25"),
            NumberPopup.inputShownIs("••"),
            NumberPopup.pressNumpad("8 1"),
            NumberPopup.fillPopupValue("2581"),
            NumberPopup.inputShownIs("••••"),
            NumberPopup.clickConfirm(),
            ErrorPopup.isShown(),
            ErrorPopup.clickConfirm(),
            PosHr.clickLoginButton(),
            SelectionPopup.clickItem("Pos Employee1"),
            NumberPopup.isShown(),
            NumberPopup.enterValue("25"),
            NumberPopup.inputShownIs("••"),
            NumberPopup.pressNumpad("8 0"),
            NumberPopup.fillPopupValue("2580"),
            NumberPopup.inputShownIs("••••"),
            NumberPopup.clickConfirm(),
            ProductScreen.isShown(),
            ProductScreen.confirmOpeningPopup(),
            PosHr.cashierNameIs("Pos Employee1"),
            PosHr.clickCashierName(),
            SelectionPopup.clickItem("Mitchell Admin"),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.clickMenuButton(),
            PosHr.clickLockButton(),
            PosHr.clickLoginButton(),
            SelectionPopup.clickItem("Pos Employee2"),
            NumberPopup.enterValue("12"),
            NumberPopup.inputShownIs("••"),
            NumberPopup.pressNumpad("3 4"),
            NumberPopup.fillPopupValue("1234"),
            NumberPopup.inputShownIs("••••"),
            NumberPopup.clickConfirm(),
            ProductScreen.isShown(),
            ProductScreen.clickHomeCategory(),

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
            SelectionPopup.clickItem("Mitchell Admin"),
            PosHr.cashierNameIs("Mitchell Admin"),
            TicketScreen.clickNewTicket(),
            ProductScreen.addOrderline("Desk Pad", "1", "8"),
            ProductScreen.totalAmountIs("8.0"),
            Chrome.clickMenuButton(),
            Chrome.clickTicketButton(),
            TicketScreen.nthRowContains(4, "Mitchell Admin", false),
        ].flat(),
});

registry.category("web_tour.tours").add("CashierStayLogged", {
    test: true,
    steps: () =>
        [
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.isShown(),
            SelectionPopup.hasSelectionItem("Pos Employee1"),
            SelectionPopup.hasSelectionItem("Pos Employee2"),
            SelectionPopup.hasSelectionItem("Mitchell Admin"),
            SelectionPopup.clickItem("Mitchell Admin"),
            PosHr.cashierNameIs("Mitchell Admin"),
            PosHr.refreshPage(),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.clickMenuButton(),
            PosHr.clickLockButton(),
            PosHr.refreshPage(),
            PosHr.loginScreenIsShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("CashierCannotClose", {
    test: true,
    steps: () =>
        [
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.isShown(),
            SelectionPopup.clickItem("Test Employee 3"),
            PosHr.cashierNameIs("Test Employee 3"),
            Chrome.clickMenuButton(),
            {
                trigger: negate(".close-button"),
            },
            PosHr.cashierNameIs("Test Employee 3"),
        ].flat(),
});
