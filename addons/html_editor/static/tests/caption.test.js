import { expect, test } from "@odoo/hoot";
import {
    manuallyDispatchProgrammaticEvent,
    click,
    press,
    queryOne,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { contains, makeMockEnv, onRpc } from "@web/../tests/web_test_helpers";
import { CaptionPlugin } from "@html_editor/others/embedded_components/plugins/caption_plugin/caption_plugin";
import { MAIN_PLUGINS, EMBEDDED_COMPONENT_PLUGINS } from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";
import { closestElement } from "@html_editor/utils/dom_traversal";
import { setupEditor, testEditor } from "./_helpers/editor";
import { unformat } from "./_helpers/format";
import { deleteBackward, deleteForward, insertText } from "./_helpers/user_actions";
import { cleanHints } from "./_helpers/dispatch";
import { getContent } from "./_helpers/selection";
import { expectElementCount } from "./_helpers/ui_expectations";

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
const addLinkToImage = async (url) => {
    await click("img");
    await waitFor(".o-we-toolbar button[name='link']");
    await click(".o-we-toolbar");
    await click("button[name='link']");
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
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
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
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="">
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
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
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
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption-id="${captionId}" data-caption="${caption}">
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
            await expectElementCount(".o-we-toolbar", 1);
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
        contentBefore: `<p><img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}"></p><h1>Heading</h1>`,
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
                <img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}ab" data-caption-id="${captionId}">
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
            await expectElementCount(".o-we-powerbox", 0);
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
        contentBefore: `<img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="Hello"><h1>[]Heading</h1>`,
        stepFunction: async (editor) => {
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            await animationFrame();
            await expectElementCount(".o-we-toolbar", 0);
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
        contentBefore: `<p><img class="img-fluid test-image o_editable_media" src="${base64Img}" data-caption="${caption}"></p><h1>[]Heading</h1>`,
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
        contentAfter: unformat(
            `<p><br></p>
            <h1>[]Heading</h1>`
        ),
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
            await toggleCaption();
            await waitFor("figcaption > input");
            // Check that we indeed have a proper figure structure.
            expect(getContent(editor.editable).replace("[]", "")).toBe(
                unformat(
                    `<p><br></p>
                            <figure contenteditable="false">
                            <img class="img-fluid test-image o_editable_media" data-caption="${caption}" src="${base64Img}" data-caption-id="${captionId}">
                            <figcaption ${getFigcaptionAttributes(
                                captionId,
                                caption,
                                true
                            )}><input ${CAPTION_INPUT_ATTRIBUTES}></figcaption>
                        </figure>
                        <h1>Heading</h1>`
                )
            );
            const input = queryOne("input");
            expect(editor.document.activeElement).toBe(input);
            expect(input.value).toBe(caption);
            // Deselect and reselect the image.
            await click("h1");
            await click("img");
        },
        contentAfter: unformat(
            `<p><br></p>
            <h1>[]Heading</h1>`
        ),
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
            `<p><br></p>
            <figure>
                <img src="/web/static/img/logo2.png" alt="" data-attachment-id="1" class="img img-fluid o_we_custom_image">
                <figcaption>Hello</figcaption>
            </figure>
            <h1>[]Heading</h1>`
        ),
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
            `<p><br></p>
            <p>
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
            await toggleCaption();
            await waitFor("figcaption > input");
            const input = queryOne("figure > figcaption > input");
            expect(editor.document.activeElement).toBe(input);
            // Remove the editor selection for the test because it's irrelevant
            // since the focus is not in it.
            const selection = editor.document.getSelection();
            selection.removeAllRanges();
        },
        contentAfter: unformat(
            `<p><br></p>
            <div>
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
        stepFunction: async () => {
            await toggleCaption("Hello");
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
        stepFunction: async () => {
            await addLinkToImage("odoo.com");
            await animationFrame();
            await toggleCaption("Hello");
            // Blur the input to commit the caption.
            await click("p");
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
                        <figcaption ${getFigcaptionAttributes(captionId, caption)}>
                            <input ${CAPTION_INPUT_ATTRIBUTES}>
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
                        <figcaption ${getFigcaptionAttributes(captionId, caption)}>
                            <input ${CAPTION_INPUT_ATTRIBUTES}>
                        </figcaption>
                    </figure>
                </a>
            </div>
            <h1>Heading</h1>`
        ),
        stepFunction: async () => {
            await toggleCaption();
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
    await setupEditorWithEmbeddedCaption(`<img class="img-fluid test-image" src="${base64Img}">`);

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
    await toggleCaption("Hello");
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
    await setupEditorWithEmbeddedCaption(`<img class="img-fluid test-image" src="${base64Img}">`);

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
    await toggleCaption("Hello");
    await waitForNone(".o-we-toolbar button[name='image_caption']");

    // Remove the caption
    await toggleCaption();
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
