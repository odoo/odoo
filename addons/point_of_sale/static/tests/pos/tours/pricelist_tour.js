/* global posmodel */

import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Pricelist from "@point_of_sale/../tests/pos/tours/utils/pricelist_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as ProductConfigurator from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";
import { refresh, scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("pos_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Pricelist.setUp(),
            Pricelist.waitForUnitTest(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            ProductScreen.clickPriceList("Fixed", true, "Public Pricelist"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Lumber Inc"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickDisplayedProduct("Wall Shelf", true, "1"),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Wall Shelf")[0], isActive: ["mobile"] },
            Numpad.click("2"),
            ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf", "2"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ...Order.hasTotal(`$ 2.00`),
            ProductScreen.clickDisplayedProduct("Small Shelf", true, "1"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Small Shelf")[0], isActive: ["mobile"] },
            Numpad.click("Price"),
            Numpad.isActive("Price"),
            Numpad.click("5"),
            ...Order.hasLine({ productName: "Small Shelf", price: "5.0", withClass: ".selected" }),
            Numpad.click("Qty"),
            Numpad.isActive("Qty"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.clickPriceList("Public Pricelist"),
            ...Order.hasTotal(`$ 8.96`),
            ProductScreen.clickPriceList("min_quantity ordering"),
            OfflineUtil.setOnlineMode(),
            ProductScreen.closePos(),
        ].flat(),
});

// # With test_pricelist set on the order:
// # - First banana variant will be priced at 100 via product variant
// # - Second banana variant will be priced at 150 via product variant
// # - Third banana variant will be priced at 20 via product template
// # - First apple variant will be priced at 100 via product variant
// # - All product without rules and with product_category will be priced at 500
const test_pricelists_in_pos_steps = [
    ProductScreen.clickPriceList("Test Pricelist"),
    scan_barcode("banana_0"),
    ProductScreen.selectedOrderlineHas("Banana", "1", "100.0", "BIG"),
    scan_barcode("banana_1"),
    ProductScreen.selectedOrderlineHas("Banana", "1", "150.0", "MEDIUM"),
    scan_barcode("banana_2"),
    ProductScreen.selectedOrderlineHas("Banana", "1", "20.0", "SMALL"),
    scan_barcode("apple_0"),
    ProductScreen.selectedOrderlineHas("Apple", "1", "100.0", "BIG"),
    scan_barcode("apple_1"),
    ProductScreen.selectedOrderlineHas("Apple", "1", "500.0", "MEDIUM"),
    scan_barcode("apple_2"),
    ProductScreen.selectedOrderlineHas("Apple", "1", "500.0", "SMALL"),

    ProductScreen.clickPriceList("Percentage Pricelist"),
    scan_barcode("banana_0"),
    ProductScreen.selectedOrderlineHas("Banana", "2", "100.0", "BIG"),
    scan_barcode("banana_1"),
    ProductScreen.selectedOrderlineHas("Banana", "2", "150.0", "MEDIUM"),
    scan_barcode("banana_2"),
    ProductScreen.selectedOrderlineHas("Banana", "2", "20.0", "SMALL"),
    scan_barcode("apple_0"),
    ProductScreen.selectedOrderlineHas("Apple", "2", "100.0", "BIG"),
    scan_barcode("apple_1"),
    ProductScreen.selectedOrderlineHas("Apple", "2", "500.0", "MEDIUM"),
    scan_barcode("apple_2"),
    ProductScreen.selectedOrderlineHas("Apple", "2", "500.0", "SMALL"),

    // Try scan a product with nested pricelist on variant
    scan_barcode("pear_0"),
    ProductScreen.selectedOrderlineHas("Pear", "1", "10.0", "BIG"),
    scan_barcode("pear_1"),
    ProductScreen.selectedOrderlineHas("Pear", "1", "20.0", "MEDIUM"),
    scan_barcode("pear_2"),
    ProductScreen.selectedOrderlineHas("Pear", "1", "30.0", "SMALL"),

    // Try scan a product with nested pricelist on template
    scan_barcode("lime_0"),
    ProductScreen.selectedOrderlineHas("Lime", "1", "50.0", "BIG"),
    scan_barcode("lime_1"),
    ProductScreen.selectedOrderlineHas("Lime", "1", "100.0", "MEDIUM"),
    scan_barcode("lime_2"),
    ProductScreen.selectedOrderlineHas("Lime", "1", "200.0", "SMALL"),

    // Try scan a product with nested pricelist on category
    scan_barcode("orange_0"),
    ProductScreen.selectedOrderlineHas("Orange", "1", "500.0", "BIG"),
    scan_barcode("orange_1"),
    ProductScreen.selectedOrderlineHas("Orange", "1", "300.0", "MEDIUM"),
    scan_barcode("orange_2"),
    ProductScreen.selectedOrderlineHas("Orange", "1", "250.0", "SMALL"),

    // Try scan a product with no pricelist rules
    scan_barcode("kiwi_0"),
    ProductScreen.selectedOrderlineHas("Kiwi", "1", "10.0", "BIG"),
    scan_barcode("kiwi_1"),
    ProductScreen.selectedOrderlineHas("Kiwi", "1", "5.0", "MEDIUM"),
    scan_barcode("kiwi_2"),
    ProductScreen.selectedOrderlineHas("Kiwi", "1", "5.0", "SMALL"),

    // Test if post-loaded product with attribute open the configrator
    scan_barcode("cherry_3"),
    Chrome.waitRequest(),
    {
        content: "Click hided product with attribute",
        trigger: "body",
        run: () => {
            const productTemplate = posmodel.models["product.template"].find(
                (p) => p.name === "Cherry"
            );

            posmodel.addLineToCurrentOrder({
                product_tmpl_id: productTemplate,
            });
        },
    },
    ProductConfigurator.pickRadio("BIG"),
    ProductConfigurator.pickRadio("GREEN"),
    ProductConfigurator.isUnavailable("RED"),
    Dialog.confirm(),
    ProductScreen.clickPayButton(),
    PaymentScreen.clickPaymentMethod("Bank", true, { remaining: "0.00" }),
    PaymentScreen.clickValidate(),
    ReceiptScreen.isShown(),
    ReceiptScreen.clickNextOrder(),
];

registry.category("web_tour.tours").add("test_pricelists_in_pos", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...test_pricelists_in_pos_steps,
            refresh(), // Check pricelist sorting after a refresh
            ...test_pricelists_in_pos_steps,
        ].flat(),
});
