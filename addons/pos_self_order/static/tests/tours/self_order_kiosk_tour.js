import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as CategoryPage from "@pos_self_order/../tests/tours/utils/category_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        ProductPage.checkKioskReferenceNotInProductName("Coca-Cola", "12345"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        ProductPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Yummy Burger"),
        ProductPage.clickKioskProduct("Taxi Burger"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53"),
        CartPage.checkKioskProduct("Yummy Burger", "10"),
        CartPage.checkKioskProduct("Taxi Burger", "11"),
        CartPage.checkTotalPrice("23.53"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53"),
        Utils.clickBtn("Pay"),
        CartPage.fillInput("Name", "Mr Kiosk"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Miscellaneous"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        ProductPage.clickKioskProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkKioskProduct("Fanta", "2.53", "1"),
        CartPage.clickBack(),
        ProductPage.clickBack(),
        ...CategoryPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickKioskCategory("Miscellaneous"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("kiosk_simple_order", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "2.53"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});

registry.category("web_tour.tours").add("kiosk_order_price_null", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickKioskProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Coca-Cola", "0.00"),
        Utils.clickBtn("Pay"),
        ConfirmationPage.orderNumberShown(),
        Utils.checkBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("self_order_language_changes", {
    steps: () => [
        Utils.clickBtn("Order Now"),

        LandingPage.checkKioskLanguageSelected("English"),
        LandingPage.checkKioskCountryFlagShown("us"),

        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Test Product"),
        ProductPage.clickBack(),
        ...CategoryPage.clickCancel(),

        Utils.clickBtn("Order Now"),
        ...Utils.changeKioskLanguage("Français"),
        Utils.clickBackBtn(),

        Utils.clickBtn("Commander maintenant"),
        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Produit Test"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_combo_sides", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Office Combo"),
        ProductPage.clickKioskProduct("Desk Organizer"),
        {
            trigger: `button:disabled:contains("Next")`,
        },
        ...ProductPage.setupKioskAttribute([
            { name: "Size", value: "M" },
            { name: "Fabric", value: "Leather" },
        ]),
        Utils.clickBtn("Add to cart"),
    ],
});

registry.category("web_tour.tours").add("test_self_order_kiosk_combo_qty_max_free", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Category 2"),
        ProductPage.clickKioskProduct("Office Combo"),
        ProductPage.clickKioskProduct("Combo Product 4"),
        ...Utils.increaseComboItemQty("Combo Product 4", 3),
        Utils.clickBtn("Next"),
        Utils.clickBtn("Add to cart"),
    ],
});
