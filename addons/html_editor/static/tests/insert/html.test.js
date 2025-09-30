import { parseHTML } from "@html_editor/utils/html";
import { describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { setupEditor, testEditor } from "../_helpers/editor";
import { unformat } from "../_helpers/format";
import { getContent } from "../_helpers/selection";
import { cleanHints } from "../_helpers/dispatch";
import { MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { addStep } from "../_helpers/user_actions";
import { Plugin } from "@html_editor/plugin";

function span(text) {
    const span = document.createElement("span");
    span.innerText = text;
    span.classList.add("a");
    return span;
}

const insertHTML = (html) => (editor) => {
    editor.shared.dom.insert(parseHTML(editor.document, html));
    editor.shared.history.addStep();
};

describe("collapsed selection", () => {
    test("should insert html in an empty paragraph / empty editable", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]</p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]</p>',
        });
    });

    test("should insert html after an empty paragraph", async () => {
        await testEditor({
            // This scenario is only possible with the allowInlineAtRoot option.
            contentBefore: "<p><br></p>[]",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p><br></p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]',
            contentAfter: '<p><br></p><i class="fa fa-pastafarianism"></i>[]',
            config: { allowInlineAtRoot: true },
        });
    });

    test("should insert html between two letters", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]b</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b</p>',
        });
    });

    test("should insert html in between naked text in the editable", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]b</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b</p>',
        });
    });

    test("should insert several html nodes in between naked text in the editable", async () => {
        await testEditor({
            contentBefore: "<p>a[]e<br></p>",
            stepFunction: insertHTML("<p>b</p><p>c</p><p>d</p>"),
            contentAfter: "<p>ab</p><p>c</p><p>d[]e</p>",
        });
    });

    test("should wrap a div block in selection placeholders", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: insertHTML("<div><p>content</p></div>"),
            contentAfterEdit:
                '<p data-selection-placeholder=""><br></p><div><p>content[]</p></div><p data-selection-placeholder=""><br></p>',
            contentAfter: "<div><p>content[]</p></div>",
        });
    });

    test("should not split a pre to insert another pre but just insert the text", async () => {
        await testEditor({
            contentBefore: "<pre>abc[]<br>ghi</pre>",
            stepFunction: insertHTML("<pre>def</pre>"),
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
                insertHTML("<p>def</p>")(editor);
            },
            contentAfter: "<p>content</p><p>def[]</p>",
        });
    });

    test("should not unwrap nodes if the selection anchorNode is the editable", async () => {
        await testEditor({
            contentBefore: "<p>content</p>",
            stepFunction: async (editor) => {
                editor.shared.selection.setCursorEnd(editor.editable);
                editor.shared.selection.focusEditable();
                await tick();
                insertHTML("<div>abc</div><p>def</p>")(editor);
            },
            contentAfter: "<p>content</p><div>abc</div><p>def[]</p>",
            config: { allowInlineAtRoot: true },
        });
    });

    test('should insert an "empty" block', async () => {
        await testEditor({
            contentBefore: "<p>abcd[]</p>",
            stepFunction: insertHTML("<p>efgh</p><p></p>"),
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
        insertHTML("<table><tbody><tr><td/></tr></tbody></table>")(editor);
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
        insertHTML("<table><tbody><tr><td/></tr></tbody></table>")(editor);
        await tick();
        expect(getContent(editor.editable)).toBe(
            `<p data-selection-placeholder=""><br></p><p class="oe_unbreakable">content</p><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p><table><tbody><tr><td></td></tr></tbody></table><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`
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

        insertHTML("<table><tbody><tr><td/></tr></tbody></table>")(editor);
        expect(getContent(editor.editable)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                `<div><p class="oe_unbreakable" contenteditable="true"><b class="oe_unbreakable">content[]</b><table><tbody><tr><td></td></tr></tbody></table></p></div>` +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("Should ensure a paragraph after an inserted unbreakable (add)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p>`, {});
        insertHTML(`<p class="oe_unbreakable">1</p>`)(editor);
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1[]</p>` +
                '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>'
        );
    });

    test("Should ensure a paragraph after an inserted unbreakable (keep)", async () => {
        const { editor } = await setupEditor(`<p>cont[]</p><p>+</p>`, {});
        insertHTML(`<p class="oe_unbreakable">1</p>`)(editor);
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
        editor.shared.history.addStep();
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">1</p>` +
                `<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>` +
                `<p class="oe_unbreakable">2[]</p>` +
                `<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
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
        insertHTML(`<p>in</p>`)(editor);
        expect(getContent(editor.editable)).toBe(`<p>contin[]ent</p>`);
    });

    test("should unwrap a contenteditable='true' ancestor which is not descendant of a contenteditable='false'", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        insertHTML(`<p contenteditable="true">in</p>`)(editor);
        expect(getContent(editor.editable)).toBe(`<p>contin[]ent</p>`);
    });

    test("should not unwrap a contenteditable='false'", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        insertHTML(`<p contenteditable="false">in</p>`)(editor);
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p contenteditable="false">in</p><p>[]ent</p>`
        );
    });

    test("should not unwrap an unsplittable", async () => {
        const { editor } = await setupEditor(`<p>cont[]ent</p>`, {});
        insertHTML(`<p class="oe_unbreakable">in</p>`)(editor);
        expect(getContent(editor.editable)).toBe(
            `<p>cont</p><p class="oe_unbreakable">in[]</p><p>ent</p>`
        );
    });

    test("should normalize the parent when inserting a single element", async () => {
        const { editor } = await setupEditor(`<p>[]<br></p>`, {});
        editor.shared.dom.insert(
            parseHTML(editor.document, `<p data-oe-protected="true">in</p>`).firstElementChild
        );
        editor.shared.history.addStep();
        cleanHints(editor);
        expect(getContent(editor.editable, { sortAttrs: true })).toBe(
            `<p data-selection-placeholder=""><br></p><p contenteditable="false" data-oe-protected="true">in[]</p><p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>`
        );
    });

    test("insert inline in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        insertHTML(`<span class="a">a</span>`)(editor);
        expect(getContent(el)).toBe(`<p><span class="a">a</span>[]</p>`);
    });

    test("insert inline at the end of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]</p>`);
        insertHTML(`<span class="a">a</span>`)(editor);
        expect(getContent(el)).toBe(`<p>b<span class="a">a</span>[]</p>`);
    });

    test("insert inline at the start of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]b</p>`);
        insertHTML(`<span class="a">a</span>`)(editor);
        expect(getContent(el)).toBe(`<p><span class="a">a</span>[]b</p>`);
    });

    test("insert inline at the middle of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]c</p>`);
        insertHTML(`<span class="a">a</span>`)(editor);
        expect(getContent(el)).toBe(`<p>b<span class="a">a</span>[]c</p>`);
    });

    test("insert block in empty paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]<br></p>`);
        insertHTML(`<div class="oe_unbreakable">a</div>`)(editor);
        cleanHints(editor);
        expect(getContent(el)).toBe(
            '<p data-selection-placeholder=""><br></p>' +
                '<div class="oe_unbreakable">a[]</div>' +
                '<p data-selection-placeholder=""><br></p>'
        );
    });

    test("insert block at the end of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]</p>`);
        insertHTML(`<div class="oe_unbreakable">a</div>`)(editor);
        cleanHints(editor);
        expect(getContent(el)).toBe(
            `<p>b</p><div class="oe_unbreakable">a[]</div><p data-selection-placeholder=""><br></p>`
        );
    });

    test("insert block at the start of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>[]b</p>`);
        insertHTML(`<div class="oe_unbreakable">a</div>`)(editor);
        expect(getContent(el)).toBe(
            `<p data-selection-placeholder=""><br></p><div class="oe_unbreakable">a</div><p>[]b</p>`
        );
    });

    test("insert block at the middle of a paragraph", async () => {
        const { el, editor } = await setupEditor(`<p>b[]c</p>`);
        insertHTML(`<div class="oe_unbreakable">a</div>`)(editor);
        expect(getContent(el)).toBe(`<p>b</p><div class="oe_unbreakable">a</div><p>[]c</p>`);
    });

    test("insert content processed by a plugin", async () => {
        class CustomPlugin extends Plugin {
            static id = "customPlugin";
            static dependencies = ["dom", "selection"];
            resources = {
                before_insert_processors: (container) => {
                    const second = this.editable.querySelector(".second");
                    this.dependencies.selection.setCursorStart(second);
                    container.replaceChildren(parseHTML(this.document, `<p>surprise</p>`));
                    return container;
                },
            };
        }
        const { el, editor } = await setupEditor(
            `<p class="first">[]?</p><p class="second">!</p>`,
            {
                config: {
                    Plugins: [...MAIN_PLUGINS, CustomPlugin],
                },
            }
        );
        editor.shared.dom.insert("notasurprise");
        addStep(editor);
        expect(getContent(el)).toBe(`<p class="first">?</p><p class="second">surprise[]!</p>`);
    });
});

describe("not collapsed selection", () => {
    test("should delete selection and insert html in its place", async () => {
        await testEditor({
            contentBefore: "<p>[a]</p>",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p>\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]</p>',
            contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]</p>',
        });
    });

    test("should delete selection and insert html in its place (2)", async () => {
        await testEditor({
            contentBefore: "<p>a[b]c</p>",
            stepFunction: insertHTML('<i class="fa fa-pastafarianism"></i>'),
            contentAfterEdit:
                '<p>a\ufeff<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>\ufeff[]c</p>',
            contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]c</p>',
        });
    });

    test("should delete selection and insert html in its place (3)", async () => {
        await testEditor({
            contentBefore: "<h1>[abc</h1><p>def]</p>",
            stepFunction: async (editor) => {
                // There's an empty text node after the paragraph:
                editor.editable.lastChild.after(editor.document.createTextNode(""));
                insertHTML("<p>ghi</p><p>jkl</p>")(editor);
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
