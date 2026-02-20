import { describe, expect, test } from "@odoo/hoot";
import { setupEditor, testEditor } from "./_helpers/editor";
import {
    alignCenter,
    justify,
    alignStart,
    alignEnd,
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

describe("start", () => {
    test("should align start", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: alignStart,
            contentAfter: "<p>ab</p><p>c[]d</p>",
        });
    });

    test("should not align start a non-editable node", async () => {
        await testEditor({
            contentBefore: '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>',
            contentBeforeEdit:
                '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>' +
                '<p data-selection-placeholder=""><br></p>',
            stepFunction: alignStart,
            contentAfterEdit:
                '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>' +
                '<p data-selection-placeholder=""><br></p>',
            contentAfter: '<p>ab</p><div contenteditable="false"><p>c[]d</p></div>',
        });
    });

    test("should align several paragraphs start", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: alignStart,
            contentAfter: "<p>a[b</p><p>c]d</p>",
        });
    });

    test("should start align a node within a right-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: start;">c[d]e</p></div>',
        });
    });

    test("should start align a node within an end-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: start;">c[d]e</p></div>',
        });
    });

    test("should start align a node within a right-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: right;"><p>ab</p><p style="text-align: start;">c[d</p></div><p>e]f</p>',
        });
    });

    test("should start align a node within an end-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: start;">c[d</p></div><p>e]f</p>',
        });
    });

    test("should start align a node within a right-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: right;"><p>ab</p><p style="text-align: start;">c[d</p></div><p style="text-align: start;">e]f</p></div>',
        });
    });

    test("should start align a node within an end-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p style="text-align: start;">c[d</p></div><p style="text-align: start;">e]f</p></div>',
        });
    });

    test("should start align a node within a right-aligned node and a paragraph, with a left-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: left;"><div style="text-align: right;"><p>ab</p><p style="text-align: start;">c[d</p></div><p style="text-align: start;">e]f</p></div>',
        });
    });

    test("should start align a node within an end-aligned node and a paragraph, with a left-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: left;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: left;"><div style="text-align: end;"><p>ab</p><p style="text-align: start;">c[d</p></div><p style="text-align: start;">e]f</p></div>',
        });
    });

    test("should start align a node within an end-aligned node and a paragraph, with a start-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: start;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div style="text-align: start;"><div style="text-align: end;"><p>ab</p><p style="text-align: start;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not start align a node that is already within a start-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: start;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignStart,
            contentAfter: '<div style="text-align: start;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should start align a container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1>a[]b</h1></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: start;">a[]b</h1></div>',
        });
    });

    test("should END align an RTL container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1 dir="rtl">a[]b</h1></div>',
            stepFunction: alignStart,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 dir="rtl" style="text-align: end;">a[]b</h1></div>',
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

    test("should center align a node within an end-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: center;">c[d]e</p></div>',
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

    test("should center align a node within a end-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: center;">c[d</p></div><p style="text-align: center;">e]f</p>',
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

    test("should center align a node within an end-aligned node and a paragraph, with a left-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: left;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: left;"><div style="text-align: end;"><p>ab</p><p style="text-align: center;">c[d</p></div><p style="text-align: center;">e]f</p></div>',
        });
    });

    test("should center align a node within an end-aligned node and a paragraph, with a start-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: start;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: start;"><div style="text-align: end;"><p>ab</p><p style="text-align: center;">c[d</p></div><p style="text-align: center;">e]f</p></div>',
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

    test("should center align a node within an end-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p style="text-align: center;">c[d</p></div><p>e]f</p></div>',
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

    test("should center align a start-aligned container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: start;">a[]b</h1></div>',
            stepFunction: alignCenter,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: center;">a[]b</h1></div>',
        });
    });
});

describe("end", () => {
    test("should align end", async () => {
        await testEditor({
            contentBefore: "<p>ab</p><p>c[]d</p>",
            stepFunction: alignEnd,
            contentAfter: '<p>ab</p><p style="text-align: end;">c[]d</p>',
        });
    });

    test("should align several paragraphs end", async () => {
        await testEditor({
            contentBefore: "<p>a[b</p><p>c]d</p>",
            stepFunction: alignEnd,
            contentAfter: '<p style="text-align: end;">a[b</p><p style="text-align: end;">c]d</p>',
        });
    });

    test("should end align a node within a center-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: center;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div style="text-align: center;"><p>ab</p><p style="text-align: end;">c[d]e</p></div>',
        });
    });

    test("should end align a node within a center-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: alignEnd,
            contentAfter:
                '<div style="text-align: center;"><p>ab</p><p style="text-align: end;">c[d</p></div><p style="text-align: end;">e]f</p>',
        });
    });

    test("should end align a node within a center-aligned node and a paragraph, with a justify-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: justify;"><div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div style="text-align: justify;"><div style="text-align: center;"><p>ab</p><p style="text-align: end;">c[d</p></div><p style="text-align: end;">e]f</p></div>',
        });
    });

    test("should end align a node within a center-aligned node and a paragraph, with a right-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: right;"><div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div style="text-align: right;"><div style="text-align: center;"><p>ab</p><p style="text-align: end;">c[d</p></div><p style="text-align: end;">e]f</p></div>',
        });
    });

    test("should end align a node within a center-aligned node and a paragraph, with an end-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: end;"><div style="text-align: center;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div style="text-align: end;"><div style="text-align: center;"><p>ab</p><p style="text-align: end;">c[d</p></div><p>e]f</p></div>',
        });
    });

    test("should not end align a node that is already within an end-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: alignEnd,
            contentAfter: '<div style="text-align: end;"><p>ab</p><p>c[d]e</p></div>',
        });
    });

    test("should end align a container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1>a[]b</h1></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 style="text-align: end;">a[]b</h1></div>',
        });
    });

    test("should START align an RTL container within an editable that is center-aligned", async () => {
        await testEditor({
            contentBefore:
                '<div contenteditable="true" style="text-align: center;"><h1 dir="rtl">a[]b</h1></div>',
            stepFunction: alignEnd,
            contentAfter:
                '<div contenteditable="true" style="text-align: center;"><h1 dir="rtl" style="text-align: start;">a[]b</h1></div>',
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

    test("should justify align a node within an end-aligned node", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d]e</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: justify;">c[d]e</p></div>',
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

    test("should justify align a node within an end-aligned node and a paragraph", async () => {
        await testEditor({
            contentBefore: '<div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: end;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p style="text-align: justify;">e]f</p>',
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

    test("should justify align a node within an end-aligned node and a paragraph, with a center-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: center;"><div style="text-align: end;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p style="text-align: justify;">e]f</p></div>',
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

    test("should justify align a node within an end-aligned node and a paragraph, with a justify-aligned common ancestor", async () => {
        await testEditor({
            contentBefore:
                '<div style="text-align: justify;"><div style="text-align: end;"><p>ab</p><p>c[d</p></div><p>e]f</p></div>',
            stepFunction: justify,
            contentAfter:
                '<div style="text-align: justify;"><div style="text-align: end;"><p>ab</p><p style="text-align: justify;">c[d</p></div><p>e]f</p></div>',
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
