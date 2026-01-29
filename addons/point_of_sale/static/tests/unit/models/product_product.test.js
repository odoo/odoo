import { test, expect } from "@odoo/hoot";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ProductProduct } from "@point_of_sale/app/models/product_product";
import { ProductTemplate } from "@point_of_sale/app/models/product_template";

definePosModels();

test("product template and product product override", async () => {
    const store = await setupPosEnv();
    const product = store.models["product.template"].get(18);

    patchWithCleanup(ProductProduct.prototype, {
        get allBarcodes() {
            return this.barcode || "";
        },
    });
    patchWithCleanup(ProductTemplate.prototype, {
        get allBarcodes() {
            return (
                (this.barcode || "") + this.product_variant_ids.map((p) => p.allBarcodes).join(",")
            );
        },
    });
    expect(product.allBarcodes).toBe("");
});
