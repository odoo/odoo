import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyValidity1", {
    steps: () =>
        [
            // First tour should not get any automatic rewards

            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Not valid -> date
            ProductScreen.addOrderline("Awesome Item", "5"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
            PosLoyalty.orderTotalIs("500"),
            PosLoyalty.finalizeOrder("Cash", "500"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosLoyaltyValidity2", {
    steps: () =>
        [
            // Second tour
            // Valid
            Chrome.startPoS(),
            ProductScreen.addOrderline("Awesome Item", "5"), // 500
            PosLoyalty.hasRewardLine("90% on the cheapest product", "-90"),
            PosLoyalty.finalizeOrder("Cash", "410"),

            // Not valid -> usage
            ProductScreen.addOrderline("Awesome Item", "5"),
            PosLoyalty.isRewardButtonHighlighted(false, true),
            PosLoyalty.orderTotalIs("500"),
            PosLoyalty.finalizeOrder("Cash", "500"),
        ].flat(),
});
