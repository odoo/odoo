import { setupHTMLBuilder, dummyBase64Img } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("image field should not be editable, but the image can be replaced", async () => {
    await setupHTMLBuilder(
        `<div data-oe-model="product.product" data-oe-id="12" data-oe-field="image_1920" data-oe-type="image" data-oe-expression="product_image.image_1920">
            <img src="${dummyBase64Img}" alt="Product Image" style="max-width: 100%;"/>
        </div>`
    );
    expect(":iframe img").toHaveProperty("isContentEditable", false);
    await contains(":iframe img").click();
    expect("span:contains('Double-click to edit')").toHaveCount(1);
});
