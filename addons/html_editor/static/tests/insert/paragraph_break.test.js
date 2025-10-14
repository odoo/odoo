import { beforeEach, describe, test } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { tick } from "@odoo/hoot-mock";
import { testEditor } from "../_helpers/editor";
import { insertText, splitBlock } from "../_helpers/user_actions";
import { unformat } from "../_helpers/format";
import { EMBEDDED_COMPONENT_PLUGINS, MAIN_PLUGINS } from "@html_editor/plugin_sets";
import { QWebPlugin } from "@html_editor/others/qweb_plugin";
import { findInSelection } from "@html_editor/utils/selection";
import {
    compareHighlightedContent,
    highlightedPre,
    patchPrism,
} from "../_helpers/syntax_highlighting";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

describe("Selection collapsed", () => {
    describe("Basic", () => {
        test("should duplicate an empty paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]<br></p>",
            });
            // TODO this cannot actually be tested currently as a
            // backspace/delete in that case is not even detected
            // (no input event to rollback)
            // await testEditor({
            //     contentBefore: '<p>[<br>]</p>',
            //     stepFunction: splitBlock,
            //     contentAfter: '<p><br></p><p>[]<br></p>',
            // });
            await testEditor({
                contentBefore: "<p><br>[]</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]<br></p>",
            });
        });

        test("should insert an empty paragraph before a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>[]abc</p>",
                stepFunction: splitBlock,
                contentAfter: "<p><br></p><p>[]abc</p>",
            });
            await testEditor({
                contentBefore: "<p>[] abc</p>",
                stepFunction: splitBlock,
                // JW cAfter: '<p><br></p><p>[]abc</p>',
                contentAfter: "<p><br></p><p>[] abc</p>",
            });
        });

        test("should split a paragraph in two", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: splitBlock,
                contentAfter: "<p>ab</p><p>[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab []cd</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p>ab&nbsp;</p><p>[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab[] cd</p>",
                stepFunction: splitBlock,
                // The space is converted to a non-breaking
                // space so it is visible.
                contentAfter: "<p>ab</p><p>[]&nbsp;cd</p>",
            });
        });

        test("should insert an empty paragraph after a paragraph", async () => {
            await testEditor({
                contentBefore: "<p>abc[]</p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p>[]<br></p>",
            });
            await testEditor({
                contentBefore: "<p>abc[] </p>",
                stepFunction: splitBlock,
                contentAfter: "<p>abc</p><p>[]<br></p>",
            });
        });
        test("should split block without afecting the uploaded document link", async () => {
            await testEditor({
                contentBefore: `<p>abc<a href="#" title="document" data-mimetype="application/pdf" class="o_image"></a>[]def</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>abc<a href="#" title="document" data-mimetype="application/pdf" class="o_image"></a></p><p>[]def</p>`,
            });
        });
        test("should split block without afecting the uploaded document link (2)", async () => {
            await testEditor({
                contentBefore: `<p>abc<a href="#" title="document" data-mimetype="application/pdf" class="o_image"></a>[]</p>`,
                stepFunction: splitBlock,
                contentAfter: `<p>abc<a href="#" title="document" data-mimetype="application/pdf" class="o_image"></a></p><p>[]<br></p>`,
            });
        });
        test("should not split block with conditional template", async () => {
            await testEditor({
                contentBefore: unformat(`
                    <h1 t-if="true">
                        <t t-out="Hello"></t>
                        []<t t-out="World"></t>
                    </h1>
                `),
                stepFunction: splitBlock,
                contentAfter: unformat(`
                    <h1 t-if="true">
                        <t t-out="Hello"></t>
                        <br>
                        []<t t-out="World"></t>
                    </h1>
                `),
                config: { Plugins: [...MAIN_PLUGINS, QWebPlugin] },
            });
        });
    });

    describe("Pre", () => {
        describe("with syntax highlighting", () => {
            const configWithEmbeddings = {
                Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
                resources: { embedded_components: MAIN_EMBEDDINGS },
            };
            const testEnterInCodeBlock = (selectionStart) => async (editor) => {
                // Set the given selection in the textarea.
                const textarea = editor.editable.querySelector("textarea");
                textarea.focus();
                textarea.setSelectionRange(selectionStart, selectionStart, "forward");
                // Trigger native paragraph break.
                await editor.document.execCommand("insertParagraph", false, null);
                // Wait for the input event to resolve so the content is
                // highlighted and the focus is in the textarea.
                await animationFrame();
            };

            beforeEach(patchPrism);

            test("should insert a line break within the pre", async () => {
                await testEditor({
                    compareFunction: compareHighlightedContent,
                    contentBefore: "<pre>abcd</pre>",
                    contentBeforeEdit:
                        '<p data-selection-placeholder=""><br></p>' +
                        highlightedPre({ value: "abcd" }) +
                        '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                    stepFunction: testEnterInCodeBlock(2), // "ab[]cd"
                    contentAfterEdit:
                        '<p data-selection-placeholder=""><br></p>' +
                        highlightedPre({
                            value: "ab\ncd",
                            textareaRange: 3, // "ab\n[]cd"
                        }) +
                        '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                    contentAfter: `<pre data-language-id="plaintext">ab<br>cd</pre>[]`,
                    config: configWithEmbeddings,
                });
            });
            test("should insert a new line at the end of the pre", async () => {
                await testEditor({
                    compareFunction: compareHighlightedContent,
                    contentBefore: "<pre>abc</pre>",
                    contentBeforeEdit:
                        '<p data-selection-placeholder=""><br></p>' +
                        highlightedPre({ value: "abc" }) +
                        '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                    stepFunction: testEnterInCodeBlock(3), // "abc[]"
                    contentAfterEdit:
                        '<p data-selection-placeholder=""><br></p>' +
                        highlightedPre({
                            value: "abc\n",
                            preHtml: "abc<br><br>",
                            textareaRange: 4, // "abc\n[]"
                        }) +
                        '<p data-selection-placeholder="" style="margin: -9px 0px 8px;"><br></p>',
                    contentAfter: `<pre data-language-id="plaintext">abc<br><br></pre>[]`,
                    config: configWithEmbeddings,
                });
            });
        });
        describe("without syntax highlighting", () => {
            test("should insert a line break within the pre", async () => {
                await testEditor({
                    contentBefore: "<pre>ab[]cd</pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre>ab<br>[]cd</pre>",
                });
            });
            test("should insert a line break within the pre containing inline element", async () => {
                await testEditor({
                    contentBefore: "<pre>a<strong>b[]c</strong>d</pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre>a<strong>b<br>[]c</strong>d</pre>",
                });
            });
            test("should insert a line break within the pre containing inline elementd", async () => {
                await testEditor({
                    contentBefore: "<pre><em>a<strong>b[]c</strong>d</em></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre><em>a<strong>b<br>[]c</strong>d</em></pre>",
                });
            });

            test("should insert a new paragraph after the pre", async () => {
                await testEditor({
                    contentBefore: "<pre>abc[]</pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre>abc</pre><p>[]<br></p>",
                });
            });
            test("should insert a new paragraph after the pre containing inline element", async () => {
                await testEditor({
                    contentBefore: "<pre>ab<strong>c[]</strong></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre>ab<strong>c</strong></pre><p>[]<br></p>",
                });
            });
            test("should insert a new paragraph after the pre containing inline elements", async () => {
                await testEditor({
                    contentBefore: "<pre><em>ab<strong>c[]</strong></em></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre><em>ab<strong>c</strong></em></pre><p>[]<br></p>",
                });
            });

            test("should be able to break out of an empty pre", async () => {
                await testEditor({
                    contentBefore: "<pre>[]<br></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre><br></pre><p>[]<br></p>",
                });
            });
            test("should insert a new line within the pre", async () => {
                await testEditor({
                    contentBefore: "<pre><p>abc</p><p>def[]</p></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre><p>abc</p><p>def</p><p>[]<br></p></pre>",
                });
            });
            test("should insert a new line after pre", async () => {
                await testEditor({
                    contentBefore: "<pre><p>abc</p><p>def</p><p>[]<br></p></pre>",
                    stepFunction: splitBlock,
                    contentAfter: "<pre><p>abc</p><p>def</p></pre><p>[]<br></p>",
                });
            });
            test("should insert a new paragraph after a pre tag with rtl direction", async () => {
                await testEditor({
                    contentBefore: `<pre dir="rtl">ab[]</pre>`,
                    stepFunction: splitBlock,
                    contentAfter: `<pre dir="rtl">ab</pre><p dir="rtl">[]<br></p>`,
                });
            });
            test("should insert a new paragraph after a pre tag with rtl direction (2)", async () => {
                await testEditor({
                    contentBefore: `<pre><p dir="rtl">abc</p><p dir="rtl">[]<br></p></pre>`,
                    stepFunction: splitBlock,
                    contentAfter: `<pre><p dir="rtl">abc</p></pre><p dir="rtl">[]<br></p>`,
                });
            });
        });

        describe("Consecutive", () => {
            test("should duplicate an empty paragraph twice", async () => {
                await testEditor({
                    contentBefore: "<p>[]<br></p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p><br></p><p><br></p><p>[]<br></p>",
                });
                // TODO this cannot actually be tested currently as a
                // backspace/delete in that case is not even detected
                // (no input event to rollback)
                // await testEditor({
                //     contentBefore: '<p>[<br>]</p>',
                //     stepFunction: async (editor) => {
                //         splitBlock(editor);
                //         splitBlock(editor);
                //     },
                //     contentAfter: '<p><br></p><p><br></p><p>[]<br></p>',
                // });
                await testEditor({
                    contentBefore: "<p><br>[]</p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p><br></p><p><br></p><p>[]<br></p>",
                });
            });

            test("should insert two empty paragraphs before a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>[]abc</p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p><br></p><p><br></p><p>[]abc</p>",
                });
            });

            test("should split a paragraph in three", async () => {
                await testEditor({
                    contentBefore: "<p>ab[]cd</p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p>ab</p><p><br></p><p>[]cd</p>",
                });
            });

            test("should split a paragraph in four", async () => {
                await testEditor({
                    contentBefore: "<p>ab[]cd</p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p>ab</p><p><br></p><p><br></p><p>[]cd</p>",
                });
            });

            test("should insert two empty paragraphs after a paragraph", async () => {
                await testEditor({
                    contentBefore: "<p>abc[]</p>",
                    stepFunction: async (editor) => {
                        splitBlock(editor);
                        splitBlock(editor);
                    },
                    contentAfter: "<p>abc</p><p><br></p><p>[]<br></p>",
                });
            });
        });

        describe("Format", () => {
            test("should split a paragraph before a format node", async () => {
                await testEditor({
                    contentBefore: "<p>abc[]<b>def</b></p>",
                    stepFunction: splitBlock,
                    contentAfter: "<p>abc</p><p><b>[]def</b></p>",
                });
                await testEditor({
                    // That selection is equivalent to []<b>
                    contentBefore: "<p>abc<b>[]def</b></p>",
                    stepFunction: splitBlock,
                    contentAfter: "<p>abc</p><p><b>[]def</b></p>",
                });
                await testEditor({
                    contentBefore: "<p>abc <b>[]def</b></p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible (because it's after a
                    // <br>).
                    contentAfter: "<p>abc&nbsp;</p><p><b>[]def</b></p>",
                });
                await testEditor({
                    contentBefore: "<p>abc<b>[] def </b></p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible (because it's before a
                    // <br>).
                    // JW cAfter: '<p>abc</p><p><b>[]&nbsp;def</b></p>',
                    contentAfter: "<p>abc</p><p><b>[]&nbsp;def </b></p>",
                });
            });

            test("should split a paragraph after a format node", async () => {
                await testEditor({
                    contentBefore: "<p><b>abc</b>[]def</p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: "<p><b>abc</b></p><p>[]def</p>",
                    contentAfter: "<p><b>abc</b></p><p>[]def</p>",
                });
                await testEditor({
                    // That selection is equivalent to </b>[]
                    contentBefore: "<p><b>abc[]</b>def</p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b>abc</b></p><p><b data-oe-zws-empty-inline="">[]\u200b</b>def</p>`,
                    contentAfter: "<p><b>abc</b></p><p>[]def</p>",
                });
                await testEditor({
                    contentBefore: "<p><b>abc[]</b> def</p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible.
                    contentAfterEdit: `<p><b>abc</b></p><p><b data-oe-zws-empty-inline="">[]\u200b</b>&nbsp;def</p>`,
                    contentAfter: "<p><b>abc</b></p><p>[]&nbsp;def</p>",
                });
                await testEditor({
                    contentBefore: "<p><b>abc []</b>def</p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible (because it's before a
                    // <br>).
                    contentAfterEdit: `<p><b>abc&nbsp;</b></p><p><b data-oe-zws-empty-inline="">[]\u200b</b>def</p>`,
                    contentAfter: "<p><b>abc&nbsp;</b></p><p>[]def</p>",
                });
            });

            test("should split a paragraph at the beginning of a format node", async () => {
                await testEditor({
                    contentBefore: "<p>[]<b>abc</b></p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b data-oe-zws-empty-inline="">\u200b</b></p><p><b>[]abc</b></p>`,
                    contentAfter: "<p><br></p><p><b>[]abc</b></p>",
                });
                await testEditor({
                    contentBefore: "<p><b>[]abc</b></p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b data-oe-zws-empty-inline="">\u200b</b></p><p><b>[]abc</b></p>`,
                    contentAfter: "<p><br></p><p><b>[]abc</b></p>",
                });
                await testEditor({
                    contentBefore: "<p><b>[] abc</b></p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b data-oe-zws-empty-inline="">\u200b</b></p><p><b>[] abc</b></p>`,
                    // The space should have been parsed away.
                    // JW cAfter: '<p><br></p><p><b>[]abc</b></p>',
                    contentAfter: "<p><br></p><p><b>[] abc</b></p>",
                });
            });

            test("should split a paragraph within a format node", async () => {
                await testEditor({
                    contentBefore: "<p><b>ab[]cd</b></p>",
                    stepFunction: splitBlock,
                    contentAfter: "<p><b>ab</b></p><p><b>[]cd</b></p>",
                });
                await testEditor({
                    contentBefore: "<p><b>ab []cd</b></p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible.
                    contentAfter: "<p><b>ab&nbsp;</b></p><p><b>[]cd</b></p>",
                });
                await testEditor({
                    contentBefore: "<p><b>ab[] cd</b></p>",
                    stepFunction: splitBlock,
                    // The space is converted to a non-breaking
                    // space so it is visible.
                    contentAfter: "<p><b>ab</b></p><p><b>[]&nbsp;cd</b></p>",
                });
            });

            test("should split a paragraph at the end of a format node", async () => {
                await testEditor({
                    contentBefore: "<p><b>abc</b>[]</p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b>abc</b></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><b data-oe-zws-empty-inline="">[]\u200b</b></p>`,
                    contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
                });
                await testEditor({
                    // That selection is equivalent to </b>[]
                    contentBefore: "<p><b>abc[]</b></p>",
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><b>abc</b></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><b data-oe-zws-empty-inline="">[]\u200b</b></p>`,
                    contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
                });
                await testEditor({
                    contentBefore: "<p><b>abc[] </b></p>",
                    stepFunction: splitBlock,
                    // The space should have been parsed away.
                    contentAfterEdit: `<p><b>abc</b></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><b data-oe-zws-empty-inline="">[]\u200b</b></p>`,
                    contentAfter: "<p><b>abc</b></p><p>[]<br></p>",
                });
            });

            async function splitBlockA(editor) {
                // splitBlock in an <a> tag will open the linkPopover which will take the focus.
                // So we need to wait for it to open and put the selection back into the editor.
                splitBlock(editor);
                const editableSelection =
                    editor.shared.selection.getSelectionData().editableSelection;
                if (findInSelection(editableSelection, "a:not([href])")) {
                    await waitFor(".o-we-linkpopover");
                }
                editor.shared.selection.focusEditable();
                await tick();
            }

            // @todo: re-evaluate this possibly outdated comment:
            // skipping these tests cause with the link isolation the cursor can be put
            // inside/outside the link so the user can choose where to insert the line break
            // see `anchor.nodeName === "A" && brEls.includes(anchor.firstChild)` in line_break_plugin.js
            test("should insert line breaks outside the edges of an anchor in unbreakable", async () => {
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable">ab<a href="http://test.test/">[]cd</a></div>`,
                    stepFunction: splitBlockA,
                    contentAfter: `<div class="oe_unbreakable">ab<br><a href="http://test.test/">[]cd</a></div>`,
                });
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable"><a href="http://test.test/">a[]b</a></div>`,
                    stepFunction: splitBlockA,
                    contentAfter: `<div class="oe_unbreakable"><a href="http://test.test/">a<br>[]b</a></div>`,
                });
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable"><a href="http://test.test/">ab[]</a></div>`,
                    stepFunction: splitBlockA,
                    contentAfter: `<div class="oe_unbreakable"><a href="http://test.test/">ab</a><br><br>[]</div>`,
                });
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable"><a href="http://test.test/">ab[]</a>cd</div>`,
                    stepFunction: splitBlockA,
                    contentAfter: `<div class="oe_unbreakable"><a href="http://test.test/">ab</a><br>[]cd</div>`,
                });
                await testEditor({
                    contentBefore: `<div class="oe_unbreakable"><a href="http://test.test/" style="display: block;">ab[]</a></div>`,
                    stepFunction: splitBlockA,
                    contentAfter: `<div class="oe_unbreakable"><a href="http://test.test/" style="display: block;">ab</a>[]<br></div>`,
                });
            });

            test("should insert a paragraph break outside the starting edge of an anchor at start of block", async () => {
                await testEditor({
                    contentBefore: '<p><a href="http://test.test/">[]ab</a></p>',
                    stepFunction: splitBlockA,
                    contentAfterEdit:
                        '<p><br></p><p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]ab\ufeff</a>\ufeff</p>',
                    contentAfter: '<p><br></p><p><a href="http://test.test/">[]ab</a></p>',
                });
            });
            test("should insert a paragraph break outside the starting edge of an anchor after some text", async () => {
                await testEditor({
                    contentBefore: '<p>ab<a href="http://test.test/">[]cd</a></p>',
                    stepFunction: splitBlockA,
                    contentAfterEdit:
                        '<p>ab</p><p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]cd\ufeff</a>\ufeff</p>',
                    contentAfter: '<p>ab</p><p><a href="http://test.test/">[]cd</a></p>',
                });
            });
            test("should insert a paragraph break in the middle of an anchor", async () => {
                await testEditor({
                    contentBefore: '<p><a href="http://test.test/">a[]b</a></p>',
                    stepFunction: splitBlockA,
                    contentAfterEdit:
                        '<p>\ufeff<a href="http://test.test/">\ufeffa\ufeff</a>\ufeff</p><p>\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]b\ufeff</a>\ufeff</p>',
                    contentAfter:
                        '<p><a href="http://test.test/">a</a></p><p><a href="http://test.test/">[]b</a></p>',
                });
            });
            test("should insert a paragraph break outside the ending edge of an anchor", async () => {
                await testEditor({
                    contentBefore: '<p><a href="http://test.test/">ab[]</a></p>',
                    stepFunction: splitBlockA,
                    contentAfterEdit: `<p>\ufeff<a href="http://test.test/">\ufeffab\ufeff</a>\ufeff</p><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                    contentAfter: `<p><a href="http://test.test/">ab</a></p><p>[]<br></p>`,
                });
            });
            test("should insert a paragraph break outside the ending edge of an anchor (2)", async () => {
                await testEditor({
                    contentBefore: '<p><a href="http://test.test/">ab[]</a>cd</p>',
                    stepFunction: splitBlockA,
                    contentAfterEdit:
                        '<p>\ufeff<a href="http://test.test/">\ufeffab\ufeff</a>\ufeff</p><p>[]cd</p>',
                    contentAfter: '<p><a href="http://test.test/">ab</a></p><p>[]cd</p>',
                });
            });
        });

        describe("With attributes", () => {
            test("should insert an empty paragraph before a paragraph with a span with a class", async () => {
                await testEditor({
                    contentBefore:
                        '<p><span class="a">ab</span></p><p><span class="b">[]cd</span></p>',
                    stepFunction: splitBlock,
                    contentAfter:
                        '<p><span class="a">ab</span></p><p><span class="b">\u200b</span><br></p><p><span class="b">[]cd</span></p>',
                });
            });

            test("should split a paragraph with a span with a bold in two", async () => {
                await testEditor({
                    contentBefore: '<p><span class="a"><b>ab[]cd</b></span></p>',
                    stepFunction: splitBlock,
                    contentAfter:
                        '<p><span class="a"><b>ab</b></span></p><p><span class="a"><b>[]cd</b></span></p>',
                });
            });

            test("should split a paragraph at its end, with a paragraph after it, and both have the same class", async () => {
                await testEditor({
                    contentBefore: '<p class="a">a[]</p><p class="a"><br></p>',
                    stepFunction: splitBlock,
                    contentAfter: '<p class="a">a</p><p class="a">[]<br></p><p class="a"><br></p>',
                });
            });
        });

        describe("POC extra tests", () => {
            test("should insert a paragraph after an empty h1", async () => {
                await testEditor({
                    contentBefore: "<h1>[]<br></h1>",
                    stepFunction: splitBlock,
                    contentAfter: "<h1><br></h1><p>[]<br></p>",
                });
            });

            test("should insert a paragraph after an empty h1 with styles and a zero-width space", async () => {
                await testEditor({
                    contentBefore:
                        '<h1><font style="color: red;" data-oe-zws-empty-inline="">[]\u200B</font></h1>',
                    stepFunction: splitBlock,
                    contentAfterEdit:
                        '<h1><font style="color: red;" data-oe-zws-empty-inline="">\u200b</font></h1>' +
                        `<p o-we-hint-text='Type "/" for commands' class="o-we-hint"><font style="color: red;" data-oe-zws-empty-inline="">[]\u200b</font></p>`,
                    contentAfter: "<h1><br></h1><p>[]<br></p>",
                });
            });

            test("should insert a new paragraph after an h1 with style", async () => {
                await testEditor({
                    contentBefore: `<h1 style="color: red">ab[]</h1>`,
                    stepFunction: splitBlock,
                    contentAfterEdit: `<h1 style="color: red">ab</h1><p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]<br></p>`,
                    contentAfter: `<h1 style="color: red">ab</h1><p>[]<br></p>`,
                });
            });
            test("should insert a new paragraph after a heading tag with rtl direction", async () => {
                await testEditor({
                    contentBefore: `<h1 dir="rtl">ab[]</h1>`,
                    stepFunction: splitBlock,
                    contentAfter: `<h1 dir="rtl">ab</h1><p dir="rtl">[]<br></p>`,
                });
            });
        });
        describe("Styles", () => {
            test("should split a paragraph at the end of style node", async () => {
                await testEditor({
                    contentBefore: '<p><font style="color: red;">abc[]</font></p>',
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><font style="color: red;">abc</font></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><font style="color: red;" data-oe-zws-empty-inline="">[]\u200b</font></p>`,
                    contentAfter: `<p><font style="color: red;">abc</font></p><p>[]<br></p>`,
                });
                await testEditor({
                    contentBefore: '<p><font style="background-color: red;">abc[]</font></p>',
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><font style="background-color: red;">abc</font></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><font style="background-color: red;" data-oe-zws-empty-inline="">[]\u200b</font></p>`,
                    contentAfter: `<p><font style="background-color: red;">abc</font></p><p>[]<br></p>`,
                });
                await testEditor({
                    contentBefore: '<p><span style="font-size: 36px;">abc[]</span></p>',
                    stepFunction: splitBlock,
                    contentAfterEdit: `<p><span style="font-size: 36px;">abc</span></p><p o-we-hint-text='Type "/" for commands' class="o-we-hint"><span style="font-size: 36px;" data-oe-zws-empty-inline="">[]\u200b</span></p>`,
                    contentAfter: `<p><span style="font-size: 36px;">abc</span></p><p>[]<br></p>`,
                });
            });
        });
    });
});

describe("Selection not collapsed", () => {
    test("should delete the first half of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[ab]cd</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]cd</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>]ab[cd</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]cd</p>",
        });
    });

    test("should delete part of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>a[bc]d</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>a</p><p>[]d</p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>a]bc[d</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>a</p><p>[]d</p>",
        });
    });

    test("should delete the last half of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>ab[cd]</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>ab</p><p>[]<br></p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>ab]cd[</p>",
            stepFunction: splitBlock,
            contentAfter: "<p>ab</p><p>[]<br></p>",
        });
    });

    test("should delete all contents of a paragraph, then split it", async () => {
        // Forward selection
        await testEditor({
            contentBefore: "<p>[abcd]</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]<br></p>",
        });
        // Backward selection
        await testEditor({
            contentBefore: "<p>]abcd[</p>",
            stepFunction: splitBlock,
            contentAfter: "<p><br></p><p>[]<br></p>",
        });
    });

    test("should keep the selection at the start of the second text node after paragraph break", async () => {
        await testEditor({
            contentBefore: "<p>ab<br>[c]de</p>",
            stepFunction: async (editor) => {
                await insertText(editor, "f");
            },
            contentAfter: "<p>ab<br>f[]de</p>",
        });
    });
});

describe("Table", () => {
    test("should remove all contents of an anchor td and split paragraph on forward selection", async () => {
        // Forward selection
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>[abc</p><p>def</p></td>
                            <td><p>abcd</p></td>
                            <td><p>ab]</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: splitBlock,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td><p><br></p><p>[]<br></p></td>
                            <td><p>abcd</p></td>
                            <td><p>ab</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
    test("should remove all contents of an anchor td and split paragraph on backward selection", async () => {
        // Backward selection
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>]ab</p></td>
                            <td><p>abcd</p></td>
                            <td><p>abc</p><p>def[</p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: splitBlock,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>ab</p></td>
                            <td><p>abcd</p></td>
                            <td><p><br></p><p>[]<br></p></td>
                        </tr>
                        <tr>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
    test("remove selected text and insert paragraph tag within a table cell and enter key is pressed", async () => {
        await testEditor({
            contentBefore: `
                <table>
                    <tbody>
                        <tr>
                            <td><p>[Test</p><p>Test</p><p>Test]</p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
            stepFunction: splitBlock,
            contentAfter: `
                <table>
                    <tbody>
                        <tr>
                            <td><p><br></p><p>[]<br></p></td>
                            <td><p><br></p></td>
                        </tr>
                    </tbody>
                </table>`,
        });
    });
});
