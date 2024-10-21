import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import { inLeftSide, waitForLoading } from "@point_of_sale/../tests/tours/utils/common";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";

registry.category("web_tour.tours").add("pos_basic_order_01_multi_payment_and_change", {
    steps: () =>
        [
            waitForLoading(),
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0", "5.10"),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "2.0", "10.20"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.enterPaymentLineAmount("Cash", "5", true, {
                amount: "5.0",
                remaining: "5.20",
            }),
            PaymentScreen.clickPaymentMethod("Bank", true, { amount: "5.2" }),
            PaymentScreen.enterPaymentLineAmount("Bank", "6", true, {
                amount: "6.0",
                change: "0.80",
            }),
            ProductScreen.finishOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_basic_order_02_decimal_order_quantity", {
    steps: () =>
        [
            waitForLoading(),
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Desk Organizer", true, "1.0"),
            inLeftSide(Numpad.click(".")),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.0", "0.0"),
            inLeftSide(Numpad.click("9")),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.9", "4.59"),
            inLeftSide(Numpad.click("9")),
            ProductScreen.selectedOrderlineHas("Desk Organizer", "0.99", "5.05"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash", true, { amount: "5.05" }),
            ProductScreen.finishOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_basic_order_03_tax_position", {
    steps: () =>
        [
            waitForLoading(),
            Chrome.startPoS(),
            ProductScreen.clickDisplayedProduct("Letter Tray", true, "1.0"),
            inLeftSide(...Order.hasTotal("5.28")),
            ProductScreen.clickFiscalPosition("FP-POS-2M", true),
            inLeftSide(...Order.hasTotal("5.52")),
            ProductScreen.closePos(),
        ].flat(),
});
