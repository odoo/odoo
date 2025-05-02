import { describe, test } from "@odoo/hoot";
import { testEditor } from "./_helpers/editor";

test("should remove empty class attribute", async () => {
    // content after is compared after cleaning up DOM
    await testEditor({
        contentBefore: '<div class=""></div>',
        contentAfter: "<div><br></div>",
    });
});

describe("blockquote", () => {
    test("should unwrap links within blockquote", async () => {
        await testEditor({
            contentBefore: `<blockquote>a <a href="https://www.google.com">b</a> <a href="https://www.test.com">c</a></blockquote>`,
            contentAfter: "<blockquote>a b c</blockquote>",
        });
    });
});

describe("pre", () => {
    test("should unwrap links within pre", async () => {
        await testEditor({
            contentBefore: `<pre>a <a href="https://www.google.com">b</a> <a href="https://www.test.com">c</a></pre>`,
            contentAfter: "<pre>a b c</pre>",
        });
    });
});
