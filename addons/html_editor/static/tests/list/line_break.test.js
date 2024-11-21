import { test } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { insertLineBreak } from "../_helpers/user_actions";

test("should insert a <br> into an empty list item", async () => {
    await testEditor({
        contentBefore: "<ul><li>[]<br></li></ul>",
        stepFunction: insertLineBreak,
        contentAfter: "<ul><li><br>[]<br></li></ul>",
    });
});

test("should insert a <br> at the beggining of a list item", async () => {
    await testEditor({
        contentBefore: "<ul><li>[]abc</li></ul>",
        stepFunction: insertLineBreak,
        contentAfter: "<ul><li><br>[]abc</li></ul>",
    });
});

test("should insert a <br> within a list item", async () => {
    await testEditor({
        contentBefore: "<ul><li>ab[]cd</li></ul>",
        stepFunction: insertLineBreak,
        contentAfter: "<ul><li>ab<br>[]cd</li></ul>",
    });
});

test("should insert a line break (2 <br>) at the end of a list item", async () => {
    await testEditor({
        contentBefore: "<ul><li>abc[]</li></ul>",
        stepFunction: insertLineBreak,
        // The second <br> is needed to make the first
        // one visible.
        contentAfter: "<ul><li>abc<br>[]<br></li></ul>",
    });
});

test("should delete part of a list item, then insert a <br>", async () => {
    await testEditor({
        contentBefore: "<ul><li>ab[cd]ef</li></ul>",
        stepFunction: insertLineBreak,
        contentAfter: "<ul><li>ab<br>[]ef</li></ul>",
    });
});
