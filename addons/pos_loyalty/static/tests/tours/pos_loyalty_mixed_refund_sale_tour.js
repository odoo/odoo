import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as TicketScreen from "@point_of_sale/../tests/tours/utils/ticket_screen_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosLoyaltyMixedRefundSaleReward", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            ProductScreen.addOrderline("Mixed Refund Product", "1"),
            PosLoyalty.finalizeOrder("Cash", "10"),

            ...ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("-0001"),
            TicketScreen.confirmRefund(),
            ProductScreen.isShown(),

            ProductScreen.addOrderline("Mixed Large Sale Product", "1"),
            ProductScreen.addOrderline("Mixed Cheapest Sale Product", "1"),
            PosLoyalty.enterCode("mixedrefund"),
            PosLoyalty.hasRewardLine("10% on the cheapest product", "-3.00"),
            PosLoyalty.orderTotalIs("217.00"),

            ProductScreen.clickLine("Mixed Large Sale Product"),
            ProductScreen.clickNumpad("⌫"),
            Order.doesNotHaveLine({ productName: "10% on the cheapest product" }),
            PosLoyalty.orderTotalIs("20.00"),
        ].flat(),
});
