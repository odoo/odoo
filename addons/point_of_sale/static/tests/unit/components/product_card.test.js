import { test, expect } from "@odoo/hoot";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { queryOne } from "@odoo/hoot-dom";
import { ProductCard } from "@point_of_sale/app/components/product_card/product_card";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";

definePosModels();

test("ProductCardUoMPrecision: product cart quantity is formatted with product quantity precision", async () => {
    await setupPosEnv();
    await mountWithCleanup(ProductCard, {
        props: {
            name: "Configurable Chair",
            product: {},
            productId: 1,
            imageUrl: false,
            productCartQty: 0.1 + 0.7,
        },
    });

    expect(queryOne(".product-cart-qty")).toHaveText("0.8");
});
