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
            combo.select("Combo Product 3"),
            combo.isConfirmationButtonDisabled(),
            combo.select("Combo Product 9"),
            // Check Product Configurator is open
            Dialog.is("Attribute selection"),
            {
                content: "dialog discard",
                trigger: ".modal-footer .btn:text(Add) + .btn:text(Discard)",
                run: "click",
            },
            combo.select("Combo Product 5"),
            combo.select("Combo Product 7"),
            combo.isSelected("Combo Product 7"),
            combo.select("Combo Product 8"),
            combo.isSelected("Combo Product 8"),
            combo.isNotSelected("Combo Product 7"),
            Dialog.confirm(),
            inLeftSide([
                ...ProductScreen.selectedOrderlineHasDirect("Office Combo", "1", "62.1"),
                ...ProductScreen.clickLine("Combo Product 3"),
                ...Order.hasLine({ withClass: ":eq(3).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 3", "1"),
                ...ProductScreen.clickLine("Combo Product 5"),
                ...Order.hasLine({ withClass: ":eq(1).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 5", "1"),
                ...ProductScreen.clickLine("Combo Product 8"),
                ...Order.hasLine({ withClass: ":eq(2).selected" }),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 8", "1"),
            ]),
            // check that you can select a customer which triggers a recomputation of the price
            ...ProductScreen.clickPartnerButton(),
            ...ProductScreen.clickCustomer("Partner Test 1"),

            // check that you can change the quantity of a combo product
            inLeftSide([
                ...ProductScreen.clickLine("Combo Product 3"),
                Numpad.click("2"),
                ...ProductScreen.selectedOrderlineHasDirect("Combo Product 3", "2"),
                ...ProductScreen.orderLineHas("Combo Product 5", "2"),
                ...ProductScreen.orderLineHas("Combo Product 8", "2"),
                ...ProductScreen.orderLineHas("Office Combo", "2", "124.2"),
            ]),

            // check that removing a combo product removes all the combo products
            inLeftSide([
                {
                    ...ProductScreen.clickLine("Combo Product 3", "2")[0],
                    isActive: ["mobile"],
                },
                Numpad.click("⌫"),
                Numpad.click("⌫"),
                ...Order.doesNotHaveLine(),
            ]),

            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 3"),
            combo.select("Combo Product 5"),
            combo.select("Combo Product 8"),
            Dialog.confirm(),
            ...ProductScreen.totalAmountIs("62.10"),
            ...ProductScreen.clickPayButton(),
            ...PaymentScreen.clickPaymentMethod("Bank"),
            ...PaymentScreen.clickValidate(),
            ...FeedbackScreen.isShown(),
            ...FeedbackScreen.clickNextOrder(),

            // another order but won't be sent to the backend
            ...ProductScreen.clickDisplayedProduct("Office Combo"),
            combo.select("Combo Product 2"),
            combo.select("Combo Product 4"),
            combo.select("Combo Product 6"),
            Dialog.confirm(),
            {
                content: "The 'Combo Product 6' card should not display a quantity.",
                trigger:
                    "article.product .product-content:has(.product-name:contains('Combo Product 6')):not(:has(.product-cart-qty))",
            },
            ...ProductScreen.totalAmountIs("59.17"),
            ...inLeftSide(Order.hasTax("10.56")),
            // the split screen is tested in `pos_restaurant`
        ].flat(),
});

registry.category("web_tour.tours").add("ProductComboPriceCheckTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Desk Combo"),
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
