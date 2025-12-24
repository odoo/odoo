import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as StockPaymentScreen from "@pos_stock/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PosSale from "@pos_sale/../tests/tours/utils/pos_sale_utils";
import * as PosSaleStock from "@pos_sale_stock/../tests/tours/utils/pos_sale_stock_utils";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Utils from "@point_of_sale/../tests/generic_helpers/utils";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("PosSettleOrderRealTime", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.totalAmountIs(40),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder3", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.0" }),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_import_lot_groupable_and_non_groupable", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1, { loadSN: true }),
            PosSaleStock.selectedOrderLinesHasLots("Groupable Product", []),
            ProductScreen.checkOrderlinesNumber(5),
            ProductScreen.totalAmountIs(60),
            ProductScreen.selectedOrderlineHas("Groupable Product", "1", "10"),
        ].flat(),
});

registry.category("web_tour.tours").add("PosShipLaterNoDefault", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            PaymentScreen.isShown(),
            Utils.negateStep(StockPaymentScreen.shippingLaterHighlighted()),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrder4", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.selectedOrderlineHas("Product A", "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            StockPaymentScreen.clickShipLaterButton(),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("PosSettleOrderShipLater", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(2),
            ProductScreen.clickPayButton(),
            StockPaymentScreen.clickShipLaterButton(),
            StockPaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            PosSale.settleNthOrder(1),
            ProductScreen.clickPayButton(),
            StockPaymentScreen.clickShipLaterButton(),
            StockPaymentScreen.shippingLaterHighlighted(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.remainingIs("0.0"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_order_with_lot", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1, { loadSN: true }),
            PosSaleStock.selectedOrderLinesHasLots("Product A", ["1001", "1002"]),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_lots_sale_order_1", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            Order.hasLine({ productName: "Product", quantity: "6.0" }),
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_lots_sale_order_2", {
    steps: () =>
        [
            Chrome.startPoS(),
            PosSale.settleNthOrder(1, { loadSN: false }),
            Order.hasLine({ productName: "Product", quantity: "6.0" }),
            {
                content: "Check that the line-lot-icon has text-danger class",
                trigger: `.order-container .orderline:has(.product-name:contains("Product")) .line-lot-icon.text-danger`,
            },
        ].flat(),
});

registry.category("web_tour.tours").add("test_multiple_lots_sale_order_3", {
    steps: () =>
        [
            Chrome.startPoS(),
            PosSale.settleNthOrder(1, { loadSN: true }),
            PosSaleStock.selectedOrderLinesHasLots("Product", ["1002"]),
            Utils.negateStep(...PosSaleStock.selectedOrderLinesHasLots("Product", ["1001"])),
            ProductScreen.selectedOrderlineHas("Product", "2.00"),
            ProductScreen.clickOrderline("Product", "4"),
            PosSaleStock.selectedOrderLinesHasLots("Product", ["1001"]),
            ProductScreen.selectedOrderlineHas("Product", "4.00"),
            Utils.negateStep(...PosSaleStock.selectedOrderLinesHasLots("Product", ["1002"])),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_groupable_lot_total_amount", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1, { loadSN: true }),
            Order.hasTotal("12.00"),
        ].flat(),
});

registry.category("web_tour.tours").add("test_settle_changed_price_with_lots", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            PosSale.settleNthOrder(1),
            ProductScreen.totalAmountIs("180.00"),
            Order.doesNotHaveLine({
                productName: "Settle Lots",
                quantity: "1.0",
                price: "100",
            }),
        ].flat(),
});
