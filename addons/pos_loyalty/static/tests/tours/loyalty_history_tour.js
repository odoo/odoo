import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("LoyaltyHistoryTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            PosLoyalty.orderTotalIs("10"),

            PosLoyalty.finalizeOrder("Cash", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_history_earn_and_spend", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // Select the partner first so their pre-loaded points are visible
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAA Test Partner"),
            // Buy a $10 product — this earns 10 points
            ProductScreen.addOrderline("Whiteboard Pen", "1"),
            // Claim the reward that costs 5 points (10% discount on the order)
            PosLoyalty.claimReward("10% on your order"),
            // $10 - 10% = $9.00
            PosLoyalty.orderTotalIs("9.00"),
            PosLoyalty.finalizeOrder("Cash", "9"),
        ].flat(),
});
