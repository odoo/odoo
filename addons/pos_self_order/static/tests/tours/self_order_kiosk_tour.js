import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.checkReferenceNotInProductName("Coca-Cola", "12345"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Numpad.click("3"),
        Utils.clickBtn("Order"),
        ConfirmationPage.orderNumberShown(),
        ConfirmationPage.orderNumberIs("K", "1"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("test_duplicate_order_kiosk", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});

registry.category("web_tour.tours").add("self_order_language_changes", {
    steps: () => [
        LandingPage.checkLanguageSelected("English"),
        LandingPage.checkCountryFlagShown("us"),

        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Test Category"),
        ProductPage.clickProduct("Test Product"),
        ...ProductPage.clickCancel(),
        LandingPage.checkLanguageSelected("English"),
        LandingPage.checkCountryFlagShown("us"),
        ...Utils.changeLanguage("Français"),

        Utils.clickBtn("Commander maintenant"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickCategory("Catégorie Test"),
        ProductPage.clickProduct("Produit Test"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_unpaid", {
    steps: () => [
        Utils.clickBtn("Order now"),
        ProductPage.clickCategory("Miscellaneous"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
        ConfirmationPage.orderNumberShown(),
    ],
});
