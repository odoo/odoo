// @ts-check
import "@website/interactions/cookies/cookies_approval";

import { describe, expect, test } from "@odoo/hoot";
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
import { Modal } from "@web/libs/bootstrap";
import { SIZES, utils } from "@web/ui/viewport";
import { MediaVideo } from "@website/interactions/video/media_video";

setupInteractionWhiteList(["website.media_video", "website.cookies_approval"]);
describe.current.tags("interaction_dev");

function mockYoutube(download = Promise.resolve()) {
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
            await download;
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
}

test("accepting cookies initializes autoplay after the iframe source is restored", async () => {
    mockYoutube();
    const { core } = await startInteractions(`
        <div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1"
             data-need-cookies-approval="true">
            <iframe src="about:blank" data-need-cookies-approval="true"
                data-nocookie-src="https://www.youtube.com/embed/1?autoplay=1"></iframe>
        </div>
    `);
    const interaction = getInteraction(core, MediaVideo);
    expect.verifySteps([]);
    document.dispatchEvent(new Event("optionalCookiesAccepted"));
    await tick();
    expect(interaction.iframeEl).toHaveAttribute(
        "src",
        "https://www.youtube.com/embed/1?autoplay=1",
    );
    expect.verifySteps(["script", "player"]);
    document.dispatchEvent(new Event("optionalCookiesAccepted"));
    await tick();
    expect.verifySteps([]);
});

test("a malformed video in a popup tolerates opening and closing", async () => {
    const { core } = await startInteractions(
        '<div class="s_popup"><div class="media_iframe_video"></div></div>',
    );
    const interaction = getInteraction(core, MediaVideo);
    interaction.el.parentElement.dispatchEvent(new Event("shown.bs.modal"));
    interaction.el.parentElement.dispatchEvent(new Event("hide.bs.modal"));
    expect(interaction.iframeEl).toBe(null);
});

test("closing a popup before API readiness prevents late autoplay", async () => {
    const download = /** @type {Deferred<void>} */ (new Deferred());
    mockYoutube(download);
    const { core } = await startInteractions(`
        <div class="s_popup"><div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1">
            <iframe src="https://www.youtube.com/embed/1?autoplay=1"></iframe>
        </div></div>
    `);
    const interaction = getInteraction(core, MediaVideo);
    await tick();
    expect.verifySteps(["script"]);
    interaction.el.parentElement.dispatchEvent(new Event("hide.bs.modal"));
    download.resolve();
    await tick();
    expect.verifySteps([]);
});

test("popup controls follow a replaced iframe and ignore the obsolete API request", async () => {
    const download = /** @type {Deferred<void>} */ (new Deferred());
    mockYoutube(download);
    const { core } = await startInteractions(`
        <div class="s_popup"><div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1">
            <iframe src="https://www.youtube.com/embed/1?autoplay=1"></iframe>
        </div></div>
    `);
    const interaction = getInteraction(core, MediaVideo);
    await tick();
    expect.verifySteps(["script"]);
    const replacement = /** @type {HTMLIFrameElement} */ (
        interaction.iframeEl.cloneNode()
    );
    interaction.iframeEl.replaceWith(replacement);
    interaction.el.parentElement.dispatchEvent(new Event("hide.bs.modal"));
    await tick();
    expect(replacement).toHaveAttribute("src", "");
    download.resolve();
    await tick();
    expect.verifySteps([]);
    interaction.el.parentElement.dispatchEvent(new Event("shown.bs.modal"));
    await tick();
    expect.verifySteps(["player"]);
    expect(interaction.iframeEl).toBe(replacement);
});

