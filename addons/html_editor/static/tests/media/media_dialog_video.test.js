import { beforeEach, describe, expect, mockFetch, test, advanceTime } from "@odoo/hoot";
import { click, edit, press, hover, queryAll, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { patch } from "@web/core/utils/patch";

import { setupEditor } from "../_helpers/editor";
import { insertText } from "../_helpers/user_actions";
import { expectElementCount } from "../_helpers/ui_expectations";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";
import { VideoFile } from "@html_editor/main/media/video/providers/video_file";

import {
    EMBEDDED_COMPONENT_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { getContent } from "../_helpers/selection";
import { contains } from "../../../../web/static/tests/_framework/dom_test_helpers";
const NO_EMBEDDED_COMPONENTS_CONFIG = {
    includePlugins: NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
};
const EMBEDDED_COMPONENTS_CONFIG = {
    includePlugins: EMBEDDED_COMPONENT_PLUGINS,
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

const getEmbededComponentHtml = (videoId) =>
    `<div data-embedded="video" data-oe-protected="true" contenteditable="false" data-embedded-props='{"baseUrl":"https://www.youtube.com/watch?v=${videoId}","videoId":"${videoId}","platform":"youtube","params":{"startFrom":0,"autoplay":false,"loop":false,"hideControls":false,"hideFullscreen":false,"noCookie":false,"enableJsApi":true,"showRelatedVideos":false}}' class=""><iframe title="Video player" frameborder="0" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" src="" data-base-url="https://www.youtube.com/watch?v=${videoId}" data-src="https://www.youtube.com/embed/${videoId}?enablejsapi=1&rel=0"> Your browser does not support iframe. </iframe></div>`;

describe("media dialog video", () => {
    describe("without embeded Components", () => {
        for (const [platform, platformClass] of Object.entries(PLATFORMS)) {
            const videoUrl = platformClass.exampleUrls.base;
            test(`should accept a ${platform} URL`, async () => {
                const { editor } = await setupEditor("<p>ab[]cd</p>", {
                    config: NO_EMBEDDED_COMPONENTS_CONFIG,
                });
                mockFetch(() => '{"data": "mockFetch api result data"}');
                await insertText(editor, "/video");
                await animationFrame();
                await expectElementCount(".o-we-powerbox", 1);
                await press("Enter");

                await waitFor(`div.modal`);
                await click("#o_video_text");
                await edit(videoUrl);
                // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
                await advanceTime(100);
                // Click on save button
                await click(`div.modal .modal-footer button.btn-primary`);
                await animationFrame();
                await waitForNone(`div.modal`);

                const iframeContainer = await waitFor(`div.media_iframe_video`);
                const iframe = await waitFor(`div.media_iframe_video iframe`);
                const iframeContainerData = iframeContainer?.dataset || {};
                expect(iframeContainerData.platform).toBe(platform);
                expect(iframeContainerData.embedUrl).toBe(iframe.src);
            });
        }

        test("Should insert a video", async () => {
            const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
                config: NO_EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');
            // Open the media dialog with the /video command
            await insertText(editor, "/video");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");

            // Ensure the video tab is selected by default
            const selectedTab = await waitFor(`div.modal .nav-tabs button.active`);
            expect(selectedTab.textContent).toBe("Videos");
            const textarea = await waitFor(`div.modal #o_video_text`);

            // Insert a random text and encure it's not accepted as a video URL
            await click(`#o_video_text`);
            await edit("not a url");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            const warningAlert = await waitFor(`div.modal .o_video_preview .alert`);
            expect(textarea.classList.contains("is-invalid")).toBe(true);
            expect(warningAlert.textContent).toBe("The provided url is not valid");

            // Clear textarea and ensure the warning alert is removed
            await click(`#o_video_text`);
            await edit("");
            await animationFrame();
            expect(textarea.classList.contains("is-invalid")).toBe(false);

            // Insert an invalid URL and ensure it's not accepted as a video URL
            await click(`#o_video_text`);
            await edit("https://www.myvideos.com/video/123456789");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            // Otherwise `waitFor()` will instantly resolve since the alert already exists in the DOM,
            // and we won't be able to check the updated textContent of the alert.
            await advanceTime(100);
            const warningAlert2 = await waitFor(`div.modal .o_video_preview .alert`);
            expect(textarea.classList.contains("is-invalid")).toBe(true);
            expect(warningAlert2.textContent).toBe(
                "The provided url does not reference any supported video"
            );

            // Insert a valid video URL
            await click("#o_video_text");
            await edit("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Click on save button
            await click(`div.modal .modal-footer button.btn-primary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`div.media_iframe_video`);
            const iframe = await waitFor(`div.media_iframe_video iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};

            expect(iframeContainerData.platform).toBe("youtube");
            expect(iframeContainerData.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            expect(iframeContainerData.embedUrl).toBe(
                "https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0"
            );
            expect(iframeContainerData.videoId).toBe("dQw4w9WgXcQ");
            expect(iframeContainerData.embedUrl).toBe(iframe.src);
            expect(getContent(el)).toBe(
                `<p>ab</p><div data-platform="youtube" data-base-url="https://www.youtube.com/watch?v=dQw4w9WgXcQ" data-embed-url="https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0" data-video-id="dQw4w9WgXcQ" class="media_iframe_video" contenteditable="false">
                <div class="css_editable_mode_display"></div>
                <div class="media_iframe_video_size" contenteditable="false"></div>
            <iframe loading="lazy" frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen" src="https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0"></iframe></div><p>[]cd</p>`
            );
        });
        test("Should insert an instagram video verticaly", async () => {
            const { editor } = await setupEditor("<p>ab[]cd</p>", {
                config: NO_EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');
            // Open the media dialog with the /video command
            await insertText(editor, "/video");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");

            // Ensure the video tab is selected by default
            const selectedTab = await waitFor(`div.modal .nav-tabs button.active`);
            expect(selectedTab.textContent).toBe("Videos");
            await waitFor(`div.modal #o_video_text`);

            // Insert a valid instagram video URL
            await click("#o_video_text");
            await edit("https://www.instagram.com/reel/B6dXGTxggTG/");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Click on save button
            await click(`div.modal .modal-footer button.btn-primary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`div.media_iframe_video`);
            const iframe = await waitFor(`div.media_iframe_video iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};

            expect(iframeContainerData.platform).toBe("instagram");
            expect(iframeContainerData.baseUrl).toBe("https://www.instagram.com/reel/B6dXGTxggTG/");
            expect(iframeContainerData.embedUrl).toBe(
                "https://www.instagram.com/p/B6dXGTxggTG/embed/"
            );
            expect(iframeContainerData.isVertical).toBe("true");
            expect(iframeContainerData.videoId).toBe("B6dXGTxggTG");
            expect(iframeContainerData.embedUrl).toBe(iframe.src);
        });
    });

    describe("with embeded Components", () => {
        for (const [platform, platformClass] of Object.entries(PLATFORMS)) {
            const videoUrl = platformClass.exampleUrls.base;
            test(`should accept a ${platform} URL`, async () => {
                const { editor } = await setupEditor("<p>ab[]cd</p>", {
                    config: EMBEDDED_COMPONENTS_CONFIG,
                });
                mockFetch(() => '{"data": "mockFetch api result data"}');
                await insertText(editor, "/video");
                await animationFrame();
                await expectElementCount(".o-we-powerbox", 1);
                await press("Enter");

                await waitFor(`div.modal`);
                await click("#o_video_text");
                await edit(videoUrl);
                // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
                await advanceTime(100);
                // Click on save button
                await click(`div.modal .modal-footer button.btn-primary`);
                await animationFrame();
                await waitForNone(`div.modal`);

                const iframeContainer = await waitFor(`[data-embedded="video"]`);
                await waitFor(`[data-embedded="video"] iframe`);

                const iframeContainerData = iframeContainer?.dataset || {};
                const embededProps = JSON.parse(iframeContainerData.embeddedProps);
                expect(embededProps.platform).toBe(platform);
                expect(embededProps.baseUrl).toBe(videoUrl);
            });
        }

        const mediaReplaceRegex = /<div.*data-embedded="video".*><iframe.*src="([^"]*)".*<\/div>/gi;
        test("Should insert a video", async () => {
            const { el, editor } = await setupEditor("<p>ab[]cd</p>", {
                config: EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');
            // Open the media dialog with the /video command
            await insertText(editor, "/video");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");

            // Ensure the video tab is selected by default
            const selectedTab = await waitFor(`div.modal .nav-tabs button.active`);
            expect(selectedTab.textContent).toBe("Videos");
            const textarea = await waitFor(`div.modal #o_video_text`);

            // Insert a random text and encure it's not accepted as a video URL
            await click(`#o_video_text`);
            await edit("not a url");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            const warningAlert = await waitFor(`div.modal .o_video_preview .alert`);
            expect(textarea.classList.contains("is-invalid")).toBe(true);
            expect(warningAlert.textContent).toBe("The provided url is not valid");

            // Clear textarea and ensure the warning alert is removed
            await click(`#o_video_text`);
            await edit("");
            await animationFrame();
            expect(textarea.classList.contains("is-invalid")).toBe(false);

            // Insert an invalid URL and ensure it's not accepted as a video URL
            await click(`#o_video_text`);
            await edit("https://www.myvideos.com/video/123456789");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            // Otherwise `waitFor()` will instantly resolve since the alert already exists in the DOM,
            // and we won't be able to check the updated textContent of the alert.
            await advanceTime(100);
            const warningAlert2 = await waitFor(`div.modal .o_video_preview .alert`);
            expect(textarea.classList.contains("is-invalid")).toBe(true);
            expect(warningAlert2.textContent).toBe(
                "The provided url does not reference any supported video"
            );

            // Insert a valid video URL
            await click(`#o_video_text`);
            await edit("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Click on save button
            await click(`div.modal .modal-footer button.btn-primary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`[data-embedded="video"]`);
            const iframe = await waitFor(`[data-embedded="video"] iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};
            const embededProps = JSON.parse(iframeContainerData.embeddedProps);

            expect(embededProps.platform).toBe("youtube");
            expect(embededProps.videoId).toBe("dQw4w9WgXcQ");
            expect(embededProps.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");

            expect(iframe.dataset.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            // QWeb templates rendered during unit test store src in data-src
            // @see: addons/web/static/tests/_framework/mock_templates.hoot.js :: replaceAttributes()
            expect(iframe.dataset.src).toBe(
                "https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0"
            );

            // replace html in the getContent with a placeholder to improve readability of the test assertion
            expect(
                getContent(el).replaceAll(mediaReplaceRegex, "{MEDIA_HTML_PLACEHOLDER:$1}")
            ).toBe(
                `<p>ab</p>{MEDIA_HTML_PLACEHOLDER:https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0}<p>[]cd</p>`
            );
        });

        test("Should replace an existing video and keep focus", async () => {
            const { el, editor } = await setupEditor(
                `<p>a[]b</p>${getEmbededComponentHtml("dQw4w9WgXcQ")}<p>cd</p>`,
                {
                    config: EMBEDDED_COMPONENTS_CONFIG,
                }
            );
            mockFetch(() => '{"data": "mockFetch api result data"}');

            // In order to test the media dialog, we need to provide a real src for the iframe,
            // otherwise the media dialog won't recognize the existing video as valid.
            const iframeToFix = el.querySelector("iframe");
            iframeToFix.src = iframeToFix.dataset.src;

            hover('div[data-embedded="video"]');
            await animationFrame();
            await contains("button.video-options-button").click();
            await contains(".video-replace-button").click();
            await animationFrame();

            // Ensure the media dialog is open and the video tab is selected
            const selectedTab = await waitFor(`div.modal .nav-tabs button.active`);
            expect(selectedTab.textContent).toBe("Videos");
            const videoTextarea = await waitFor("#o_video_text");
            await advanceTime(100);
            expect(videoTextarea.value).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Insert a new valid video URL
            await click(`#o_video_text`);
            await edit("https://www.youtube.com/watch?v=qAgW3oG7Zmc");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            expect(videoTextarea.value).toBe("https://www.youtube.com/watch?v=qAgW3oG7Zmc");
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Click on save button
            await click(`div.modal .modal-footer button.btn-primary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`[data-embedded="video"]`);
            const iframe = await waitFor(`[data-embedded="video"] iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};
            const embededProps = JSON.parse(iframeContainerData.embeddedProps);

            expect(embededProps.platform).toBe("youtube");
            expect(embededProps.videoId).toBe("qAgW3oG7Zmc");
            expect(embededProps.baseUrl).toBe("https://www.youtube.com/watch?v=qAgW3oG7Zmc");

            expect(iframe.dataset.baseUrl).toBe("https://www.youtube.com/watch?v=qAgW3oG7Zmc");
            // QWeb templates rendered during unit test store src in data-src
            // @see : addons/web/static/tests/_framework/mock_templates.hoot.js :: replaceAttributes()
            expect(iframe.dataset.src).toBe(
                "https://www.youtube.com/embed/qAgW3oG7Zmc?enablejsapi=1&rel=0"
            );

            // replace html in the getContent with a placeholder to improve readability of the test assertion
            expect(
                getContent(el).replaceAll(mediaReplaceRegex, "{MEDIA_HTML_PLACEHOLDER:$1}")
            ).toBe(
                `<p>a[]b</p>{MEDIA_HTML_PLACEHOLDER:https://www.youtube.com/embed/qAgW3oG7Zmc?enablejsapi=1&rel=0}<p>cd</p>`
            );

            await insertText(editor, "x");
            expect(
                getContent(el).replaceAll(mediaReplaceRegex, "{MEDIA_HTML_PLACEHOLDER:$1}")
            ).toBe(
                `<p>ax[]b</p>{MEDIA_HTML_PLACEHOLDER:https://www.youtube.com/embed/qAgW3oG7Zmc?enablejsapi=1&rel=0}<p>cd</p>`
            );
        });

        test("Should not replace an existing video if cancel and keep focus", async () => {
            const { el } = await setupEditor(
                `<p>a[]b</p>${getEmbededComponentHtml("dQw4w9WgXcQ")}<p>cd</p>`,
                {
                    config: EMBEDDED_COMPONENTS_CONFIG,
                }
            );
            mockFetch(() => '{"data": "mockFetch api result data"}');

            // In order to test the media dialog, we need to provide a real src for the iframe,
            // otherwise the media dialog won't recognize the existing video as valid.
            const iframeToFix = el.querySelector("iframe");
            iframeToFix.src = iframeToFix.dataset.src;

            hover('div[data-embedded="video"]');
            await animationFrame();
            await contains("button.video-options-button").click();
            await contains(".video-replace-button").click();
            await animationFrame();

            // Ensure the media dialog is open and the video tab is selected
            const selectedTab = await waitFor(`div.modal .nav-tabs button.active`);
            expect(selectedTab.textContent).toBe("Videos");
            const videoTextarea = await waitFor("#o_video_text");
            await advanceTime(100);
            expect(videoTextarea.value).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Insert a new valid video URL
            await click(`#o_video_text`);
            await edit("https://www.youtube.com/watch?v=qAgW3oG7Zmc");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            expect(videoTextarea.value).toBe("https://www.youtube.com/watch?v=qAgW3oG7Zmc");
            await waitForNone(`div.modal .o_video_preview .alert`);

            // Click on discard button
            await click(`div.modal .modal-footer button.btn-secondary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`[data-embedded="video"]`);
            const iframe = await waitFor(`[data-embedded="video"] iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};
            const embededProps = JSON.parse(iframeContainerData.embeddedProps);

            expect(embededProps.platform).toBe("youtube");
            expect(embededProps.videoId).toBe("dQw4w9WgXcQ");
            expect(embededProps.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");

            expect(iframe.dataset.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            // QWeb templates rendered during unit test store src in data-src
            // @see : addons/web/static/tests/_framework/mock_templates.hoot.js :: replaceAttributes()
            expect(iframe.dataset.src).toBe(
                "https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0"
            );

            // replace HTML in the getContent with a placeholder to improve readability of the test assertion
            expect(
                getContent(el).replaceAll(mediaReplaceRegex, "{MEDIA_HTML_PLACEHOLDER:$1}")
            ).toBe(
                `<p>a[]b</p>{MEDIA_HTML_PLACEHOLDER:https://www.youtube.com/embed/dQw4w9WgXcQ?enablejsapi=1&rel=0}<p>cd</p>`
            );
        });

        test("Should delete an existing video and keep focus", async () => {
            const { el } = await setupEditor(
                `<p>a[]b</p>${getEmbededComponentHtml("dQw4w9WgXcQ")}<p>cd</p>`,
                {
                    config: EMBEDDED_COMPONENTS_CONFIG,
                }
            );
            mockFetch(() => '{"data": "mockFetch api result data"}');
            hover('div[data-embedded="video"]');
            await animationFrame();
            await contains("button.video-options-button").click();
            await contains(".video-delete-button").click();
            await animationFrame();

            expect(getContent(el)).toBe(`<p>a[]b</p><p>cd</p>`);
        });

        test("Video options should be inserted and be editable", async () => {
            const { editor } = await setupEditor(`<p>ab[]cd</p>`, {
                config: EMBEDDED_COMPONENTS_CONFIG,
            });
            const activeOptions = [
                "Start at",
                "Autoplay",
                "Loop",
                "Hide fullscreen button",
                "Vertical",
            ];
            const getOptionsInputs = (mediaModal) => {
                const optionsInputs = {};
                for (const el of mediaModal.querySelectorAll(`.o_video_dialog_options .o_switch`)) {
                    const label = el.querySelector("span.ms-2").textContent.trim();
                    const input = el.querySelector("input");
                    optionsInputs[label] = input;
                }
                return optionsInputs;
            };

            mockFetch(() => '{"data": "mockFetch api result data"}');
            // Open the media dialog with the /video command
            await insertText(editor, "/video");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            let mediaModal = await waitFor(`div.modal`);

            // Insert a valid video URL
            await click(`#o_video_text`);
            await edit("https://www.youtube.com/watch?v=dQw4w9WgXcQ");
            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(100);
            await waitForNone(`div.modal .o_video_preview .alert`);

            // activate all the desired options
            for (const [textLabel, input] of Object.entries(getOptionsInputs(mediaModal))) {
                if (activeOptions.includes(textLabel)) {
                    await click(input.closest("label"));
                    expect(input).toBeChecked();
                    if (textLabel === "Start at") {
                        await animationFrame(); // template need to be updated to show time input
                        const timeInput = input.parentElement.nextElementSibling;
                        await click(timeInput);
                        await edit("1:15");
                        await click(`#o_video_text`); // force focus out
                        await animationFrame();
                        expect(timeInput.value).toBe("1:15");
                        await click(timeInput);
                        await edit("83");
                        await click(`#o_video_text`); // force focus out
                        await animationFrame();
                        expect(timeInput.value).toBe("1:23");
                    }
                }
            }

            // We manualy advanceTime for `refreshVideoData()` to be triggered (the call is debounced).
            await advanceTime(50);
            // Click on save button
            await click(`div.modal .modal-footer button.btn-primary`);
            await animationFrame();
            await waitForNone(`div.modal`);

            const iframeContainer = await waitFor(`[data-embedded="video"]`);
            const iframe = await waitFor(`[data-embedded="video"] iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};
            const embededProps = JSON.parse(iframeContainerData.embeddedProps);

            expect(embededProps.platform).toBe("youtube");
            expect(embededProps.videoId).toBe("dQw4w9WgXcQ");
            expect(embededProps.baseUrl).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");

            expect(embededProps.params?.autoplay).toBe(true, {
                message: "autoplay should be true",
            });
            expect(embededProps.params?.loop).toBe(true, { message: "loop should be true" });
            expect(embededProps.params?.hideControls).toBe(false, {
                message: "hideControls should be false",
            });
            expect(embededProps.params?.hideFullscreen).toBe(true, {
                message: "hideFullscreen should be true",
            });
            expect(embededProps.params?.startFrom).toBe(83, { message: "startFrom should be 83" });

            // QWeb templates rendered during unit test store src in data-src
            // @see: addons/web/static/tests/_framework/mock_templates.hoot.js :: replaceAttributes()
            expect(iframe.dataset.src).toBe(
                "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&enablejsapi=1&fs=0&loop=1&mute=1&playlist=dQw4w9WgXcQ&rel=0&start=83"
            );
            // In order to test the media dialog edition, we need to provide a real src for the iframe;
            // otherwise the media dialog won't recognize the existing video as valid.

            // open the media modal on the newly added media in the DOM
            hover('div[data-embedded="video"]');
            await animationFrame();
            await contains("button.video-options-button").click();
            await contains(".video-replace-button").click();
            await animationFrame();
            mediaModal = await waitFor(`div.modal`);
            const videoTextarea = await waitFor("#o_video_text");
            await advanceTime(100);
            expect(videoTextarea.value).toBe("https://www.youtube.com/watch?v=dQw4w9WgXcQ");

            const verifiedOptions = [];
            for (const [textLabel, input] of Object.entries(getOptionsInputs(mediaModal))) {
                if (activeOptions.includes(textLabel)) {
                    verifiedOptions.push(textLabel);
                    expect(input).toBeChecked();
                } else {
                    expect(input).not.toBeChecked();
                }
            }
            // ensure all the options that should be active have been verified
            expect(`${activeOptions.toSorted()}`).toBe(`${verifiedOptions.toSorted()}`);
        });

        test("YouTube: toggles loop off without stale playlist parameter", async () => {
            // Playlist is a linkedParam, not a param, so it is not parsed as independent state.
            const { editor } = await setupEditor("<p>ab[]cd</p>", {
                config: NO_EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');

            await insertText(editor, "/video");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");

            const videoId = "dQw4w9WgXcQ";
            const mediaModal = await waitFor(`div.modal`);
            await waitFor(`div.modal #o_video_text`);
            await click(`#o_video_text`);
            await edit(`https://www.youtube.com/embed/${videoId}?loop=1&playlist=${videoId}`);
            await advanceTime(100);
            await animationFrame();

            const iframe = await waitFor(`div.modal .o_video_preview iframe`);
            expect(iframe.dataset.src || iframe.src).toInclude(`playlist=${videoId}`);

            let loopToggle = null;
            for (const switchEl of mediaModal.querySelectorAll(
                ".o_video_dialog_options .o_switch"
            )) {
                const label = switchEl.querySelector("span.ms-2")?.textContent.trim();
                if (label === "Loop") {
                    loopToggle = switchEl.querySelector("input");
                    break;
                }
            }
            expect(loopToggle).not.toBe(null);
            expect(loopToggle).toBeChecked();

            await click(loopToggle.closest("label"));
            await advanceTime(100);
            await animationFrame();

            expect(loopToggle).not.toBeChecked();

            const iframeAfter = await waitFor(`div.modal .o_video_preview iframe`);
            const regeneratedUrl = iframeAfter.dataset.src || iframeAfter.src;
            expect(regeneratedUrl).not.toInclude("playlist=");
            expect(regeneratedUrl).not.toInclude("loop=");
        });
    });

    describe("video files", () => {
        const VIDEO_FILE_CONFIG = {
            ...NO_EMBEDDED_COMPONENTS_CONFIG,
            allowVideoFile: true,
        };

        /**
         * Open the media dialog on the "Videos" tab, focused on the url input.
         */
        async function openVideoDialog(editor) {
            await insertText(editor, "/video");
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            await waitFor("div.modal");
            await click("#o_video_text");
        }

        async function typeVideoUrl(url) {
            await edit(url);
            // `refreshVideoData()` is debounced.
            await advanceTime(100);
            await waitForNone(".o_video_dialog_loading");
        }

        async function toggleVideoOption(label) {
            const switchEl = queryAll(".o_video_dialog_options .o_switch").find(
                (el) => el.querySelector("span.ms-2")?.textContent.trim() === label
            );
            expect(switchEl).not.toBe(undefined);
            await click(switchEl.querySelector("input").closest("label"));
            await advanceTime(100);
        }

        beforeEach(() => patch(VideoFile, { isValidVideoUrl: (url) => Promise.resolve([url]) }));

        test("should insert a video file with the default options", async () => {
            const { editor } = await setupEditor("<p>ab[]cd</p>", { config: VIDEO_FILE_CONFIG });
            await openVideoDialog(editor);
            await typeVideoUrl("https://example.com/video/my-video.mp4");
            await expectElementCount("div.modal .o_video_preview .alert", 0);
            await click("div.modal .modal-footer button.btn-primary");
            await animationFrame();
            await waitForNone("div.modal");

            const containerEl = await waitFor("div.media_iframe_video");
            const videoEl = await waitFor("div.media_iframe_video video");
            expect("div.media_iframe_video iframe").toHaveCount(0);
            expect(containerEl.dataset.platform).toBe("video_file");
            expect(videoEl).toHaveAttribute("src", "https://example.com/video/my-video.mp4");
            expect(videoEl).toHaveAttribute("controls");
            expect(videoEl).toHaveAttribute("playsinline");
            expect(videoEl).toHaveAttribute("preload", "metadata");
            expect(videoEl).not.toHaveAttribute("loop");
            expect(videoEl).not.toHaveAttribute("autoplay");
        });

        test("should apply the selected options on the inserted video file", async () => {
            const { editor } = await setupEditor("<p>ab[]cd</p>", { config: VIDEO_FILE_CONFIG });
            await openVideoDialog(editor);
            await typeVideoUrl("https://example.com/video/my-video.mp4");
            await waitFor(".o_video_dialog_options");
            // The fullscreen button of a native player cannot be hidden, so
            // the option must not be proposed.
            const optionLabels = queryAll(".o_video_dialog_options .o_switch").map((el) =>
                el.querySelector("span.ms-2")?.textContent.trim()
            );
            expect(optionLabels).toEqual([
                "Autoplay",
                "Loop",
                "Hide player controls",
                "Vertical",
                "Start at",
            ]);
            await toggleVideoOption("Loop");
            await toggleVideoOption("Autoplay");
            await toggleVideoOption("Hide player controls");
            await click("div.modal .modal-footer button.btn-primary");
            await animationFrame();
            await waitForNone("div.modal");

            const videoEl = await waitFor("div.media_iframe_video video");
            expect(videoEl).toHaveAttribute("loop");
            expect(videoEl).toHaveAttribute("autoplay");
            expect(videoEl).toHaveAttribute("muted");
            // The attribute is not enough on an element which is not created by
            // the html parser.
            expect(videoEl.muted).toBe(true);
            expect(videoEl).not.toHaveAttribute("controls");
        });

        test("should play the previewed video file when autoplay is enabled", async () => {
            patch(HTMLMediaElement.prototype, {
                play() {
                    expect.step("play");
                    return Promise.resolve();
                },
                pause() {
                    expect.step("pause");
                },
            });
            const { editor } = await setupEditor("<p>ab[]cd</p>", { config: VIDEO_FILE_CONFIG });
            await openVideoDialog(editor);
            await typeVideoUrl("https://example.com/video/my-video.mp4");

            const videoEl = await waitFor("div.modal .o_video_preview video");
            expect(videoEl).not.toHaveAttribute("autoplay");
            expect(videoEl.muted).toBe(false);
            expect.verifySteps(["pause"]);

            await toggleVideoOption("Autoplay");
            await animationFrame();
            expect(videoEl).toHaveAttribute("autoplay");
            expect(videoEl.muted).toBe(true);
            expect.verifySteps(["play"]);

            await toggleVideoOption("Autoplay");
            await animationFrame();
            expect(videoEl).not.toHaveAttribute("autoplay");
            expect(videoEl.muted).toBe(false);
            expect.verifySteps(["pause"]);
        });

        test("should not accept an url that is not a video", async () => {
            patch(VideoFile, {
                isValidVideoUrl(url) {
                    expect.step(`probe ${url}`);
                    return Promise.resolve(false);
                },
            });
            const { editor } = await setupEditor("<p>ab[]cd</p>", { config: VIDEO_FILE_CONFIG });
            await openVideoDialog(editor);
            await typeVideoUrl("https://www.myvideos.com/page/123456789");

            const alertEl = await waitFor("div.modal .o_video_preview .alert");
            expect(alertEl.textContent).toBe(
                "The provided url does not reference any supported video"
            );
            expect.verifySteps(["probe https://www.myvideos.com/page/123456789"]);
        });
    });
});
