import { expect, mockFetch, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Vimeo } from "@html_editor/main/media/video/providers/vimeo";
import { generateVideoPlayer } from "@website/js/content/generate_video_iframe";

test("saved Vimeo player skips thumbnails", async () => {
    mockFetch(() => {
        expect.step("thumbnail");
        return JSON.stringify({ thumbnail_url: "https://example.com/thumbnail.jpg" });
    });
    const container = document.createElement("div");
    container.innerHTML = `<div class="media_iframe_video"
        data-embed-url="https://player.vimeo.com/video/395399735?autoplay=1"></div>`;
    const iframe = generateVideoPlayer(container.firstElementChild);
    await animationFrame();

    expect.verifySteps([]);
    expect(iframe.src).toBe("https://player.vimeo.com/video/395399735?autoplay=1&muted=1");
});

test("Vimeo data still includes thumbnails by default", async () => {
    mockFetch(() => {
        expect.step("thumbnail");
        return JSON.stringify({ thumbnail_url: "https://example.com/thumbnail.jpg" });
    });
    const match = Vimeo.isValidVideoUrl("https://vimeo.com/395399735");
    const videoData = Vimeo.getVideoUrlData(match);
    expect(await videoData.thumbnailUrl).toBe("https://example.com/thumbnail.jpg");
    expect.verifySteps(["thumbnail"]);
});
