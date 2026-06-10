import { expect, test, describe } from "@odoo/hoot";
import { click, waitFor, animationFrame } from "@odoo/hoot-dom";
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

    const { getEditor, waitSidebarUpdated } = await setupHTMLBuilder(`
        <img class="img-fluid test-image" src="${dummyBase64Img}" data-shape="${oldShapeId}">
    `);

    await contains(":iframe img.test-image").click();
    await waitSidebarUpdated();

    const { imageShapeOption } = getEditor().shared;
    expect(imageShapeOption).not.toBe(undefined);

    expect(imageShapeOption.isAnimableShape(oldShapeId)).toBe(false);
    expect(imageShapeOption.isTechnicalShape(oldShapeId)).toBe(false);
    expect(imageShapeOption.isTogglableRatioShape(oldShapeId)).toBe(false);
    expect(imageShapeOption.isTransformableShape(oldShapeId)).toBe(true);
    expect(imageShapeOption.getShapeLabel(oldShapeId).toString()).toBe("None");
});
