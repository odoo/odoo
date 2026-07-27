import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as ProductConfiguratorPopup from "@point_of_sale/../tests/pos/tours/utils/product_configurator_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import { registry } from "@web/core/registry";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";

registry.category("web_tour.tours").add("GS1BarcodeScanningTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // Add the Product 1 with GS1 barcode
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1"),
            scan_barcode("0108431673020125100000001"),
            ProductScreen.selectedOrderlineHas("Product 1", 2),

            // Add the product 1 with GS1 barcode and quantity
            scan_barcode("0108431673020125305"),
            ProductScreen.selectedOrderlineHas("Product 1", 7),
            scan_barcode("01084316730201253010"),
            ProductScreen.selectedOrderlineHas("Product 1", 17),

            // Add the Product 2 with normal barcode
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2"),
            scan_barcode("08431673020126"),
            ProductScreen.selectedOrderlineHas("Product 2", 2),

            // Add the Product 3 with normal barcode
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3"),
            scan_barcode("3760171283370"),
            ProductScreen.selectedOrderlineHas("Product 3", 2),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_variants_merge_line_barcode", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("A variant product"),
            ProductConfiguratorPopup.pickRadio("S"),
            Dialog.confirm(),
            Order.hasLine({
                productName: "A variant product",
                quantity: 1,
                attributeLine: "S, blue",
            }),
            scan_barcode("TEST123"),
            Order.hasLine({
                productName: "A variant product",
                quantity: 2,
                attributeLine: "S, Blue",
            }),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_gs1_barcode_scan_missing_product_variant", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            scan_barcode("0105400000002649"),
            inLeftSide(
                Order.hasLine({
                    productName: "GS1 Missing Variant Product",
                    quantity: 1,
                    attributeLine: "S",
                })
            ),
            scan_barcode("0105400000002649"),
            inLeftSide(
                Order.hasLine({
                    productName: "GS1 Missing Variant Product",
                    quantity: 2,
                    attributeLine: "S",
                })
            ),
            Chrome.endTour(),
        ].flat(),
});

registry.category("web_tour.tours").add("test_dynamic_barcode_extra", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            scan_barcode("1234567890"),
            inLeftSide(
                Order.hasLine({
                    productName: "Dynamic Product",
                    attributeLine: "L",
                    price: "40.0",
                })
            ),
        ].flat(),
});
