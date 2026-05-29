import { expect, test } from "@odoo/hoot";
import {
    manuallyDispatchProgrammaticEvent,
    click,
    press,
    queryAll,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, makeMockEnv, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CaptionPlugin } from "@html_editor/others/embedded_components/plugins/caption_plugin/caption_plugin";
import { MAIN_PLUGINS, EMBEDDED_COMPONENT_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { deleteBackward, deleteForward, insertText, undo } from "./_helpers/user_actions";
import { cleanHints } from "./_helpers/dispatch";
import { getContent, setSelection } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";
import { childNodeIndex, nodeSize } from "@html_editor/utils/position";
import { parseHTML } from "@html_editor/utils/html";

class CaptionPluginWithPredictableId extends CaptionPlugin {
    getCaptionId() {
        return "1";
    }
}
const base64Img =
    "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";
const configWithEmbeddedCaption = {
    Plugins: [
        ...MAIN_PLUGINS,
        CaptionPluginWithPredictableId,
        ...EMBEDDED_COMPONENT_PLUGINS.filter((plugin) => plugin.id !== "caption"),
    ],
    resources: {
        embedded_components: MAIN_EMBEDDINGS,
    },
};
const setupEditorWithEmbeddedCaption = async (content) =>
    await setupEditor(content, { config: configWithEmbeddedCaption });
const toggleCaption = async (editor, captionText) => {
    await click("img");
    await waitFor(".o-we-toolbar button[name='image_caption']");
    await click("button[name='image_caption']");
    if (captionText) {
        await waitFor("figure > figcaption > span.o_caption_editable");
        for (const char of captionText) {
            await insertText(editor, char);
        }
        const span = queryOne("figcaption > span.o_caption_editable");
        expect(span.textContent).toBe("Hello");
    }
};
const addLinkToImage = async (url) => {
    await click("img");
    await waitFor(".o-we-toolbar button[name='link']:not([disabled])");
    await click(".o-we-toolbar button[name='link']");
    if (url) {
        await waitFor(".o-we-linkpopover");
        await contains(".o-we-linkpopover input.o_we_href_input_link", { timeout: 1500 }).edit(
            "odoo.com"
        );
    }
};
const removeLinkFromImage = async () => {
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar");
    await click("button[name='unlink']");
};
const objectToAttributesString = (attributes) =>
    Object.entries(attributes)
        .map(([k, v]) => (v.includes('"') ? `${k}='${v}'` : `${k}="${v}"`))
        .join(" ");
/**
 * Generate the attribute string for a <figcaption> element in DOM mode.
 * @param {string} [caption] - Optional caption text for the placeholder attribute.
 */
const getFigcaptionAttributes = (caption = "") => {
    const attributes = {
        contenteditable: "false",
        class: "mt-2",
    };
    if (caption) {
        attributes.placeholder = caption;
    }
    return objectToAttributesString(attributes);
};
/**
 * Generate the <span> HTML for a caption in DOM mode.
 * @param {string|number} captionId
 * @param {string} [captionText]
 */
const getCaptionSpan = (captionId, captionText = "", focused = false, hasSelection = false) =>
    `<span class="o_caption_editable${
        focused ? " o-we-hint" : ""
    }" contenteditable="true" data-caption-id="${captionId}"${
        focused ? ` o-we-hint-text="Write a caption..."` : ""
    }>${captionText}${hasSelection ? "[]" : ""}</span>`;

test.tags("focus required");
test("add a caption to an image and focus it", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<img class="img-fluid test-image" src="${base64Img}">`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(span.textContent).toBe("");
            expect(editor.document.activeElement).toBe(span);
            expect(editor.document.getSelection().anchorNode.nodeName).toBe("SPAN");
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
            cleanHints(editor);
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes()}>
                    ${getCaptionSpan(captionId)}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
    });
});

test.tags("focus required");
test("add a caption to an image surrounded by text and focus it", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p>ab<img class="img-fluid test-image" src="${base64Img}">cd</p>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(span.textContent).toBe("");
            expect(editor.document.activeElement).toBe(span);
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
        },
        contentAfterEdit: unformat(
            `<p>ab</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes()}>
                    ${getCaptionSpan(captionId, "", true)}
                </figcaption>
            </figure>
            <p>cd</p>`
        ),
    });
});

test("saving an image with a caption replaces the span with plain text", async () => {
    const captionId = 1;
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>`
        ),
        contentBeforeEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                <figcaption ${getFigcaptionAttributes(caption)}>
                    ${getCaptionSpan(captionId, caption, false, true)}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        // Unchanged.
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                <figcaption ${getFigcaptionAttributes(caption)}>
                    ${getCaptionSpan(captionId, caption, false, true)}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
        // Cleaned up for screen readers.
        contentAfter: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">[]
                <figcaption>
                    ${caption}
                </figcaption>
            </figure>`
        ),
    });
});

test.tags("focus required");
test("loading an image with a caption embeds it", async () => {
    const { editor } = await setupEditorWithEmbeddedCaption(`
        <figure>
            <img class="img-fluid test-image" src="${base64Img}">
            <figcaption>Hello</figcaption>
        </figure>
    `);
    const image = queryOne("img");
    expect(image.getAttribute("data-caption")).toBe("Hello");
    const span = queryOne("figure > figcaption > span.o_caption_editable");
    expect(span.textContent).toBe("Hello");
    expect(editor.document.activeElement).toBe(span);
});

test.tags("focus required");
test("clicking the caption button on an image with a caption doesn't removes the caption", async () => {
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>`
        ),
        stepFunction: async (editor) => {
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            await toggleCaption(editor);
            expect(editor.document.activeElement).not.toBe(span);
            await expectElementCount(".o-we-toolbar", 1);
        },
        contentAfterEdit: unformat(
            `<p>[<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]</p>`
        ),
        // Unchanged
        contentAfter: unformat(
            `<p>[<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]</p>`
        ),
    });
});

