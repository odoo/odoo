import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { dispatchClean } from "../_helpers/dispatch";

function span(text) {
    const span = document.createElement("span");
    span.innerText = text;
    span.classList.add("a");
    return span;
}

describe("collapsed selection", () => {
    test("should insert html in an empty paragraph / empty editable", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
                editor.shared.history.addStep();
            },
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]</p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]</p>',
        });
    });

    test("should insert html after an empty paragraph", async () => {
        await testEditor({
            // This scenario is only possible with the allowInlineAtRoot option.
            contentBefore: "<p><br></p>[]",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
                editor.shared.history.addStep();
            },
            contentAfterEdit:
                '<p><br></p>\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]',
            contentAfter: '<p><br></p><i class="fa fa-pastafarianism"></i>[]',
            config: { allowInlineAtRoot: true },
        });
    });

    test("should insert html between two letters", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
                editor.shared.history.addStep();
            },
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]b</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b</p>',
        });
    });

    test("should insert html in between naked text in the editable", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
                editor.shared.history.addStep();
            },
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]b</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b</p>',
        });
    });

    test("should insert several html nodes in between naked text in the editable", async () => {
        await testEditor({
            contentBefore: "<p>a[]e<br></p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(parseHTML(editor.document, "<p>b</p><p>c</p><p>d</p>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<p>ab</p><p>c</p><p>d[]e</p>",
        });
    });

    test("should keep a paragraph after a div block", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(parseHTML(editor.document, "<div><p>content</p></div>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<div><p>content</p></div><p>[]<br></p>",
        });
    });

    test("should not split a pre to insert another pre but just insert the text", async () => {
        await testEditor({
            contentBefore: "<pre>abc[]<br>ghi</pre>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(parseHTML(editor.document, "<pre>def</pre>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<pre>abcdef[]<br>ghi</pre>",
        });
    });

    test('should keep an "empty" block which contains fontawesome nodes when inserting multiple nodes', async () => {
        await testEditor({
            contentBefore: "<p>content[]</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(
                        editor.document,
                        '<p>unwrapped</p><div><i class="fa fa-circle-o-notch"></i></div><p>culprit</p><p>after</p>'
                    )
                );
                editor.shared.history.addStep();
            },
            contentAfter:
                '<p>contentunwrapped</p><div><i class="fa fa-circle-o-notch"></i></div><p>culprit</p><p>after[]</p>',
        });
    });

    test("should not unwrap single node if the selection anchorNode is the editable", async () => {
        await testEditor({
            contentBefore: "<p>content</p>",
            stepFunction: async (editor) => {
                editor.shared.selection.setCursorEnd(editor.editable, false);
                editor.shared.selection.focusEditable();
                editor.shared.dom.insert(parseHTML(editor.document, "<p>def</p>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<p>content</p><p>def[]</p>",
        });
    });

    test("should not unwrap nodes if the selection anchorNode is the editable", async () => {
        await testEditor({
            contentBefore: "<p>content</p>",
            stepFunction: async (editor) => {
                editor.shared.selection.setCursorEnd(editor.editable, false);
                editor.shared.selection.focusEditable();
                await tick();
                editor.shared.dom.insert(parseHTML(editor.document, "<div>abc</div><p>def</p>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<p>content</p><div>abc</div><p>def[]</p>",
        });
    });

    test('should insert an "empty" block', async () => {
        await testEditor({
            contentBefore: "<p>abcd[]</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(parseHTML(editor.document, "<p>efgh</p><p></p>"));
                editor.shared.history.addStep();
            },
            contentAfter: "<p>abcdefgh</p><p>[]<br></p>",
        });
    });

    test("never unwrap tables in breakable paragrap", async () => {
        // P elements' content can only be "phrasing" content
        // Adding a table within p is not possible
        // We have split the p and insert the table unwrapped in between
        // https://developer.mozilla.org/en-US/docs/Web/HTML/Element/p
        // https://developer.mozilla.org/en-US/docs/Web/HTML/Content_categories#phrasing_content
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        editor.shared.dom.insert(
            parseHTML(editor.document, "<table><tbody><tr><td/></tr></tbody></table>")
        );
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><table><tbody><tr><td></td></tr></tbody></table><p>[]ent</p>`
        );
    });

    test("should not unwrap table in unbreakable paragraph find a suitable spot to insert table element", async () => {
        // P elements' content can only be "phrasing" content
        // Adding a table within an unbreakable p is not possible
        // We have to find a better spot to insert the table
        // https://developer.mozilla.org/en-US/docs/Web/HTML/Element/p
        // https://developer.mozilla.org/en-US/docs/Web/HTML/Content_categories#phrasing_content
        const { editor } = await setupEditor(`<p class="oe_unbreakable">cont[]ent</p>`, {});
        editor.shared.dom.insert(
            parseHTML(editor.document, "<table><tbody><tr><td/></tr></tbody></table>")
        );
        expect(getContent(editor.editable)).toBe(
            `<p class="oe_unbreakable">content[]</p><table><tbody><tr><td></td></tr></tbody></table>`
        );
    });

    test("stops at boundary when inserting unfit content", async () => {
        // P elements' content can only be "phrasing" content
        // This test forces to stop at the <p contenteditable="true" />
        // This test is a bit odd and whitebox but this is because multiple
        // parameters of the use case are interacting
        const { editor } = await setupEditor(
            `<div><p class="oe_unbreakable" contenteditable="true"><b class="oe_unbreakable">cont[]ent</b></p></div>`,
            {}
        );

        editor.shared.dom.insert(
            parseHTML(editor.document, "<table><tbody><tr><td/></tr></tbody></table>")
        );
        expect(getContent(editor.editable)).toBe(
            `<div><p class="oe_unbreakable" contenteditable="true"><b class="oe_unbreakable">content[]</b><table><tbody><tr><td></td></tr></tbody></table></p></div>`
        );
    });

    test("Should ensure a paragraph after an inserted unbreakable (add)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p class="oe_unbreakable">1</p>`));
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1[]</p><p><br></p>`
        );
    });

    test("Should ensure a paragraph after an inserted unbreakable (keep)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p><p>+</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p class="oe_unbreakable">1</p>`));
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1[]</p><p>+</p>`
        );
    });

    test("Should ensure a paragraph after inserting multiple unbreakables (add)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p>`, {});
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                `<p class="oe_unbreakable">1</p><p class="oe_unbreakable">2</p>`
            )
        );
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1</p><p class="oe_unbreakable">2[]</p><p><br></p>`
        );
    });

    test("Should ensure a paragraph after inserting multiple unbreakables (keep)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p><p>+</p>`, {});
        editor.shared.dom.insert(
            parseHTML(
                editor.document,
                `<p class="oe_unbreakable">1</p><p class="oe_unbreakable">2</p>`
            )
        );
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1</p><p class="oe_unbreakable">2[]</p><p>+</p>`
        );
    });

    test("should unwrap a paragraphRelated element inside another", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p>in</p>`));
        expect(getContent(editor.editable)).toBe(`<p>contin[]ent</p>`);
    });

    test("should unwrap a contenteditable='true' ancestor which is not descendant of a contenteditable='false'", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p contenteditable="true">in</p>`));
        expect(getContent(editor.editable)).toBe(`<p>contin[]ent</p>`);
    });

    test("should not unwrap a contenteditable='false'", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p contenteditable="false">in</p>`));
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p contenteditable="false">in</p><p>[]ent</p>`
        );
    });

    test("should not unwrap an unsplittable", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        editor.shared.dom.insert(parseHTML(editor.document, `<p class="oe_unbreakable">in</p>`));
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">in[]</p><p>ent</p>`
        );
    });

    test("should normalize the parent when inserting a single element", async () => {
        const { editor } = await setupEditor(`<p>[]<br></p>`, {});
        editor.shared.dom.insert(
            parseHTML(editor.document, `<p data-oe-protected="true">in</p>`).firstElementChild
        );
        expect(getContent(editor.editable, { sortAttrs: true })).toBe(
            `<p contenteditable="false" data-oe-protected="true">in</p><p>[]<br></p>`
        );
    });

    test("insert inline in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<span class="a">a</span>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p><span class="a">a</span>[]</p>`);
    });

    test("insert inline at the end of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<span class="a">a</span>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>b<span class="a">a</span>[]</p>`);
    });

    test("insert inline at the start of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]b</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<span class="a">a</span>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p><span class="a">a</span>[]b</p>`);
    });

    test("insert inline at the middle of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]c</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<span class="a">a</span>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>b<span class="a">a</span>[]c</p>`);
    });

    test("insert block in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<div class="oe_unbreakable">a</div>`));
        editor.shared.history.addStep();
        dispatchClean(editor);
        expect(getContent(el)).toBe(`<div class="oe_unbreakable">a</div><p>[]<br></p>`);
    });

    test("insert block at the end of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<div class="oe_unbreakable">a</div>`));
        editor.shared.history.addStep();
        dispatchClean(editor);
        expect(getContent(el)).toBe(`<p>b</p><div class="oe_unbreakable">a</div><p>[]<br></p>`);
    });

    test("insert block at the start of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]b</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<div class="oe_unbreakable">a</div>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<div class="oe_unbreakable">a</div><p>[]b</p>`);
    });

    test("insert block at the middle of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]c</p>`);
        editor.shared.dom.insert(parseHTML(editor.document, `<div class="oe_unbreakable">a</div>`));
        editor.shared.history.addStep();
        expect(getContent(el)).toBe(`<p>b</p><div class="oe_unbreakable">a</div><p>[]c</p>`);
    });
});

