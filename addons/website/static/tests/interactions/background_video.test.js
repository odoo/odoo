import { describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, waitFor } from "@odoo/hoot-dom";
import { mockMatchMedia } from "@odoo/hoot-mock";
import { setupInteractionWhiteList, startInteractions } from "@web/../tests/public/helpers";

setupInteractionWhiteList("website.background_video");

describe.current.tags("interaction_dev");

for (const reducedMotion of [false, true]) {
    test(`native background video with reduced motion ${reducedMotion}`, async () => {
        mockMatchMedia({ "prefers-reduced-motion": reducedMotion ? "reduce" : "no-preference" });
        await startInteractions(`
            <section class="o_background_video" data-bg-video-src="/test-video.mp4" data-bg-video-is-file="true"></section>
        `);

        const videoEl = await waitFor(".o_bg_video_file");
        expect(videoEl).toHaveAttribute("src", "/test-video.mp4");
        expect(videoEl.autoplay).toBe(!reducedMotion);
        expect(videoEl.preload).toBe("auto");
        expect(videoEl).toHaveClass("show");
        expect(videoEl).toHaveAttribute("muted");
        expect(videoEl).toHaveAttribute("loop");
        await manuallyDispatchProgrammaticEvent(videoEl, "loadeddata");
        expect(".o_bg_video_loading").toHaveCount(0);
    });

    for (const [src, disabledAutoplay] of [
        ["https://www.youtube.com/embed/test-video?autoplay=1&mute=1", "0"],
        ["https://player.vimeo.com/video/123?autoplay=1&muted=1", "0"],
        ["https://player.twitch.tv/?video=123&autoplay=true&muted=true", "false"],
    ]) {
        test(`${
            new URL(src).hostname
        } background video with reduced motion ${reducedMotion}`, async () => {
            mockMatchMedia({
                "prefers-reduced-motion": reducedMotion ? "reduce" : "no-preference",
            });
            await startInteractions(`
                <section class="o_background_video" data-bg-video-src="${src}"></section>
            `);

            const iframeEl = await waitFor(".o_bg_video_iframe");
            const originalUrl = new URL(src);
            // The test templates move iframe sources to `data-src`.
            const playerUrl = new URL(iframeEl.dataset.src);
            expect(playerUrl.searchParams.get("autoplay")).toBe(
                reducedMotion ? disabledAutoplay : originalUrl.searchParams.get("autoplay")
            );
            playerUrl.searchParams.delete("autoplay");
            originalUrl.searchParams.delete("autoplay");
            expect(playerUrl.href).toBe(originalUrl.href);
            expect(".o_background_video").toHaveAttribute("data-bg-video-src", src);
        });
    }
}
