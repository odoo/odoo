import "@website/interactions/cookies/cookies_approval";

// @ts-check
import { describe, expect, test } from "@odoo/hoot";
import { animationFrame, queryOne } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import {
    getInteraction,
    setupInteractionWhiteList,
    startInteractions,
} from "@web/../tests/public/helpers";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { assets } from "@web/core/assets";
import { browser } from "@web/core/browser/browser";
import { Deferred } from "@web/core/utils/concurrency";
import { SIZES, utils } from "@web/ui/viewport";
import { BackgroundVideo } from "@website/interactions/video/background_video";

setupInteractionWhiteList(["website.background_video", "website.cookies_approval"]);
describe.current.tags("interaction_dev");

test("background video stays hidden during its modal opening transition", async () => {
    // Exercise modal wiring without loading a third-party video iframe.
    patchWithCleanup(BackgroundVideo.prototype, { appendBgVideo() {} });
    await startInteractions(`
        <div class="modal">
            <div class="o_background_video" data-bg-video-src="about:blank">
                <div class="o_bg_video_container"></div>
            </div>
        </div>
    `);
    queryOne(".modal").dispatchEvent(new Event("show.bs.modal"));
    await animationFrame();
    expect(".o_bg_video_container").toHaveClass("d-none");
    queryOne(".modal").dispatchEvent(new Event("shown.bs.modal"));
    await animationFrame();
    expect(".o_bg_video_container").not.toHaveClass("d-none");
});

test("cookie acceptance before the background iframe exists is retained", async () => {
    patchWithCleanup(window, { YT: { Player: class {} } });
    const appendBgVideo = BackgroundVideo.prototype.appendBgVideo;
    patchWithCleanup(BackgroundVideo.prototype, { appendBgVideo() {} });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/example?autoplay=1"
             data-need-cookies-approval="true"></div>
    `);
    const interaction = getInteraction(core, BackgroundVideo);
    document.dispatchEvent(new Event("optionalCookiesAccepted"));
    expect(interaction.cookiesAccepted).toBe(true);
    expect(interaction.iframeEl).toBe(null);
    appendBgVideo.call(interaction);
    // The HOOT template processor moves iframe URLs to data-src to avoid navigation.
    expect(interaction.iframeEl).toHaveAttribute("data-src", interaction.videoSrc);
});

test("background API parameters precede fragments and replace existing values", async () => {
    patchWithCleanup(BackgroundVideo.prototype, { appendBgVideo() {} });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/1?enablejsapi=0#start"></div>
    `);
    const interaction = getInteraction(core, BackgroundVideo);
    const url = new URL(interaction.videoSrc);
    expect(url.searchParams.getAll("enablejsapi")).toEqual(["1"]);
    expect(url.hash).toBe("#start");
});

test("background videos retain other providers without YouTube parameters", async () => {
    patchWithCleanup(BackgroundVideo.prototype, { appendBgVideo() {} });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://custom.example/video#start"></div>
    `);
    expect(getInteraction(core, BackgroundVideo).videoSrc).toBe(
        "https://custom.example/video#start",
    );
});

test("accepting cookies initializes an already-rendered background video", async () => {
    patchWithCleanup(browser, { ontouchstart() {} });
    patchWithCleanup(utils, { getSize: () => SIZES.SM });
    const youtubeWindow = /** @type {Window & {
        YT?: { Player: new (...args: any[]) => any }, onYouTubeIframeAPIReady?: () => void,
    }} */ (window);
    patchWithCleanup(youtubeWindow, {
        YT: undefined,
        onYouTubeIframeAPIReady: undefined,
    });
    patchWithCleanup(assets, {
        async loadJS() {
            expect.step("script");
            youtubeWindow.YT = {
                Player: class {
                    constructor() {
                        expect.step("player");
                    }
                },
            };
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/1?autoplay=1"
             data-need-cookies-approval="true"></div>
    `);
    const interaction = getInteraction(core, BackgroundVideo);
    expect(interaction.iframeEl).not.toBe(null);
    expect.verifySteps([]);
    document.dispatchEvent(new Event("optionalCookiesAccepted"));
    await tick();
    expect.verifySteps(["script", "player"]);
});

test("a pending provider API does not delay iframe rendering or outlive teardown", async () => {
    patchWithCleanup(browser, { ontouchstart() {} });
    patchWithCleanup(utils, { getSize: () => SIZES.SM });
    const youtubeWindow = /** @type {Window & {
        YT?: { Player: new (...args: any[]) => any }, onYouTubeIframeAPIReady?: () => void,
    }} */ (window);
    patchWithCleanup(youtubeWindow, {
        YT: undefined,
        onYouTubeIframeAPIReady: undefined,
    });
    const downloaded = /** @type {Deferred<void>} */ (new Deferred());
    patchWithCleanup(assets, {
        async loadJS() {
            expect.step("script");
            await downloaded;
            youtubeWindow.YT = {
                Player: class {
                    constructor() {
                        expect.step("player");
                    }
                },
            };
            youtubeWindow.onYouTubeIframeAPIReady();
        },
    });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/1?autoplay=1"></div>
    `);
    expect(getInteraction(core, BackgroundVideo).iframeEl).not.toBe(null);
    await tick();
    expect.verifySteps(["script"]);
    core.stopInteractions();
    downloaded.resolve();
    await tick();
    expect.verifySteps([]);
});

test("acceptance invalidates an earlier pending blocked autoplay attempt", async () => {
    patchWithCleanup(browser, { ontouchstart() {} });
    patchWithCleanup(utils, { getSize: () => SIZES.SM });
    patchWithCleanup(window, {
        YT: {
            Player: class {
                constructor() {
                    expect.step("player");
                }
            },
        },
    });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/1?autoplay=1"
             data-need-cookies-approval="true"></div>
    `);
    await tick();
    const interaction = getInteraction(core, BackgroundVideo);
    interaction.activateAutoplay();
    document.dispatchEvent(new Event("optionalCookiesAccepted"));
    await tick();
    expect.verifySteps(["player"]);
});

test("background player readiness after teardown does not start playback", async () => {
    patchWithCleanup(browser, { ontouchstart() {} });
    patchWithCleanup(utils, { getSize: () => SIZES.SM });
    let onReady;
    patchWithCleanup(window, {
        YT: {
            Player: class {
                constructor(iframe, options) {
                    onReady = options.events.onReady;
                }
            },
        },
    });
    const { core } = await startInteractions(`
        <div class="o_background_video" data-bg-video-src="https://www.youtube.com/embed/1?autoplay=1"></div>
    `);
    const interaction = getInteraction(core, BackgroundVideo);
    // The HOOT template processor keeps iframe URLs in data-src.
    interaction.iframeEl.src = interaction.videoSrc;
    interaction.activateAutoplay();
    await tick();
    expect(typeof onReady).toBe("function");
    core.stopInteractions();
    onReady({
        target: {
            playVideo() {
                expect.step("late playback");
            },
        },
    });
    expect.verifySteps([]);
});
