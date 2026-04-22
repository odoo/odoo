import { describe, test, tick } from "@odoo/hoot";
import { deleteBackward, simulateArrowKeyPress, undo } from "../_helpers/user_actions";
import { testEditor } from "../_helpers/editor";

describe("delete selection involving links", () => {
    test("should remove link", async () => {
        await testEditor({
            contentBefore: '<p><a href="#">[abc</a>d]ef</p>',
            contentBeforeEdit: '<p>\ufeff<a href="#">\ufeff[abc\ufeff</a>\ufeffd]ef</p>',
            stepFunction: deleteBackward,
            contentAfterEdit: "<p>[]ef</p>",
            contentAfter: "<p>[]ef</p>",
        });
    });
    test("should remove link (2)", async () => {
        await testEditor({
            contentBefore: '<p>ab[c<a href="#">def]</a></p>',
            contentBeforeEdit: '<p>ab[c\ufeff<a href="#">\ufeffdef]\ufeff</a>\ufeff</p>',
            stepFunction: deleteBackward,
            contentAfterEdit: "<p>ab[]</p>",
            contentAfter: "<p>ab[]</p>",
        });
    });
    test("should not remove link (only after clean)", async () => {
        await testEditor({
            contentBefore: '<p><a href="#">[abc]</a>def</p>',
            contentBeforeEdit:
                '<p>\ufeff<a href="#" class="o_link_in_selection">\ufeff[abc]\ufeff</a>\ufeffdef</p>',
            stepFunction: deleteBackward,
            contentAfterEdit:
                '<p>\ufeff<a href="#" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffdef</p>',
            contentAfter: "<p>[]def</p>",
        });
    });
});

describe("empty list items, starting and ending with links", () => {
    // Since we introduce \ufeff characters in and around links, we
    // can enter situations where the links aren't technically fully
    // selected but should be treated as if they were. These tests
    // are there to ensure that is the case. They represent four
    // variations of the same situation, and have the same expected
    // result.
    const tests = [
        // (1) <a>[...</a>...<a>...]</a>
        '<ul><li>ab</li><li><a href="#">[cd</a></li><li>ef</li><li><a href="#a">gh]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">[\ufeffcd</a></li><li>ef</li><li><a href="#a">gh\ufeff]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">\ufeff[cd</a></li><li>ef</li><li><a href="#a">gh\ufeff]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">[\ufeffcd</a></li><li>ef</li><li><a href="#a">gh]\ufeff</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">\ufeff[cd</a></li><li>ef</li><li><a href="#a">gh]\ufeff</a></li><li>ij</li></ul>',
        // (2) [<a>...</a>...<a>...]</a>
        '<ul><li>ab</li><li>[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li>[\ufeff<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh\ufeff]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li>\ufeff[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh\ufeff]</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li>[\ufeff<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh]\ufeff</a></li><li>ij</li></ul>',
        '<ul><li>ab</li><li>\ufeff[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh]\ufeff</a></li><li>ij</li></ul>',
        // (3) <a>[...</a>...<a>...</a>]
        '<ul><li>ab</li><li><a href="#">[cd</a></li><li>ef</li><li><a href="#a">gh</a>]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">[\ufeffcd</a></li><li>ef</li><li><a href="#a">gh</a>\ufeff]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">\ufeff[cd</a></li><li>ef</li><li><a href="#a">gh</a>\ufeff]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">[\ufeffcd</a></li><li>ef</li><li><a href="#a">gh</a>]\ufeff</li><li>ij</li></ul>',
        '<ul><li>ab</li><li><a href="#">\ufeff[cd</a></li><li>ef</li><li><a href="#a">gh</a>]\ufeff</li><li>ij</li></ul>',
        // (4) [<a>...</a>...<a>...</a>]
        '<ul><li>ab</li><li>[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh</a>]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li>[\ufeff<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh</a>\ufeff]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li>\ufeff[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh</a>\ufeff]</li><li>ij</li></ul>',
        '<ul><li>ab</li><li>[\ufeff<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh</a>]\ufeff</li><li>ij</li></ul>',
        '<ul><li>ab</li><li>\ufeff[<a href="#">cd</a></li><li>ef</li><li><a href="#a">gh</a>]\ufeff</li><li>ij</li></ul>',
    ];
    let testIndex = 1;
    for (const contentBefore of tests) {
        test(`should empty list items, starting and ending with links (${testIndex})`, async () => {
            await testEditor({
                contentBefore,
                stepFunction: deleteBackward,
                contentAfterEdit:
                    '<ul><li>ab</li><li placeholder="List" class="o-we-hint">[]<br></li><li>ij</li></ul>',
                contentAfter: "<ul><li>ab</li><li>[]<br></li><li>ij</li></ul>",
            });
        });
        testIndex += 1;
    }
});

test("Should properly restore selection on undo the delete", async () => {
    await testEditor({
        contentBefore: `<div class="o-paragraph">abc</div><div class="o-paragraph"><strong>cb[]</strong></div>`,
        stepFunction: async (editor) => {
            await simulateArrowKeyPress(editor, "ArrowUp");
            await tick();
            deleteBackward(editor);
            undo(editor);
        },
        contentAfter: `<div>ab[]c</div><div><strong>cb</strong></div>`,
    });
});
