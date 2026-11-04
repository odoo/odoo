// Part of Odoo. See LICENSE file for full copyright and licensing details.

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";

/**
 * Steps applying the Senior Citizen privilege of Juan Dela Cruz on the whole
 * order, shared among ``persons`` persons.
 */
export function applySeniorCitizenPrivilege(persons) {
    return [
        ProductScreen.clickControlButton("Discount Privileges"),
        {
            content: "select the Senior Citizen privilege",
            trigger:
                '.mb-3:has(label:contains("20% Senior Citizen Discount")) input[type="checkbox"]',
            run: "click",
        },
        {
            content: `share between ${persons} persons`,
            trigger: "#l10n_ph_persons_sharing",
            run: `edit ${persons}`,
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
            content: "the Senior Citizen share is split off",
            trigger:
                '.order-container .orderline .o_l10n_ph_discount_privilege_holder:contains("Juan Dela Cruz")',
        },
    ];
}