test.tags("focus required");
test("leaving the caption persists its value", async () => {
    const captionId = 1;
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p><img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}"></p><h1>Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            await insertText(editor, "a");
            await insertText(editor, "b");
            await insertText(editor, "c");
            await press("Backspace");
            expect(span.textContent).toBe(`${caption}ab`);
            expect(editor.document.activeElement).toBe(span);
            const heading = queryOne("h1");
            await click(heading);
            expect(editor.document.activeElement).not.toBe(span);
            editor.shared.selection.setCursorStart(heading);
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}ab" data-caption-id="${captionId}">
                <figcaption ${getFigcaptionAttributes(caption + "ab")}>
                    ${getCaptionSpan(captionId, caption + "ab")}
                </figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        contentAfter: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>
                    ${caption}ab
                </figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
    });
});

test.tags("focus required");
test("can't use the powerbox in a caption", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<img class="img-fluid test-image" src="${base64Img}"><h1>Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            await insertText(editor, "/");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            const heading = queryOne("h1");
            await click(heading);
            editor.shared.selection.setCursorStart(heading);
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfter: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>
                    /
                </figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
    });
});

test.tags("desktop", "focus required");
test("can't use the toolbar in a caption", async () => {
    // TODO: The toolbar should not _always_ be usable in mobile!
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="Hello"><h1>[]Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
            // Select all content of the span and replace it.
            const range = document.createRange();
            range.selectNodeContents(span);
            document.getSelection().removeAllRanges();
            document.getSelection().addRange(range);
            editor.document.execCommand("insertText", false, "a");
            expect(span.textContent).toBe("a");
            await click("h1"); // Blur the span.
            await animationFrame(); // Wait for the focus event to trigger a step.
            editor.shared.selection.setCursorStart(queryOne("h1"));
        },
        contentAfter: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>a</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
    });
});

test.tags("focus required");
test("undo in a caption undoes the last caption action then returns to regular editor undo", async () => {
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p><img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}"></p><h1>[]Heading</h1>`,
        stepFunction: async (editor) => {
            await insertText(editor, "a");
            const heading = queryOne("h1");
            expect(heading.textContent).toBe("aHeading");
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            // Using native execCommand so the span's native history works.
            await insertText(editor, "b");
            await insertText(editor, "c");
            await insertText(editor, "d");
            deleteBackward(editor);
            await animationFrame();
            expect(span.textContent).toBe(`${caption}bc`);

            expect(editor.document.activeElement).toBe(span);
            undo(editor);
            await animationFrame();
            expect(span.textContent).toBe(`${caption}bcd`);
            expect(heading.textContent).toBe("aHeading");

            expect(editor.document.activeElement).toBe(span);
            // undo all chars and caption insertion.
            undo(editor);
            undo(editor);
            undo(editor);
            await animationFrame();
            expect(span.textContent).toBe(caption);
            expect(heading.textContent).toBe("aHeading");

            // Editor undo removes the caption.
            expect(editor.document.activeElement).toBe(span);
            undo(editor);
            await animationFrame();
            expect(span.isConnected).toBe(false);
            expect(heading.textContent).toBe("aHeading");

            // Editor undo removes the key press in the heading.
            expect(editor.document.activeElement).not.toBe(span);
            undo(editor);
            await animationFrame();
            expect(heading.textContent).toBe("Heading");
        },
        contentAfter: unformat(
            `<p>
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}">
            </p>
            <h1>[]Heading</h1>`
        ),
    });
});

test("remove an image with a caption", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='image_delete']");
            await click(".o-we-toolbar button[name='image_delete']");
        },
        contentAfter: "<h1>[]Heading</h1>",
    });
});

