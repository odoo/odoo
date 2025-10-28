import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";

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

        // Check if the partner is available in cache
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Delivery"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Free", "0", "1"),
        Utils.clickBtn("Order"),
        CartPage.selectRandomValueInInput(".partner-select"),
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
        ...CartPage.selectTimeSlot(),
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.checkConfirmationString(true),
        Utils.clickBtn("Ok"),
    ],
});

registry.category("web_tour.tours").add("test_slot_limit_orders", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
<<<<<<< 5fcd906e76e3a1f4de2db3af7f3e6eeaf0210a6b
        ...CartPage.selectTimeSlot(),
||||||| 9d514f96215bf5b88d8a044cf0aae46aba205bde
        // Will always pick the first available: 00:00
        CartPage.selectRandomValueInInput(".slot-select"),
=======
        CartPage.selectSpecificValueInInput(".slot-select", "18:00"),
>>>>>>> 23b44411f19e16812c3e0e84a832f6f0e478ae7a
        CartPage.fillInput("Name", "Dr Dre"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Free"),
        Utils.clickBtn("Checkout"),
        Utils.clickBtn("Order"),
<<<<<<< 5fcd906e76e3a1f4de2db3af7f3e6eeaf0210a6b
        {
            content: `Check that the 00:00 slot is not available`,
            trigger: `.self_order_pills_selection_popup`,
            run: () => {
                const slots = Array.from(
                    document.querySelectorAll(".self_order_pills_selection_popup .option-item")
                );
                const firstSlotText = slots[0]?.textContent.trim();
                if (firstSlotText === "00:00") {
                    throw new Error(`00:00 should not be available`);
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_preset_takeaway_email_tour", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Takeaway"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Public user"),
        CartPage.fillInput("Email", "public.user@test.com"),
        Utils.clickBtn("Continue"),
        // Waiting for mail to be sent
        {
            trigger: "body",
            run: function () {
                return new Promise((resolve) => setTimeout(resolve, 500));
            },
        },
        Utils.clickBtn("Ok"),
||||||| 9d514f96215bf5b88d8a044cf0aae46aba205bde
        CartPage.checkSlotUnavailable("00:00"),
=======
        CartPage.checkSlotUnavailable("18:00"),
>>>>>>> 23b44411f19e16812c3e0e84a832f6f0e478ae7a
    ],
});