describe("not collapsed selection", () => {
    test("should delete selection and insert html in its place", async () => {
        await testEditor({
            contentBefore: "<p>[a]</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
            },
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]</p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]</p>',
        });
    });

    test("should delete selection and insert html in its place (2)", async () => {
        await testEditor({
            contentBefore: "<p>a[b]c</p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(editor.document, '<i class="fa fa-pastafarianism"></i>')
                );
                editor.shared.history.addStep();
            },
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]c</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]c</p>',
        });
    });

    test("should delete selection and insert html in its place (3)", async () => {
        await testEditor({
            contentBefore: "<h1>[abc</h1><p>def]</p>",
            stepFunction: async editor => {
                // There's an empty text node after the paragraph:
                editor.editable.lastChild.after(editor.document.createTextNode(""));
                editor.shared.dom.insert(
                    parseHTML(editor.document, "<p>ghi</p><p>jkl</p>")
                );
                editor.shared.history.addStep();
            },
            contentAfter: "<p>ghi</p><p>jkl[]</p>",
        });
    });

    test("should remove a fully selected table then insert a span before it", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: '<p>a<span class="a">TEST</span>[]l</p>',
        });
    });

    test("should only remove the text content of cells in a partly selected table", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td class="o_selected_td">e[f</td><td>gh</td></tr>
                        <tr><td>ij</td><td class="o_selected_td">k]l</td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td><p><span class="a">TEST</span>[]</p></td><td>gh</td></tr>
                        <tr><td>ij</td><td><p><br></p></td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`
            ),
        });
    });

    test("should remove some text and a table (even if the table is partly selected)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>g]h</td><td>ij</td></tr>
                    </tbody></table>
                    <p>kl</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: unformat(
                `<p>a<span class="a">TEST</span>[]</p>
                    <p>kl</p>`
            ),
        });
    });

    test("should remove a table and some text (even if the table is partly selected)", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>ab</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>i[j</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: unformat(
                `<p>ab</p>
                    <p><span class="a">TEST</span>[]l</p>`
            ),
        });
    });

    test("should remove some text, a table and some more text", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: `<p>a<span class="a">TEST</span>[]l</p>`,
        });
    });

    test("should remove a selection of several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<table><tbody>
                        <tr><td>cd</td><td>e[f</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <table><tbody>
                        <tr><td>cd</td><td>e]f</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>`
            ),
            stepFunction: async (editor) => {
                // Table selection happens on selectionchange event which is
                // fired in the next tick.
                await tick();
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: `<p><span class="a">TEST</span>[]</p>`,
        });
    });

    test("should remove a selection including several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>0[1</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>23</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>45</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>67]</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: `<p>0<span class="a">TEST</span>[]</p>`,
        });
    });

    test("should remove everything, including several tables", async () => {
        await testEditor({
            contentBefore: unformat(
                `<p>[01</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>23</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>45</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>67]</p>`
            ),
            stepFunction: (editor) => {
                editor.shared.dom.insert(span("TEST"));
                editor.shared.history.addStep();
            },
            contentAfter: `<p><span class="a">TEST</span>[]</p>`,
        });
    });

    test("should insert html containing ZWNBSP", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                editor.shared.dom.insert(
                    parseHTML(
                        editor.document,
                        '<p>\uFEFF<a href="#">\uFEFFlink\uFEFF</a>\uFEFF</p><p>\uFEFF<a href="#">\uFEFFlink\uFEFF</a>\uFEFF</p>'
                    )
                );
                editor.shared.history.addStep();
            },
            contentAfter: '<p><a href="#">link</a></p><p><a href="#">link</a>[]</p>',
        });
    });
});