for (const transition of ["active", "close", "destroy"]) {
    test(`player readiness respects the ${transition} lifecycle state`, async () => {
        patchWithCleanup(browser, { ontouchstart() {} });
        patchWithCleanup(utils, { getSize: () => SIZES.SM });
        let onReady = (event) => {
            throw new Error(
                "The YouTube player did not register its readiness callback",
            );
        };
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
            <div class="s_popup"><div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1">
                <iframe src="https://www.youtube.com/embed/1?autoplay=1"></iframe>
            </div></div>
        `);
        await tick();
        expect(typeof onReady).toBe("function");
        const interaction = getInteraction(core, MediaVideo);
        if (transition === "close") {
            interaction.el.parentElement.dispatchEvent(new Event("hide.bs.modal"));
        } else if (transition === "destroy") {
            core.stopInteractions();
        }
        await tick();
        onReady({
            target: {
                playVideo() {
                    expect.step("late playback");
                },
            },
        });
        expect.verifySteps(transition === "active" ? ["late playback"] : []);
    });
}

for (const acceptWhileClosed of [true, false]) {
    test(`cookie acceptance while popup is ${acceptWhileClosed ? "closed" : "reopened"}`, async () => {
        mockYoutube();
        const { core } = await startInteractions(`
            <div class="s_popup"><div class="modal show">
                <div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1"
                     data-need-cookies-approval="true">
                    <iframe src="about:blank" data-need-cookies-approval="true"
                        data-nocookie-src="https://www.youtube.com/embed/1?autoplay=1"></iframe>
                </div>
            </div></div>
        `);
        const interaction = getInteraction(core, MediaVideo);
        const modal = interaction.el.parentElement;
        const dispatch = (name) =>
            modal.dispatchEvent(new Event(name, { bubbles: true }));
        dispatch("hide.bs.modal");
        await tick();
        expect(interaction.iframeEl).toHaveAttribute("src", "");
        if (!acceptWhileClosed) {
            dispatch("shown.bs.modal");
        }
        document.dispatchEvent(new Event("optionalCookiesAccepted"));
        await tick();
        if (acceptWhileClosed) {
            expect(interaction.iframeEl).toHaveAttribute("src", "");
            expect.verifySteps([]);
            dispatch("shown.bs.modal");
            await tick();
        }
        expect(interaction.iframeEl).toHaveAttribute(
            "src",
            "https://www.youtube.com/embed/1?autoplay=1",
        );
        expect.verifySteps(["script", "player"]);
    });
}

for (const needsConsent of [false, true]) {
    test(`an initially hidden popup waits for opening with consent ${needsConsent ? "pending" : "granted"}`, async () => {
        mockYoutube();
        const { core } = await startInteractions(`
            <div class="s_popup"><div class="modal"><div class="modal-dialog"><div class="modal-content">
                <div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1"
                     ${needsConsent ? 'data-need-cookies-approval="true"' : ""}></div>
            </div></div></div></div>
        `);
        const interaction = getInteraction(core, MediaVideo);
        await tick();
        if (needsConsent) {
            document.dispatchEvent(new Event("optionalCookiesAccepted"));
            await tick();
        }
        expect(interaction.iframeEl).toHaveAttribute("src", "about:blank");
        expect.verifySteps([]);
        const modal = new Modal(interaction.el.closest(".modal"), { backdrop: false });
        try {
            modal.show();
            await tick();
            expect(interaction.iframeEl).toHaveAttribute(
                "src",
                "https://www.youtube.com/embed/1?autoplay=1",
            );
            expect.verifySteps(["script", "player"]);
        } finally {
            modal.hide();
            await tick();
            modal.dispose();
        }
    });
}

for (const transition of ["cancel at modal", "cancel at document", "reopen"]) {
    test(`modal transition preserves playback: ${transition}`, async () => {
        mockYoutube();
        const { core } = await startInteractions(`
            <div class="s_popup"><div class="modal"><div class="modal-dialog"><div class="modal-content">
                <div class="media_iframe_video" data-src="https://www.youtube.com/embed/1?autoplay=1"></div>
            </div></div></div></div>
        `);
        const interaction = getInteraction(core, MediaVideo);
        const modalEl = interaction.el.closest(".modal");
        const modal = new Modal(modalEl, { backdrop: false });
        try {
            modal.show();
            await tick();
            expect.verifySteps(["script", "player"]);
            const cancelTarget = transition === "cancel at modal" ? modalEl : document;
            const cancel = (event) => event.preventDefault();
            if (transition !== "reopen") {
                cancelTarget.addEventListener("hide.bs.modal", cancel, { once: true });
            }
            try {
                modal.hide();
            } finally {
                cancelTarget.removeEventListener("hide.bs.modal", cancel);
            }
            if (transition === "reopen") {
                modal.show();
            }
            await tick();
            expect(modalEl).toHaveClass("show");
            expect(interaction.iframeEl).toHaveAttribute(
                "src",
                "https://www.youtube.com/embed/1?autoplay=1",
            );
            expect.verifySteps(transition === "reopen" ? ["player"] : []);
        } finally {
            modal.hide();
            await tick();
            modal.dispose();
        }
    });
}
