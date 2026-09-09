import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
<<<<<<< 165b08303b1c4444c0085e9742b5bb699852a707
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
const { DateTime } = luxon;
import { today } from "@web/core/l10n/dates";
||||||| 157874aad3aebef5bc9268de6e17530641107e31
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { today } from "@web/core/l10n/dates";
=======
>>>>>>> 4695f4eeff770fce02ca0ccf7754db0d9955b7af

registry.category("web_tour.tours").add("self_order_preset_dine_in_tour", {
    steps: () => [
        // Test preset "Dine in" location with table
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Dine in"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_takeaway_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.checkConfirmationString(),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_delivery_tour", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Delivery"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Free", "0", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        CartPage.fillInput("Email", "dre@dr.com"),
        CartPage.fillInput("Phone", "+32490904390"),
        CartPage.fillInput("Street and Number", "Rue du Bronx 90"),
        CartPage.fillInput("Zip", "9999"),
        CartPage.fillInput("City", "New York"),
        Utils.clickBtn("Continue"),
        Utils.checkConfirmationString(),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("self_order_preset_slot_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.selectRandomValueInInput(".slot-select"), // Selects the first available slot
        {
            content: `Select value should be a future slot`,
            trigger: ".slot-select",
            run: ({ anchor }) => {
                const slotTs = DateTime.fromFormat(anchor.value, "yyyy-MM-dd HH:mm:ss").ts;
                // Only future slots should be available for selection
                if (slotTs < DateTime.now().ts) {
                    throw new Error(`The selected slot ${anchor.value} is in the past!`);
                }
            },
        },
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.checkConfirmationString(true),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("test_preset_takeaway_email_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Free", "0", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Public user"),
        CartPage.fillInput("Email", "public.user@test.com"),
        CartPage.fillInput("Phone", "+32000111222"),
        Utils.clickBtn("Continue"),
        // Waiting for mail to be sent
        {
            trigger: "body",
            run: function () {
                return new Promise((resolve) => setTimeout(resolve, 500));
            },
        },
        Utils.clickBtn("Ok"),
    ],
});
