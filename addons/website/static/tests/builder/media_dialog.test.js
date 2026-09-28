import { expect, test } from "@odoo/hoot";
import { click, dblclick } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, onRpc } from "@web/../tests/web_test_helpers";
import {
    defineWebsiteModels,
    setupWebsiteBuilder,
} from "@website/../tests/builder/website_helpers";

defineWebsiteModels();

test("Icon styles should be retained when it is replaced with another icon", async () => {
    const extractClasses = "rounded-circle rounded shadow img-thumbnail";
    await setupWebsiteBuilder(`<i class="fa fa-search ${extractClasses}"/>`);

    await dblclick(":iframe .fa");
    await animationFrame();
    await click(".fa-heart");
    expect(":iframe .fa-heart").toHaveClass(extractClasses);
});

test("Video size should be retained when the video or its options are changed", async () => {
    const videoUrl = "//www.youtube.com/embed/qxb74CMR748";
    onRpc("/html_editor/video_url/data", () => ({ platform: "youtube", embed_url: videoUrl }));
    await setupWebsiteBuilder(
        `<div class="media_iframe_video" data-oe-expression="${videoUrl}"
            style="width: 50% !important;"/>`
    );

    await dblclick(":iframe .media_iframe_video");
    await contains(".o_video_dialog_options input[type='checkbox']").click();
    await contains(".modal-footer .btn-primary").click();
    expect(":iframe .media_iframe_video").toHaveStyle(
        { width: "50% !important" },
        { inline: true }
    );
});
