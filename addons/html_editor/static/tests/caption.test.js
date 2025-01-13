import { expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent, click, press, queryOne, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { CaptionPlugin } from "@html_editor/others/embedded_components/plugins/caption_plugin/caption_plugin";
import { MAIN_PLUGINS, EMBEDDED_COMPONENT_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { insertText } from "./_helpers/user_actions";
import { cleanHints } from "./_helpers/dispatch";

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
        embedded_components: [
            CaptionPluginWithPredictableId,
            ...MAIN_EMBEDDINGS.filter((plugin) => plugin.id !== "caption"),
        ],
    },
};
const setupEditorWithEmbeddedCaption = async (content) =>
    await setupEditor(content, { config: configWithEmbeddedCaption });
const toggleCaption = async (captionText) => {
    await click("img");
    await waitFor(".o-we-toolbar button[name='image_caption']");
    await click("button[name='image_caption']");
    if (captionText) {
        await waitFor("figure > figcaption > input");
        for (const char of captionText) {
            if (char.toUpperCase() === char) {
                await press(["Shift", char]);
            } else {
                await press(char);
            }
        }
        const input = queryOne("input");
        expect(input.value).toBe("Hello");
    }
};
const objectToAttributesString = (attributes) =>
    Object.entries(attributes)
        .map(([k, v]) => (v.includes('"') ? `${k}='${v}'` : `${k}="${v}"`))
        .join(" ");
const getFigcaptionAttributes = (captionId, caption = "", focusInput = false) => {
    const attributes = {
        "data-embedded": "caption",
        "data-oe-protected": "true",
        contenteditable: "false",
        class: "mt-2",
        "data-embedded-props": `{"id":"${captionId}","focusInput":${focusInput}}`,
    };
    if (caption) {
        attributes.placeholder = caption;
    }
    return objectToAttributesString(attributes);
};
const CAPTION_INPUT_ATTRIBUTES = objectToAttributesString({
    type: "text",
    maxlength: "100",
    class: "border-0 p-0",
    placeholder: "Write your caption here",
});

