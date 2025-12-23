import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/tours/utils/number_popup_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as SelectionPopup from "@point_of_sale/../tests/tours/utils/selection_popup_util";
import { registry } from "@web/core/registry";
import { negate, scan_barcode } from "@point_of_sale/../tests/tours/utils/common";

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
            {
                trigger: "body",
                run: () => {
                    window.dispatchEvent(new KeyboardEvent("keyup", { key: "8" }));
                },
            },
            NumberPopup.isShown("•••"),
            NumberPopup.enterValue("1"),
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

registry.category("web_tour.tours").add("CashierCannotClose", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuButton(),
            {
                trigger: negate(`span.dropdown-item:contains("Close Register")`),
            },
            PosHr.cashierNameIs("Test Employee 3"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Chrome.clickMenuButton(),
            {
                trigger: `span.dropdown-item:contains("Close Register")`,
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_basic_user_can_change_price", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Desk Pad", "1", "10", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_cashier_changed_in_receipt", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("product_a", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            PaymentScreen.clickValidate(),
            ReceiptScreen.cashierNameExists("Test Employee 3"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_hr_go_backend_closed_registered", {
    steps: () =>
        [
            // Admin --> 403: not the one that opened the session
            Chrome.clickBtn("Backend"),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            PosHr.loginScreenIsShown(),

            // Employee with user --> 403
            Chrome.clickBtn("Backend"),
            SelectionPopup.has("Pos Employee1", { run: "click" }),
            PosHr.enterPin("2580"),
            PosHr.loginScreenIsShown(),

            // Employee without user --> 403
            Chrome.clickBtn("Backend"),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            PosHr.loginScreenIsShown(),

            // Manager without user --> 403
            Chrome.clickBtn("Backend"),
            SelectionPopup.has("Test Manager 2", { run: "click" }),
            PosHr.enterPin("5652"),
            PosHr.loginScreenIsShown(),

            // Manager that opened the session --> access granted
            Chrome.clickBtn("Backend"),
            SelectionPopup.has("Test Manager 1", { run: "click" }),
            PosHr.enterPin("5651"),
            PosHr.loginScreenIsNotShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_hr_go_backend_opened_registered", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.clickLoginButton(),

            // Admin --> 403: not the one that opened the session
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Chrome.clickBtn("Open Register"),
            Chrome.existMenuOption("Close Register"),
            Chrome.notExistMenuOption("Backend"),

            // Employee with user --> 403
            PosHr.clickCashierName(),
            SelectionPopup.has("Pos Employee1", { run: "click" }),
            PosHr.enterPin("2580"),
            Chrome.notExistMenuOption("Close Register"),
            Chrome.notExistMenuOption("Backend"),

            // Employee without user --> 403
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            Chrome.notExistMenuOption("Close Register"),
            Chrome.notExistMenuOption("Backend"),

            // Manager without user --> 403
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Manager 2", { run: "click" }),
            PosHr.enterPin("5652"),
            Chrome.existMenuOption("Close Register"),
            Chrome.notExistMenuOption("Backend"),

            // Manager that opened the session --> access granted
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Manager 1", { run: "click" }),
            PosHr.enterPin("5651"),
            Chrome.existMenuOption("Close Register"),
            Chrome.clickMenuOption("Backend", { expectUnloadPage: true }),
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("pos_hr_go_backend_opened_registered_different_user_logged", {
        steps: () =>
            [
                Chrome.clickBtn("Unlock Register"),
                PosHr.clickLoginButton(),

                // Employee, connected user
                SelectionPopup.has("Pos Employee1", { run: "click" }),
                PosHr.enterPin("2580"),
                Chrome.existMenuOption("Backend"),

                // Manager that opened the session, not connected user
                PosHr.clickCashierName(),
                SelectionPopup.has("Test Manager 1", { run: "click" }),
                PosHr.enterPin("5651"),
                Chrome.notExistMenuOption("Backend"),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_maximum_closing_difference", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            ProductScreen.enterOpeningAmount("10"),
            Chrome.clickBtn("Open Register"),

            PosHr.clickCashierName(),
            SelectionPopup.has("Test Manager 2", { run: "click" }),
            PosHr.enterPin("5652"),
            Chrome.clickMenuOption("Close Register"),
            Chrome.clickBtn("Close Register"),
            {
                trigger: negate(`button:contains("Proceed anyway")`),
            },
            Chrome.clickBtn("Ok"),
            Chrome.clickBtn("Discard"),

            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Chrome.clickMenuOption("Close Register"),
            Chrome.clickBtn("Close Register"),
            Chrome.hasBtn("Proceed anyway"),
            Chrome.clickBtn("Proceed anyway"),
            PosHr.loginScreenIsShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_scan_employee_barcode_with_pos_hr_disabled", {
    steps: () =>
        [
            // scan a barcode with 041 as prefix for cashiers
            scan_barcode("041123"),
            Chrome.clickBtn("Open Register"),
            ProductScreen.isShown(),
        ].flat(),
});
