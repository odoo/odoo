import { registry } from "@web/core/registry";
import * as Utils from "@pos_self_order/../tests/tours/utils/common";
import * as ProductPage from "@pos_self_order/../tests/tours/utils/product_page_util";
import * as ComboPage from "@pos_self_order/../tests/tours/utils/combo_page_util";

registry.category("web_tour.tours").add("test_self_combo_extra_price_selection_and_confirmation", {
    steps: () => [
        // Start ordering
        Utils.clickBtn("Order Now"),

        // ============================================
        // Test 1: Combo with qty_free = 0
        // Expected: All items show "+ €X" price badge
        // ============================================
        ProductPage.clickProduct("Office Combo"),

        ComboPage.verifyItemHasNoExtraBadge("Combo Product 1"),
        ProductPage.clickComboProduct("Combo Product 1"),
        ComboPage.verifyItemHasNoExtraBadge("Combo Product 1"),
        ProductPage.clickComboProduct("Combo Product 1"),
        ComboPage.verifyItemHasExtraBadge("Combo Product 1", 10),
        ProductPage.clickComboProduct("Combo Product 3"),
        ComboPage.verifyItemHasExtraBadge("Combo Product 3", 12),
        Utils.clickBtn("Next"),

        // Verify first combo item shows price badge
        ComboPage.verifyItemHasPriceBadge("Combo Product 4", 20),
        ComboPage.verifyItemHasPriceBadge("Combo Product 5", 22),

        // Select first item
        ProductPage.clickComboProduct("Combo Product 4"),
        Utils.clickBtn("Next"),

        // Select second and third item
        ProductPage.clickComboProduct("Combo Product 6"),

        // ============================================
        // Verify Confirmation Page shows Extra prices
        // ============================================
        ComboPage.verifyConfirmationPageShown(),
        ComboPage.verifyConfirmationHasExtraPrice("Combo Product 1"),
        ComboPage.verifyConfirmationHasExtraPrice("Combo Product 3"),
        ComboPage.verifyConfirmationHasExtraPrice("Combo Product 4"),

        Utils.clickBtn("Add to cart"),
    ],
});
