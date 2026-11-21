import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mockMatchMedia } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";
import { patch } from "@web/core/utils/patch";
import { Vimeo } from "@html_editor/main/media/video/providers/vimeo";

setupInteractionWhiteList("website.media_video");

describe.current.tags("interaction_dev");

// Building a Vimeo player also requests its thumbnail from the Vimeo API.
beforeEach(() => patch(Vimeo, { getThumbnailUrl: () => Promise.resolve("") }));

for (const reducedMotion of [false, true]) {
    test(`video file with reduced motion ${reducedMotion}`, async () => {
        mockMatchMedia({ "prefers-reduced-motion": reducedMotion ? "reduce" : "no-preference" });
        await startInteractions(`
            <div class="media_iframe_video" data-platform="video_file"
                 data-embed-url="https://example.com/video/my-video.mp4"
                 data-video-options='{"autoplay": true, "hideControls": true}'></div>
        `);

        const videoEl = await waitFor(".media_iframe_video > video");
        expect(videoEl.autoplay).toBe(!reducedMotion);
        expect(videoEl.controls).toBe(reducedMotion);
    });

    // Params equal to the platform default are omitted from the url: Twitch
    // autoplays by default, the others show their controls by default.
    for (const [embedUrl, autoplay, disabledAutoplay, controls] of [
        ["https://www.youtube.com/embed/xCvFZrrQq7k?autoplay=1&controls=0&mute=1", "1", null, "0"],
        ["https://player.vimeo.com/video/395399735?autoplay=1&controls=0&muted=1", "1", null, "0"],
        ["https://player.twitch.tv/?video=1064007405&muted=true", null, "false", null],
    ]) {
        test(`${
            new URL(embedUrl).hostname
        } video with reduced motion ${reducedMotion}`, async () => {
            mockMatchMedia({
                "prefers-reduced-motion": reducedMotion ? "reduce" : "no-preference",
            });
            await startInteractions(`
                <div class="media_iframe_video" data-embed-url="${embedUrl}"></div>
            `);

            const iframeEl = await waitFor(".media_iframe_video > iframe");
            const params = new URL(iframeEl.src).searchParams;
            expect(params.get("autoplay")).toBe(reducedMotion ? disabledAutoplay : autoplay);
            expect(params.get("controls")).toBe(reducedMotion ? null : controls);
            expect(".media_iframe_video").toHaveAttribute("data-embed-url", embedUrl);
        });
    }
}
