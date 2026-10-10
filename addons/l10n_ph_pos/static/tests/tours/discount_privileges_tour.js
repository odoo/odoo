// Part of Odoo. See LICENSE file for full copyright and licensing details.

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ph_pos_discount_privileges", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Soda", "3"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Juan Dela Cruz"),
            ProductScreen.clickControlButton("Discount Privileges"),
            {
                content:
                    "the selected line is only targeted on explicit request: the whole " +
                    "order is the default",
                trigger: "#l10n_ph_target_order:checked",
            },
            {
                content: "select the Senior Citizen privilege",
                trigger:
                    '.mb-3:has(label:contains("20% Senior Citizen Discount")) input[type="checkbox"]',
                run: "click",
            },
            {
                content: "select the PWD privilege",
                trigger: '.mb-3:has(label:contains("20% PWD Discount")) input[type="checkbox"]',
                run: "click",
            },
            {
                content: "share between 3 persons",
                trigger: "#l10n_ph_persons_sharing",
                run: "edit 3",
            },
            Dialog.confirm("Next"),
            {
                content: "the PWD ID is collected first (privileges are ordered by name)",
                trigger: '.modal-body h6:contains("20% PWD Discount")',
            },
            {
                content: "the ID holder's contact is required",
                trigger: '.modal-body button:contains("Add Customer Information"):disabled',
            },
            {
                content: "pick a contact without a PWD ID",
                trigger: "#l10n_ph_holder_partner",
                run: "click",
            },
            ProductScreen.clickCustomer("Pedro Penduko"),
            {
                content: "their missing PWD ID must be added on their contact first",
                trigger:
                    '.modal-body:has(.alert-warning:contains("Pedro Penduko has no Person with Disability ID")) button:contains("Add Customer Information"):disabled',
            },
            {
                content: "pick the PWD holder among the contacts",
                trigger: "#l10n_ph_holder_partner",
                run: "click",
            },
            ProductScreen.clickCustomer("Abigail Dela Cruz"),
            {
                content: "the PWD holder's ID is taken from their contact",
                trigger:
                    '.modal-body:has(h6:contains("20% PWD Discount")):has(#l10n_ph_holder_partner:contains("Abigail Dela Cruz")):not(:has(.alert-warning)) .l10n_ph_holder_id:contains("PWD-REG-001")',
            },
            {
                content: "the PWD holder is not present",
                trigger: "#l10n_ph_is_present_no",
                run: "click",
            },
            {
                content: "fill in the representative's name",
                trigger: "#l10n_ph_representative_name",
                run: "edit Maria Dela Cruz",
            },
            {
                content: "fill in the representative's ID",
                trigger: "#l10n_ph_representative_id",
                run: "edit REP-001",
            },
            {
                content: "add the PWD holder's information",
                trigger: '.modal-body button:contains("Add Customer Information")',
                run: "click",
            },
            // Only one of the two ID slots has been filled: Confirm must stay
            // disabled until the second holder is collected too.
            Dialog.footerBtnIsDisabled("Confirm"),
            {
                content:
                    "the Senior Citizen slot isn't prefilled from the order's customer, " +
                    "even though they have a Senior Citizen ID",
                trigger:
                    '.modal-body:has(h6:contains("20% Senior Citizen Discount")) #l10n_ph_holder_partner:contains("Select the ID holder")',
            },
            {
                content: "try to pick the PWD holder again for the Senior Citizen slot",
                trigger: "#l10n_ph_holder_partner",
                run: "click",
            },
            ProductScreen.clickCustomer("Abigail Dela Cruz"),
            {
                content: "a person can only claim one privilege",
                trigger:
                    '.modal-body .alert-danger:contains("Abigail Dela Cruz already claims the 20% PWD Discount privilege")',
            },
            {
                content: "pick the Senior Citizen holder among the contacts",
                trigger: "#l10n_ph_holder_partner",
                run: "click",
            },
            ProductScreen.clickCustomer("Juan Dela Cruz"),
            {
                content: "the Senior Citizen holder's ID is taken from their contact",
                trigger:
                    '.modal-body:has(h6:contains("20% Senior Citizen Discount")):not(:has(.alert-danger)):has(#l10n_ph_holder_partner:contains("Juan Dela Cruz")) .l10n_ph_holder_id:contains("SC-REG-001")',
            },
            {
                content: "add the prefilled Senior Citizen holder's information",
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
            {
                content: "each ID holder shows on their own discounted share",
                trigger:
                    '.order-container .orderline:has(.info-list li:contains("discount off")) .l10n_ph_discount_privilege_holder:contains("Juan Dela Cruz"):contains("SC-REG-001")',
            },
            {
                content: "the PWD holder shows on their own share too",
                trigger:
                    '.order-container .orderline .l10n_ph_discount_privilege_holder:contains("Abigail Dela Cruz"):contains("PWD-REG-001"):contains("Representative: Maria Dela Cruz (REP-001)")',
            },
            {
                content: "the regular share shows no ID holder",
                trigger:
                    '.order-container .orderline:not(:has(.info-list li:contains("discount off"))):not(:has(.l10n_ph_discount_privilege_holder))',
            },
            {
                content:
                    "the SC/PWD discount breakdown summary renders on the order screen, " +
                    "without the ID holders",
                trigger:
                    '.l10n_ph_discount_privileges_summary:has(span:contains("20% Senior Citizen Discount")):has(span:contains("20% PWD Discount")):not(:contains("Discount Discount")):not(:contains("Juan Dela Cruz"))',
            },
            {
                content: "select one of the already-privileged shares",
                trigger: '.order-container .orderline:has(.info-list li:contains("discount off"))',
                run: "click",
            },
            {
                content: "no double discounting: a privileged share's discount can't be edited",
                trigger: ".numpad button.numpad-discount:disabled",
            },
            {
                content: "nor its price",
                trigger: ".numpad button.numpad-price:disabled",
            },
            {
                content: "nor its quantity, pro-rated by headcount",
                trigger: ".numpad button.numpad-qty:disabled",
            },
            ProductScreen.clickNumpad("3"),
            Dialog.is({ title: "Cannot modify a discount privilege share" }),
            Dialog.confirm(),
            {
                content: "the privileged share kept its quantity",
                trigger:
                    '.order-container .orderline.selected:has(.qty:contains("1")):has(.info-list li:contains("discount off"))',
            },
            ProductScreen.clickControlButton("Discount Privileges"),
            {
                content:
                    "reopening on an already-privileged line shows the BIR Customer " +
                    "Information already on file, not the configure step (that specific " +
                    "line has nothing left to split)",
                trigger:
                    '.modal-body:has(:contains("ID Holder Juan Dela Cruz")):has(:contains("ID Holder Abigail Dela Cruz"))',
            },
            Dialog.confirm("Close", ".btn-secondary"),
            // Changing the customer reprices the order from the pricelist: the
            // privileged shares must keep their VAT-exempt price.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Pedro Penduko"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Juan Dela Cruz"),
            ProductScreen.customerIsSelected("Juan Dela Cruz"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("l10n_ph_pos_discount_privileges_undo", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Soda", "2"),
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
                content: "select the Senior Citizen share",
                trigger:
                    '.order-container .orderline:has(.l10n_ph_discount_privilege_holder:contains("Juan Dela Cruz"))',
                run: "click",
            },
            ProductScreen.clickNumpad("⌫"),
            {
                content:
                    "undoing the split gives the Senior Citizen share back to the regular one, " +
                    "rather than dropping it from the order",
                trigger:
                    '.order-container:not(:has(.l10n_ph_discount_privilege_holder)) .orderline:has(.product-name:contains("Test Soda")):has(.qty:contains("2"))',
            },
            ProductScreen.totalAmountIs("200.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