// For the following two tests.
const getDeleteImageTestData = () => {
    const captionId = 1;
    const caption = "Hello";
    return {
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<p><img class="img-fluid test-image" data-caption="${caption}" src="${base64Img}"></p>
            <h1>[]Heading</h1>`
        ),
        prepareImage: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            // Check that we indeed have a proper figure structure.
            expect(getContent(editor.editable).replace("[]", "")).toBe(
                unformat(
                    `<p data-selection-placeholder=""><br></p>
                            <figure contenteditable="false">
                            <img class="img-fluid test-image o_editable_media" data-caption="${caption}" src="${base64Img}" data-caption-id="${captionId}">
                            <figcaption ${getFigcaptionAttributes(caption)}>${getCaptionSpan(
                        captionId,
                        caption
                    )}</figcaption>
                        </figure>
                        <h1>Heading</h1>`
                )
            );
            const span = queryOne("figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            expect(span.textContent).toBe(caption);
            // Deselect and reselect the image.
            await click("h1");
            await click("img");
        },
        contentAfter: "<h1>[]Heading</h1>",
    };
};

test.tags("focus required");
test("remove an image with a caption, using the delete key", async () => {
    const { config, contentBefore, prepareImage, contentAfter } = getDeleteImageTestData();
    await testEditor({
        config,
        contentBefore,
        stepFunction: async (editor) => {
            await prepareImage(editor);
            deleteForward(editor);
        },
        contentAfter,
    });
});

test.tags("focus required");
test("remove an image with a caption, using the backspace key", async () => {
    const { config, contentBefore, prepareImage, contentAfter } = getDeleteImageTestData();
    await testEditor({
        config,
        contentBefore,
        stepFunction: async (editor) => {
            await prepareImage(editor);
            deleteBackward(editor);
        },
        contentAfter,
    });
});

test("replace an image with a caption", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    await testEditor({
        env,
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img src="/web/static/img/logo.png">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='replace_image']");
            await click("button[name='replace_image']");
            await waitFor(".o_select_media_dialog");
            await click(".o_existing_attachment_cell .o_button_area");
            await animationFrame();
            expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
            expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
        },
        // TODO: fix the weird final selection
        contentAfter: unformat(
            `<figure>
                <img src="/web/static/img/logo2.png" alt="" data-attachment-id="1" class="img img-fluid o_we_custom_image">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
    });
});

test("remove caption when replacing an image with other media", async () => {
    onRpc("ir.attachment", "search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const { el } = await setupEditorWithEmbeddedCaption(
        unformat(
            `<figure>
                <img src="/web/static/img/logo.png">
                <figcaption>Hello</figcaption>
            </figure>
            <p>abc</p>`
        )
    );
    await click("img");
    await waitFor(".o-we-toolbar button[name='replace_image']");
    await click("button[name='replace_image']");
    await waitFor(".o_select_media_dialog");
    await click(".modal .modal-body .nav-item:nth-child(3) a"); // Icons
    await waitFor(".modal .modal-body .fa-heart");
    await click(".modal .modal-body .fa-heart");
    expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
    expect(getContent(el)).toBe(
        '<p>\ufeff<span class="fa fa-heart" contenteditable="false">\u200b</span>[]\ufeff</p><p>abc</p>'
    );
});

test("edit caption after replacing image", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    await testEditor({
        env,
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img src="/web/static/img/logo.png">
                <figcaption>ab</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async (editor) => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='replace_image']");
            await click("button[name='replace_image']");
            await waitFor(".o_select_media_dialog");
            await click(".o_existing_attachment_cell .o_button_area");
            await animationFrame();
            expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
            expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            setSelection({ anchorNode: span, anchorOffset: span.childNodes.length });
            await animationFrame();
            expect(editor.document.activeElement).toBe(span);
            await insertText(editor, "c");
            expect(span.textContent).toBe("abc");
            expect(editor.document.activeElement).toBe(span);
            await click("img");
            await animationFrame();
        },
        contentAfter: unformat(
            `<figure>
                [<img src="/web/static/img/logo2.png" alt="" data-attachment-id="1" class="img img-fluid o_we_custom_image">]
                <figcaption>abc</figcaption>
            </figure>
            <h1>Heading</h1>`
        ),
    });
});

test("after replacing a captioned image, undo should revert to the original image and caption", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);
    const env = await makeMockEnv();
    await testEditor({
        env,
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img src="/web/static/img/logo.png" class="img-fluid test-image">
                <figcaption></figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='replace_image']");
            await click("button[name='replace_image']");
            await waitFor(".o_select_media_dialog");
            await click(".o_existing_attachment_cell .o_button_area");
            await animationFrame();
            expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
            expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
            await press(["ctrl", "z"]);
            await animationFrame();
            expect("img[src='/web/static/img/logo.png']").toHaveCount(1);
            expect("img[src='/web/static/img/logo2.png']").toHaveCount(0);
        },
        contentAfter: unformat(`
            <figure>
                [<img src="/web/static/img/logo.png" class="img-fluid test-image">]
                <figcaption></figcaption>
            </figure>
            <h1>Heading</h1>
        `),
    });
});

