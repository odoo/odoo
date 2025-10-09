import * as PosHr from "@pos_hr/../tests/tours/utils/pos_hr_helpers";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as NumberPopup from "@point_of_sale/../tests/generic_helpers/number_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as SelectionPopup from "@point_of_sale/../tests/generic_helpers/selection_popup_util";
import * as BackendUtils from "@point_of_sale/../tests/pos/tours/utils/backend_utils";
import * as Utils from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";
import { negate } from "@point_of_sale/../tests/generic_helpers/utils";

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
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
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
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "Pos Employee2", false),

            // order for employee 1
            PosHr.clickLockButton(),
            Chrome.clickBtn("Unlock Register"),
            PosHr.login("Pos Employee1", "2580"),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1"),
            ProductScreen.totalAmountIs("1.98"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(1, "Pos Employee2", false),
            TicketScreen.nthRowContains(2, "Pos Employee1", false),

            // Cash in/out should be accessible for all users.
            Chrome.clickMenuOption("Cash In/Out"),
            Dialog.discard(),

            // order for admin
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Chrome.createFloatingOrder(),
            ProductScreen.addOrderline("Desk Pad", "1", "8"),
            ProductScreen.totalAmountIs("8.0"),
            Chrome.clickOrders(),
            TicketScreen.nthRowContains(3, "Mitchell Admin", false),

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
            PosHr.refreshPage(),
            ProductScreen.isShown(),
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
            ProductScreen.clickInfoProduct("product_a", [Dialog.confirm("Close")]),
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

registry.category("web_tour.tours").add("test_change_on_rights_reflected_directly", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            Chrome.clickMenuOption("Backend", { expectUnloadPage: true }),
            BackendUtils.editShopConfiguration("Shop"),
            {
                trigger: ".o_tag:contains('Pos Employee1') .o_delete",
                run: "click",
            },
            BackendUtils.saveConfiguration(),
            {
                trigger: ".o_main_navbar .o-dropdown-item:contains('Dashboard')",
                run: "click",
            },
            {
                trigger: ".btn:contains('Continue Selling')",
                run: "click",
                expectUnloadPage: true,
            },
            Chrome.clickBtn("Unlock Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            Utils.negateStep(...SelectionPopup.has("Pos Employee1")),
        ].flat(),
});

registry.category("web_tour.tours").add("test_minimal_employee_refund", {
    steps: () =>
        [
            Chrome.clickBtn("Unlock Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Minimal Employee", { run: "click" }),
            Chrome.clickOrders(),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            {
                trigger: negate(".subpads"),
            },
            PosHr.clickCashierName(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            TicketScreen.selectFilter("Paid"),
            TicketScreen.selectOrder("001"),
            {
                trigger: ".subpads",
            },
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
            ReceiptScreen.cashierNameExists("Test"), // Test Employee 3 (Take the first word)
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_cost_and_margin_visibility", {
    steps: () =>
        [
            Chrome.clickBtn("Open Register"),
            PosHr.loginScreenIsShown(),
            PosHr.clickLoginButton(),
            SelectionPopup.has("Mitchell Admin", { run: "click" }),
            Dialog.confirm("Open Register"),
            ProductScreen.clickInfoProduct("product_a"),
            {
                trigger: ".section-financials :contains('Margin')",
            },
            Dialog.confirm("Close"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Employee 3", { run: "click" }),
            ProductScreen.clickInfoProduct("product_a"),
            {
                trigger: ".section-financials :contains('Margin')",
            },
            Dialog.confirm("Close"),
            PosHr.clickCashierName(),
            SelectionPopup.has("Test Employee 4", { run: "click" }),
            ProductScreen.clickInfoProduct("product_a"),
            Utils.negateStep({
                trigger: ".section-financials :contains('Margin')",
            }),
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
            PosHr.enterPin("5651").map((step, index, array) => {
                if (index === array.length - 1) {
                    return {
                        ...step,
                        expectUnloadPage: true,
                    };
                }
                return step;
            }),
            PosHr.loginScreenIsNotShown().map((step) => ({ ...step, expectUnloadPage: true })),
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
