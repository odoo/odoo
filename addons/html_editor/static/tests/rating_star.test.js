import { expect, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { deleteBackward, insertText } from "./_helpers/user_actions";
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
        `<p>\u200B<span contenteditable="false" class="o_stars">\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff</span>\u200B[]</p>`
    );
});

test("add 5 star elements", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>");
    await insertText(editor, "/5star");
    await animationFrame();
    await expectElementCount(".o-we-powerbox", 1);

    await press("Enter");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars">\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff</span>\u200B[]</p>`
    );
});

test("select star rating", async () => {
    const { el } = await setupEditor(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );

    await click("i.fa-star-o:first");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars">\ufeff<i class="fa fa-star" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i>\ufeff</span>\u200B[]</p>`
    );

    await click("i.fa-star-o:last");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars">\ufeff<i class="fa fa-star" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star" contenteditable="false">\u200B</i>\ufeff</span>\u200B[]</p>`
    );

    await click("i.fa-star:last");
    await animationFrame();
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars">\ufeff<i class="fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i>\ufeff<i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i>\ufeff</span>\u200B[]</p>`
    );
});

test("should delete star rating elements when delete is pressed twice", async () => {
    await testEditor({
        contentBefore: `<p>\u200B<span contenteditable="false" class="o_stars o_three_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`,
        stepFunction: async (editor) => {
            deleteBackward(editor);
            deleteBackward(editor);
        },
        contentAfter: "<p>[]<br></p>",
    });
});
