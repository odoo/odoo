import { expect, test, advanceTime } from "@odoo/hoot";
import { animationFrame, dblclick, waitFor, queryOne } from "@odoo/hoot-dom";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

test("double click on video", async () => {
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

test("vertical toggle of video options", async () => {
    await setupWebsiteBuilder(`
        <div>
            <div data-oe-expression="//www.youtube.com/embed/wf9gPmNc2sc?rel=0&autoplay=0"
                 class="media_iframe_video o_snippet_drop_in_only">
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
    expect(
        ".modal-content:contains(Select a media) .media_iframe_video .media_iframe_video_size"
    ).toHaveCount(1);
    // Wait for options to be rendered before interaction
    await waitFor(
        ".modal-content:contains(Select a media) .o_video_dialog_form .o_video_dialog_options"
    );
    // Toggle the “Vertical” option
    const verticalToggle = queryOne(
        '.modal-content:contains("Select a media") .o_video_dialog_form .o_video_dialog_options label:contains(Vertical) input'
    );
    verticalToggle.click();

    // Confirm vertical class is applied in the preview area
    await waitFor(
        ".modal-content:contains(Select a media) .media_iframe_video .media_iframe_video_size_for_vertical"
    );
    // Advance time to force the video preview refresh (debounced).
    await advanceTime(100);
    queryOne(".modal-content:contains(Select a media) footer button:contains(Add)").click();
    await animationFrame();
    // Verify the vertical class persists in the website preview
    expect(":iframe .media_iframe_video .media_iframe_video_size_for_vertical").toHaveCount(1);
    // Reopen configurator and ensure the vertical setting is still active
    await dblclick(":iframe iframe");
    await waitFor(
        ".modal-content:contains(Select a media) .media_iframe_video .media_iframe_video_size_for_vertical"
    );
});
