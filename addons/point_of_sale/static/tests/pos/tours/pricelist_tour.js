import { registry } from "@web/core/registry";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Pricelist from "@point_of_sale/../tests/pos/tours/utils/pricelist_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as OfflineUtil from "@point_of_sale/../tests/generic_helpers/offline_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as ReceiptScreen from "@point_of_sale/../tests/pos/tours/utils/receipt_screen_util";

registry.category("web_tour.tours").add("pos_pricelist", {
    steps: () =>
        [
            Chrome.startPoS(),
            Pricelist.setUp(),
            Dialog.confirm("Open Register"),
            OfflineUtil.setOfflineMode(),
            ProductScreen.clickPriceList("Fixed", true, "Public Pricelist"),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner One"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Two"),
            ProductScreen.clickPriceList("Public Pricelist", true),
            ProductScreen.clickDisplayedProduct("Product for pricelist 1", true, "1"),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Product for pricelist 1")[0], isActive: ["mobile"] },
            Numpad.click("2"),
            ...ProductScreen.selectedOrderlineHasDirect("Product for pricelist 1", "2"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ...Order.hasTotal(`$ 2.00`),
            ProductScreen.clickDisplayedProduct("Product for pricelist 2", true, "1"),
            ProductScreen.clickReview(),
            { ...ProductScreen.clickLine("Product for pricelist 2")[0], isActive: ["mobile"] },
            Numpad.click("Price"),
            Numpad.isActive("Price"),
            Numpad.click("5"),
            ...Order.hasLine({
                productName: "Product for pricelist 2",
                price: "5.0",
                withClass: ".selected",
            }),
            Numpad.click("Qty"),
            Numpad.isActive("Qty"),
            { ...ProductScreen.back(), isActive: ["mobile"] },
            ProductScreen.clickPriceList("Public Pricelist"),
            ...Order.hasTotal(`$ 8.96`),
            ProductScreen.clickPriceList("min_quantity ordering"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            Dialog.confirm(),
            Order.hasLine({ price: "5.00" }),
            ReceiptScreen.clickNextOrder(),
            ProductScreen.clickDisplayedProduct("Awesome Item", true, "1"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Cash"),
            PaymentScreen.clickValidate(),
            ReceiptScreen.noDiscountAmount(),
            OfflineUtil.setOnlineMode(),
            ProductScreen.closePos(),
        ].flat(),
});
