import { beforeEach, expect, test, advanceTime } from "@odoo/hoot";
import { animationFrame, click, dblclick, edit, queryAll, waitFor, queryOne } from "@odoo/hoot-dom";
import { patch } from "@web/core/utils/patch";
import { VideoFile } from "@html_editor/main/media/video/providers/video_file";
import { defineWebsiteModels, setupWebsiteBuilder } from "./website_helpers";

defineWebsiteModels();

// A video file url is accepted once its metadata loaded, which no test
// environment can carry out for real.
beforeEach(() => patch(VideoFile, { isValidVideoUrl: (url) => Promise.resolve([url]) }));

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

const VIDEO_FILE_SRC = "https://example.com/video/my-video.mp4";

function getVideoOptionToggle(label) {
    return queryAll(".modal-content .o_video_dialog_options .o_switch").find(
        (el) => el.querySelector("span.ms-2")?.textContent.trim() === label
    );
}

test("insert a video file through the media dialog", async () => {
    await setupWebsiteBuilder(`
        <div>
            <div class="media_iframe_video o_snippet_drop_in_only">
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size"></div>
                <iframe frameborder="0" allowfullscreen="allowfullscreen" aria-label="Video"></iframe>
            </div>
        </div>
    `);
    await dblclick(":iframe iframe");
    await waitFor(".modal-content:contains(Select a media) .o_video_dialog_form");

    await click("#o_video_text");
    await edit(VIDEO_FILE_SRC);
    // `refreshVideoData()` is debounced.
    await advanceTime(100);
    await waitFor(".modal-content .o_video_preview video");

    await click(".modal-content footer button:contains(Add)");
    await animationFrame();

    const videoEl = await waitFor(":iframe .media_iframe_video video");
    expect(":iframe .media_iframe_video iframe").toHaveCount(0);
    expect(videoEl.getAttribute("src")).toBe(VIDEO_FILE_SRC);
    expect(queryOne(":iframe .media_iframe_video").dataset.platform).toBe("video_file");
});

test("reopening a video file keeps its options", async () => {
    // No `controls` attribute: the "Hide player controls" option is on.
    await setupWebsiteBuilder(`
        <div>
            <div class="media_iframe_video o_snippet_drop_in_only" data-platform="video_file">
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size"></div>
                <video src="${VIDEO_FILE_SRC}" playsinline="" contenteditable="false" loop=""></video>
            </div>
        </div>
    `);

    await dblclick(":iframe video");
    await waitFor(".modal-content:contains(Select a media) .o_video_dialog_form");
    await advanceTime(100);

    expect("#o_video_text").toHaveValue(VIDEO_FILE_SRC);
    await waitFor(".modal-content .o_video_dialog_options");
    expect(getVideoOptionToggle("Loop").querySelector("input")).toBeChecked();
    expect(getVideoOptionToggle("Hide player controls").querySelector("input")).toBeChecked();

    // Turning "Loop" off must be reflected on the saved video.
    await click(getVideoOptionToggle("Loop").querySelector("input").closest("label"));
    await advanceTime(100);
    await click(".modal-content footer button:contains(Add)");
    await animationFrame();

    const videoEl = await waitFor(":iframe .media_iframe_video video");
    expect(videoEl.hasAttribute("loop")).toBe(false);
    expect(videoEl.hasAttribute("controls")).toBe(false);
});