test("add a link to an image with a caption", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async () => {
            await addLinkToImage("odoo.com");
            await expectElementCount(".o-we-linkpopover", 1);
            await expectElementCount(".o-we-toolbar", 1);
        },
        contentAfter: unformat(
            `<p>
                <a href="https://odoo.com">
                    <figure>
                        [<img class="img-fluid test-image" src="${base64Img}">]
                        <figcaption>Hello</figcaption>
                    </figure>
                </a>
            </p>
            <h1>Heading</h1>`
        ),
    });
});

test.tags("focus required");
test("add a caption to an image with a link", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<a href="https://odoo.com">
                <img class="img-fluid test-image" src="${base64Img}">
            </a>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(editor.document.activeElement).toBe(span);
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
        },
        contentAfter: unformat(
            `<div>
                <a href="https://odoo.com">
                    <figure>
                        <img class="img-fluid test-image" src="${base64Img}">
                        <figcaption></figcaption>
                    </figure>
                </a>
            </div>
            <h1>Heading</h1>`
        ),
    });
});

test("add a caption then a link to an image surrounded by text", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p>ab<img class="img-fluid test-image" src="${base64Img}">cd</p>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor, "Hello");
            await addLinkToImage("odoo.com");
            await expectElementCount(".o-we-linkpopover", 1);
            await expectElementCount(".o-we-toolbar", 1);
        },
        contentAfter: unformat(
            `<p>ab</p>
            <p>
                <a href="https://odoo.com">
                    <figure>
                        [<img class="img-fluid test-image" src="${base64Img}">]
                        <figcaption>Hello</figcaption>
                    </figure>
                </a>
            </p>
            <p>cd</p>`
        ),
    });
});

test("add a link then a caption to an image surrounded by text", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p>ab<img class="img-fluid test-image" src="${base64Img}">cd</p>`,
        stepFunction: async (editor) => {
            await addLinkToImage("odoo.com");
            await animationFrame();
            await toggleCaption(editor, "Hello");
            // Blur the span to commit the caption.
            const p = queryAll("p")[1];
            await click(p);
            editor.shared.selection.setCursorStart(p);
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfter: unformat(
            `<p>ab</p>
            <p>[]
                <a href="https://odoo.com">
                    <figure>
                        <img class="img-fluid test-image" src="${base64Img}">
                        <figcaption>Hello</figcaption>
                    </figure>
                </a>
            </p>
            <p>cd</p>`
        ),
    });
});

test("remove a link from an image with a caption", async () => {
    const caption = "Hello";
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<p><br></p>
            <a href="https://odoo.com">
                <figure>
                    <img class="img-fluid test-image" src="${base64Img}">
                    <figcaption>${caption}</figcaption>
                </figure>
            </a>
            <h1>Heading</h1>`
        ),
        contentBeforeEdit: unformat(
            `<p><br></p>
            <div class="o-paragraph">
                <a href="https://odoo.com">
                    <figure contenteditable="false">
                        <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                        <figcaption ${getFigcaptionAttributes(caption)}>
                            ${getCaptionSpan(captionId, caption, false, true)}
                        </figcaption>
                    </figure>
                </a>
            </div>
            <h1>Heading</h1>`
        ),
        stepFunction: async () => {
            await removeLinkFromImage();
            await animationFrame();
            await expectElementCount(".o-we-linkpopover", 0);
            await expectElementCount(".o-we-toolbar", 1);
        },
        contentAfter: unformat(
            `<p><br></p>
            <figure>
                [<img class="img-fluid test-image" src="${base64Img}">]
                <figcaption>Hello</figcaption>
            </figure>
            <h1>Heading</h1>`
        ),
    });
});

