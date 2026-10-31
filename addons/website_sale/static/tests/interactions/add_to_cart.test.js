import { expect, mockFetch, test } from "@odoo/hoot";
import { cartService } from "@website_sale/js/cart_service";

async function test_add_to_cart_helper(quantity = 0) {
    mockFetch((input, init) => {
        if (input === "/shop/cart/add") {
            return {
                "jsonrpc": "2.0",
                "id": init.id,
                "result": {
                    "cart_quantity": 1,
                    "notification_info": {"warning": "ProductName was not added to your cart because it is not available."},
                    "quantity": quantity,
                    "tracking_info": [] // will error if it tries to call _trackProducts()
                }
            };
        }
    });
    
    const cs = cartService.start({}, {'cartNotificationService': {add: () => {}}, 'dialog': {}})
    const qty = await cs.add({
        productTemplateId: 1
    }, {
        // skip shouldShowProductConfigurator check, but don't try to redirect
        isBuyNow: true,
        redirectToCart: false
    })
    expect(qty).toBe(quantity)
}

test("doesn't track product when receiving zero quantity", async () => {
    return await test_add_to_cart_helper(0)
});

// Server can sometimes return negative quantity, for example after inventory adjustment on a rental
test("doesn't track product when receiving negative quantity", async () => {
    return await test_add_to_cart_helper(-2)
});
