import { setupHTMLBuilder, dummyBase64Img } from "@html_builder/../tests/helpers";
import { expect, test, describe } from "@odoo/hoot";
import { contains, onRpc } from "@web/../tests/web_test_helpers";

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

test("replacing an image should display the image tool options", async () => {
    onRpc("/html_editor/get_image_info", () => ({
        original: {
            image_src: dummyBase64Img,
        },
    }));
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<div data-oe-model="product.product" data-oe-id="12" data-oe-field="image_1920" data-oe-type="image" data-oe-expression="product_image.image_1920">
            <img src="${dummyBase64Img}"/>
        </div>`
    );
    await contains(":iframe img").click();
    await waitSidebarUpdated();
    expect("button[data-action-id=replaceMedia]").toHaveCount(1);

    // Fields that don't appear before replacing the image
    expect("div[data-label=Shape] div[role=button]").toHaveCount(0);
    expect("div[data-label=Transform] button[data-action-id=cropImage]").toHaveCount(0);
    expect("div[data-label=Transform] button[data-action-id=transformImage]").toHaveCount(0);
    expect("div[data-label=Size] button").toHaveCount(0);

    await contains("[data-action-id=replaceMedia]").click();
    await contains(".o_existing_attachment_cell .o_button_area").click();
    await waitSidebarUpdated();

    // Fields that are displayed after replacing the image
    expect("div[data-label=Shape] div[role=button]").toHaveCount(1);
    expect("div[data-label=Transform] button[data-action-id=cropImage]").toHaveCount(1);
    expect("div[data-label=Transform] button[data-action-id=transformImage]").toHaveCount(0);
    expect("div[data-label=Format] button").toHaveCount(1)

    // Fields that should not appear in [data-oe-type='image'] > img for a binary field image
    expect("div[data-label=Description] input").toHaveCount(0);
    expect("div[data-label=Tooltip] input").toHaveCount(0);
    expect("div[data-label=Alignment] button").toHaveCount(0);
    expect("div[data-label=Style] button").toHaveCount(0);
    expect("div[data-label=Padding] input").toHaveCount(0);
    expect("div[data-label=Size] button").toHaveCount(0);
});