test.tags("focus required");
test("add a caption to an image and focus it", async () => {
    const captionId = 1;
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<img class="img-fluid test-image" src="${base64Img}">`,
        stepFunction: async (editor) => {
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(input.value).toBe("");
            expect(editor.document.activeElement).toBe(input);
            expect(editor.document.getSelection().anchorNode.nodeName).toBe("FIGCAPTION");
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
            cleanHints(editor);
        },
        contentAfterEdit: unformat(
            `<p><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes(captionId, "", true)}>
                    <input ${CAPTION_INPUT_ATTRIBUTES}>
                </figcaption>
            </figure>
            <p><br></p>`
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
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(input.value).toBe("");
            expect(editor.document.activeElement).toBe(input);
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
        },
        contentAfterEdit: unformat(
            `<p>ab</p>
            <figure contenteditable="false">
                <img class="img-fluid test-image" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
                <figcaption ${getFigcaptionAttributes(captionId, "", true)}>
                    <input ${CAPTION_INPUT_ATTRIBUTES}>
                </figcaption>
            </figure>
            <p>cd</p>`
        ),
    });
});

test("saving an image with a caption replaces the input with plain text", async () => {
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
            // Paragraphs get added to ensure we can write before/after the figure.
            `<p><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                <figcaption ${getFigcaptionAttributes(captionId, caption)}>
                    <input ${CAPTION_INPUT_ATTRIBUTES}>
                </figcaption>
            </figure>
            <p><br></p>`
        ),
        // Unchanged.
        contentAfterEdit: unformat(
            `<p><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
                <figcaption ${getFigcaptionAttributes(captionId, caption)}>
                    <input ${CAPTION_INPUT_ATTRIBUTES}>
                </figcaption>
            </figure>
            <p><br></p>`
        ),
        // Cleaned up for screen readers.
        contentAfter: unformat(
            `<p><br></p>
            <figure>
                <img class="img-fluid test-image" src="${base64Img}">
                <figcaption>
                    ${caption}
                </figcaption>
            </figure>
            <p><br></p>`
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
    const input = queryOne("figure > figcaption > input");
    expect(input.value).toBe("Hello");
    // Do not focus the input when loading the page.
    expect(editor.document.activeElement).not.toBe(input);
});

test.tags("focus required");
test("clicking the caption button on an image with a caption removes the caption", async () => {
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
            const input = queryOne("figure > figcaption > input");
            await toggleCaption();
            expect(editor.document.activeElement).not.toBe(input);
            expect(".o-we-toolbar").toHaveCount(1);
        },
        contentAfterEdit: unformat(
            `<p><br></p>
            <p>[<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]</p>
            <p><br></p>`
        ),
        // Unchanged
        contentAfter: unformat(
            `<p><br></p>
            <p>[<img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">]</p>
            <p><br></p>`
        ),
    });
});

test.tags("focus required");
test("leaving the caption persists its value", async () => {
    const captionId = 1;
    const caption = "Hello";
    await testEditor({
        config: configWithEmbeddedCaption,
        contentBefore: `<p><img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}"></p><h1>Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            await press("a");
            await press("b");
            await press("c");
            await press("Backspace");
            expect(input.value).toBe(`${caption}ab`);
            expect(editor.document.activeElement).toBe(input);
            const heading = queryOne("h1");
            await click(heading);
            expect(editor.document.activeElement).not.toBe(input);
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfterEdit: unformat(
            `<p><br></p>
            <figure contenteditable="false">
                <img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}ab" data-caption-id="${captionId}">
                <figcaption ${getFigcaptionAttributes(captionId, caption + "ab", true)}>
                    <input ${CAPTION_INPUT_ATTRIBUTES}>
                </figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        contentAfter: unformat(
            `<p><br></p>
            <figure>
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
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            await press("/");
            await animationFrame();
            expect(".o-we-powerbox").toHaveCount(0);
            const heading = queryOne("h1");
            await click(heading);
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfter: unformat(
            `<p><br></p>
            <figure>
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
        contentBefore: `<img class="img-fluid test-image" src="${base64Img}" data-caption="Hello"><h1>[]Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            await animationFrame();
            expect(".o-we-toolbar").toHaveCount(0);
            input.select();
            // Check that the contents of the input were indeed selected by
            // inserting text.
            editor.document.execCommand("insertText", false, "a");
            expect(input.value).toBe("a");
            await click("h1");
            await animationFrame(); // Wait for the selection to change.
        },
        contentAfter: unformat(
            `<p><br></p>
            <figure>
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
        contentBefore: `<p><img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}"></p><h1>[]Heading</h1>`,
        stepFunction: async (editor) => {
            await insertText(editor, "a");
            const heading = queryOne("h1");
            expect(heading.textContent).toBe("aHeading");
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            // Using native execCommand so the input's native history works.
            await editor.document.execCommand("insertText", false, "b");
            await editor.document.execCommand("insertText", false, "c");
            await editor.document.execCommand("insertText", false, "d");
            await editor.document.execCommand("delete", false, null); // Backspace.
            expect(input.value).toBe(`${caption}bc`);

            // We simulate undo with Ctrl+Z because we want to see how it
            // interacts with native browser behavior.
            const ctrlZ = async (target, shouldApplyNativeUndo) => {
                const keydown = await manuallyDispatchProgrammaticEvent(target, "keydown", {
                    key: "z",
                    ctrlKey: true,
                });
                if (keydown.defaultPrevented) {
                    return;
                }
                let valueBeforeUndo;
                if (target === input) {
                    valueBeforeUndo = input.value;
                    // This is supposed to happen only after "beforeinput" but
                    // beforeinput doesn't happen at all if there is nothing to
                    // undo and this allows us to determine if that is the case.
                    editor.document.execCommand("undo", false, null);
                }
                if (shouldApplyNativeUndo) {
                    // The native undo should have changed the value of the
                    // input.
                    expect(input.value).not.toBe(valueBeforeUndo);
                } else if (target === input) {
                    // The native undo should not have changed the value of the input.
                    expect(input.value).toBe(valueBeforeUndo);
                }
                if (target !== input || input.value !== valueBeforeUndo) {
                    // The input events don't get triggered if the input has
                    // nothing to undo.
                    const beforeInput = await manuallyDispatchProgrammaticEvent(
                        target,
                        "beforeinput",
                        {
                            inputType: "historyUndo",
                        }
                    );
                    // --> Here the editor should do its own UNDO.
                    if (beforeInput.defaultPrevented) {
                        return;
                    }
                    const inputEvent = await manuallyDispatchProgrammaticEvent(target, "input", {
                        inputType: "historyUndo",
                    });
                    if (inputEvent.defaultPrevented) {
                        return;
                    }
                }
                await manuallyDispatchProgrammaticEvent(target, "keyup", {
                    key: "z",
                    ctrlKey: true,
                });
            };

            // Native input undo undoes backspace in the input.
            expect(editor.document.activeElement).toBe(input);
            await ctrlZ(input, true);
            expect(input.value).toBe(`${caption}bcd`);
            expect(heading.textContent).toBe("aHeading");

            // Native input undo undoes all the other key presses in the input.
            expect(editor.document.activeElement).toBe(input);
            await ctrlZ(input, true);
            expect(input.value).toBe(caption);
            expect(heading.textContent).toBe("aHeading");

            // Editor undo removes the caption.
            expect(editor.document.activeElement).toBe(input);
            await ctrlZ(input, false);
            expect(input.isConnected).toBe(false);
            expect(heading.textContent).toBe("aHeading");

            // Editor undo removes the key press in the heading.
            expect(editor.document.activeElement).not.toBe(input);
            const anchor = editor.document.getSelection().anchorNode;
            await ctrlZ(closestElement(anchor), false);
            expect(heading.textContent).toBe("Heading");
        },
        contentAfter: unformat(
            `<p>
                <img class="img-fluid test-image" src="${base64Img}" data-caption="${caption}">
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
        contentAfter: unformat(
            `<p><br></p>
            <h1>[]Heading</h1>`
        ),
    });
});

test("replace an image with a caption", async () => {
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
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
        stepFunction: async () => {
            await click("img");
            await waitFor(".o-we-toolbar button[name='replace_image']");
            await click("button[name='replace_image']");
            await waitFor(".o_select_media_dialog");
            await click("img.o_we_attachment_highlight");
            await animationFrame();
            expect("img[src='/web/static/img/logo.png']").toHaveCount(0);
            expect("img[src='/web/static/img/logo2.png']").toHaveCount(1);
        },
        // TODO: fix the weird final selection
        contentAfter: unformat(
            `<p><br></p>
            <figure>
                <img src="/web/static/img/logo2.png" alt="" class="img img-fluid o_we_custom_image">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
    });
});
