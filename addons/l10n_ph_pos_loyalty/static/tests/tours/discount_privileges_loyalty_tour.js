// Part of Odoo. See LICENSE file for full copyright and licensing details.

import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import { applySeniorCitizenPrivilege } from "@l10n_ph_pos/../tests/tours/utils/discount_privileges_util";
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
            ...applySeniorCitizenPrivilege(2),
            // No double discounting: 10% of the regular soda (112.00) only,
            // not of the Senior Citizen's share too (80.00).
            PosLoyalty.hasRewardLine("10% on the order", "-11.20"),
            // ... and no reward line of the VAT exempt group for it either.
            PosLoyalty.orderTotalIs("180.80"),
        ].flat(),
});
