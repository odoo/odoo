// Part of Odoo. See LICENSE file for full copyright and licensing details.

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("l10n_ph_pos_loyalty_discount_privileges", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Test Soda", "2"),
            // 10% of 2 x 112.00 (VAT included).
            PosLoyalty.hasRewardLine("10% on the order", "-22.40"),
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
            // No double discounting: 10% of the regular soda (112.00) only,
            // not of the Senior Citizen's share too (80.00).
            PosLoyalty.hasRewardLine("10% on the order", "-11.20"),
            // ... and no reward line of the VAT exempt group for it either.
            PosLoyalty.orderTotalIs("180.80"),
        ].flat(),
});
