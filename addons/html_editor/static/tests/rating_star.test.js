import { expect, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import {
    deleteBackward,
    deleteForward,
    insertText,
    simulateArrowKeyPress,
    splitBlock,
} from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { animationFrame } from "@odoo/hoot-mock";
import { expectElementCount } from "./_helpers/ui_expectations";

/**
 * Rating Star Element Tests
 */

test("add 3 star elements", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/3star");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);

    await press("Enter");
    expect(getContent(el)).toBe(
        `<p>\uFEFF<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF[]</p>`
    );
});

test("add 5 star elements", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/5star");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);

    await press("Enter");
    expect(getContent(el)).toBe(
        `<p>\uFEFF<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF[]</p>`
    );
});

test("select star rating", async () => {
    const { el } = await setupEditor(
        `<p><span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>[]</p>`
    );

    await click("i.fa-star-o:first");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\uFEFF<span contenteditable="false" class="o_stars"><i class="fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF[]</p>`
    );

    await click("i.fa-star-o:last");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\uFEFF<span contenteditable="false" class="o_stars"><i class="fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star" contenteditable="false">\u200B</i></span>\uFEFF[]</p>`
    );

    await click("i.fa-star:last");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\uFEFF<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF[]</p>`
    );
});

test("should insert two empty paragraphs when Enter is pressed twice before the star element", async () => {
    const { el, editor } = await setupEditor(
        `<p>\u200B[]<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B</p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p>\uFEFF[]<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF\u200B</p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p><br></p><p><br></p><p>\uFEFF[]<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF\u200B</p>`
    );
});

test("should insert two empty paragraphs when Enter is pressed twice after the star element", async () => {
    const { el, editor } = await setupEditor(
        `<p>\u200B<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p>\u200B\uFEFF<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF</p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
    splitBlock(editor);
    expect(getContent(el)).toBe(
        `<p>\u200B\uFEFF<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\uFEFF</p><p><br></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
    );
});

test("should delete star rating elements when delete is pressed twice", async () => {
    await testEditor({
        contentBefore: `<p><span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>[]</p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
            deleteBackward(editor);
        },
        contentAfter: "<p>[]<br></p>",
    });
});

test("stars line should be reachable with up/down", async () => {
    const { el, editor } = await setupEditor("<p>abc[]def</p>");
    splitBlock(editor);
    splitBlock(editor);
    await simulateArrowKeyPress(editor, "ArrowUp");
    await insertText(editor, "/3star");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);
    await press("Enter");

    const stars = `<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i></span>`;
    expect(getContent(el)).toBe(`<p>abc</p><p>\uFEFF${stars}\uFEFF[]</p><p>def</p>`);

    await simulateArrowKeyPress(editor, "ArrowDown");
    await simulateArrowKeyPress(editor, "ArrowUp");
    await simulateArrowKeyPress(editor, "ArrowUp");
    await simulateArrowKeyPress(editor, "ArrowDown");
    expect(getContent(el)).toBe(`<p>abc</p><p>\uFEFF${stars}[]\uFEFF</p><p>def</p>`);

    deleteForward(editor);
    await simulateArrowKeyPress(editor, "ArrowLeft");
    deleteBackward(editor);

    expect(getContent(el)).toBe(`<p>abc[]\uFEFF${stars}\uFEFFdef</p>`);

    splitBlock(editor);
    await simulateArrowKeyPress(editor, "ArrowRight");
    splitBlock(editor);

    expect(getContent(el)).toBe(`<p>abc</p><p>\uFEFF${stars}\uFEFF</p><p>[]def</p>`);

    await simulateArrowKeyPress(editor, "ArrowUp");
    expect(getContent(el)).toBe(`<p>abc</p><p>[]\uFEFF${stars}\uFEFF</p><p>def</p>`);

    await simulateArrowKeyPress(editor, "ArrowUp");
    await simulateArrowKeyPress(editor, "ArrowDown");
    expect(getContent(el)).toBe(`<p>abc</p><p>[]\uFEFF${stars}\uFEFF</p><p>def</p>`);
});
