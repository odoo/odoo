/* global posmodel */

import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PartnerList from "@point_of_sale/../tests/tours/utils/partner_list_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";
import * as Utils from "@point_of_sale/../tests/tours/utils/common";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("pos_settle_account_due", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ProductScreen.closePos(),
            Dialog.confirm("Close Register"),
            {
                trigger: "body:not(:has(.modal))",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_pos_settle_due_with_rounding", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            // Cash method should be rounded: 10.02 -> 10.00
            Utils.selectButton("Cash"),
            PaymentScreen.changeIs("10.00"),
            PaymentScreen.selectedPaymentlineHas("Cash", "10.00"),
            PaymentScreen.clickPaymentlineDelButton("Cash", "10.00"),
            PaymentScreen.clickBackToProductScreen(),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("Partner Test 1"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            // Non-Cash method should not be rounded: 10.02 remains 10.02
            Utils.selectButton("Bank"),
            PaymentScreen.changeIs("10.02"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ProductScreen.closePos(),
            Dialog.confirm("Close Register"),
            {
                trigger: "body:not(:has(.modal))",
            },
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("SettleDueUICoherency", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.checkDropDownItemText("Deposit money"),
            PartnerList.clickPartnerOptions("B Partner"),
            PartnerList.checkDropDownItemText("Settle due accounts"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Bank"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            {
                content: "Receipt doesn't include Empty State",
                trigger: ".pos-receipt:not(:has(i.fa-shopping-cart))",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("pos_settle_account_due_update_instantly", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            {
                trigger: "tr:contains('A Partner') .partner-due:contains('19.80')",
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_account_due_aml_reconcile", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("A Partner"),
            ProductScreen.addOrderline("Desk Pad", "10"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Customer Account"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("A Partner"),
            PartnerList.checkDropDownItemText("Settle due accounts"),
            {
                isActive: ["auto"],
                trigger: "div.o_popover :contains('Settle Due Accounts')",
                content: "Check the popover opened",
                run: "click",
            },
            Utils.selectButton("Bank"),
            PaymentScreen.changeIs("19.80"),
            PaymentScreen.clickValidate(),
            Utils.selectButton("Yes"),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_due_account_ui_coherency_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("B Partner"),
            Utils.negateStep(PartnerList.checkDropDownItemText("Deposit money")),
        ].flat(),
});

registry.category("web_tour.tours").add("SettleDueAmountMoreCustomers", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            {
                trigger: ".modal-header .input-container input",
                run: `fill BPartner`,
            },
            {
                /**
                 * Manually trigger keyup event to show the search field list
                 * because the previous step do not trigger keyup event.
                 */
                trigger: ".modal-header .input-container input",
                run: function () {
                    document
                        .querySelector(".modal-header .input-container input")
                        .dispatchEvent(new KeyboardEvent("keyup", { key: "" }));
                },
            },
            Utils.selectButton("Search more"),
            {
                trigger: ".partner-line-balance:contains('10.00')",
                run: () => {},
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_deposit_shown_partner_list", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPartnerButton(),
            PartnerList.clickPartnerOptions("AAA Partner"),
            PartnerList.clickDropDownItem("Deposit"),
            {
                trigger: ".modal .selection-item:contains('Cash')",
                run: "click",
            },
            PaymentScreen.clickNumpad("5"),
            PaymentScreen.changeIs("5.00"),
            PaymentScreen.clickValidate(),
            Dialog.confirm("Yes"),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickPartnerButton(),
            {
                trigger:
                    '.partner-info:contains("AAA Partner") .partner-line-balance:contains("Deposited: $ 5.00") ',
            },
        ].flat(),
});

registry
    .category("web_tour.tours")
    .add("test_pos_settling_account_resets_on_payment_screen_unmount", {
        steps: () =>
            [
                Chrome.startPoS(),
                Dialog.confirm("Open Register"),
                {
                    content: "Set the pos_settle_due to True and open payment screen",
                    trigger: "body",
                    run: () => {
                        posmodel.get_order().is_settling_account = true;
                        posmodel.showScreen("PaymentScreen", {
                            orderUuid: posmodel.selectedOrderUuid,
                        });
                    },
                },
                PaymentScreen.clickBackToProductScreen(),
                {
                    isActive: ["auto"],
                    content: "Check is_settling_account set to true",
                    trigger: "body",
                    run: () => {
                        const order = posmodel.get_order();
                        if (order.is_settling_account) {
                            throw new Error(
                                "Expected order.is_settling_account to be false, but got true"
                            );
                        }
                    },
                },
                Chrome.endTour(),
            ].flat(),
    });
