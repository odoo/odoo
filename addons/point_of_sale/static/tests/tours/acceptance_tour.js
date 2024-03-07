/** @odoo-module */

import * as Numpad from "@point_of_sale/../tests/tours/helpers/NumpadTourMethods";
import { registry } from "@web/core/registry";
import * as Order from "@point_of_sale/../tests/tours/helpers/generic_components/OrderWidgetMethods";
import { inLeftSide } from "@point_of_sale/../tests/tours/helpers/utils";
import * as Acceptance from "@point_of_sale/../tests/tours/helpers/AcceptanceTourMethod";
import * as ProductScreen from "./helpers/ProductScreenTourMethods";

registry.category("web_tour.tours").add("pos_basic_order_01", {
    test: true,
    steps: () =>
        [
            Acceptance.waitForLoading(),
            ProductScreen.clickShowProductsMobile(),
            Acceptance.addProductToOrder("Desk Organizer"),
            inLeftSide(Order.hasTotal("5.10")),
            Acceptance.addProductToOrder("Desk Organizer"),
            inLeftSide(Order.hasTotal("10.20")),
            Acceptance.gotoPaymentScreenAndSelectPaymentMethod(),
            Acceptance.fillPaymentValue("Cash", "5"),
            Acceptance.selectedPaymentHas("Cash", "5.0"),
            Acceptance.verifyPaymentRemaining("5.20"),
            Acceptance.verifyPaymentChange("0.00"),
            Acceptance.payWithBank(),
            Acceptance.selectedPaymentHas("Bank", "5.2"),
            Acceptance.fillPaymentValue("Bank", "6"),
            Acceptance.selectedPaymentHas("Bank", "6.0"),
            Acceptance.verifyPaymentRemaining("0.00"),
            Acceptance.verifyPaymentChange("0.80"),
            Acceptance.finishOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_basic_order_02", {
    test: true,
    steps: () =>
        [
            Acceptance.waitForLoading(),
            ProductScreen.clickShowProductsMobile(),
            Acceptance.addProductToOrder("Desk Organizer"),
            Acceptance.selectedOrderlineHas({ product: "Desk Organizer", quantity: "1.0" }),
            inLeftSide(Numpad.click(".")),
            Acceptance.selectedOrderlineHas({
                product: "Desk Organizer",
                quantity: "0.0",
                price: "0.0",
            }),
            inLeftSide(Numpad.click("9")),
            Acceptance.selectedOrderlineHas({
                product: "Desk Organizer",
                quantity: "0.9",
                price: "4.59",
            }),
            inLeftSide(Numpad.click("9")),
            Acceptance.selectedOrderlineHas({
                product: "Desk Organizer",
                quantity: "0.99",
                price: "5.05",
            }),
            Acceptance.gotoPaymentScreenAndSelectPaymentMethod(),
            Acceptance.selectedPaymentHas("Cash", "5.05"),
            Acceptance.finishOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("pos_basic_order_03", {
    test: true,
    steps: () =>
        [
            Acceptance.waitForLoading(),
            ProductScreen.clickShowProductsMobile(),
            Acceptance.addProductToOrder("Letter Tray"),
            Acceptance.selectedOrderlineHas({ product: "Letter Tray", quantity: "1.0" }),
            inLeftSide(Order.hasTotal("5.28")),
            Acceptance.setFiscalPositionOnOrder("FP-POS-2M"),
            inLeftSide(Order.hasTotal("5.52")),
            ProductScreen.closePos(),
        ].flat(),
});
