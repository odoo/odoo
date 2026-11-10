import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as CartPage from "@pos_self_order/../tests/tours/utils/cart_page_util";
import * as LandingPage from "@pos_self_order/../tests/tours/utils/landing_page_util";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ConfirmationPage from "@pos_self_order/../tests/tours/utils/confirmation_page_util";
import { negateStep } from "@point_of_sale/../tests/generic_helpers/utils";

registry.category("web_tour.tours").add("self_mobile_online_payment_meal_table", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-In"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_online_payment_meal_dynamic_qr", {
    steps: () => [
        Utils.checkBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("self_mobile_online_payment_meal", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        negateStep(LandingPage.checkLocation("Test-In")),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Order"),
        CartPage.fillInput("Name", "Dr Dre"),
        CartPage.fillInput("Phone", "490904390"),
        Utils.clickBtn("Continue"),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Order"),
        ConfirmationPage.isShown(),
        Utils.clickBtn("Ok"),
        Utils.clickBtn("My Order"),
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("test_online_payment_kiosk_qr_code", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.checkQRCodeGenerated(),
    ],
});

registry.category("web_tour.tours").add("test_online_payment_self_multi_company", {
    steps: () => [
        Utils.checkIsNoBtn("My Order"),
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
    ],
});

registry
    .category("web_tour.tours")
    .add("test_online_payment_mobile_self_order_preparation_changes", {
        steps: () =>
            [
                Utils.checkIsNoBtn("My Order"),
                Utils.clickBtn("Order Now"),
                ProductPage.clickProduct("Coca-Cola"),
                ProductPage.clickProduct("Fanta"),
                Utils.clickBtn("Checkout"),
                CartPage.checkProduct("Fanta", "2.53", "1"),
                CartPage.checkProduct("Coca-Cola", "2.53", "1"),
                Utils.clickBtn("Pay"),
                ...CartPage.selectTable("1"),
            ].flat(),
    });

registry.category("web_tour.tours").add("test_kiosk_cart_restore_and_cancel", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        ProductPage.clickProduct("Fanta"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBtn("Pay"),
        Utils.clickBtn("Back"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        CartPage.checkProduct("Fanta", "2.53", "1"),
        Utils.clickBackBtn(),
        ...ProductPage.clickCancel(),
    ],
});

registry.category("web_tour.tours").add("self_order_tip_amount_with_tax", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("15%"), // Select 15% tip
        CartPage.checkTotalPrice("2.97"), // Total with tax on tip
        Utils.clickBtn("Pay"),
    ],
});

registry.category("web_tour.tours").add("self_order_tip_amount_without_tax", {
    steps: () => [
        Utils.clickBtn("Order Now"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("15%"), // Select 15% tip
        CartPage.checkTotalPrice("2.91"), // Total without tax on tip
        Utils.clickBtn("Pay"),
    ],
});

function selectTomorrowSlot(time) {
    return [
        {
            content: "Wait for the time slot popup",
            trigger: ".self_order_pills_selection_popup",
        },
        {
            content: "Select tomorrow's slots",
            trigger: ".self_order_pills_selection_popup .preset_date_buttons:contains('Tomorrow')",
            run: "click",
        },
        {
            // Today's slots stay rendered until the click is handled, wait for tomorrow's ones
            content: "Tomorrow's slots are shown",
            trigger:
                ".self_order_pills_selection_popup .preset_date_buttons.btn-primary:contains('Tomorrow')",
        },
        {
            content: `Slot ${time} must be selectable`,
            trigger: `.self_order_pills_selection_popup .option-item:contains('${time}'):not(:disabled)`,
            run: "click",
        },
        {
            content: "Confirm the time slot",
            trigger:
                ".self_order_pills_selection_popup .btn-primary:contains('Confirm'):not(:disabled)",
            run: "click",
        },
    ];
}

function orderCocaColaWithSlot(time) {
    return [
        Utils.clickBtn("Order Now"),
        LandingPage.selectLocation("Test-Takeout"),
        ProductPage.clickProduct("Coca-Cola"),
        Utils.clickBtn("Checkout"),
        CartPage.checkProduct("Coca-Cola", "2.53", "1"),
        Utils.clickBtn("Pay"),
        ...selectTomorrowSlot(time),
        Utils.clickBtn("Continue"),
    ];
}

// A: books the 12:00 slot and leaves on the online payment page without paying.
registry.category("web_tour.tours").add("self_online_payment_slot_pending_order_a", {
    steps: () => orderCocaColaWithSlot("12:00"),
});

// B: the 12:00 slot must still be available since A did not start its payment.
registry.category("web_tour.tours").add("self_online_payment_slot_order_b", {
    steps: () => orderCocaColaWithSlot("12:00"),
});

const backToCartSteps = [
    Utils.clickBtn("My Order"),
    CartPage.checkProduct("Coca-Cola", "2.53", "1"),
    Utils.clickBtn("Pay"),
];

function changeSlot(fullSlot = null, startSteps = backToCartSteps) {
    const selectSlot = selectTomorrowSlot("12:30");
    return [
        ...startSteps,
        selectSlot[0],
        {
            content: "The slot unavailable message is shown in the slot selection",
            trigger:
                ".self_order_pills_selection_popup .text-danger:contains('the slot you selected is no longer available')",
        },
        selectSlot[1],
        ...(fullSlot
            ? [
                  {
                      content: `Slot ${fullSlot} is full`,
                      trigger: `.self_order_pills_selection_popup .option-item:contains('${fullSlot}'):disabled`,
                  },
              ]
            : []),
        ...selectSlot.slice(2),
        Utils.clickBtn("Continue"),
    ];
}

// C: back from A's failed payment, A picks another slot and pays again.
registry.category("web_tour.tours").add("self_online_payment_slot_order_a_change_slot", {
    steps: () => changeSlot(),
});

// C: back from A's failed payment, the 12:00 slot is full, A picks another slot and pays again.
registry.category("web_tour.tours").add("self_online_payment_slot_order_a_change_full_slot", {
    steps: () => changeSlot("12:00"),
});

// C: redirected from A's refused payment, the slot selection opens directly, the 12:00 slot is full, A picks another slot and pays again.
registry.category("web_tour.tours").add("self_online_payment_slot_order_a_reschedule_full_slot", {
    steps: () => changeSlot("12:00", []),
});
