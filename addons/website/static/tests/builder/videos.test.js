import { expect, test } from "@odoo/hoot";
import { animationFrame, dblclick } from "@odoo/hoot-dom";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";
import { onRpc } from "@web/../tests/web_test_helpers";

defineWebsiteModels();

test("double click on video", async () => {
    onRpc("/api/oembed.json", async () => ({
        // Those lead to 404 but it's fine for the test
        thumbnailSrc: "/hello/world.jpg",
    }));
    await setupWebsiteBuilder(`
        <div>
            <div class="media_iframe_video o_snippet_drop_in_only">
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size"></div>
                <iframe frameborder="0" allowfullscreen="allowfullscreen" aria-label="Video"></iframe>
            </div>
        </div>
    `);
    expect(".modal-content").toHaveCount(0);
    await dblclick(":iframe iframe");
    await animationFrame();
    expect(".modal-content:contains(Select a media) .o_video_dialog_form").toHaveCount(1);
});
