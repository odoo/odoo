import { expect, test } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";
import { setupHTMLBuilder } from "./helpers";
import { base64Img } from "@html_editor/../tests/_helpers/editor";

test("image field should not be editable, but the image can be replaced", async () => {
    await setupHTMLBuilder(
        `<div data-oe-model="product.product" data-oe-id="12" data-oe-field="image_1920" data-oe-type="image" data-oe-expression="product_image.image_1920">
            <img src="${base64Img}">
        </div>`
    );
    expect(":iframe img").toHaveProperty("isContentEditable", false);
    await contains(":iframe img").click();
    expect("span:contains('Double-click to edit')").toHaveCount(1);
});