test("remove a caption from an image with a link", async () => {
    const caption = "Hello";
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<p><br></p>
            <a href="https://odoo.com">
                <figure>
                    <img class="img-fluid test-image" src="${base64Img}">
                    <figcaption>${caption}</figcaption>
                </figure>
            </a>
            <h1>Heading</h1>`
        ),
        contentBeforeEdit: unformat(
            `<p><br></p>
            <div class="o-paragraph">
                <a href="https://odoo.com">
                    <figure contenteditable="false">
                        <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                        <figcaption ${getFigcaptionAttributes(caption)}>
                            ${getCaptionSpan(captionId, caption, false, true)}
                        </figcaption>
                    </figure>
                </a>
            </div>
            <h1>Heading</h1>`
        ),
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await expectElementCount(".o-we-linkpopover", 1);
            await expectElementCount(".o-we-toolbar", 1);
        },
        contentAfter: unformat(
            `<p><br></p>
            <div>
                <a href="https://odoo.com">
                    [<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]
                </a>
            </div>
            <h1>Heading</h1>`
        ),
    });
});

test("previewing an image with a caption shows the caption as title", async () => {
    const { editor } = await setupEditorWithEmbeddedCaption(
        `<img class="img-fluid test-image" src="${base64Img}">`
    );

    // Preview without a caption shows the file name.
    await click("img");
    await waitFor(".o-we-toolbar");
    await click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    let titleSpan = queryOne(".o-FileViewer .o-FileViewer-header span.text-truncate");
    expect(titleSpan.textContent).toBe(base64Img.replaceAll("\n", "%0A"));
    await click(".o-FileViewer-headerButton[title='Close (Esc)']");
    await animationFrame();

    // Add a caption
    await toggleCaption(editor, "Hello");
    await waitForNone(".o-we-toolbar button[name='image_caption']");

    // Preview with a caption show the caption.
    await click("img");
    await waitFor(".o-we-toolbar button[name='image_preview']");
    await click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    titleSpan = queryOne(".o-FileViewer .o-FileViewer-header span.text-truncate");
    expect(titleSpan.textContent).toBe("Hello");
});

test("previewing an image without caption doesn't show the caption as title (even if data-caption exists)", async () => {
    const { editor } = await setupEditorWithEmbeddedCaption(
        `<img class="img-fluid test-image" src="${base64Img}">`
    );

    // Preview without a caption shows the file name.
    await click("img");
    await waitFor(".o-we-toolbar button[name='image_preview']");
    await click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    let titleSpan = queryOne(".o-FileViewer .o-FileViewer-header span.text-truncate");
    expect(titleSpan.textContent).toBe(base64Img.replaceAll("\n", "%0A"));
    await click(".o-FileViewer-headerButton[title='Close (Esc)']");
    await animationFrame();

    // Add a caption
    await toggleCaption(editor, "Hello");
    await waitForNone(".o-we-toolbar button[name='image_caption']");

    // Remove the caption
    await toggleCaption(editor);
    const image = queryOne("img");
    expect(image.getAttribute("data-caption")).toBe("Hello");
    expect("figure").toHaveCount(0);

    // Preview without a caption still shows the file name.
    await click("img");
    await waitFor(".o-we-toolbar button[name='image_preview']");
    await click(".o-we-toolbar button[name='image_preview']");
    await animationFrame();
    titleSpan = queryOne(".o-FileViewer .o-FileViewer-header span.text-truncate");
    expect(titleSpan.textContent).toBe(base64Img.replaceAll("\n", "%0A"));
});

test("should drag and drop image with its caption(1)", async () => {
    const captionId = 1;
    const caption = "Hello";
    const { el } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p>a</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>
            <p>b</p>
        `)
    );
    const imgElement = el.querySelector("img");
    const parent = imgElement.parentElement;
    const index = childNodeIndex(imgElement);
    setSelection({
        anchorNode: parent,
        anchorOffset: index,
        focusNode: parent,
        focusOffset: index + 1,
    });
    const targetNodeForDrop = el.lastChild;
    patchWithCleanup(document, {
        caretPositionFromPoint: () => ({
            offsetNode: targetNodeForDrop,
            offset: nodeSize(targetNodeForDrop),
        }),
    });

    const dragdata = new DataTransfer();
    await manuallyDispatchProgrammaticEvent(imgElement, "dragstart", { dataTransfer: dragdata });
    await animationFrame();
    const imageHTML = dragdata.getData("application/vnd.odoo.odoo-editor");
    const dropData = new DataTransfer();
    dropData.setData(
        "text/html",
        `<meta http-equiv="Content-Type" content="text/html;charset=UTF-8"><img src="${base64Img}">`
    );
    // Simulate the application/vnd.odoo.odoo-editor data that the browser would do.
    dropData.setData("application/vnd.odoo.odoo-editor", imageHTML);
    await manuallyDispatchProgrammaticEvent(targetNodeForDrop, "drop", { dataTransfer: dropData });
    await animationFrame();

    expect(getContent(el)).toBe(
        unformat(`
            <p>a</p>
            <p>b</p>
            <figure contenteditable="false">
                <img data-caption="${caption}" data-caption-id="${captionId}" src="${base64Img}" class="img-fluid test-image o_editable_media">
                <figcaption placeholder="${caption}" class="mt-2" contenteditable="false">
                    <span data-caption-id="1" contenteditable="true" class="o_caption_editable">Hello[]</span>
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should drag and drop image with its caption(2)", async () => {
    const captionId = 1;
    const caption = "Hello";
    const { el } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p>a</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>
            <p>b</p>
        `)
    );
    const imgElement = el.querySelector("img");
    const targetNodeForDrop = el.lastChild;
    patchWithCleanup(document, {
        caretPositionFromPoint: () => ({
            offsetNode: targetNodeForDrop,
            offset: nodeSize(targetNodeForDrop),
        }),
    });

    await manuallyDispatchProgrammaticEvent(imgElement, "pointerdown");
    const dragdata = new DataTransfer();
    await manuallyDispatchProgrammaticEvent(imgElement, "dragstart", { dataTransfer: dragdata });
    await animationFrame();
    const imageHTML = dragdata.getData("application/vnd.odoo.odoo-editor");
    const dropData = new DataTransfer();
    dropData.setData(
        "text/html",
        `<meta http-equiv="Content-Type" content="text/html;charset=UTF-8"><img src="${base64Img}">`
    );
    // Simulate the application/vnd.odoo.odoo-editor data that the browser would do.
    dropData.setData("application/vnd.odoo.odoo-editor", imageHTML);
    await manuallyDispatchProgrammaticEvent(targetNodeForDrop, "drop", { dataTransfer: dropData });
    await manuallyDispatchProgrammaticEvent(imgElement, "dragend");
    await animationFrame();

    expect(getContent(el)).toBe(
        unformat(`
            <p>a</p>
            <p>b</p>
            <figure contenteditable="false">
                <img data-caption="${caption}" data-caption-id="${captionId}" src="${base64Img}" class="img-fluid test-image o_editable_media">
                <figcaption placeholder="${caption}" class="mt-2" contenteditable="false">
                    <span data-caption-id="1" contenteditable="true" class="o_caption_editable">Hello[]</span>
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
        `)
    );
});

