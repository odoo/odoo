import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as CategoryPage from "@pos_self_order/../tests/tours/utils/category_page_util";
import * as Numpad from "@point_of_sale/../tests/generic_helpers/numpad_util";

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.checkKioskReferenceNotInProductName("Desk Pad", "12345"),
        ProductPage.clickKioskProduct("Desk Pad"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28", "1"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Misc test"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_table_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.clickKioskProduct("Desk Pad"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Misc test"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_in", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.clickKioskProduct("Desk Pad"),
        CategoryPage.clickKioskCategory("Chair test"),
        ProductPage.clickKioskProduct("Letter Tray"),
        ProductPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Desk Organizer"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28"),
        CartPage.checkKioskProduct("Letter Tray", "11.36"),
        CartPage.checkKioskProduct("Desk Organizer", "12.27"),
        CartPage.checkTotalPrice("25.91"),
        Utils.clickBtn("Pay"),
        Numpad.click("3"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-In"),
        CategoryPage.clickKioskCategory("Misc test"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_kiosk_each_counter_takeaway_out", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.clickKioskProduct("Desk Pad"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28"),
        Utils.clickBtn("Pay"),
        CartPage.fillInput("Name", "Mr Kiosk"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectKioskLocation("Test-Takeout"),
        CategoryPage.clickKioskCategory("Misc test"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("self_order_kiosk_cancel", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.clickKioskProduct("Desk Pad"),
        CategoryPage.clickKioskCategory("Chair test"),
        ProductPage.clickKioskProduct("Letter Tray"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28", "1"),
        CartPage.checkKioskProduct("Letter Tray", "11.36", "1"),
        CartPage.clickBack(),
        ProductPage.clickBack(),
        ...CategoryPage.clickCancel(),
        Utils.clickBtn("Order Now"),
        ProductPage.clickKioskCategory("Misc test"),
        Utils.checkIsDisabledBtn("Checkout"),
    ],
});

registry.category("web_tour.tours").add("kiosk_simple_order", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Desk test"),
        ProductPage.clickKioskProduct("Desk Pad"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Pad", "2.28"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Close"),
        Utils.checkIsNoBtn("My Order"),
    ],
});

registry.category("web_tour.tours").add("kiosk_order_price_null", {
    checkDelay: 100,
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        CategoryPage.clickKioskCategory("Uncategorised"),
        ProductPage.clickKioskProduct("Desk Organizer"),
        Utils.clickBtn("Checkout"),
        CartPage.checkKioskProduct("Desk Organizer", "0.00"),
        Utils.clickBtn("Pay"),
        ConfirmationPage.orderNumberShown(),
        Utils.checkBtn("Close"),
    ],
});

registry.category("web_tour.tours").add("self_order_language_changes", {
    checkDelay: 100,
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
        ProductPage.clickKioskProduct("Organisateur de bureau"),
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
        ProductPage.clickKioskProduct("Desk Organizer"),
        ...ProductPage.clickCancel(),

        ...Utils.changeLanguage("French"),

        Utils.clickBtn("Commander maintenant"),
        ProductPage.clickKioskProduct("Organisateur de bureau"),
    ],
});
