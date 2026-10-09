// Part of Odoo. See LICENSE file for full copyright and licensing details.
/* global posmodel */

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { addDiscount } from "@pos_discount/../tests/tours/test_taxes_global_discount";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ph_pos_discount_discount_privileges", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Soda", "2"),
            ...addDiscount("10"),
            // 10% of 2 x 112.00 (VAT included).
            ProductScreen.selectedOrderlineHas("Global Discount", "1", "-22.40"),
            ProductScreen.clickControlButton("Discount Privileges"),
            {
                content: "select the Senior Citizen privilege",
                trigger:
                    '.mb-3:has(label:contains("20% Senior Citizen Discount")) input[type="checkbox"]',
                run: "click",
            },
            {
                content: "share between 2 persons",
                trigger: "#l10n_ph_persons_sharing",
                run: "edit 2",
            },
            Dialog.confirm("Next"),
            {
                content: "pick the Senior Citizen holder",
                trigger: "#l10n_ph_holder_partner",
                run: "click",
            },
            ProductScreen.clickCustomer("Juan Dela Cruz"),
            {
                content: "add the Senior Citizen holder's information",
                trigger: '.modal-body button:contains("Add Customer Information"):enabled',
                run: "click",
            },
            Dialog.confirm("Confirm"),
            {
                content: "the Senior Citizen share is privileged",
                trigger:
                    '.order-container .orderline .l10n_ph_discount_privilege_holder:contains("Juan Dela Cruz")',
            },
            // No double discounting: the global discount is recomputed on the
            // regular soda (112.00) only, not on the Senior Citizen's share
            // (80.00) too.
            {
                content: "the global discount only applies on the regular share",
                trigger:
                    '.order-container .orderline:has(.product-name:contains("Global Discount")):has(.price:contains("-11.20"))',
            },
            ProductScreen.totalAmountIs("180.80"),
            {
                content:
                    "privileged shares still count among the items a bill can be split " +
                    "into (pos_restaurant's other use of isGlobalDiscountApplicable)",
                trigger: ".order-container",
                run() {
                    const line = posmodel
                        .getOrder()
                        .lines.find((line) => line.l10n_ph_discount_privilege_id);
                    if (!line.isGlobalDiscountApplicable()) {
                        throw new Error("The privileged share can't be split into another bill.");
                    }
                },
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