test("should drag and drop image with caption along with selected text", async () => {
    const captionId = 1;
    const caption = "Hello";
    const { el } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p>a</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>
            <p>b</p>
            <p>c</p>
        `)
    );
    const [p1, p2] = el.querySelectorAll("p");
    setSelection({ anchorNode: p1, anchorOffset: 0, focusNode: p2, focusOffset: nodeSize(p2) });
    await animationFrame();
    const imgElement = el.querySelector("img");
    const targetNodeForDrop = el.lastChild;
    patchWithCleanup(document, {
        caretPositionFromPoint: () => ({
            offsetNode: targetNodeForDrop,
            offset: nodeSize(targetNodeForDrop),
        }),
    });

    const dragdata = new DataTransfer();
    await manuallyDispatchProgrammaticEvent(imgElement, "dragstart", { dataTransfer: dragdata });
    await animationFrame();
    const odooEditorData = dragdata.getData("application/vnd.odoo.odoo-editor");
    const textHtml = dragdata.getData("text/html");
    const dropData = new DataTransfer();
    dropData.setData("text/html", textHtml);
    // Simulate the application/vnd.odoo.odoo-editor data that the browser would do.
    dropData.setData("application/vnd.odoo.odoo-editor", odooEditorData);
    await manuallyDispatchProgrammaticEvent(targetNodeForDrop, "drop", { dataTransfer: dropData });
    await animationFrame();

    expect(getContent(el)).toBe(
        unformat(`
            <p><br></p>
            <p>ca</p>
            <figure contenteditable="false">
                <img data-caption="${caption}" data-caption-id="${captionId}" src="${base64Img}" class="img-fluid test-image o_editable_media">
                <figcaption placeholder="${caption}" class="mt-2" contenteditable="false">
                    <span data-caption-id="1" contenteditable="true" class="o_caption_editable">Hello</span>
                </figcaption>
            </figure>
            <p>b[]</p>
        `)
    );
});

test("should cut an image and its caption as a single embedded figure", async () => {
    const captionId = 1;
    const captionText = "Hello";

    const { el: editorRoot, editor } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p>a</p>
            <p>b</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}">
                <figcaption>${captionText}</figcaption>
            </figure>
            <p>c</p>
        `)
    );

    const image = editorRoot.querySelector("img");
    const figure = image.parentElement;
    const imageIndex = childNodeIndex(image);

    // Select the image node for cutting
    setSelection({
        anchorNode: figure,
        anchorOffset: imageIndex,
        focusNode: figure,
        focusOffset: imageIndex + 1,
    });

    const clipboard = new DataTransfer();
    const cutEvent = new ClipboardEvent("cut", { clipboardData: clipboard });
    editor.editable.dispatchEvent(cutEvent);
    await animationFrame();

    // Verify editor content after cut
    expect(getContent(editorRoot)).toBe(
        unformat(`
            <p>a</p>
            <p>b</p>
            <p>[]c</p>
        `)
    );

    // Verify cut fragment stored inside clipboard data
    const cutPayload = clipboard.getData("application/vnd.odoo.odoo-editor");
    const fragment = parseHTML(editor.document, cutPayload);

    expect(getContent(fragment)).toBe(
        unformat(`
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${captionText}">
                <figcaption ${getFigcaptionAttributes(captionText)}>
                    ${getCaptionSpan(captionId, captionText)}
                </figcaption>
            </figure>
        `)
    );
});

