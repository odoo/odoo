import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import {
    alignCenter,
    justify,
    alignLeft,
    alignRight,
    alignTop,
    alignMiddle,
    alignBottom,
} from "./_helpers/user_actions";
import { expandToolbar } from "./_helpers/toolbar";

test("should have align tool only if the block is content editable", async () => {
    for (const [contenteditable, count] of [
        [false, 0],
        [true, 1],
    ]) {
        await setupEditor(
            `<div contenteditable="${contenteditable}"><p><span contenteditable="true">ab[cde]fg</span></p></div>`
        );
        await expandToolbar();
        expect(".btn[name='text_align']").toHaveCount(count);
    }
});

describe("left", () => {
    test("should align left", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: alignLeft,
            contentAfter: "<p>ab</p><p>c[]d</p>",
        });
    });

    test("should not align left a non-editable node", async () => {
        await testEditor({
            contentBefore: '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>',
            contentBeforeEdit:
                '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>' +
                '<p data-selection-placeholder=""><br></p>',
            stepFunction: alignLeft,
            contentAfterEdit:
                '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>' +
                '<p data-selection-placeholder=""><br></p>',
            contentAfter: '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>',
        });
    });

    test("should align several paragraphs left", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: alignLeft,
            contentAfter: "<p>a[b</p><p>c]d</p>",
        });
    });

    test("should left align a node within a right-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignLeft,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: left;">c[d]e</p></div>',
        });
    });

    test("should left align a node within a right-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignLeft,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: left;">c[d</p></div><p>e]f</p>',
        });
    });

    test("should left align a node within a right-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignLeft,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p style="text-align: left;">c[d</p></div><p style="text-align: left;">e]f</p></div>',
        });
    });

    test("should left align a node within a right-aligned node and a paragraph, with a left-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignLeft,
            contentAfter:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p style="text-align: left;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not left align a node that is already within a left-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: left;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignLeft,
            contentAfter: '<div style="text-align: left;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should left align a container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1>a[]b</h1></div>',
            stepFunction: alignLeft,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: left;">a[]b</h1></div>',
        });
    });
});

describe("center", () => {
    test("should align center", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: alignCenter,
            contentAfter: '<p>ab</p><p style="text-align: center;">c[]d</p>',
        });
    });

    test("should align several paragraphs center", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: alignCenter,
            contentAfter:
                '<p style="text-align: center;">a[b</p><p style="text-align: center;">c]d</p>',
        });
    });

    test("should center align a node within a right-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: center;">c[d]e</p></div>',
        });
    });

    test("should center align a node within a right-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: center;">c[d</p></div><p style="text-align: center;">e]f</p>',
        });
    });

    test("should center align a node within a right-aligned node and a paragraph, with a left-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p style="text-align: center;">c[d</p></div><p style="text-align: center;">e]f</p></div>',
        });
    });

    test("should center align a node within a right-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p style="text-align: center;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not center align a node that is already within a center-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: center;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignCenter,
            contentAfter: '<div style="text-align: center;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should center align a left-aligned container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: left;">a[]b</h1></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: center;">a[]b</h1></div>',
        });
    });
});

describe("right", () => {
    test("should align right", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: alignRight,
            contentAfter: '<p>ab</p><p style="text-align: right;">c[]d</p>',
        });
    });

    test("should align several paragraphs right", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: alignRight,
            contentAfter:
                '<p style="text-align: right;">a[b</p><p style="text-align: right;">c]d</p>',
        });
    });

    test("should right align a node within a center-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: center;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignRight,
            contentAfter:
                '<div style="text-align: center;"><p>ab</p><p style="text-align: right;">c[d]e</p></div>',
        });
    });

    test("should right align a node within a center-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignRight,
            contentAfter:
                '<div style="text-align: center;"><p>ab</p><p style="text-align: right;">c[d</p></div><p style="text-align: right;">e]f</p>',
        });
    });

    test("should right align a node within a center-aligned node and a paragraph, with a justify-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: justify;"><div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignRight,
            contentAfter:
                '<div style="text-align: justify;"><div style="text-align: center;"><p>ab</p><p style="text-align: right;">c[d</p></div><p style="text-align: right;">e]f</p></div>',
        });
    });

    test("should right align a node within a center-aligned node and a paragraph, with a right-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: right;"><div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignRight,
            contentAfter:
                '<div style="text-align: right;"><div style="text-align: center;"><p>ab</p><p style="text-align: right;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not right align a node that is already within a right-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignRight,
            contentAfter: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should right align a container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1>a[]b</h1></div>',
            stepFunction: alignRight,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: right;">a[]b</h1></div>',
        });
    });
});

