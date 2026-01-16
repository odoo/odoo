import { describe, expect, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";
import { setupEditor } from "./_helpers/editor";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";

describe("range collapsed", () => {
    test("should ignore copying an empty selection with empty clipboardData", async () => {
        await setupEditor("<p>[]</p>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        // Check that nothing was set as clipboard content
        expect(clipboardData.types.length).toBe(0);
    });

    test("should ignore copying an empty selection with clipboardData", async () => {
        await setupEditor("<p>[]</p>");
        const clipboardData = new DataTransfer();
        clipboardData.setData("text/plain", "should stay");
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        // Check that clipboard data was not overwritten
        expect(clipboardData.getData("text/plain")).toBe("should stay");
    });
});

describe("range not collapsed", () => {
    test("should copy a selection as text/plain, text/html and application/vnd.odoo.odoo-editor only text", async () => {
        await setupEditor("<p>a[bcd]e</p>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("bcd");
        expect(clipboardData.getData("text/html")).toBe("<p>bcd</p>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("<p>bcd</p>");
    });

    test("should copy a selection as text/plain, text/html and application/vnd.odoo.odoo-editor with a <br>", async () => {
        await setupEditor("<p>[abc<br>efg]</p>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("abc\nefg");
        expect(clipboardData.getData("text/html")).toBe("<p>abc<br>efg</p>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("<p>abc<br>efg</p>");
    });

    test.tags("focus required");
    test("should copy a selection as text/plain, text/html and application/vnd.odoo.odoo-editor in table", async () => {
        await setupEditor(
            `]<table><tbody><tr><td><ul><li>a[</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>`,
            // Exclude the selection placeholder plugin so we have a DOM that
            // really starts with a table.
            { config: { Plugins: MAIN_PLUGINS.filter((p) => p.id !== "selectionPlaceholder") } }
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("a");
        expect(clipboardData.getData("text/html")).toBe(
            "<table><tbody><tr><td><ul><li>a</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>"
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            "<table><tbody><tr><td><ul><li>a</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>"
        );
    });

    test("should copy a selection as text/html and application/vnd.odoo.odoo-editor in table", async () => {
        await setupEditor(
            "<p>[abcd</p><table><tbody><tr><td><br></td><td><br></td></tr></tbody></table>]"
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/html")).toBe(
            "<p>abcd</p><table><tbody><tr><td><br></td><td><br></td></tr></tbody></table>"
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            "<p>abcd</p><table><tbody><tr><td><br></td><td><br></td></tr></tbody></table>"
        );
    });

    test("should wrap the selected text with clones of ancestors up to a block element to keep styles (1)", async () => {
        await setupEditor(
            '<p>[<span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span>]</p>'
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("Test Test");
        expect(clipboardData.getData("text/html")).toBe(
            '<p><span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span></p>'
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            '<p><span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span></p>'
        );
    });

    test("should wrap the selected text with clones of ancestors up to a block element to keep styles (2)", async () => {
        await setupEditor(
            '<p><strong><em><u><font class="text-o-color-1">hello [there]</font></u></em></strong></p>'
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("there");
        expect(clipboardData.getData("text/html")).toBe(
            '<p><strong><em><u><font class="text-o-color-1">there</font></u></em></strong></p>'
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            '<p><strong><em><u><font class="text-o-color-1">there</font></u></em></strong></p>'
        );
    });

    test("should copy the selection as a single list item (1)", async () => {
        await setupEditor("<ul><li>[First]</li><li>Second</li></ul>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("First");
        expect(clipboardData.getData("text/html")).toBe("First");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("First");
    });

    test("should copy the selection as a single list item (2)", async () => {
        await setupEditor("<ul><li>First [List]</li><li>Second</li></ul>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("List");
        expect(clipboardData.getData("text/html")).toBe("List");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("List");
    });

    test("should copy the selection as a single list item (3)", async () => {
        await setupEditor(
            '<ul><li><span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">[First]</font></span></li><li>Second</li></ul>'
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("First");
        expect(clipboardData.getData("text/html")).toBe(
            '<span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">First</font></span>'
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            '<span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">First</font></span>'
        );
    });

    test("should copy the selection as a list with multiple list items", async () => {
        await setupEditor("<ul><li>[First</li><li>Second]</li></ul>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("First\nSecond");
        expect(clipboardData.getData("text/html")).toBe("<ul><li>First</li><li>Second</li></ul>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            "<ul><li>First</li><li>Second</li></ul>"
        );
    });

    test("should remove ufeff characters from link selection", async () => {
        await setupEditor('<p>[<a href="http://test.com/">label</a>]</p>');
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("label");
        expect(clipboardData.getData("text/html")).toBe(
            '<p><a href="http://test.com/">label</a></p>'
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            '<p><a href="http://test.com/">label</a></p>'
        );
    });

    test("should add origin to images urls", async () => {
        await setupEditor('<p>[<img src="/nice.png">]</p>');
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/html")).toBe(
            `<p><img src="${window.location.origin}/nice.png"></p>`
        );
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            `<p><img src="${window.location.origin}/nice.png"></p>`
        );
    });

    test("should not add origin to base64 images", async () => {
        const base64Img =
            "data:image/png;base64, iVBORw0KGgoAAAANSUhEUgAAAAUA\n        AAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO\n            9TXL0Y4OHwAAAABJRU5ErkJggg==";
        await setupEditor(`<p>[<img src="${base64Img}">]</p>`);
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/html")).toBe(`<p><img src="${base64Img}"></p>`);
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe(
            `<p><img src="${base64Img}"></p>`
        );
    });

    test("should copy style and font of ancestors up to a block", async () => {
        await setupEditor("<p>a<b>b[c]d</b>e</p>");
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("c");
        expect(clipboardData.getData("text/html")).toBe("<p><b>c</b></p>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("<p><b>c</b></p>");
    });

    test("should not clone ancestors outside the contenteditable (block)", async () => {
        await setupEditor(
            `<div contenteditable="false"><p contenteditable="true">a<b>b[c]d</b>e</p></div>`
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("c");
        expect(clipboardData.getData("text/html")).toBe("<b>c</b>");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("<b>c</b>");
    });

    test("should not clone ancestors outside the contenteditable (inline)", async () => {
        await setupEditor(
            `<div contenteditable="false"><p>a<b contenteditable="true">b[c]d</b>e</p></div>`
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("c");
        expect(clipboardData.getData("text/html")).toBe("c");
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("c");
    });

    test("should not copy to odoo-editor clipboard when selection is outside the contenteditable", async () => {
        await setupEditor(
            `<div contenteditable="false"><p>a[b<b contenteditable="true">c</b>d]e</p></div>`
        );
        const clipboardData = new DataTransfer();
        await press(["ctrl", "c"], { dataTransfer: clipboardData });
        expect(clipboardData.getData("text/plain")).toBe("bcd");
        expect(clipboardData.getData("text/html")).toBe(`<p>b<b contenteditable="true">c</b>d</p>`);
        expect(clipboardData.getData("application/vnd.odoo.odoo-editor")).toBe("");
        expect(clipboardData.types).not.toInclude("application/vnd.odoo.odoo-editor");
    });
});
