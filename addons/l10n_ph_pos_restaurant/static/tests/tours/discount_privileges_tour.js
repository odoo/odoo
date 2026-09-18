// Part of Odoo. See LICENSE file for full copyright and licensing details.

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ph_pos_restaurant_discount_privileges", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Soda", "3"),
            ProductScreen.clickControlButton("Discount Privileges"),
            {
                content: "select the Senior Citizen privilege",
                trigger: '.mb-3:has(label:contains("Senior Citizen")) input[type="checkbox"]',
                run: "click",
            },
            {
                content: "select the PWD privilege",
                trigger: '.mb-3:has(label:contains("PWD")) input[type="checkbox"]',
                run: "click",
            },
            {
                content: "share between 3 persons",
                trigger: "#l10n_ph_persons_sharing",
                run: "edit 3",
            },
            Dialog.confirm("Next"),
            {
                content: "fill in the first ID holder's name",
                trigger: "#l10n_ph_holder_name",
                run: "edit Juan Dela Cruz",
            },
            {
                content: "fill in the first ID holder's ID number",
                trigger: "#l10n_ph_holder_id_number",
                run: "edit SC-REG-001",
            },
            {
                content: "add the first customer's information",
                trigger: '.modal-body button:contains("Add Customer Information")',
                run: "click",
            },
            // Only one of the two ID slots has been filled: Confirm must stay
            // disabled until the second holder is collected too.
            Dialog.footerBtnIsDisabled("Confirm"),
            {
                content: "fill in the second ID holder's name",
                trigger: "#l10n_ph_holder_name",
                run: "edit Abigail Dela Cruz",
            },
            {
                content: "fill in the second ID holder's ID number",
                trigger: "#l10n_ph_holder_id_number",
                run: "edit PWD-REG-001",
            },
            {
                content: "add the second customer's information",
                trigger: '.modal-body button:contains("Add Customer Information")',
                run: "click",
            },
            Dialog.confirm("Confirm"),
            {
                content: "the SC share renders with its 20% discount badge",
                trigger:
                    '.order-container .orderline:has(.product-name:contains("Test Soda")):has(.qty:contains("1")):has(.info-list li:contains("discount off"))',
            },
            {
                content: "the regular share renders alongside it, undiscounted",
                trigger:
                    '.order-container .orderline:has(.product-name:contains("Test Soda")):has(.qty:contains("1")):not(:has(.info-list li:contains("discount off")))',
            },
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