test("should copy an image along with its caption", async () => {
    const captionId = 1;
    const caption = "Hello";
    const { el, editor } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p>a</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}">
                <figcaption>${caption}</figcaption>
            </figure>
            <p>[]<br></p>
        `)
    );
    const imgElement = el.querySelector("img");
    const parent = imgElement.parentElement;
    const index = childNodeIndex(imgElement);
    setSelection({
        anchorNode: parent,
        anchorOffset: index,
        focusNode: parent,
        focusOffset: index + 1,
    });

    const clipboardData = new DataTransfer();
    await press(["ctrl", "c"], { dataTransfer: clipboardData });
    const copiedContent = clipboardData.getData("application/vnd.odoo.odoo-editor");
    const fragment = parseHTML(editor.document, copiedContent);
    expect(getContent(fragment)).toBe(
        unformat(`
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                <figcaption ${getFigcaptionAttributes(caption)}>
                    ${getCaptionSpan(captionId, caption)}
                </figcaption>
            </figure>
        `)
    );
});

test("should properly parse figure without fig caption", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
            </figure>`
        ),
        contentBeforeEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes()}>
                    ${getCaptionSpan(captionId, "", true, true)}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>
            `
        ),
    });
});

test("removing an image caption inside a table should wrap image in a base container", async () => {
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<table>
                <tbody>
                    <tr>
                        <td>
                            <p>a</p>
                            <figure>
                                <img class="img-fluid test-image" src="${base64Img}">
                                <figcaption>${caption}</figcaption>
                            </figure>
                            <p>b[]</p>
                        </td>
                        <td><p>c</p></td>
                    </tr>
                </tbody>
            </table>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='image_caption']");
            await click(".o-we-toolbar button[name='image_caption']");
        },
        contentAfter: unformat(
            `<table>
                <tbody>
                    <tr>
                        <td>
                            <p>a</p>
                            <p>
                                [<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]
                            </p>
                            <p>b</p>
                        </td>
                        <td><p>c</p></td>
                    </tr>
                </tbody>
            </table>`
        ),
    });
});

test("adding an image caption inside a list item should not split a list item", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<ul>
                <li>
                    ab
                    <img class="img-fluid test-image" src="${base64Img}">
                    cd
                </li>
            </ul>`
        ),
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            expect(span.textContent).toBe("");
            expect(editor.document.activeElement).toBe(span);
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
        },
        contentAfterEdit: unformat(
            `<ul>
                <li>
                    ab
                    <figure contenteditable="false">
                        <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                        <figcaption ${getFigcaptionAttributes()}>
                            ${getCaptionSpan(captionId, "", true)}
                        </figcaption>
                    </figure>
                    cd
                </li>
            </ul>`
        ),
    });
});

test("removing an image caption inside list item should wrap image in a base container", async () => {
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<ul>
                <li>
                    ab
                    <figure>
                        <img class="img-fluid test-image" src="${base64Img}">
                        <figcaption>${caption}</figcaption>
                    </figure>
                    cd[]
                </li>
            </ul>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='image_caption']");
            await click(".o-we-toolbar button[name='image_caption']");
        },
        contentAfter: unformat(
            `<ul>
                <li>
                    <p>ab</p>
                    <p>[<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]</p>
                    <p>cd</p>
                </li>
            </ul>`
        ),
    });
});

test("Should be able to revert image replace", async () => {
    onRpc("/web/dataset/call_kw/ir.attachment/search_read", () => [
        {
            id: 1,
            name: "logo",
            mimetype: "image/png",
            image_src: "/web/static/img/logo2.png",
            access_token: false,
            public: true,
        },
    ]);

    await makeMockEnv();
    const captionText = "caption";

    const { el } = await setupEditorWithEmbeddedCaption(
        unformat(`
            <p><br></p>
            <figure>
                <img src="/web/static/img/logo.png" class="img-fluid test-image">
                <figcaption>${captionText}</figcaption>
            </figure>
            <h1>[]Heading</h1>
        `)
    );

    await animationFrame();

    await click("img");
    await waitFor(".o-we-toolbar button[name='replace_image']");
    await click("button[name='replace_image']");

    // Select the image
    await waitFor(".o_select_media_dialog");
    await click(
        ".o_we_media_dialog_img_wrapper:has(img.o_we_attachment_highlight) + .o_button_area"
    );
    await animationFrame();

    // Check the image was successfully replaced
    expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);

    // UNDO
    await press(["ctrl", "z"]);
    await animationFrame();

    // Check the original image is back
    expect("img[src='/web/static/img/logo.png']").toHaveCount(1);
    expect("img[src='/web/static/img/logo2.png']").toHaveCount(0);

    // Check the caption text is still the same
    const span = el.querySelector("figcaption > span.o_caption_editable");
    expect(span.textContent).toBe(captionText);
});

test("should toggle caption on an image with display:block (add and remove caption)", async () => {
    const captionId = 1;
    const { el, editor } = await setupEditorWithEmbeddedCaption(
        `<img class="img-fluid test-image o_editable_media" style="display:block" src="${base64Img}">`
    );
    await animationFrame();
    await toggleCaption(editor);
    await animationFrame();
    const span = queryOne("figure > figcaption > span.o_caption_editable");
    expect(span.textContent).toBe("");
    expect(editor.document.activeElement).toBe(span);
    // Remove the editor selection for the test because it's irrelevant
    // since the focus is not in it.
    const selection = editor.document.getSelection();
    selection.removeAllRanges();
    await waitForNone(".o-we-toolbar");
    expect(getContent(el)).toBe(
        unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" style="display:block" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes()}>
                    ${getCaptionSpan(captionId, "", true)}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        )
    );
    await click("img");
    const captionButton = ".o-we-toolbar button[name='image_caption']";
    await waitFor(captionButton);
    expect(captionButton).toHaveClass("active");
    await click(captionButton);
    await animationFrame();
    expect(getContent(el)).toBe(
        unformat(`
            <p>[<img class="img-fluid test-image" style="display:block" src="${base64Img}" data-caption="">]</p>
        `)
    );
});

