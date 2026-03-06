import { expect, test, describe } from "@odoo/hoot";
import { contains, dataURItoBlob, onRpc } from "@web/../tests/web_test_helpers";
import { dummyBase64Img, setupHTMLBuilder } from "./helpers";

describe.current.tags("desktop");

test("Size should not be displayed on CORS protected images", async () => {
    onRpc("/html_editor/get_image_info", () => ({
        original: {
            id: 1,
            image_src: "/web/image/0-redirect/foo.jpg",
            mimetype: "image/jpeg",
        },
    }));
    onRpc("/web/image/0-redirect/foo.jpg", () => {
        throw new Error("simulated cors error");
    });
    // The next line is needed in order to correctly run the test without the
    // fix.
    onRpc("/web/image/__odoo__unknown__src__/", () => dataURItoBlob(dummyBase64Img));
    const { waitSidebarUpdated } = await setupHTMLBuilder(
        `<img src='/web/image/0-redirect/foo.jpg'>`
    );
    await contains(":iframe img").click();
    await waitSidebarUpdated();
    expect(".o-hb-image-size-info").toHaveCount(0);
});
