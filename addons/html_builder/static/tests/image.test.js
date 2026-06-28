import { expect, test, describe } from "@odoo/hoot";
import { contains, dataURItoBlob, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { dummyBase64Img, dummyCORSSrc, setupCORSProtectedImg, setupHTMLBuilder } from "./helpers";
import { ImageShapeOptionPlugin } from "@html_builder/plugins/image/image_shape_option_plugin";
import { ImageToolOptionPlugin } from "@html_builder/plugins/image/image_tool_option_plugin";

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

test("Transfer all options before processing image at image replace", async () => {
    expect.assertions(1);
    patchWithCleanup(ImageShapeOptionPlugin.prototype, {
        async onWillSaveMediaDialogHandlers(elements, { node }) {
            await super.onWillSaveMediaDialogHandlers(elements, { node });
            expect.step("shape_option_media_dialog_saved");
        },
    });
    patchWithCleanup(ImageToolOptionPlugin.prototype, {
        async onWillSaveMediaDialogHandlers() {
            expect.verifySteps(["shape_option_media_dialog_saved"]);
        },
    });
    onRpc("/html_editor/get_image_info", () => ({}));
    const { waitSidebarUpdated } = await setupHTMLBuilder(`
        <div class="test-options-target">
            <img src="${dummyBase64Img}"/>
        </div>
    `);
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/jpeg",
            image_src: dummyCORSSrc,
            access_token: false,
            public: true,
        },
    ]);
    await contains(":iframe img").click();
    await waitSidebarUpdated();
    await contains("[data-action-id=replaceMedia]").click();
    await contains(".o_we_existing_attachments .o_button_area").click();
    await waitSidebarUpdated();
});