test.tags("focus required");
test("should select whole editable on 'ctrl+a' when image with caption is selected", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p>abc</p><img class="img-fluid test-image" src="${base64Img}"><p>def</p>`,
        stepFunction: async (editor) => {
            await toggleCaption(editor);
            await waitFor("figcaption > span.o_caption_editable");

            await click("figure > img");
            await expectElementCount(".o-we-toolbar", 1);

            // Select whole figure with ctrl+a
            await press(["ctrl", "a"]);
        },
        contentAfterEdit: unformat(
            `<p>[abc</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes()}>
                    ${getCaptionSpan(captionId, "", true)}
                </figcaption>
            </figure>
            <p>def]</p>`
        ),
    });
});

test("paste inside span should only paste text", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>`
        ),
        stepFunction: async (editor) => {
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            editor.shared.selection.setCursorStart(span);
            await animationFrame();

            const clipboardData = new DataTransfer();
            clipboardData.setData("text/plain", "world");
            clipboardData.setData("text/html", "<b>world</b>");
            const pasteEvent = new ClipboardEvent("paste", { clipboardData, bubbles: true });
            span.dispatchEvent(pasteEvent);
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="1" data-caption="worldHello">
                <figcaption ${getFigcaptionAttributes("worldHello")}>
                    ${getCaptionSpan(1, "world[]Hello")}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
    });
});

test("select all inside span and paste should not create paragraph", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>`
        ),
        stepFunction: async (editor) => {
            const span = queryOne("figure > figcaption > span.o_caption_editable");

            setSelection({
                anchorNode: span,
                anchorOffset: 0,
                focusNode: span,
                focusOffset: nodeSize(span),
            });
            await animationFrame();

            const clipboardData = new DataTransfer();
            clipboardData.setData("text/plain", "world");
            clipboardData.setData("text/html", "<b>world</b>");
            const pasteEvent = new ClipboardEvent("paste", { clipboardData, bubbles: true });
            span.dispatchEvent(pasteEvent);
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="1" data-caption="world">
                <figcaption ${getFigcaptionAttributes("world")}>
                    ${getCaptionSpan(1, "world[]")}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
    });
});

test("when selecting the text inside o_caption_editable CTRL+B should not format the text", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>`
        ),
        stepFunction: async (editor) => {
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            setSelection({
                anchorNode: span.firstChild,
                anchorOffset: 1,
                focusNode: span.firstChild,
                focusOffset: 4,
            });
            await animationFrame();
            await press(["ctrl", "b"]);
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="1" data-caption="Hello">
                <figcaption ${getFigcaptionAttributes("Hello")}>
                    ${getCaptionSpan(1, "H[ell]o")}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
    });
});

test("When selecting text along with o_caption_editable CTRL+B should format the text outside the figure but not o_caption_editable", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<p>[abc</p>
            <figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>
            <p>def]</p>`
        ),
        stepFunction: async (editor) => {
            const [p1, p2] = queryAll("p");
            setSelection({
                anchorNode: p1,
                anchorOffset: 0,
                focusNode: p2,
                focusOffset: nodeSize(p2),
            });
            await animationFrame();
            await press(["ctrl", "b"]);
        },
        contentAfterEdit: unformat(
            `<p><strong>[abc</strong></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="Hello">
                <figcaption ${getFigcaptionAttributes("Hello")}>
                    ${getCaptionSpan(captionId, "Hello")}
                </figcaption>
            </figure>
            <p><strong>def</strong>]</p>`
        ),
    });
});

test("drop inside span should only drop text", async () => {
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: unformat(
            `<figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>Hello</figcaption>
            </figure>`
        ),
        stepFunction: async () => {
            const span = queryOne("figure > figcaption > span.o_caption_editable");
            const firstTextNode = span.firstChild;
            setSelection({ anchorNode: firstTextNode, anchorOffset: 0 });
            await animationFrame();

            patchWithCleanup(document, {
                caretPositionFromPoint: () => ({
                    offsetNode: firstTextNode,
                    offset: 0,
                }),
            });

            const dragData = new DataTransfer();
            dragData.setData("text/plain", "world");
            dragData.setData("text/html", "<b>world</b>");
            await manuallyDispatchProgrammaticEvent(span, "drop", { dataTransfer: dragData });
            await animationFrame();
        },
        contentAfterEdit: unformat(
            `<p data-selection-placeholder=""><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="1" data-caption="worldHello">
                <figcaption ${getFigcaptionAttributes("worldHello")}>
                    ${getCaptionSpan(1, "world[]Hello")}
                </figcaption>
            </figure>
            <p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        ),
    });
});
