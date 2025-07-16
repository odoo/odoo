import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { defineWebsiteModels, dummyBase64Img, setupWebsiteBuilder } from "./website_helpers";
import { queryOne } from "@odoo/hoot-dom";

defineWebsiteModels();

test.tags("desktop");
test("image field should not be editable, but the image can be replaced", async () => {
    await setupWebsiteBuilder(
        `<div data-oe-model="product.product" data-oe-id="12" data-oe-field="image_1920" data-oe-type="image" data-oe-expression="product_image.image_1920">
            <img src="${dummyBase64Img}">
        </div>`
    );
    expect(queryOne(":iframe img").isContentEditable).toBe(false);
    await contains(":iframe img").click();
    expect("span:contains('Double-click to edit')").toHaveCount(1);
});
