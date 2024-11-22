import { describe, test, tick } from "@odoo/hoot";
import { testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";

const splitBlockSegments = async (editor) => {
    editor.shared.split.splitBlockSegments();
    editor.shared.history.addStep();
    await tick();
};

describe("basic", () => {
    test("should isolate a line in a paragraph", async () => {
        await testEditor({
            contentBefore: `<p>a<br>b<br>[c]<br>d<br>e</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>a<br>b</p><p>[c]</p><p>d<br>e</p>`,
        });
    });

    test("should isolate a line in a paragraph (collapsed)", async () => {
        await testEditor({
            contentBefore: `<p>a<br>b<br>[]c<br>d<br>e</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>a<br>b</p><p>[]c</p><p>d<br>e</p>`,
        });
    });

    test("should isolate multiple lines in a paragraph (reversed selection)", async () => {
        await testEditor({
            contentBefore: `<p>a<br>b<br>]c<br>d[<br>e<br>f</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>a<br>b</p><p>]c</p><p>d[</p><p>e<br>f</p>`,
        });
    });

    test("should isolate all lines in a paragraph", async () => {
        await testEditor({
            contentBefore: `<p>[a<br>b<br>c<br>d<br>e]</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>[a</p><p>b</p><p>c</p><p>d</p><p>e]</p>`,
        });
    });

    test("should isolate all lines in a paragraph (reversed selection)", async () => {
        await testEditor({
            contentBefore: `<p>]a<br>b<br>c<br>d<br>e[</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>]a</p><p>b</p><p>c</p><p>d</p><p>e[</p>`,
        });
    });
});

describe("unbreakable", () => {
    test("should isolate a line in an unbreakable block", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">a<br>b<br>[c]<br>d<br>e</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>a<br>b</p><p>[c]</p><p>d<br>e</p></div>`,
        });
    });

    test("should isolate a line in an unbreakable block (collapsed)", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">a<br>b<br>[]c<br>d<br>e</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>a<br>b</p><p>[]c</p><p>d<br>e</p></div>`,
        });
    });

    test("should isolate multiple lines in an unbreakable block", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">a<br>b<br>[c<br>d]<br>e<br>f</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>a<br>b</p><p>[c</p><p>d]</p><p>e<br>f</p></div>`,
        });
    });

    test("should isolate multiple lines in an unbreakable block (reversed selection)", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">a<br>b<br>]c<br>d[<br>e<br>f</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>a<br>b</p><p>]c</p><p>d[</p><p>e<br>f</p></div>`,
        });
    });

    test("should isolate all lines in an unbreakable block", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">[a<br>b<br>c<br>d<br>e]</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>[a</p><p>b</p><p>c</p><p>d</p><p>e]</p></div>`,
        });
    });

    test("should isolate all lines in an unbreakable block (reversed selection)", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable">]a<br>b<br>c<br>d<br>e[</div>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<div class="oe_unbreakable"><p>]a</p><p>b</p><p>c</p><p>d</p><p>e[</p></div>`,
        });
    });

    test("should isolate a line in an unbreakable block starting with a block (do not wrap said block)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    <div>do not wrap</div>
                    a<br>b<br>[]c<br>d<br>e
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <div>do not wrap</div>
                    <p>a<br>b</p>
                    <p>[]c</p>
                    <p>d<br>e</p>
                </div>`
            ),
        });
    });

    test("should isolate a line in an unbreakable block ending with a block (do not wrap said block)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b<br>[]c<br>d<br>e
                    <div>do not wrap</div>
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>a<br>b</p>
                    <p>[]c</p>
                    <p>d<br>e</p>
                    <div>do not wrap</div>
                </div>`
            ),
        });
    });

    test("should isolate a line in an unbreakable block starting and ending with a block (do not wrap said blocks)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    <div>do not wrap</div>
                    a<br>b<br>[]c<br>d<br>e
                    <div>do not wrap</div>
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <div>do not wrap</div>
                    <p>a<br>b</p>
                    <p>[]c</p>
                    <p>d<br>e</p>
                    <div>do not wrap</div>
                </div>`
            ),
        });
    });

    test("should isolate a line in an unbreakable block containing blocks (do not wrap said blocks)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b
                    <div>do not wrap</div>
                    c<br>[]d<br>e
                    <div>do not wrap</div>
                    f<br>g
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    a<br>b
                    <div>do not wrap</div>
                    <p>c</p>
                    <p>[]d</p>
                    <p>e</p>
                    <div>do not wrap</div>
                    f<br>g
                </div>`
            ),
        });
    });

    test("should isolate all lines in an unbreakable block containing blocks (do not wrap said blocks)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    [a<br>b
                    <div>do not wrap</div>
                    c<br>d<br>e
                    <div>do not wrap</div>
                    f<br>g]
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>[a</p>
                    <p>b</p>
                    <div>do not wrap</div>
                    <p>c</p>
                    <p>d</p>
                    <p>e</p>
                    <div>do not wrap</div>
                    <p>f</p>
                    <p>g]</p>
                </div>`
            ),
        });
    });

    test("should isolate all lines in an unbreakable block containing blocks (do not wrap said blocks) (reversed selection)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    ]a<br>b
                    <div>do not wrap</div>
                    c<br>d<br>e
                    <div>do not wrap</div>
                    f<br>g[
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>]a</p>
                    <p>b</p>
                    <div>do not wrap</div>
                    <p>c</p>
                    <p>d</p>
                    <p>e</p>
                    <div>do not wrap</div>
                    <p>f</p>
                    <p>g[</p>
                </div>`
            ),
        });
    });

    test("should not isolate a line in an unbreakable node that doesn't accept paragraph-related elements (inline)", async () => {
        await testEditor({
            contentBefore: `<p>a<br><span class="oe_unbreakable">b<br>[c]<br>d</span><br>e</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p>a<br><span class="oe_unbreakable">b<br>[c]<br>d</span><br>e</p>`,
        });
    });

    test("should not isolate a line in an unbreakable node that doesn't accept paragraph-related elements (paragraph)", async () => {
        await testEditor({
            contentBefore: `<p class="oe_unbreakable">a<br>b<br>[c]<br>d<br>e</p>`,
            stepFunction: splitBlockSegments,
            contentAfter: `<p class="oe_unbreakable">a<br>b<br>[c]<br>d<br>e</p>`,
        });
    });

    test("should isolate a line in an unbreakable block (deep)", async () => {
        await testEditor({
            contentBefore: `<div class="oe_unbreakable"><span>a<br>b<br>[c]<br>d<br>e</span></div>`,
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p><span>a<br>b</span></p>
                    <p><span>[c]</span></p>
                    <p><span>d<br>e</span></p>
                </div>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at start)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b<br>[c<br>d<br>e
                </div>
                <p>
                    f<br>g<br>h]<br>i<br>j
                </p>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>a<br>b</p>
                    <p>[c</p>
                    <p>d</p>
                    <p>e</p>
                </div>
                <p>f</p>
                <p>g</p>
                <p>h]</p>
                <p>i<br>j</p>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at start) (reversed selection)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b<br>]c<br>d<br>e
                </div>
                <p>
                    f<br>g<br>h[<br>i<br>j
                </p>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>a<br>b</p>
                    <p>]c</p>
                    <p>d</p>
                    <p>e</p>
                </div>
                <p>f</p>
                <p>g</p>
                <p>h[</p>
                <p>i<br>j</p>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at end)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>
                    a<br>b<br>[c<br>d<br>e
                </p>
                <div class="oe_unbreakable">
                    f<br>g<br>h]<br>i<br>j
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<p>a<br>b</p>
                <p>[c</p>
                <p>d</p>
                <p>e</p>
                <div class="oe_unbreakable">
                    <p>f</p>
                    <p>g</p>
                    <p>h]</p>
                    <p>i<br>j</p>
                </div>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at end) (reversed selection)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>
                    a<br>b<br>]c<br>d<br>e
                </p>
                <div class="oe_unbreakable">
                    f<br>g<br>h[<br>i<br>j
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<p>a<br>b</p>
                <p>]c</p>
                <p>d</p>
                <p>e</p>
                <div class="oe_unbreakable">
                    <p>f</p>
                    <p>g</p>
                    <p>h[</p>
                    <p>i<br>j</p>
                </div>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at start and end)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b<br>[c<br>d<br>e
                </div>
                <p>
                    f<br>g<br>h<br>i<br>j
                </p>
                <div class="oe_unbreakable">
                    k<br>l<br>m]<br>n<br>o
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>a<br>b</p>
                    <p>[c</p>
                    <p>d</p>
                    <p>e</p>
                </div>
                <p>f</p>
                <p>g</p>
                <p>h</p>
                <p>i</p>
                <p>j</p>
                <div class="oe_unbreakable">
                    <p>k</p>
                    <p>l</p>
                    <p>m]</p>
                    <p>n<br>o</p>
                </div>`
            ),
        });
    });

    test("should isolate lines in and out of an unbreakable block (at start and end) (reversed selection)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<div class="oe_unbreakable">
                    a<br>b<br>]c<br>d<br>e
                </div>
                <p>
                    f<br>g<br>h<br>i<br>j
                </p>
                <div class="oe_unbreakable">
                    k<br>l<br>m[<br>n<br>o
                </div>`
            ),
            stepFunction: splitBlockSegments,
            contentAfter: unformat(
                `<div class="oe_unbreakable">
                    <p>a<br>b</p>
                    <p>]c</p>
                    <p>d</p>
                    <p>e</p>
                </div>
                <p>f</p>
                <p>g</p>
                <p>h</p>
                <p>i</p>
                <p>j</p>
                <div class="oe_unbreakable">
                    <p>k</p>
                    <p>l</p>
                    <p>m[</p>
                    <p>n<br>o</p>
                </div>`
            ),
        });
    });
});
