import { describe, expect, test } from "@odoo/hoot";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

describe.current.tags("interaction_dev");
setupInteractionWhiteList("website.background_video");

// Cookies approval is required so that the video is not actually loaded.
const getTemplate = (videoSrc) => `
    <section class="o_background_video" data-bg-video-src="${videoSrc}" data-need-cookies-approval="true">
        <div class="container">Content</div>
    </section>
`;

test("background video: vimeo videos are not tracked and do not pause each other", async () => {
    const videoSrc =
        "https://player.vimeo.com/video/395399735?autoplay=1&amp;controls=0&amp;loop=1&amp;muted=1";
    const { core } = await startInteractions(getTemplate(videoSrc));
    const url = new URL(core.interactions[0].interaction.videoSrc);
    expect(url.searchParams.get("dnt")).toBe("1");
    expect(url.searchParams.get("autopause")).toBe("0");
    expect(url.searchParams.get("autoplay")).toBe("1");
    expect(url.searchParams.get("loop")).toBe("1");
    // The saved source is left untouched.
    expect(".o_background_video").toHaveAttribute(
        "data-bg-video-src",
        "https://player.vimeo.com/video/395399735?autoplay=1&controls=0&loop=1&muted=1"
    );
});

test("background video: the privacy hash of unlisted vimeo videos is fixed", async () => {
    const videoSrc =
        "https://player.vimeo.com/video/795669787/0763fdb816?autoplay=1&amp;loop=1&amp;muted=1";
    const { core } = await startInteractions(getTemplate(videoSrc));
    const url = new URL(core.interactions[0].interaction.videoSrc);
    expect(url.pathname).toBe("/video/795669787");
    expect(url.searchParams.get("h")).toBe("0763fdb816");
    expect(url.searchParams.get("dnt")).toBe("1");
    expect(url.searchParams.get("autopause")).toBe("0");
});

test("background video: other videos are left untouched", async () => {
    const videoSrc = "https://www.youtube.com/embed/G8b4UZIcTfg?autoplay=1&amp;mute=1";
    const { core } = await startInteractions(getTemplate(videoSrc));
    expect(core.interactions[0].interaction.videoSrc).toBe(
        "https://www.youtube.com/embed/G8b4UZIcTfg?autoplay=1&mute=1"
    );
});
