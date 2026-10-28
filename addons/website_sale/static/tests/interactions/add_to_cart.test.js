import { expect, test } from "@odoo/hoot";
import { CartService } from "@website_sale/js/cart_service";
import { getService, makeMockEnv, mockService, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

async function testAddToCartHelper(quantity = 0) {
    await makeMockEnv()
    onRpc("/shop/cart/add", () => ({
        "cart_quantity": 1,
        "notification_info": {"warning": "ProductName was not added to your cart because it is not available."},
        "quantity": quantity,
        "tracking_info": [] // will error if it tries to call _trackProducts()
    }));
    onRpc("/website_sale/should_show_product_configurator", () => false);

    mockService("cartNotificationService", { add: () => expect.step("notification") });

    patchWithCleanup(CartService.prototype, {
        _trackProducts: () => expect.step("track"),
    });

    await getService("cart").add({ productTemplateId: 1 });

    expect.verifySteps(["notification"]); // "track" must not be called with an empty array.
}

test("doesn't track product when receiving zero quantity", async () => {
    return await testAddToCartHelper(0)
});

// Server can sometimes return negative quantity, for example after inventory adjustment on a rental
test("doesn't track product when receiving negative quantity", async () => {
    return await testAddToCartHelper(-2)
});
