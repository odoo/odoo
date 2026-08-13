import { describe, expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { switchToEditMode } from "../../helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.media_video");

const videoTemplate = `
    <div style="background-color: white;" data-need-cookies-approval>
        <div class="media_iframe_video" data-oe-expression="//www.youtube.com/embed/G8b4UZIcTfg?rel=0&amp;autoplay=0" contenteditable="false">
            <div class="css_editable_mode_display">&nbsp;</div>
            <div class="media_iframe_video_size">&nbsp;</div>
            <iframe original="true" allowfullscreen="" aria-label="Media video" src="about:blank"></iframe>
        </div>
    </div>
`;

test("media video: iframe not replaced in edition if present", async () => {
    const { core } = await startInteractions(videoTemplate, { editMode: true });
    expect("iframe[original='true']").toHaveCount(1);
    expect("iframe").toHaveCount(1);
    await switchToEditMode(core);
    expect("iframe[original='true']").toHaveCount(1);
    expect("iframe").toHaveCount(1);
});

test("media video: iframe replaced in edition if not present", async () => {
    const { core } = await startInteractions(videoTemplate.replace(/<iframe.*<\/iframe>/, ""), {
        editMode: true,
    });
    expect("iframe").toHaveCount(0);
    await switchToEditMode(core);
    expect("iframe").toHaveCount(1);
});

test("media video: video file rebuilt in edition if not present", async () => {
    const { core } = await startInteractions(
        `
        <div style="background-color: white;">
            <div class="media_iframe_video" data-platform="video_file"
                 data-embed-url="https://example.com/video/my-video.mp4"
                 data-video-options='{"loop":true,"hideControls":true}' contenteditable="false">
                <div class="css_editable_mode_display">&nbsp;</div>
                <div class="media_iframe_video_size">&nbsp;</div>
            </div>
        </div>
    `,
        { editMode: true }
    );
    expect(".media_iframe_video video").toHaveCount(0);
    await switchToEditMode(core);

    expect(".media_iframe_video video").toHaveCount(1);
    expect("iframe").toHaveCount(0);
    const videoEl = queryOne(".media_iframe_video video");
    expect(videoEl).toHaveAttribute("src", "https://example.com/video/my-video.mp4");
    expect(videoEl.hasAttribute("loop")).toBe(true);
    expect(videoEl.hasAttribute("controls")).toBe(false);
});
