import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import * as combo from "@point_of_sale/../tests/pos/tours/utils/combo_popup_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { scan_barcode } from "@point_of_sale/../tests/generic_helpers/utils";
import { inLeftSide } from "@point_of_sale/../tests/pos/tours/utils/common";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("ProductComboPriceTaxIncludedTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ...ProductScreen.clickDisplayedProduct("Sofa Combo"),
            combo.select("Combo Product Sofa (L, red)"),
            Dialog.confirm(),
            inLeftSide([
                ...Order.hasLine({
                    productName: "Combo product Sofa",
                    run: "click",
                    quantity: "1",
                    attributeLine: "L, red",
                }),
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),
            scan_barcode("SuperCombo"),
            combo.select("Monitor Stand"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Configurable Chair"),
            // Check Product Configurator is open
            Dialog.is("Attribute selection"),
            {
                content: "dialog discard",
                trigger: ".modal-footer .btn:text(Add) + .btn:text(Discard)",
                run: "click",
            },
            combo.select("Desk Pad"),
            combo.select("Magnetic Board"),
            combo.isSelected("Magnetic Board"),
            combo.select("Desk Organizer"),
            combo.isSelected("Desk Organizer"),
            combo.isNotSelected("Magnetic Board"),
            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Office Combo", "1", "50.87"),
                ...ProductScreen.clickLine("Monitor Stand"),
                ...Order.hasLine({ withClass: ":eq(3).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "1"),
                ...ProductScreen.clickLine("Desk Pad"),
                ...Order.hasLine({ withClass: ":eq(1).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Pad", "1"),
                ...ProductScreen.clickLine("Desk Organizer"),
                ...Order.hasLine({ withClass: ":eq(2).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Desk Organizer", "1"),
            ]),
            // check that you can select a customer which triggers a recomputation of the price
            ...ProductScreen.clickPartnerButton(),
            ...ProductScreen.clickCustomer("Partner Test 1", true),

            // check that you can change the quantity of a combo product
            inLeftSide([
                ...ProductScreen.clickLine("Monitor Stand"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Monitor Stand", "2"),
                ...ProductScreen.orderLineHas("Desk Pad", "2"),
                ...ProductScreen.orderLineHas("Desk Organizer", "2"),
                ...ProductScreen.orderLineHas("Office Combo", "2", "101.74"),
            ]),

            // check that removing a combo product removes all the combo products
            inLeftSide([
                {
                    ...ProductScreen.clickLine("Monitor Stand", "2")[0],
                    isActive: ["mobile"],
                },
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Monitor Stand"),
            combo.select("Desk Pad"),
            combo.select("Desk Organizer"),
            Dialog.confirm(),
            ...ProductScreen.totalAmountIs("50.87"),
            ...ProductScreen.clickPayButton(),
            ...PaymentScreen.clickPaymentMethod("Bank"),
            ...PaymentScreen.clickValidate(),
            ...FeedbackScreen.isShown(),
            ...FeedbackScreen.clickNextOrder(),

            // another order but won't be sent to the backend
            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Small Shelf"),
            combo.select("Wall Shelf Unit"),
            combo.select("Letter Tray"),
            Dialog.confirm(),
            {
                content: "The 'Letter Tray' card should not display a quantity.",
                trigger:
                    "article.product .product-content:has(.product-name:contains('Letter Tray')):not(:has(.product-cart-qty))",
            },
            ...ProductScreen.totalAmountIs("41.17"),
            ...inLeftSide(Order.hasTax("3.34")),
            // the split screen is tested in `pos_restaurant`
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboPriceCheckTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Combo"),
            combo.select("Whiteboard Pen"),
            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Desk Combo", "1", "7.00"),
                ...ProductScreen.orderLineHas("Desk Organizer", "1"),
                ...ProductScreen.orderLineHas("Desk Pad", "1"),
                ...ProductScreen.orderLineHas("Whiteboard Pen", "1"),
            ]),
            ProductScreen.totalAmountIs("7.00"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
        ].flat(),
});
