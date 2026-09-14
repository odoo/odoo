// @ts-check
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { assets } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { SIZES, utils } from "@web/ui/viewport";
import { generateVideoIframe } from "@website/js/content/generate_video_iframe";
import { setupAutoplay, triggerAutoplay } from "@website/utils/videos";

const youtubeWindow = /** @type {Window & {
    YT?: { Player?: new (...args: any[]) => any },
    onYouTubeIframeAPIReady?: () => void,
}} */ (window);

describe.current.tags("headless");
beforeEach(() => {
    patchWithCleanup(browser, { ontouchstart() {} });
    patchWithCleanup(utils, { getSize: () => SIZES.SM });
    patchWithCleanup(window, { YT: undefined, onYouTubeIframeAPIReady: undefined });
});

test("concurrent YouTube callers share readiness and preserve the prior callback", async () => {
    const downloaded = /** @type {Deferred<void>} */ (new Deferred());
    const prior = () => expect.step("prior ready");
    youtubeWindow.onYouTubeIframeAPIReady = prior;
    patchWithCleanup(assets, {
        loadJS() {
            expect.step("script");
            return downloaded;
        },
    });
    const first = setupAutoplay("https://www.youtube.com/embed/example");
    const second = setupAutoplay("https://www.youtube.com/embed/example");
    let ready = false;
    first.then(() => {
        ready = true;
    });
    downloaded.resolve();
    await tick();
    expect(ready).toBe(false);
    youtubeWindow.onYouTubeIframeAPIReady();
    await Promise.all([first, second]);
    expect(youtubeWindow.onYouTubeIframeAPIReady).toBe(prior);
    expect.verifySteps(["script", "prior ready"]);
});

test("failed YouTube downloads settle and permit a later retry", async () => {
    let attempts = 0;
    patchWithCleanup(assets, {
        async loadJS() {
            attempts++;
            if (attempts === 1) {
                throw new Error("offline");
            }
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    await setupAutoplay("https://www.youtube.com/embed/example");
    expect(youtubeWindow.onYouTubeIframeAPIReady).toBe(undefined);
    await setupAutoplay("https://www.youtube.com/embed/example");
    expect(attempts).toBe(2);
});

test("a partial YT namespace is not a ready player API", async () => {
    youtubeWindow.YT = {};
    patchWithCleanup(assets, {
        async loadJS() {
            expect.step("script");
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    await setupAutoplay("https://www.youtube.com/embed/example");
    expect.verifySteps(["script"]);
});

test("cookie approval prevents API loading", async () => {
    patchWithCleanup(assets, {
        async loadJS() {
            expect.step("script");
        },
    });
    await setupAutoplay("https://www.youtube.com/embed/example", true);
    expect.verifySteps([]);
});

test("autoplay requires a ready player and an iframe without pending approval", () => {
    const iframe = document.createElement("iframe");
    iframe.src = "https://www.youtube.com/embed/example";
    const container = document.createElement("div");
    container.append(iframe);
    // Failed loading must not turn into a second exception in its caller.
    triggerAutoplay(iframe);
    youtubeWindow.YT = {
        Player: class {
            constructor() {
                expect.step("player");
            }
        },
    };
    container.dataset.needCookiesApproval = "true";
    triggerAutoplay(iframe);
    expect.verifySteps([]);
    delete container.dataset.needCookiesApproval;
    triggerAutoplay(iframe);
    expect.verifySteps(["player"]);
});

test("a failing prior ready callback does not strand video initialization", async () => {
    const prior = () => {
        throw new Error("other embed failed");
    };
    youtubeWindow.onYouTubeIframeAPIReady = prior;
    patchWithCleanup(assets, {
        async loadJS() {
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    await setupAutoplay("https://www.youtube.com/embed/example");
    expect(youtubeWindow.onYouTubeIframeAPIReady).toBe(prior);
});

test("readiness cleanup preserves a callback installed by another embed", async () => {
    const downloaded = /** @type {Deferred<void>} */ (new Deferred());
    patchWithCleanup(assets, {
        loadJS() {
            return downloaded;
        },
    });
    const loading = setupAutoplay("https://www.youtube.com/embed/example");
    const onReady = youtubeWindow.onYouTubeIframeAPIReady;
    const newer = () => {};
    youtubeWindow.onYouTubeIframeAPIReady = newer;
    onReady();
    downloaded.resolve();
    await loading;
    expect(youtubeWindow.onYouTubeIframeAPIReady).toBe(newer);
});

test("provider detection uses the hostname, not query text or lookalike domains", async () => {
    patchWithCleanup(assets, {
        async loadJS() {
            expect.step("script");
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    await setupAutoplay("https://player.vimeo.com/video/1?youtube=true");
    await setupAutoplay("https://youtube.com.example.test/embed/1");
    expect.verifySteps([]);
    await setupAutoplay("https://WWW.YOUTUBE.COM:443/embed/1");
    expect.verifySteps(["script"]);
});

test("missing and malformed video sources preserve placeholder contents", () => {
    for (const src of [undefined, "https://[", "https://unsupported.example/video"]) {
        const placeholder = document.createElement("div");
        placeholder.innerHTML = "<span>Preview</span>";
        if (src !== undefined) {
            placeholder.dataset.src = src;
        }
        expect(generateVideoIframe(placeholder)).toBe(undefined);
        expect(placeholder.innerHTML).toBe("<span>Preview</span>");
    }
});

test("video placeholders accept normalized hostnames and retain consent blocking", () => {
    const placeholder = document.createElement("div");
    placeholder.dataset.src = "https://WWW.YOUTUBE.COM:443/embed/1";
    placeholder.dataset.needCookiesApproval = "true";
    const iframe = generateVideoIframe(placeholder);
    expect(iframe).toHaveAttribute("src", "about:blank");
    expect(iframe).toHaveAttribute("data-nocookie-src", placeholder.dataset.src);
    expect(iframe).toHaveAttribute("data-need-cookies-approval", "true");
});

for (const shown of [false, true]) {
    test(`early video generation in a ${shown ? "shown" : "hidden"} popup`, () => {
        const popup = document.createElement("div");
        popup.className = "s_popup";
        popup.innerHTML = `<div class="modal ${shown ? "show" : ""}"><div class="media_iframe_video"
            data-src="https://www.youtube.com/embed/1?autoplay=1"></div></div>`;
        const placeholder = /** @type {HTMLElement} */ (
            popup.querySelector(".media_iframe_video")
        );
        const iframe = generateVideoIframe(placeholder);
        expect(iframe).toHaveAttribute(
            "src",
            shown ? placeholder.dataset.src : "about:blank",
        );
    });
}
