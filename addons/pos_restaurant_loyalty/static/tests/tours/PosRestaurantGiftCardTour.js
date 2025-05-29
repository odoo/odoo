import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PosLoyalty from "@pos_loyalty/../tests/tours/utils/pos_loyalty_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosRestaurantGiftCardReturnFromFloor", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            FloorScreen.clickTable("4"),
            ProductScreen.addOrderline("Gift Card", "1", "50", "50"),
            PosLoyalty.createManualGiftCard("dummy-card-0000", 125),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "125"),
            Chrome.clickPlanButton(),
            FloorScreen.isShown(),
            FloorScreen.clickTable("4"),
            Order.hasLine({
                run: "click",
                productName: "Gift Card",
            }),
            ProductScreen.selectedOrderlineHas("Gift Card", "1", "125"),
            PosLoyalty.orderTotalIs("125"),
            PosLoyalty.finalizeOrder("Cash", "125"),
        ].flat(),
});
