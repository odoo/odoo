import { expect, test, describe } from "@odoo/hoot";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import { dummyBase64Img, dummyCORSSrc, setupCORSProtectedImg, setupHTMLBuilder } from "./helpers";

describe.current.tags("desktop");

test("Size should not be displayed on CORS protected images", async () => {
    setupCORSProtectedImg();
    // The next line is needed in order to correctly run the test without the
    // fix.
    onRpc("/web/image/__odoo__unknown__src__/", () => dataURItoBlob(dummyBase64Img));
    const { waitSidebarUpdated } = await setupHTMLBuilder(`<img src="${dummyCORSSrc}">`);
    await contains(":iframe img").click();
    await waitSidebarUpdated();
    expect(".o-hb-image-size-info").toHaveCount(0);
});

test("Handle legacy image shapes from older versions", async () => {
    const oldShapeId = "web_editor/basic/bsc_organic_2";

    onRpc("/html_builder/static/image_shapes/basic/bsc_organic_2.svg", () => {
        return new Response("<svg></svg>", { headers: { "Content-Type": "image/svg+xml" } });
    });

    onRpc("/html_editor/get_image_info", () => ({
        original: {
            id: 1,
            image_src: dummyBase64Img,
            mimetype: "image/png",
        },
    }));

    const { waitSidebarUpdated } = await setupHTMLBuilder(`
        <img class="img-fluid test-image" src="${dummyBase64Img}" data-shape="${oldShapeId}">
    `);

    await contains(":iframe img.test-image").click();
    await waitSidebarUpdated();

    expect('button[data-action-id="setImageShape"]').not.toHaveCount(0);
});