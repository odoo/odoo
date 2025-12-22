import { test } from "@odoo/hoot";
import { press, waitFor, waitForNone } from "@odoo/hoot-dom";
import { contains, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ImageCrop } from "@html_editor/main/media/image_crop";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { testImg } from "./image_test_helpers";

defineWebsiteModels();

test("Image cropper Enter saves and Escape closes in website builder", async () => {
    const superShow = ImageCrop.prototype.show;
    let resolveCropperReady;
    const waitCropperReady = () =>
        new Promise((resolve) => {
            resolveCropperReady = resolve;
        });
    patchWithCleanup(ImageCrop.prototype, {
        async show(...args) {
            const res = await superShow.apply(this, args);
            resolveCropperReady?.();
            return res;
        },
    });

    const { waitSidebarUpdated } = await setupWebsiteBuilder(
        `<div class="test-options-target">${testImg}</div>`
    );
    await contains(":iframe .test-options-target img").click();
    await waitSidebarUpdated();

    const openCropper = async () => {
        const ready = waitCropperReady();
        await contains("[data-label='Transform'] [data-action-id='cropImage']").click();
        await waitFor(".o_we_crop_widget", { timeout: 1000 });
        await ready;
    };

    await openCropper();
    await press("Enter");
    await waitForNone(".o_we_crop_widget", { timeout: 1000 });

    await openCropper();
    await press("Escape");
    await waitForNone(".o_we_crop_widget", { timeout: 1000 });
});
