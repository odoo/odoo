import { expect, test } from "@odoo/hoot";
import { click, press } from "@odoo/hoot-dom";
import { setupEditor, testEditor } from "./_helpers/editor";
import { deleteBackward, insertText } from "./_helpers/user_actions";
import { getContent } from "./_helpers/selection";
import { animationFrame } from "@odoo/hoot-mock";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { StarPlugin } from "@html_editor/others/star_plugin";

/**
 * Rating Star Element Tests
 */

const Plugins = [...MAIN_PLUGINS, StarPlugin];

test("add 3 star elements", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", { config: { Plugins } });
    insertText(editor, "/3star");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    press("Enter");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );
});

test("add 5 star elements", async () => {
    const { el, editor } = await setupEditor("<p>[]</p>", { config: { Plugins } });
    insertText(editor, "/5star");
    await animationFrame();
    expect(".o-we-powerbox").toHaveCount(1);

    press("Enter");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );
});

test("select star rating", async () => {
    const { el } = await setupEditor(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`,
        { config: { Plugins } }
    );

    click("i.fa:first");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );

    click("i.fa:last");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star" contenteditable="false">\u200B</i><i class="o_stars fa fa-star" contenteditable="false">\u200B</i></span>\u200B[]</p>`
    );

    click("i.fa:last");
    expect(getContent(el)).toBe(
        `<p>\u200B<span contenteditable="false" class="o_stars"><i class="fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i><i class="o_stars fa fa-star-o" contenteditable="false">\u200B</i></span>\u200B[]</p>`
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
        config: { Plugins },
    });
});
