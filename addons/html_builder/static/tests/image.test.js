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
