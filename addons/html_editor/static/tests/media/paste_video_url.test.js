import { describe, expect, mockFetch, test } from "@odoo/hoot";
import { press, waitFor, waitForNone } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import { setupEditor } from "../_helpers/editor";
import { insertText, pasteText, undo } from "../_helpers/user_actions";
import { expectElementCount } from "../_helpers/ui_expectations";
import { getContent } from "../_helpers/selection";
import { cleanLinkArtifacts } from "../_helpers/format";
import { PLATFORMS } from "@html_editor/main/media/media_dialog/video_selector";

import {
    EMBEDDED_COMPONENT_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
const NO_EMBEDDED_COMPONENTS_CONFIG = {
    includePlugins: NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
};
const EMBEDDED_COMPONENTS_CONFIG = {
    includePlugins: EMBEDDED_COMPONENT_PLUGINS,
    resources: { embedded_components: MAIN_EMBEDDINGS },
};

for (const [platform, platformClass] of Object.entries(PLATFORMS)) {
    describe(`paste ${platform} url`, () => {
        const videoUrl = platformClass.exampleUrls.base;
        test(`should transform a ${platform} URL`, async () => {
            const { editor } = await setupEditor("<p>ab[]cd</p>", {
                config: NO_EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Validate powerbox on the default first choice
            await press("Enter");
            await animationFrame();

            const iframeContainer = await waitFor(`div.media_iframe_video`);
            const iframe = await waitFor(`div.media_iframe_video iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};

            expect(iframeContainerData.platform).toBe(platform);
            expect(iframeContainerData.baseUrl).toBe(videoUrl);

            expect(iframeContainerData.videoId).not.toBeEmpty();
            expect(videoUrl.includes(iframeContainerData.videoId)).toBe(true);
            expect(iframeContainerData.embedUrl).not.toBeEmpty();
            expect("undefined").not.toBe(iframeContainerData.embedUrl);
            expect(iframeContainerData.embedUrl).toBe(iframe.src);
        });
        test(`should transform a ${platform} URL with embeded Components`, async () => {
            const { editor } = await setupEditor("<p>ab[xx]cd</p>", {
                config: EMBEDDED_COMPONENTS_CONFIG,
            });
            mockFetch(() => '{"data": "mockFetch api result data"}');
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");

            const iframeContainer = await waitFor(`[data-embedded="video"]`);
            const iframe = await waitFor(`[data-embedded="video"] iframe`);
            const iframeContainerData = iframeContainer?.dataset || {};

            const embededProps = JSON.parse(iframeContainerData.embeddedProps);
            expect(embededProps.platform).toBe(platform);
            expect(embededProps.baseUrl).toBe(videoUrl);

            expect(iframe.dataset.baseUrl).not.toBeEmpty();
            expect(iframe.dataset.baseUrl).toBe(embededProps.baseUrl);

            // QWeb templates rendered during unit test store src in data-src
            const iframeSrc = iframe.getAttribute("src") || iframe.dataset.src || "";
            expect(iframeSrc).not.toBeEmpty();
            expect(iframeSrc.includes("https")).toBe(true);
        });
    });
}

describe("generic paste video url behaviors", () => {
    const videoUrl = "https://youtu.be/dQw4w9WgXcQ";
    test(`should NOT transform a video URL in a existing link`, async () => {
        const { el, editor, plugins } = await setupEditor(
            '<p>a<a href="http://existing.com">b[]c</a>d</p>',
            { config: EMBEDDED_COMPONENTS_CONFIG }
        );
        pasteText(editor, videoUrl);
        // Ensure the powerbox is active
        await expectElementCount(".o-we-powerbox", 0);
        const powerbox = plugins.get("powerbox");
        expect(powerbox.overlay.isOpen).not.toBe(true);
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>a<a href="http://existing.com">b${videoUrl}[]c</a>d</p>`
        );
    });
    test(`should paste a video URL as a link when selecting alternate powerbox option`, async () => {
        const { el, editor } = await setupEditor("<p>[]</p>", {
            config: NO_EMBEDDED_COMPONENTS_CONFIG,
        });
        pasteText(editor, videoUrl);
        await animationFrame();
        await expectElementCount(".o-we-powerbox", 1);
        // Pick the second command (Paste as URL)
        await press("ArrowDown");
        await press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="${videoUrl}">${videoUrl}</a>[]</p>`
        );
    });
    test("should not revert a history commit when pasting a video URL as a link", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>", {
            config: NO_EMBEDDED_COMPONENTS_CONFIG,
        });
        // paste text to have a history commit recorded
        pasteText(editor, "*should not disappear*");
        pasteText(editor, videoUrl);
        await animationFrame();
        await expectElementCount(".o-we-powerbox", 1);
        // Pick the second command (Paste as URL)
        await press("ArrowDown");
        await press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p>*should not disappear*<a href="${videoUrl}">${videoUrl}</a>[]</p>`
        );
    });
    test("should restore selection after pasting video URL followed by UNDO (1)", async () => {
        const { el, editor } = await setupEditor("<p>[abc]</p>", {
            config: NO_EMBEDDED_COMPONENTS_CONFIG,
        });
        pasteText(editor, videoUrl);
        await animationFrame();
        await expectElementCount(".o-we-powerbox", 1);
        // Force powerbox validation on the default first choice
        await press("Enter");
        // Undo
        undo(editor);
        expect(getContent(el)).toBe("<p>[abc]</p>");
    });

    test("should restore selection after pasting video URL followed by UNDO (2)", async () => {
        const { el, editor } = await setupEditor("<p>[abc]</p>", {
            config: NO_EMBEDDED_COMPONENTS_CONFIG,
        });
        pasteText(editor, videoUrl);
        await animationFrame();
        await expectElementCount(".o-we-powerbox", 1);
        // Pick the second command (Paste as URL)
        await press("ArrowDown");
        await press("Enter");
        // Undo
        undo(editor);
        expect(getContent(el)).toBe("<p>[abc]</p>");
    });
    test("should close powerbox after an undo", async () => {
        const { el, editor } = await setupEditor("<p>a[]b</p>", {
            config: NO_EMBEDDED_COMPONENTS_CONFIG,
        });
        await insertText(editor, "x");
        expect(getContent(el)).toBe(`<p>ax[]b</p>`);
        pasteText(editor, videoUrl);
        await animationFrame();
        await expectElementCount(".o-we-powerbox", 1);
        undo(editor);
        await waitForNone(".o-we-powerbox");
        expect(getContent(el)).toBe(`<p>ax[]b</p>`);
    });
});