describe("justify", () => {
    test("should align justify", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: justify,
            contentAfter: '<p>ab</p><p style="text-align: justify;">c[]d</p>',
        });
    });

    test("should align several paragraphs justify", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: justify,
            contentAfter:
                '<p style="text-align: justify;">a[b</p><p style="text-align: justify;">c]d</p>',
        });
    });

    test("should justify align a node within a right-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: justify;">c[d]e</p></div>',
        });
    });

    test("should justify align a node within a right-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p style="text-align: justify;">e]f</p>',
        });
    });

    test("should justify align a node within a right-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p style="text-align: justify;">e]f</p></div>',
        });
    });

    test("should justify align a node within a right-aligned node and a paragraph, with a justify-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: justify;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: justify;"><div style="text-align: right;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not justify align a node that is already within a justify-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: justify;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: justify,
            contentAfter: '<div style="text-align: justify;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should justify align a container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1>a[]b</h1></div>',
            stepFunction: justify,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: justify;">a[]b</h1></div>',
        });
    });
});

describe("top", () => {
    test("should align top a selected cell", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[]b</td></tr></tbody></table>",
            stepFunction: alignTop,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: top;">a[]b</td></tr></tbody></table>',
        });
    });

    test("should align top multiple selected cells", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[b</td><td>c]d</td></tr></tbody></table>",
            stepFunction: alignTop,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: top;">a[b</td><td style="vertical-align: top;">c]d</td></tr></tbody></table>',
        });
    });

    test("should change previous alignment to top", async () => {
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: bottom;">a[b</td>
                            <td style="vertical-align: middle;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: alignTop,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: top;">a[b</td>
                            <td style="vertical-align: top;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
});

describe("middle", () => {
    test("should align middle a selected cell", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[b]c</td></tr></tbody></table>",
            stepFunction: alignMiddle,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: middle;">a[b]c</td></tr></tbody></table>',
        });
    });

    test("should align middle multiple selected cells", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[b</td><td>c]d</td></tr></tbody></table>",
            stepFunction: alignMiddle,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: middle;">a[b</td><td style="vertical-align: middle;">c]d</td></tr></tbody></table>',
        });
    });

    test("should change previous alignment to middle", async () => {
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: top;">a[b</td>
                            <td style="vertical-align: bottom;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: alignMiddle,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: middle;">a[b</td>
                            <td style="vertical-align: middle;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
});

describe("bottom", () => {
    test("should align bottom a selected cell", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[b]c</td></tr></tbody></table>",
            stepFunction: alignBottom,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: bottom;">a[b]c</td></tr></tbody></table>',
        });
    });

    test("should align bottom multiple selected cells", async () => {
        await testEditor({
            contentBefore: "<table><tbody><tr><td>a[b</td><td>c]d</td></tr></tbody></table>",
            stepFunction: alignBottom,
            contentAfter:
                '<table><tbody><tr><td style="vertical-align: bottom;">a[b</td><td style="vertical-align: bottom;">c]d</td></tr></tbody></table>',
        });
    });

    test("should change previous alignment to bottom", async () => {
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: top;">a[b</td>
                            <td style="vertical-align: middle;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: alignBottom,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td style="vertical-align: bottom;">a[b</td>
                            <td style="vertical-align: bottom;">c]d</td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
});
