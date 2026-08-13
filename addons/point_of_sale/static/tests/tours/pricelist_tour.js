import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/tours/utils/numpad_util";
import * as Order from "@point_of_sale/../tests/tours/utils/generic_components/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/tours/utils/dialog_util";
import * as Pricelist from "@point_of_sale/../tests/tours/utils/pricelist_util";
import * as Chrome from "@point_of_sale/../tests/tours/utils/chrome_util";

registry.category("web_tour.tours").add("pos_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Pricelist.setUp(),
            Pricelist.waitForUnitTest(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickPriceList("Fixed", true, "Public Pricelist"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Acme Corporation"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Lumber Inc"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickDisplayedProduct("Wall Shelf", true, "1.0"),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Wall Shelf")[0], isActive: ["mobile"] },
            Numpad.click("2"),
            ...ProductScreen.selectedOrderlineHasDirect("Wall Shelf", "2.0"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ...Order.hasTotal(`$ 2.00`),
            ProductScreen.clickDisplayedProduct("Small Shelf", true, "1.0"),
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
            ProductScreen.closePos(),
        ].flat(),
});
