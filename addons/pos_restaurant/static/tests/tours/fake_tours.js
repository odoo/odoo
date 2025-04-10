/* global posmodel */

import { registry } from "@web/core/registry";
import * as ProductScreenPos from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as ProductScreenResto from "@pos_restaurant/../tests/tours/utils/product_screen_util";
import * as FloorScreen from "@pos_restaurant/../tests/tours/utils/floor_screen_util";
import * as ChromePos from "@point_of_sale/../tests/tours/utils/chrome_util";
import * as ChromeRestaurant from "@pos_restaurant/../tests/tours/utils/chrome";
import * as PaymentScreen from "@point_of_sale/../tests/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/tours/utils/receipt_screen_util";

const Chrome = { ...ChromePos, ...ChromeRestaurant };
const ProductScreen = { ...ProductScreenPos, ...ProductScreenResto };

const getRandomTable = () => {
    const tables = posmodel.currentFloor.table_ids;
    return tables[Math.floor(Math.random() * tables.length)].table_number;
};

const getRandomTableWithOrder = () => {
    const tables = posmodel.currentFloor.table_ids.filter(
        (table) => table["<-pos.order.table_id"].length > 0
    );
    return tables[Math.floor(Math.random() * tables.length)].table_number;
};

const getRandomProduct = () => {
    const products = posmodel.models["product.product"].filter(
        (p) =>
            !p.isConfigurable() &&
            !p.isCombo() &&
            !p.isTracked() &&
            p.id !== posmodel.config.tip_product_id?.id &&
            !posmodel.session._pos_special_products_ids?.includes(p.id)
    );
    return products[Math.floor(Math.random() * products.length)].name;
};

registry.category("web_tour.tours").add("PoSFakeTourRestaurant", {
    steps: () =>
        [
            FloorScreen.clickTable(getRandomTable()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            Chrome.clickPlanButton(),
            FloorScreen.clickTable(getRandomTable()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.clickNextOrder(),
        ].flat(),
});

registry.category("web_tour.tours").add("PoSFakeTourTransferOrder", {
    steps: () =>
        [
            FloorScreen.clickTable(getRandomTableWithOrder()),
            ProductScreen.clickControlButton("Transfer"),
            FloorScreen.clickTable(getRandomTable()),
            ProductScreen.clickDisplayedProduct(getRandomProduct()),
            Chrome.clickPlanButton(),
        ].flat(),
});
