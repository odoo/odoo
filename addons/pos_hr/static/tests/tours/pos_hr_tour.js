import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosHrTour", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
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
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee1", { run: "click" }),

            NumberPopup.enterValue("25"),
            NumberPopup.isShown("••"),
            NumberPopup.enterValue("80"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            Dialog.confirm("Open Register"),
            ProductScreen.isShown(),
            PosHr.cashierNameIs("Pos Employee1"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Pos Employee2", { run: "click" }),
            NumberPopup.enterValue("12"),
            NumberPopup.isShown("••"),
            NumberPopup.enterValue("34"),
            NumberPopup.isShown("••••"),
            Dialog.confirm(),
            ProductScreen.isShown(),

            // Create orders and check if the ticket list has the right employee for each order
            // order for employee 2
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.totalAmountIs("1.98"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),

            // order for employee 1
            PosHr.clickLockButton(),
            Chrome.clickBtn("Unlock Register"),
            PosHr.login("Pos Employee1", "2580"),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.totalAmountIs("1.98"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(2, "Pos Employee2", false),
            TicketScreen.nthRowContains(3, "Pos Employee1", false),

            // Cash in/out should be accessible for all users.
            Chrome.clickMenuOption("Cash In/Out"),
            Dialog.discard(),

            // order for admin
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "8"),
            ProductScreen.totalAmountIs("8.0"),
            Chrome.clickMenuOption("Orders"),
            TicketScreen.nthRowContains(4, "Mitchell Admin", false),

            // Close register should be accessible by the admin user.
            Chrome.clickMenuOption("Close Register"),
            Dialog.is("Closing Register"),
        ].flat(),
});

registry.category("web_tour.tours").add("CashierStayLogged", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Pos Employee1"),
            SelectionPopup.has("Pos Employee2"),
            SelectionPopup.has("Mitchell Admin"),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            PosHr.cashierNameIs("Mitchell Admin"),
            PosHr.refreshPage(),
            ProductScreen.isShown(),
            PosHr.cashierNameIs("Mitchell Admin"),
            Chrome.clickMenuButton(),
            PosHr.clickLockButton(),
            PosHr.refreshPage(),
            PosHr.loginScreenIsShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("CashierCanSeeProductInfo", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.clickInfoProduct("product_a"),
            Dialog.confirm("Ok"),
            Dialog.isNot(),
        ].flat(),
});
