import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyPartnerListAfterCouponRemoval", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Desk Organizer", "1"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA Partner"),

            PosLoyalty.enterCode("9911"),
            PosLoyalty.hasRewardLine("10% on your order"),
            PosLoyalty.removeRewardLine("10% on your order"),

            // The coupon is deleted from the local models when its reward line is
            // removed: the partner list must still be able to render its owner's line.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("AAAA Partner"),
            ProductScreen.customerIsSelected("AAAA Partner"),
        ].flat(),
});
