import { CLIPBOARD_WHITELISTS } from "@html_editor/core/clipboard_plugin";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { manuallyDispatchProgrammaticEvent as dispatch, press, waitFor } from "@odoo/hoot-dom";
import { animationFrame, tick } from "@odoo/hoot-mock";
import { dataURItoBlob, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { setupEditor, testEditor } from "./_helpers/editor";
import { cleanLinkArtifacts, unformat } from "./_helpers/format";
import { getContent, setSelection } from "./_helpers/selection";
import { pasteHtml, pasteOdooEditorHtml, pasteText, undo } from "./_helpers/user_actions";
import { createBaseContainer } from "@html_editor/utils/base_container";
import { expectElementCount } from "./_helpers/ui_expectations";
import {
    EMBEDDED_COMPONENT_PLUGINS,
    MAIN_PLUGINS,
    NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS,
} from "@html_editor/plugin_sets";
import { MAIN_EMBEDDINGS } from "@html_editor/others/embedded_components/embedding_sets";

function isInline(node) {
    return ["I", "B", "U", "S", "EM", "STRONG", "IMG", "BR", "A", "FONT"].includes(node);
}

function toIgnore(node) {
    return ["TABLE", "THEAD", "TH", "TBODY", "TR", "TD", "IMG", "BR", "LI", ".FA"].includes(node);
}

describe("Html Paste cleaning - whitelist", () => {
    test("should keep whitelisted Tags tag", async () => {
        const baseContainer = createBaseContainer("DIV");
        const baseContainerString = `${baseContainer.nodeName}`;
        const agg = [baseContainerString];
        const baseContainerClass = baseContainer.className;
        if (baseContainerClass) {
            agg.push(`class="${baseContainerClass}"`);
        }
        const baseContainerNode = agg.join(" ");
        for (const node of [...CLIPBOARD_WHITELISTS.nodes, baseContainerNode]) {
            const tagDescription = node.toLowerCase();
            const tagName = node.split(" ")[0].toLowerCase();
            if (!toIgnore(tagName.toUpperCase())) {
                const html = isInline(tagName.toUpperCase())
                    ? `a<${tagName}>b</${tagName}>c`
                    : `a</p><${tagName}>b</${tagName}><p>c`;

                await testEditor({
                    contentBefore: "<p>123[]4</p>",
                    stepFunction: async (editor) => {
                        pasteHtml(editor, `a<${tagDescription}>b</${tagName}>c`);
                    },
                    contentAfter: "<p>123" + html + "[]4</p>",
                    config: { baseContainers: ["DIV", "P"] },
                });
            }
        }
    });

    test("should keep whitelisted Tags tag (2)", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, 'a<img src="http://www.imgurl.com/img.jpg">d');
            },
            contentAfter: '<p>123a<img src="http://www.imgurl.com/img.jpg">d[]</p>',
        });
    });

    test("should keep tables Tags tag and add classes", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    "a<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>d"
                );
            },
            contentAfter:
                '<p>123a</p><table class="table table-bordered o_table"><tbody><tr><th>h</th></tr><tr><td>b</td></tr></tbody></table><p>d[]</p>',
        });
    });

    test("should insert a base container inside empty <td> on paste", async () => {
        await testEditor({
            contentBefore: `
                <p>[]<br></p>
            `,
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td></td>
                                </tr>
                            </tbody>
                        </table>
                    `)
                );
            },
            contentAfter: unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p>[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should not keep span", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "a<span>bc</span>d");
            },
            contentAfter: "<p>123abcd[]</p>",
        });
    });

    test("should not keep orphan LI", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "a<li>bc</li>d");
            },
            contentAfter: "<p>123a</p><p>bc</p><p>d[]</p>",
        });
    });

    test("should keep LI in UL", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "a<ul><li>bc</li></ul>d");
            },
            contentAfter: "<p>123a</p><ul><li>bc</li></ul><p>d[]</p>",
        });
    });

    test("should keep P and B and not span", async () => {
        await testEditor({
            contentBefore: "<p>123[]xx</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "a<p>bc</p>d<span>e</span>f<b>g</b>h");
            },
            contentAfter: "<p>123a</p><p>bc</p><p>def<b>g</b>h[]xx</p>",
        });
    });

    test("should keep styled span", async () => {
        await testEditor({
            contentBefore: "<p>123[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, 'a<span style="text-decoration: underline">bc</span>d');
            },
            contentAfter: "<p>123abcd[]</p>",
        });
    });

    test("should remove unwanted styles and b tag when pasting from paragraph from gdocs", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    `<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-ddad60c5-7fff-0a8f-fdd5-c1107201fe26"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test1</span></p><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></p></b>`
                );
            },
            contentAfter: "<p>test1</p><p>test2[]</p>",
        });
    });

    test.tags("font-dependent");
    test("should remove b, keep p, and remove unwanted styles when pasting list from gdocs", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-5d8bcf85-7fff-ebec-8604-eedd96f2d601"><ul style="margin-top:0;margin-bottom:0;padding-inline-start:48px;"><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Google</span></p></li><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Test</span></p></li><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></p></li></ul></b>'
                );
            },
            contentAfter:
                "<ul><li><p>Google</p></li><li><p>Test</p></li><li><p>test2[]</p></li></ul>",
        });
    });

    test.tags("font-dependent");
    test("should remove unwanted styles and keep tags when pasting list from gdoc", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-477946a8-7fff-f959-18a4-05014997e161"><ul style="margin-top:0;margin-bottom:0;padding-inline-start:48px;"><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:20pt;margin-bottom:0pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Google</span></h1></li><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:6pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Test</span></h1></li><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:20pt;margin-bottom:0pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></h1></li></ul></b>'
                );
            },
            contentAfter:
                "<ul><li><h1>Google</h1></li><li><h1>Test</h1></li><li><h1>test2[]</h1></li></ul>",
        });
    });
});

describe("Simple text", () => {
    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "x");
                },
                contentAfter: "<p>x[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: "<p>abx[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "xyz 123");
                },
                contentAfter: "<p>abxyz 123[]cd</p>",
            });
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "x    y");
                },
                contentAfter: "<p>abx&nbsp; &nbsp; y[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
            });
        });
        // TODO: We might want to have it consider \n as paragraph breaks
        // instead of linebreaks but that would be an opinionated choice.
        test("should paste text and understand \\n newlines", async () => {
            await testEditor({
                // @phoenix content adapted to make it valid html
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "a\nb\nc\nd");
                },
                contentAfter: "<div>a</div>" + "<div>b</div>" + "<div>c</div>" + "<p>d[]</p>",
            });
        });

        test("should paste text and understand \\r\\n newlines", async () => {
            await testEditor({
                // @phoenix content adapted to make it valid html
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "a\r\nb\r\nc\r\nd");
                },
                contentAfter: "<div>a</div>" + "<div>b</div>" + "<div>c</div>" + "<p>d[]</p>",
            });
        });

        test("should paste text and understand \\n newlines within UNBREAKABLE node", async () => {
            await testEditor({
                contentBefore: `<div class="oe_unbreakable">[]<br></div>`,
                stepFunction: async (editor) => {
                    pasteText(editor, "a\nb\nc\nd");
                },
                contentAfter: `<div class="oe_unbreakable">a<br>b<br>c<br>d[]</div>`,
            });
        });

        test("should paste text and understand \\n newlines within UNBREAKABLE node(2)", async () => {
            await testEditor({
                contentBefore: `<div class="oe_unbreakable"><span style="font-size: 9px;">a[]</span></div>`,
                stepFunction: async (editor) => {
                    pasteText(editor, "b\nc\nd");
                },
                contentAfter: `<div class="oe_unbreakable"><span style="font-size: 9px;">ab<br>c<br>d[]</span></div>`,
            });
        });

        test("should paste text and understand \\n newlines within PRE element", async () => {
            await testEditor({
                contentBefore: "<pre>[]<br></pre>",
                stepFunction: async (editor) => {
                    pasteText(editor, "a\nb\nc");
                },
                contentAfter: "<pre>a<br>b<br>c[]</pre>",
            });
        });

        test("should preserve spaces and not add nbsp when pasting plain text inside <pre>", async () => {
            await testEditor({
                contentBefore: "<pre>[]<br></pre>",
                stepFunction: async (editor) => {
                    pasteText(
                        editor,
                        "function example() {\n    console.log('Hello,    world!');\n    // Indented    comment\n}"
                    );
                },
                contentAfter:
                    "<pre>function example() {<br>    console.log('Hello,    world!');<br>    // Indented    comment<br>}[]</pre>",
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: "<p>ax[]d</p>",
            });
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "xyz 123");
                },
                contentAfter: "<p>axyz 123[]d</p>",
            });
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "x    y");
                },
                contentAfter: "<p>ax&nbsp; &nbsp; y[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "y");
                },
                contentAfter: '<p>a<span class="a">by[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (1)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: "<div>a<p>bx[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteText(editor, "y");
                },
                contentAfter: "<div>a<p>by[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (1)", async () => {
            await testEditor({
                contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteText(editor, "y");
                },
                contentAfter: '<div>ay[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection across two element (1)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
            });
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteText(editor, "x");
                },
                contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
            });
        });

        test("should paste a text when content contains line breaks", async () => {
            await testEditor({
                contentBefore: "<div>[abc]</div>",
                stepFunction: async (editor) => {
                    pasteText(editor, "ab\ncd");
                },
                contentAfter: "<div>ab</div><div>cd[]</div>",
            });
        });
    });
    test("should not paste a text when in contenteditable=false", async () => {
        await testEditor({
            contentBefore: '<div contenteditable="false">a[b]c</div>',
            stepFunction: async (editor) => {
                pasteText(editor, "xyz");
            },
            contentAfter: '<div contenteditable="false">a[b]c</div>',
        });
    });
});

describe("Simple html span", () => {
    const simpleHtmlCharX =
        '<span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">x</span>';

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>x[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>abx[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>ax[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (2)", async () => {
            await testEditor({
                contentBefore: "<div>1a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>1a<p>bx[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>2a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>2a<p>bx[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (2)", async () => {
            await testEditor({
                contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>ax[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection across two element (2)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
            });
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
            });
            await testEditor({
                contentBefore: "<div>3a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>3a<p>bx[]e</p>f</div>",
            });
        });
    });
});

describe("Simple html p", () => {
    const simpleHtmlCharX = "<p>x</p>";

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>x[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>abx[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<p>ax[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (3)", async () => {
            await testEditor({
                contentBefore: "<div>1a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>1a<p>bx[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>2a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>2a<p>bx[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (3)", async () => {
            await testEditor({
                contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>ax[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection across two element (3)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
            });
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
            });
            await testEditor({
                contentBefore: "<div>3a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, simpleHtmlCharX);
                },
                contentAfter: "<div>3a<p>bx[]e</p>f</div>",
            });
        });
    });
});

describe("Simple html elements containing <br>", () => {
    describe("breaking <br> elements", () => {
        test("should split h1 with <br> into seperate h1 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h1>abc<br>def<br>ghi<br>jkl</h1>");
                },
                contentAfter: "<h1>abc</h1><h1>def</h1><h1>ghi</h1><h1>jkl[]</h1>",
            });
        });

        test("should split h2 with <br> into seperate h2 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h2>abc<br>def<br>ghi<br>jkl</h2>");
                },
                contentAfter: "<h2>abc</h2><h2>def</h2><h2>ghi</h2><h2>jkl[]</h2>",
            });
        });

        test("should split h3 with <br> into seperate h3 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h3>abc<br>def<br>ghi<br>jkl</h3>");
                },
                contentAfter: "<h3>abc</h3><h3>def</h3><h3>ghi</h3><h3>jkl[]</h3>",
            });
        });

        test("should split h4 with <br> into seperate h4 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h4>abc<br>def<br>ghi<br>jkl</h4>");
                },
                contentAfter: "<h4>abc</h4><h4>def</h4><h4>ghi</h4><h4>jkl[]</h4>",
            });
        });

        test("should split h5 with <br> into seperate h5 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h5>abc<br>def<br>ghi<br>jkl</h5>");
                },
                contentAfter: "<h5>abc</h5><h5>def</h5><h5>ghi</h5><h5>jkl[]</h5>",
            });
        });

        test("should split h6 with <br> into seperate h6 elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<h6>abc<br>def<br>ghi<br>jkl</h6>");
                },
                contentAfter: "<h6>abc</h6><h6>def</h6><h6>ghi</h6><h6>jkl[]</h6>",
            });
        });

        test("should split p with <br> into seperate p elements", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc<br>def<br>ghi<br>jkl</p>");
                },
                contentAfter: "<p>abc</p><p>def</p><p>ghi</p><p>jkl[]</p>",
            });
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc<br>def<br>ghi<br>jkl</p><p>mno</p>");
                },
                contentAfter: "<p>abc</p><p>def</p><p>ghi</p><p>jkl</p><p>mno[]</p>",
            });
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc<br>def<br>ghi<br>jkl</p><p><br></p><p>mno</p>");
                },
                contentAfter: "<p>abc</p><p>def</p><p>ghi</p><p>jkl</p><p><br></p><p>mno[]</p>",
            });
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc<br>def<br><br><br>ghi</p>");
                },
                contentAfter: "<p>abc</p><p>def</p><p><br></p><p><br></p><p>ghi[]</p>",
            });
        });

        test("should split multiple elements with <br>", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        "<p>abc<br>def</p><h1>ghi<br>jkl</h1><h2><br></h2><h3>mno<br>pqr</h3>"
                    );
                },
                contentAfter:
                    "<p>abc</p><p>def</p><h1>ghi</h1><h1>jkl</h1><h2><br></h2><h3>mno</h3><h3>pqr[]</h3>",
            });
        });

        test("should split div with <br>", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<div>abc<br>def</div>");
                },
                contentAfter: `<div>abc</div><div>def[]</div>`,
                config: { baseContainers: ["DIV", "P"] },
            });
        });

        test("should split div with <br> (2)", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<div>abc<br>def</div>");
                },
                contentAfter: `<p>abc</p><p>def[]</p>`,
            });
        });
    });

    describe("not breaking <br> elements", () => {
        test("should not split li with <br>", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>abc<br>def</li></ul>");
                },
                contentAfter: "<ul><li>abc<br>def[]</li></ul>",
            });
        });

        test("should not split blockquote with <br>", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<blockquote>abc<br>def</blockquote>");
                },
                contentAfter: "<blockquote>abc<br>def[]</blockquote>",
            });
        });

        test("should not split pre with <br>", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<pre>abc<br>def</pre>");
                },
                contentAfter: "<pre>abc<br>def[]</pre>",
            });
        });
    });
});

describe("Unwrapping html element", () => {
    test("should not unwrap a node when pasting on empty node", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<h1>abc[]</h1>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h2>abc</h2>");
            },
            contentAfter: "<h2>abc[]</h2>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h3>abc</h3>");
            },
            contentAfter: "<h3>abc[]</h3>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<h1>abc</h1><h2>def[]</h2>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<h1>abc</h1><h2>def</h2><h3>ghi[]</h3>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p><p><br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h3>abc</h3>");
            },
            contentAfter: "<h3>abc[]</h3><p><br></p>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<p>abc</p><p><br></p><p><br></p>");
            },
            contentAfter: "<p>abc</p><p><br></p><p>[]<br></p>",
        });
    });
    test("should not unwrap a node when pasting in between different node", async () => {
        await testEditor({
            contentBefore: "<p>mn[]op</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<p>mn</p><h1>abc[]</h1><p>op</p>",
        });
        await testEditor({
            contentBefore: "<p>mn[]op</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<p>mn</p><h1>abc</h1><h2>def[]</h2><p>op</p>",
        });
        await testEditor({
            contentBefore: "<p>mn[]op</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<p>mn</p><h1>abc</h1><h2>def</h2><h3>ghi[]</h3><p>op</p>",
        });
    });
    test("should unwrap a node when pasting in between same node", async () => {
        await testEditor({
            contentBefore: "<h1>mn[]op</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<h1>mnabc[]op</h1>",
        });
        await testEditor({
            contentBefore: "<h1>mn[]op</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<h1>mnabc</h1><h2>def[]</h2><h1>op</h1>",
        });
        await testEditor({
            contentBefore: "<h2>mn[]op</h2>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<h2>mn</h2><h1>abc</h1><h2>def[]op</h2>",
        });
        await testEditor({
            contentBefore: "<h1>mn[]op</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h1>def</h1><h1>ghi</h1>");
            },
            contentAfter: "<h1>mnabc</h1><h1>def</h1><h1>ghi[]op</h1>",
        });
        await testEditor({
            contentBefore: "<p><strong>test []</strong></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<strong>paste</strong>");
            },
            contentAfter: "<p><strong>test paste[]</strong></p>",
        });
        await testEditor({
            contentBefore: '<p><font style="background-color: rgb(255, 0, 0);">[]test</font></p>',
            stepFunction: async (editor) => {
                pasteHtml(editor, '<font style="background-color: rgb(255, 0, 0);">nested </font>');
            },
            contentAfter:
                '<p><font style="background-color: rgb(255, 0, 0);">nested []test</font></p>',
        });
    });
    test("should not unwrap a node when pasting at start of different node", async () => {
        await testEditor({
            contentBefore: "<p>[]mn</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<h1>abc[]</h1><p>mn</p>",
        });
        await testEditor({
            contentBefore: "<p>[]mn</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<h1>abc</h1><h2>def[]</h2><p>mn</p>",
        });
        await testEditor({
            contentBefore: "<p>[]mn</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<h1>abc</h1><h2>def</h2><h3>ghi[]</h3><p>mn</p>",
        });
    });
    test("should unwrap a node when pasting at start of same node", async () => {
        await testEditor({
            contentBefore: "<h1>[]mn</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<h1>abc[]mn</h1>",
        });
        await testEditor({
            contentBefore: "<h1>[]mn</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h2>abc</h2><h1>def</h1>");
            },
            contentAfter: "<h2>abc</h2><h1>def[]mn</h1>",
        });
        await testEditor({
            contentBefore: '<h1><font style="background-color: rgb(255, 0, 0);">[]mn</font></h1>',
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h1>def</h1><h1>ghi</h1>");
            },
            contentAfter:
                '<h1>abc</h1><h1>def</h1><h1><font style="background-color: rgb(255, 0, 0);">ghi[]mn</font></h1>',
        });
    });
    test("should not unwrap a node when pasting at end of different node", async () => {
        await testEditor({
            contentBefore: "<p>mn[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<p>mn</p><h1>abc[]</h1>",
        });
        await testEditor({
            contentBefore: "<p>mn[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<p>mn</p><h1>abc</h1><h2>def[]</h2>",
        });
        await testEditor({
            contentBefore: "<p>mn[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<p>mn</p><h1>abc</h1><h2>def</h2><h3>ghi[]</h3>",
        });
    });
    test("should unwrap a node when pasting at end of same node", async () => {
        await testEditor({
            contentBefore: "<h1>mn[]</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1>");
            },
            contentAfter: "<h1>mnabc[]</h1>",
        });
        await testEditor({
            contentBefore: "<h1>mn[]</h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2>");
            },
            contentAfter: "<h1>mnabc</h1><h2>def[]</h2>",
        });
        await testEditor({
            contentBefore: '<h1><font style="background-color: rgb(255, 0, 0);">mn[]</font></h1>',
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h1>def</h1><h1>ghi</h1>");
            },
            contentAfter:
                '<h1><font style="background-color: rgb(255, 0, 0);">mnabc</font></h1><h1>def</h1><h1>ghi[]</h1>',
        });
    });
    test("should not unwrap empty block nodes even when pasting on same node", async () => {
        await testEditor({
            contentBefore: "<p>a[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<p><br></p><p><br></p><p><br></p>");
            },
            contentAfter: "<p>a</p><p><br></p><p><br></p><p>[]<br></p>",
        });
    });
    test("should unwrap base container node when pasting on different empty node", async () => {
        await testEditor({
            contentBefore: "<h1>[]<br></h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<p>abc</p>");
            },
            contentAfter: "<h1>abc[]</h1>",
        });
        await testEditor({
            contentBefore: "<h1>[]<br></h1>",
            stepFunction: async (editor) => {
                pasteHtml(editor, '<div class="o-paragraph">abc</div>');
            },
            contentAfter: "<h1>abc[]</h1>",
        });
        await testEditor({
            contentBefore: "<h1>[]<br></h1>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    '<p><font style="background-color: rgb(255, 0, 0);">abc</font></p>'
                );
            },
            contentAfter: '<h1><font style="background-color: rgb(255, 0, 0);">abc</font>[]</h1>',
        });
        await testEditor({
            contentBefore: "<h1>[]<br></h1>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    '<div class="o-paragraph"><font style="background-color: rgb(255, 0, 0);">abc</font></div>'
                );
            },
            contentAfter: '<h1><font style="background-color: rgb(255, 0, 0);">abc</font>[]</h1>',
        });
    });
    test("should unwrap li elements having no ul/ol", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(editor, "<li><p>abc</p></li><li><p>def</p></li>");
            },
            contentAfter: "<p>abc</p><p>def[]</p>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(editor, "<li><h1>abc</h1></li><li><h1>def</h1></li");
            },
            contentAfter: "<h1>abc</h1><h1>def[]</h1>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    "<li><blockquote>abc</blockquote></li><li><blockquote>def</blockquote></li>"
                );
            },
            contentAfter: "<blockquote>abc</blockquote><blockquote>def[]</blockquote>",
        });
    });
    test("should unwrap li elements with multiple blocks having no ul/ol", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    "<li><p>abc</p><p>def</p></li><li><p>abc</p><p>def</p></li>"
                );
            },
            contentAfter: "<p>abc</p><p>def</p><p>abc</p><p>def[]</p>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    "<li><h1>abc</h1><h1>def</h1></li><li><h1>abc</h1><h1>def</h1></li"
                );
            },
            contentAfter: "<h1>abc</h1><h1>def</h1><h1>abc</h1><h1>def[]</h1>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    "<li><blockquote>abc</blockquote><blockquote>def</blockquote></li><li><blockquote>abc</blockquote><blockquote>def</blockquote></li>"
                );
            },
            contentAfter:
                "<blockquote>abc</blockquote><blockquote>def</blockquote><blockquote>abc</blockquote><blockquote>def[]</blockquote>",
        });
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(
                    editor,
                    unformat(`
                    <li>
                        <p>abc</p>
                        <ul>
                            <li>abc</li>
                            <li>def</li>
                            <li>ghi</li>
                        </ul>
                    </li>
                    <li>
                        <p>abc</p>
                        <ul>
                            <li>abc</li>
                            <li>def</li>
                            <li>ghi</li>
                        </ul>
                    </li>
                `)
                );
            },
            contentAfter: unformat(`
                <p>abc</p>
                <ul>
                    <li>abc</li>
                    <li>def</li>
                    <li>ghi</li>
                </ul>
                <p>abc</p>
                <ul>
                    <li>abc</li>
                    <li>def</li>
                    <li>ghi[]</li>
                </ul>
            `),
        });
    });
});

describe("Complex html span", () => {
    const complexHtmlData =
        '<span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">1</span><b style="box-sizing: border-box; font-weight: bolder; font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">23</b><span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;"><span> </span>4</span>';

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>1<b>23</b>&nbsp;4[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>ab1<b>23</b>&nbsp;4[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>a1<b>23</b>&nbsp;4[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (4)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (4)", async () => {
            await testEditor({
                contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<div>ab<span class="a">c1<b>23</b>&nbsp;4[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<div>a1<b>23</b>&nbsp;4[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection across two element (4)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<div>1a<p>b1<b>23</b>&nbsp;4[]<span class="a">e</span>f</p></div>',
            });
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<div>2a<span class="a">b1<b>23</b>&nbsp;4[]</span>e<br>f</div>',
            });
            await testEditor({
                contentBefore: "<div>3a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>3a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>",
            });
        });
    });
});

describe("Complex html p", () => {
    const complexHtmlData =
        '<p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">12</p><p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">34</p>';

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>12</p><p>34[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>ab12</p><p>34[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a">34[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>a12</p><p>34[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span (1)", async () => {
            await testEditor({
                contentBefore: '<p>1a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>1a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span (2)", async () => {
            await testEditor({
                contentBefore: '<p>2a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>2a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (5)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b12</p><p>34[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b12</p><p>34[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (5) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>1ab<span class="a">c12</span></div><div><span class="a">34[]</span>f</div>`,
            });
            await testEditor({
                contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>2a12</div><div>34[]<span class="a">d</span>ef</div>`,
            });
        });

        test("should paste a text when selection leave a span (5) unbreakable", async () => {
            await testEditor({
                contentBefore: `<div class="oe_unbreakable">1ab<span class="a">c[d</span>e]f</div>`,
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div class="oe_unbreakable">1ab<span class="a">c12<br>34[]</span>f</div>`,
            });
            await testEditor({
                contentBefore: `<div class="oe_unbreakable">2a[b<span class="a">c]d</span>ef</div>`,
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div class="oe_unbreakable">2a12<br>34[]<span class="a">d</span>ef</div>`,
            });
        });

        test("should paste a text when selection leave a span (6)", async () => {
            await testEditor({
                contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>1ab<span class="a">c12</span></p><p><span class="a">34[]</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>2a12</p><p>34[]<span class="a">d</span>ef</p>',
            });
        });

        test("should paste a text when selection across two element (5)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                // FIXME: Bringing `e` and `f` into the `<p>` is a tradeOff
                // Should we change it ? How ? Might warrant a discussion.
                // possible alt contentAfter : <div>1a<p>b12</p>34[]<span>e</span>f</div>
                contentAfter: '<div>1a<p>b12</p><p>34[]<span class="a">e</span>f</p></div>',
            });
        });

        test("should paste a text when selection across two element (6) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>2a<span class="a">b12</span></div><div><span class="a">34[]</span>e<br>f</div>`,
            });
        });

        test("should paste a text when selection across two element (6) unbreakable", async () => {
            await testEditor({
                contentBefore: `<div class="oe_unbreakable">2a<span class="a">b[c</span><p>d]e</p>f</div>`,
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div class="oe_unbreakable">2a<span class="a">b12<br>34[]</span>e<br>f</div>`,
            });
        });
    });
});

describe("Complex html 3 p", () => {
    const complexHtmlData = "<p>1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6</p>";

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>ab1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>a1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span (1)", async () => {
            await testEditor({
                contentBefore: '<p>1a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>1a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span (2)", async () => {
            await testEditor({
                contentBefore: '<p>2a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>2a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (6)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    "<div>a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    "<div>a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (7) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>1ab<span class="a">c1<i>X</i>2</span></div><p>3<i>X</i>4</p><div><span class="a">5<i>X</i>6[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>2a1<i>X</i>2</div><p>3<i>X</i>4</p><div>5<i>X</i>6[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection leave a span (7) unbreakable", async () => {
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">1ab<span class="a">c1<i>X</i>2</span><p>3<i>X</i>4</p><span class="a">5<i>X</i>6[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">2a1<i>X</i>2<p>3<i>X</i>4</p>5<i>X</i>6[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection leave a span (8)", async () => {
            await testEditor({
                contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>1ab<span class="a">c1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>2a1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span class="a">d</span>ef</p>',
            });
        });

        test("should paste a text when selection across two element (7)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>1a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span class="a">e</span>f</p></div>',
            });
        });

        test("should paste a text when selection across two element (8)", async () => {
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>2a<span class="a">b1<i>X</i>2</span><p>3<i>X</i>4</p><span class="a">5<i>X</i>6[]</span>e<br>f</div>',
            });
        });
    });
});

describe("Complex html p+i", () => {
    const complexHtmlData =
        '<p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">12</p><p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;"><i style="box-sizing: border-box;">ii</i></p>';

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>12</p><p><i>ii</i>[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>ab12</p><p><i>ii</i>[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>a12</p><p><i>ii</i>[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>x<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (7)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b12</p><p><i>ii</i>[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b12</p><p><i>ii</i>[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (9) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>1ab<span class="a">c12</span></div><div><span class="a"><i>ii</i>[]</span>f</div>`,
            });
            await testEditor({
                contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>2a12</div><div><i>ii</i>[]<span class="a">d</span>ef</div>`,
            });
        });

        test("should paste a text when selection leave a span (9) unbreakable", async () => {
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">1ab<span class="a">c12<i><br>ii</i>[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">2a12<i><br>ii</i>[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection leave a span (10)", async () => {
            await testEditor({
                contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>1ab<span class="a">c12</span></p><p><span class="a"><i>ii</i>[]</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<p>2a12</p><p><i>ii</i>[]<span class="a">d</span>ef</p>',
            });
        });

        test("should paste a text when selection across two element (9)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: '<div>1a<p>b12</p><p><i>ii</i>[]<span class="a">e</span>f</p></div>',
            });
        });

        test("should paste a text when selection across two element (10) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>2a<span class="a">b12</span></div><div><span class="a"><i>ii</i>[]</span>e<br>f</div>`,
            });
        });

        test("should paste a text when selection across two element (10) unbreakable", async () => {
            await testEditor({
                contentBefore: `<div class="oe_unbreakable">2a<span class="a">b[c</span><p>d]e</p>f</div>`,
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div class="oe_unbreakable">2a<span class="a">b12<i><br>ii</i>[]</span>e<br>f</div>`,
            });
        });
    });
});

describe("Complex html 3p+b", () => {
    const complexHtmlData = "<p>1<b>23</b></p><p>zzz</p><p>45<b>6</b>7</p>";

    describe("range collapsed", () => {
        test("should paste a text at the beginning of a p", async () => {
            await testEditor({
                contentBefore: "<p>[]abcd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]abcd</p>",
            });
        });

        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>ab1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]cd</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]c</span>d</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste a text in a p", async () => {
            await testEditor({
                contentBefore: "<p>a[bc]d</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<p>a1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]d</p>",
            });
        });

        test("should paste a text in a span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two span", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
            });
            await testEditor({
                contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
            });
        });

        test("should paste a text when selection across two p (8)", async () => {
            await testEditor({
                contentBefore: "<div>a<p>b[c</p><p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]e</p>f</div>",
            });
            await testEditor({
                contentBefore: "<div>a<p>b[c</p>- -<p>d]e</p>f</div>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: "<div>a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]e</p>f</div>",
            });
        });

        test("should paste a text when selection leave a span (11) baseContainer", async () => {
            await testEditor({
                contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>1ab<span class="a">c1<b>23</b></span></div><p>zzz</p><div><span class="a">45<b>6</b>7[]</span>f</div>`,
            });
            await testEditor({
                contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter: `<div>2a1<b>23</b></div><p>zzz</p><div>45<b>6</b>7[]<span class="a">d</span>ef</div>`,
            });
        });

        test("should paste a text when selection leave a span (11) unbreakable", async () => {
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">1ab<span class="a">c[d</span>e]f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">1ab<span class="a">c1<b>23</b></span><p>zzz</p><span class="a">45<b>6</b>7[]</span>f</div>',
            });
            await testEditor({
                contentBefore: '<div class="oe_unbreakable">2a[b<span class="a">c]d</span>ef</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div class="oe_unbreakable">2a1<b>23</b><p>zzz</p>45<b>6</b>7[]<span class="a">d</span>ef</div>',
            });
        });

        test("should paste a text when selection across two element (11)", async () => {
            await testEditor({
                contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>1a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]<span class="a">e</span>f</p></div>',
            });
        });

        test("should paste a text when selection across two element (12)", async () => {
            await testEditor({
                contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, complexHtmlData);
                },
                contentAfter:
                    '<div>2a<span class="a">b1<b>23</b></span><p>zzz</p><span class="a">45<b>6</b>7[]</span>e<br>f</div>',
            });
        });
    });
});

describe("Complex html div", () => {
    const complexHtmlData = `<div><div><span style="color: #fb4934;">abc</span><span style="color: #ebdbb2;">def</span></div><div dir="rtl"><span style="color: #fb4934;">ghi</span><span style="color: #fe8019;">jkl</span></div><div><span style="color: #fb4934;">jkl</span><span style="color: #ebdbb2;">mno</span></div></div>`;
    test("should convert div to a baseContainer", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, complexHtmlData);
            },
            contentAfter: `<div>abcdef</div><div dir="rtl">ghijkl</div><div>jklmno[]</div>`,
            config: { baseContainers: ["DIV", "P"] },
        });
    });

    test("should convert div to a baseContainer (2)", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, complexHtmlData);
            },
            contentAfter: `<p>abcdef</p><p dir="rtl">ghijkl</p><p>jklmno[]</p>`,
        });
    });

    const copiedHtmlData = `<ol><li><div>abc</div><div></div></li><li><div></div><div style="white-space: break-spaces;"><span>def\nghi</span><br><span>jkl</span></div></li></ol>`;
    test("should remove empty <div> elements from pasted content", async () => {
        await testEditor({
            contentBefore: "<p>12[]3</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, copiedHtmlData);
            },
            contentAfter: `<p>12</p><ol><li><div>abc</div></li><li><div>def</div><div>ghi</div><div>jkl[]</div></li></ol><p>3</p>`,
            config: { baseContainers: ["DIV", "P"] },
        });
    });

    test("should remove empty <div> elements from pasted content (2)", async () => {
        await testEditor({
            contentBefore: "<p>12[]3</p>",
            stepFunction: async (editor) => {
                pasteHtml(editor, copiedHtmlData);
            },
            contentAfter: `<p>12</p><ol><li><p>abc</p></li><li><p>def</p><p>ghi</p><p>jkl[]</p></li></ol><p>3</p>`,
        });
    });
});

describe("Special cases", () => {
    describe("lists", () => {
        test("should paste a list in a p", async () => {
            await testEditor({
                contentBefore: "<p>12[]34</p>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>abc</li><li>def</li><li>ghi</li></ul>");
                },
                contentAfter: "<p>12</p><ul><li>abc</li><li>def</li><li>ghi[]</li></ul><p>34</p>",
            });
        });

        test("should paste the text of an li into another li", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>123</li></ul>");
                },
                contentAfter: "<ul><li>abc</li><li>de123[]f</li><li>ghi</li></ul>",
            });
        });

        test("should paste the text of an li into another li, and the text of another li into the next li", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>123</li><li>456</li></ul>");
                },
                contentAfter: "<ul><li>abc</li><li>de123</li><li>456[]f</li><li>ghi</li></ul>",
            });
        });

        test("should paste the text of an li into another li, insert a new li, and paste the text of a third li into the next li", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>123</li><li>456</li><li>789</li></ul>");
                },
                contentAfter:
                    "<ul><li>abc</li><li>de123</li><li>456</li><li>789[]f</li><li>ghi</li></ul>",
            });
        });

        test("should paste the text of an li into another li and insert a new li at the end of a list", async () => {
            await testEditor({
                contentBefore: "<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>123</li><li>456</li></ul>");
                },
                contentAfter: "<ul><li>abc</li><li>def</li><li>ghi123</li><li>456[]</li></ul>",
            });
        });

        test("should insert a new li at the beginning of a list and paste the text of another li into the next li", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]abc</li><li>def</li><li>ghi</li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>123</li><li>456</li></ul>");
                },
                contentAfter: "<ul><li>123</li><li>456[]abc</li><li>def</li><li>ghi</li></ul>",
            });
        });

        test("should insert a list and a p tag inside a new list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><li>abc</li><li>def</li></ul><p>ghi</p>");
                },
                contentAfter: "<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>",
            });
        });

        test("should insert content ending with a list inside a new list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc</p><ul><li>def</li><li>ghi</li></ul>");
                },
                contentAfter: "<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>",
            });
        });

        test("should convert a mixed list containing a paragraph into a checklist", async () => {
            await testEditor({
                contentBefore: `<ul class="o_checklist"><li>[]<br></li></ul>`,
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ul>
                                <li>abc</li>
                                <li>def</li>
                                <li>ghi</li>
                            </ul>
                            <p>jkl</p>
                            <ol>
                                <li>mno</li>
                                <li>pqr</li>
                                <li>stu</li>
                            </ol>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>abc</li>
                        <li>def</li>
                        <li>ghi</li>
                        <li>jkl</li>
                        <li>mno</li>
                        <li>pqr</li>
                        <li>stu[]</li>
                    </ul>
                `),
            });
        });

        test("should not unwrap a list twice when pasting on new list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<ul><ul><li>abc</li><li>def</li></ul></ul>");
                },
                contentAfter: `<ul><li class="oe-nested"><ul><li>abc</li><li>def[]</li></ul></li></ul>`,
            });
        });

        test("should paste a nested list into another list", async () => {
            await testEditor({
                contentBefore: "<ol><li>Alpha</li><li>[]<br></li></ol>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ul>
                                <li>abc</li>
                                <li>def
                                    <ul>
                                        <li>123</li>
                                        <li>456</li>
                                    </ul>
                                </li>
                            </ul>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ol>
                        <li>Alpha</li>
                        <li>abc</li>
                        <li><p>def</p>
                            <ol>
                                <li>123</li>
                                <li>456[]</li>
                            </ol>
                        </li>
                    </ol>
                `),
            });
        });

        test("should paste a nested list into another list (2)", async () => {
            await testEditor({
                contentBefore: "<ul><li>Alpha</li><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ol>
                                <li class="oe-nested">
                                    <ul>
                                        <li class="oe-nested">
                                            <ol>
                                                <li class="oe-nested">
                                                    <ul class="o_checklist">
                                                        <li>abc</li>
                                                    </ul>
                                                </li>
                                                <li>def</li>
                                            </ol>
                                        </li>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                                <li>jkl</li>
                            </ol>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ul>
                        <li><p>Alpha</p>
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>abc</li>
                                            </ul>
                                        </li>
                                        <li>def</li>
                                    </ul>
                                </li>
                                <li>ghi</li>
                            </ul>
                        </li>
                        <li>jkl[]</li>
                    </ul>
                `),
            });
        });

        test("should convert a mixed list into a ordered list", async () => {
            await testEditor({
                contentBefore: "<ol><li>[]<br></li></ol>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ul>
                                <li>ab</li>
                                <li>cd
                                    <ol>
                                        <li>ef</li>
                                        <li>gh
                                            <ul class="o_checklist">
                                                <li>ij</li>
                                                <li>kl</li>
                                            </ul>
                                        </li>
                                    </ol>
                                </li>
                            </ul>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ol>
                        <li>ab</li>
                        <li><p>cd</p>
                            <ol>
                                <li>ef</li>
                                <li><p>gh</p>
                                    <ol>
                                        <li>ij</li>
                                        <li>kl[]</li>
                                    </ol>
                                </li>
                            </ol>
                        </li>
                    </ol>
                `),
            });
        });

        test("should convert a mixed list starting with bullet list into a bullet list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ul>
                                <li>ab</li>
                                <li>cd
                                    <ol>
                                        <li>ef</li>
                                        <li>gh
                                            <ul class="o_checklist">
                                                <li>ij</li>
                                                <li>kl</li>
                                            </ul>
                                        </li>
                                    </ol>
                                </li>
                            </ul>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ul>
                        <li>ab</li>
                        <li><p>cd</p>
                            <ul>
                                <li>ef</li>
                                <li><p>gh</p>
                                    <ul>
                                        <li>ij</li>
                                        <li>kl[]</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>
                `),
            });
        });

        test("should paste a mixed list starting with deeply nested bullet list into a bullet list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li class="oe-nested">
                                                    <ul>
                                                        <li>ab</li>
                                                        <li>cd</li>
                                                    </ul>
                                                </li>
                                                <li>ef</li>
                                                <li>gh</li>
                                            </ul>
                                        </li>
                                        <li>ij</li>
                                        <li>kl</li>
                                    </ul>
                                </li>
                                <li>mn</li>
                                <li>op</li>
                            </ul>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ul>
                        <li class="oe-nested">
                            <ul>
                                <li class="oe-nested">
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>ab</li>
                                                <li>cd</li>
                                            </ul>
                                        </li>
                                        <li>ef</li>
                                        <li>gh</li>
                                    </ul>
                                </li>
                                <li>ij</li>
                                <li>kl</li>
                            </ul>
                        </li>
                        <li>mn</li>
                        <li>op[]</li>
                    </ul>
                `),
            });
        });

        test("should paste a deeply nested list copied outside from odoo", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <ol>
                                <li>ab</li>
                                <ol>
                                    <li>cd</li>
                                    <li>ef</li>
                                    <ul>
                                        <li>gh</li>
                                        <li>ij</li>
                                    </ul>
                                    <ol>
                                        <li>kl</li>
                                        <li>mn</li>
                                    </ol>
                                </ol>
                                <ul>
                                    <li>op</li>
                                    <li>qr</li>
                                    <ol>
                                        <li>st</li>
                                        <li>uv</li>
                                    </ol>
                                </ul>
                            </ol>
                        `)
                    );
                },
                contentAfter: unformat(`
                    <ul>
                        <li><p>ab</p>
                            <ul>
                                <li>cd</li>
                                <li><p>ef</p>
                                    <ul>
                                        <li>gh</li>
                                        <li>ij</li>
                                        <li>kl</li>
                                        <li>mn</li>
                                    </ul>
                                </li>
                                <li>op</li>
                                <li><p>qr</p>
                                    <ul>
                                        <li>st</li>
                                        <li>uv[]</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>
                `),
            });
        });

        test.tags("font-dependent");
        test("should paste checklist from gdoc", async () => {
            await testEditor({
                contentBefore: "<p>[]<br></p>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        unformat(`
                            <b style="font-weight:normal;" id="docs-internal-guid-5c9e50d3-7fff-c129-6dcc-e76588942722">
                                <ul style="margin-top:0;margin-bottom:0;padding-inline-start:28px;">
                                    <li dir="ltr" role="checkbox" aria-checked="false" style="list-style-type:none;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1">
                                        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAYAAABV7bNHAAAA1ElEQVR4Ae3bMQ4BURSFYY2xBuwQ7BIkTGxFRj9Oo9RdkXn5TvL3L19u+2ZmZmZmZhVbpH26pFcaJ9IrndMudb/CWadHGiden1bll9MIzqd79SUd0thY20qga4NA50qgoUGgoRJo/NL/V/N+QIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIEyFeEZyXQpUGgUyXQrkGgTSVQl/qGcG5pnkq3Sn0jOMv0k3Vpm05pmNjfsGPalFyOmZmZmdkbSS9cKbtzhxMAAAAASUVORK5CYII=" width="17.599999999999998px" height="17.599999999999998px" alt="unchecked" aria-roledescription="checkbox" style="margin-right:3px;" />
                                        <p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;display:inline-block;vertical-align:top;margin-top:0;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Abc</span></p>
                                    </li>
                                    <li dir="ltr" role="checkbox" aria-checked="false" style="list-style-type:none;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1">
                                        <img src="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEgAAABICAYAAABV7bNHAAAA1ElEQVR4Ae3bMQ4BURSFYY2xBuwQ7BIkTGxFRj9Oo9RdkXn5TvL3L19u+2ZmZmZmZhVbpH26pFcaJ9IrndMudb/CWadHGiden1bll9MIzqd79SUd0thY20qga4NA50qgoUGgoRJo/NL/V/N+QIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIECBAgQIAAAQIEyFeEZyXQpUGgUyXQrkGgTSVQl/qGcG5pnkq3Sn0jOMv0k3Vpm05pmNjfsGPalFyOmZmZmdkbSS9cKbtzhxMAAAAASUVORK5CYII=" width="17.599999999999998px" height="17.599999999999998px" alt="checked" aria-roledescription="checkbox" style="margin-right:3px;" />
                                        <p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;display:inline-block;vertical-align:top;margin-top:0;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">def</span></p>
                                    </li>
                                </ul>
                            </b>
                        `)
                    );
                },
                contentAfter: `<ul class="o_checklist"><li><p>Abc</p></li><li class="o_checked"><p>def[]</p></li></ul>`,
            });
        });
    });

    describe("paragraphs", () => {
        test("should paste multiple paragraphs into a list", async () => {
            await testEditor({
                contentBefore: "<ul><li>[]<br></li></ul>",
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<p>abc</p><p>def</p><p>ghi</p><p>jkl</p><p>mno</p>");
                },
                contentAfter:
                    "<ul><li>abc</li><li>def</li><li>ghi</li><li>jkl</li><li>mno[]</li></ul>",
            });
        });
    });
});

describe("pasting within blockquote", () => {
    test("should paste paragraph related elements within blockquote", async () => {
        await testEditor({
            contentBefore: "<blockquote>[]<br></blockquote>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<blockquote><h1>abc</h1><h2>def</h2><h3>ghi[]</h3></blockquote>",
        });
        await testEditor({
            contentBefore: "<blockquote>x[]</blockquote>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<blockquote>x<h1>abc</h1><h2>def</h2><h3>ghi[]</h3></blockquote>",
        });
        await testEditor({
            contentBefore: "<blockquote>[]x</blockquote>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<blockquote><h1>abc</h1><h2>def</h2><h3>ghi[]</h3>x</blockquote>",
        });
        await testEditor({
            contentBefore: "<blockquote>x[]y</blockquote>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<blockquote>x<h1>abc</h1><h2>def</h2><h3>ghi[]</h3>y</blockquote>",
        });
    });
});

describe("pasting within pre", () => {
    test("should paste paragraph related elements within pre as plain text", async () => {
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<pre>abc\ndef\nghi[]</pre>",
        });
        await testEditor({
            contentBefore: "<pre>x[]</pre>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<pre>xabc\ndef\nghi[]</pre>",
        });
        await testEditor({
            contentBefore: "<pre>[]x</pre>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<pre>abc\ndef\nghi[]x</pre>",
        });
        await testEditor({
            contentBefore: "<pre>x[]y</pre>",
            stepFunction: async (editor) => {
                pasteHtml(editor, "<h1>abc</h1><h2>def</h2><h3>ghi</h3>");
            },
            contentAfter: "<pre>xabc\ndef\nghi[]y</pre>",
        });
    });
    test("should paste as plain text within pre", async () => {
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<div class="o-paragraph">a<strong>bcd</strong><font style="color: rgb(255, 0, 0);">efg</font><font style="background-color: rgba(255, 156, 0, 0.6);">hij</font><span class="display-3-fs">klm</span>no</div>'
                );
            },
            contentAfter: "<pre>abcdefghijklmno[]</pre>",
        });
    });
    test("should paste lists within pre as plain text and keep the list style and indentation", async () => {
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<ol><li>abc</li><li>def</li><li class="oe-nested"><ol><li>ghi</li><li class="oe-nested"><ol><li>jkl</li></ol></li><li>mno</li></ol></li><li>pqr</li></ol>'
                );
            },
            contentAfter:
                "<pre>1. abc\n2. def\n    1. ghi\n        1. jkl\n    2. mno\n3. pqr[]</pre>",
        });
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<ul><li>abc</li><li>def</li><li class="oe-nested"><ul><li>ghi</li><li class="oe-nested"><ul><li>jkl</li></ul></li><li>mno</li></ul></li><li>pqr</li></ul>'
                );
            },
            contentAfter: "<pre>* abc\n* def\n    * ghi\n        * jkl\n    * mno\n* pqr[]</pre>",
        });
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<ul class="o_checklist"><li>abc</li><li>def</li><li class="oe-nested"><ul class="o_checklist"><li>ghi</li><li class="oe-nested"><ul class="o_checklist"><li>jkl</li></ul class="o_checklist"></li><li>mno</li></ul class="o_checklist"></li><li>pqr</li></ul class="o_checklist">'
                );
            },
            contentAfter:
                "<pre>[] abc\n[] def\n    [] ghi\n        [] jkl\n    [] mno\n[] pqr[]</pre>",
        });
    });
    test("should paste nested lists of different types within pre as plain text and keep the list style and indentation", async () => {
        await testEditor({
            contentBefore: "<pre>[]<br></pre>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    '<ol><li>ab</li><li class="oe-nested"><ul><li>cd</li><li class="oe-nested"><ul class="o_checklist"><li>ef</li><li class="oe-nested"><ol><li>gh</li></ol></li><li>ij</li></ul></li><li>kl</li></ul></li><li>mn</li></ol>'
                );
            },
            contentAfter:
                "<pre>1. ab\n    * cd\n        [] ef\n            1. gh\n        [] ij\n    * kl\n2. mn[]</pre>",
        });
    });
});

const url = "https://www.odoo.com";
const imgUrl = "https://download.odoocdn.com/icons/website/static/description/icon.png";
const videoUrl = "https://www.youtube.com/watch?v=dQw4w9WgXcQ";

describe("link", () => {
    describe("range collapsed", () => {
        test("should paste and transform an URL in a p (collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>ab[]cd</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter: '<p>ab<a href="http://www.xyz.com">http://www.xyz.com</a>[]cd</p>',
            });
        });

        test("should paste and transform an URL in a span (collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter:
                    '<p>a<span class="a">b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
            });
        });

        test("should paste and not transform an URL in a existing link (collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter: '<p>a<a href="http://existing.com">bhttp://www.xyz.com[]c</a>d</p>',
            });
            await testEditor({
                contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "random");
                },
                contentAfter: '<p>a<a href="http://existing.com">brandom[]c</a>d</p>',
            });
        });

        test("should paste and update an URL in a existing link if label and url are aligned", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="http://existing.com">[]c</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "https://www.xyz.xdc");
                },
                contentAfter: '<p>a<a href="http://existing.com">https://www.xyz.xdc[]c</a>d</p>',
            });
            await testEditor({
                contentBefore: '<p>a<a href="http://bo.com">bo[].com</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "om");
                },
                contentAfter: '<p>a<a href="http://boom.com">boom[].com</a>d</p>',
            });
        });

        test("should replace link for new content when pasting in an empty link (collapsed)", async () => {
            await testEditor({
                contentBefore:
                    '<p><a href="http://test.test/" oe-zws-empty-inline="">[]\u200B</a></p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "abc");
                },
                contentAfter: "<p>abc[]</p>",
            });
        });
        test("should replace link for new content when pasting in an empty link (collapsed)(2)", async () => {
            await testEditor({
                contentBefore:
                    '<p>xy<a href="http://test.test/" oe-zws-empty-inline="">\u200B[]</a>z</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "abc");
                },
                contentAfter: "<p>xyabc[]z</p>",
            });
        });

        test("should replace link for new content (url) when pasting in an empty link (collapsed)", async () => {
            const { el, editor } = await setupEditor(
                `<p>xy<a href="http://test.test/" oe-zws-empty-inline="">\u200B[]</a>z</p>`
            );
            pasteText(editor, "http://odoo.com");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>xy<a href="http://odoo.com">http://odoo.com</a>[]z</p>`
            );
        });

        test("should replace link for new content (imgUrl) when pasting in an empty link (collapsed) (1)", async () => {
            const { el, editor } = await setupEditor(
                `<p>xy<a href="http://test.test/">[]</a>z</p>`
            );
            expect(getContent(el)).toBe(
                `<p>xy\ufeff<a href="http://test.test/" class="o_link_in_selection">\ufeff[]\ufeff</a>\ufeffz</p>`
            );
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            expect(getContent(el)).toBe(`<p>xy${imgUrl}[]z</p>`);

            await press("Enter");
            expect(getContent(el)).toBe(`<p>xy<img src="${imgUrl}">[]z</p>`);
        });

        test("should replace link for new content (url) when pasting in an empty link (collapsed) (2)", async () => {
            const { el, editor } = await setupEditor(
                `<p>xy<a href="http://test.test/" oe-zws-empty-inline="">\u200B[]</a>z</p>`
            );
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            expect(getContent(el)).toBe(`<p>xy${imgUrl}[]z</p>`);

            await press("ArrowDown");
            await press("Enter");

            await animationFrame();
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>xy<a href="${imgUrl}">${imgUrl}</a>[]z</p>`
            );
        });

        test("should paste and transform plain text content over an empty link (collapsed)", async () => {
            await testEditor({
                contentBefore: '<p><a href="http://test.test/">[]\u200B</a></p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "abc www.odoo.com xyz");
                },
                contentAfter: '<p>abc <a href="http://www.odoo.com">www.odoo.com</a> xyz[]</p>',
            });
            await testEditor({
                contentBefore: '<p><a href="http://test.test/">[]\u200B</a></p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "odoo.com\ngoogle.com");
                },
                contentAfter:
                    '<div><a href="http://odoo.com">odoo.com</a></div>' +
                    '<p><a href="http://google.com">google.com</a>[]</p>',
            });
        });

        test("should paste html content over an empty link (collapsed)", async () => {
            await testEditor({
                contentBefore: '<p><a href="http://test.test/">[]\u200B</a></p>',
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        '<a href="www.odoo.com">odoo.com</a><br><a href="google.com">google.com</a>'
                    );
                },
                contentAfter:
                    '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="https://google.com">google.com[]</a></p>',
            });
        });
        test("should paste html content over an empty link (collapsed) (2)", async () => {
            await testEditor({
                contentBefore: '<p><a href="http://test.test/">[]\u200B</a></p>',
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>'
                    );
                },
                contentAfter:
                    '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="www.google.com">google.com[]</a></p>',
            });
        });

        test("should paste and transform URL among text (collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");
            pasteText(editor, `abc ${url} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${url}">${url}</a> def[]</p>`
            );
            undo(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]</p>`
            );
        });

        test("should paste and transform image URL among text (collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");
            pasteText(editor, `abc ${imgUrl} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]</p>`
            );
        });

        test("should paste and transform video URL among text (collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");
            pasteText(editor, `abc ${videoUrl} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${videoUrl}">${videoUrl}</a> def[]</p>`
            );
        });

        test("should paste and transform multiple URLs (collapsed) (1)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");
            pasteText(editor, `${url} ${videoUrl} ${imgUrl}`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]</p>`
            );
            undo(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]</p>`
            );
        });

        test("should paste and transform multiple URLs (collapsed) (2)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");
            pasteText(editor, `${url} abc ${videoUrl} def ${imgUrl}`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p><a href="${url}">${url}</a> abc <a href="${videoUrl}">${videoUrl}</a> def <a href="${imgUrl}">${imgUrl}</a>[]</p>`
            );
            undo(editor);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p o-we-hint-text='Type "/" for commands' class="o-we-hint">[]</p>`
            );
        });

        test("should paste plain text inside non empty link (collapsed)", async () => {
            await testEditor({
                contentBefore: '<p><a href="http://test.test/">a[]b</a></p>',
                stepFunction: async (editor) => {
                    pasteHtml(editor, "<span>123</span>");
                },
                contentAfter: '<p><a href="http://test.test/">a123[]b</a></p>',
            });
        });

        test("should paste and not transform an URL in a pre tag", async () => {
            await testEditor({
                contentBefore: "<pre>[]<br></pre>",
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter: "<pre>http://www.xyz.com[]</pre>",
            });
        });
        test("should not merge consecutive pastes of the same URL into a single anchor", async () => {
            await testEditor({
                contentBefore: "<p>[]</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter:
                    '<p><a href="http://www.xyz.com">http://www.xyz.com</a><a href="http://www.xyz.com">http://www.xyz.com</a>[]</p>',
            });
        });
    });

    describe("range not collapsed", () => {
        test("should paste and transform an URL in a p (not collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>ab[xxx]cd</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter: '<p>ab<a href="http://www.xyz.com">http://www.xyz.com</a>[]cd</p>',
            });
        });

        test("should paste and transform an URL in a span (not collapsed)", async () => {
            await testEditor({
                contentBefore:
                    '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter:
                    '<p>a<span class="a">b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
            });
        });

        test("should paste and not transform an URL in a existing link (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "http://www.xyz.com");
                },
                contentAfter: '<p>a<a href="http://existing.com">bhttp://www.xyz.com[]c</a>d</p>',
            });
        });

        test("should restore selection when pasting plain text followed by UNDO (1) (not collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "def");
                    undo(editor);
                },
                contentAfter: "<p>[abc]</p>",
            });
        });

        test("should restore selection when pasting plain text followed by UNDO (2) (not collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "www.odoo.com");
                    undo(editor);
                },
                contentAfter: "<p>[abc]</p>",
            });
        });

        test("should restore selection when pasting plain text followed by UNDO (3) (not collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: async (editor) => {
                    pasteText(editor, "def www.odoo.com xyz");
                    undo(editor);
                },
                contentAfter: "<p>[abc]</p>",
            });
        });

        test("should restore selection after pasting HTML followed by UNDO (not collapsed)", async () => {
            await testEditor({
                contentBefore: "<p>[abc]</p>",
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>'
                    );
                    undo(editor);
                },
                contentAfter: "<p>[abc]</p>",
            });
        });

        test("should paste and transform URL among text (not collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[xyz]</p>");
            pasteText(editor, `abc ${url} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${url}">${url}</a> def[]</p>`
            );
        });

        test("should paste and transform image URL among text (not collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[xyz]</p>");
            pasteText(editor, `abc ${imgUrl} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]</p>`
            );
        });

        test("should paste and transform video URL among text (not collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[xyz]</p>");
            pasteText(editor, `abc ${videoUrl} def`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>abc <a href="${videoUrl}">${videoUrl}</a> def[]</p>`
            );
        });

        test("should paste and transform multiple URLs among text (not collapsed)", async () => {
            const { el, editor } = await setupEditor("<p>[xyz]</p>");
            pasteText(editor, `${url} ${videoUrl} ${imgUrl}`);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]</p>`
            );
        });

        test("should paste and transform URL over the existing url", async () => {
            await testEditor({
                contentBefore: '<p>ab[<a href="http://www.xyz.com">http://www.xyz.com</a>]cd</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "https://www.xyz.xdc ");
                },
                contentAfter: '<p>ab<a href="https://www.xyz.xdc">https://www.xyz.xdc</a> []cd</p>',
            });
        });

        test("should paste and transform URL over the existing url (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>ab[<a href="http://www.xyz.com">http://www.xyz.com</a>]cd</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "https://www.xyz.xdc ");
                },
                contentAfter: '<p>ab<a href="https://www.xyz.xdc">https://www.xyz.xdc</a> []cd</p>',
            });
        });

        test("should paste plain text content over a link if all of its contents is selected (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="#">[xyz]</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "bc");
                },
                contentAfter: "<p>abc[]d</p>",
            });
        });

        test("should paste plain text content inside a link if all of its contents is selected but link is inside non-editable (not collapsed)", async () => {
            await testEditor({
                contentBefore:
                    '<p contenteditable="false">a<a href="#" contenteditable="true">[xyz]</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "bc");
                },
                contentAfter:
                    '<p contenteditable="false">a<a href="#" contenteditable="true">bc[]</a>d</p>',
            });
        });

        test("should paste plain text content inside a link if all of its contents is selected but link is unremovable (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p>a<a href="#" class="oe_unremovable">[xyz]</a>d</p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "bc");
                },
                contentAfter: '<p>a<a href="#" class="oe_unremovable">bc[]</a>d</p>',
            });
        });

        test("should paste and transform plain text content over a link if all of its contents is selected (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p><a href="#">[xyz]</a></p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "www.odoo.com");
                },
                contentAfter: '<p><a href="http://www.odoo.com">www.odoo.com</a>[]</p>',
            });
            await testEditor({
                contentBefore: '<p><a href="#">[xyz]</a></p>',
                stepFunction: async (editor) => {
                    pasteText(editor, "abc www.odoo.com xyz");
                },
                contentAfter: '<p>abc <a href="http://www.odoo.com">www.odoo.com</a> xyz[]</p>',
            });
        });

        test("should paste and transform plain text content over an image link if all of its contents is selected (not collapsed) (1)", async () => {
            const { el, editor } = await setupEditor(
                `<p>ab<a href="http://www.xyz.com">[http://www.xyz.com]</a>cd</p>`
            );
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            expect(getContent(el)).toBe(
                `<p>abhttps://download.odoocdn.com/icons/website/static/description/icon.png[]cd</p>`
            );
            await press("Enter");
            expect(getContent(el)).toBe(`<p>ab<img src="${imgUrl}">[]cd</p>`);
        });

        test("should paste and transform plain text content over an image link if all of its contents is selected (not collapsed) (2)", async () => {
            const { el, editor } = await setupEditor(
                `<p>ab<a href="http://www.xyz.com">[http://www.xyz.com]</a>cd</p>`
            );
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            expect(getContent(el)).toBe(
                `<p>abhttps://download.odoocdn.com/icons/website/static/description/icon.png[]cd</p>`
            );
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="${imgUrl}">${imgUrl}</a>[]cd</p>`
            );
        });

        test("should paste html content over a link if all of its contents is selected (not collapsed)", async () => {
            await testEditor({
                contentBefore: '<p><a href="#">[xyz]</a></p>',
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        '<a href="www.odoo.com">odoo.com</a><br><a href="google.com">google.com</a>'
                    );
                },
                contentAfter:
                    '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="https://google.com">google.com[]</a></p>',
            });
        });
        test("should paste html content over a link if all of its contents is selected (not collapsed) (2)", async () => {
            await testEditor({
                contentBefore: '<p><a href="#">[xyz]</a></p>',
                stepFunction: async (editor) => {
                    pasteHtml(
                        editor,
                        '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>'
                    );
                },
                contentAfter:
                    '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="www.google.com">google.com[]</a></p>',
            });
        });
    });
});

describe("images", () => {
    describe("range collapsed", () => {
        test("should paste and transform an image URL in a p (1)", async () => {
            const { el, editor } = await setupEditor("<p>ab[]cd</p>");
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            expect(getContent(el)).toBe(`<p>ab<img src="${imgUrl}">[]cd</p>`);
        });

        test("should paste and transform an image URL in a span", async () => {
            const { el, editor } = await setupEditor('<p>a<span class="a">b[]c</span>d</p>');
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            expect(getContent(el)).toBe(
                `<p>a<span class="a">b<img src="${imgUrl}">[]c</span>d</p>`
            );
        });

        test("should paste and transform an image URL in an existing link", async () => {
            const { el, editor } = await setupEditor(
                '<p>a<a href="http://existing.com">b[]c</a>d</p>'
            );

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>a<a href="http://existing.com">b<img src="${imgUrl}">[]c</a>d</p>`
            );
        });

        test("should paste an image URL as a link in a p (1)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p><a href="${imgUrl}">${imgUrl}</a>[]</p>`
            );
        });

        test("should not revert a history step when pasting an image URL as a link (1)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");

            // paste text to have a history step recorded
            pasteText(editor, "*should not disappear*");
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>*should not disappear*<a href="${imgUrl}">${imgUrl}</a>[]</p>`
            );
        });
    });

    describe("range not collapsed", () => {
        test("should paste and transform an image URL in a p (2)", async () => {
            const { el, editor } = await setupEditor("<p>ab[xxx]cd</p>");

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(`<p>ab<img src="${imgUrl}">[]cd</p>`);
        });

        test("should paste and transform an image URL in a span", async () => {
            const { el, editor } = await setupEditor(
                '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>'
            );

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            await press("Enter");
            expect(getContent(el)).toBe(
                `<p>a<span class="a">b<img src="${imgUrl}">[]c</span>d</p>`
            );
        });

        test("should paste and transform an image URL inside an existing link", async () => {
            const { el, editor } = await setupEditor(
                '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>'
            );

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 0);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>a<a href="http://existing.com">b<img src="${imgUrl}">[]c</a>d</p>`
            );
        });

        test("should paste an image URL as a link in a p (2)", async () => {
            const { el, editor } = await setupEditor("<p>ab[xxx]cd</p>");

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="${imgUrl}">${imgUrl}</a>[]cd</p>`
            );
        });

        test("should not revert a history step when pasting an image URL as a link (2)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>");

            // paste text (to have a history step recorded)
            pasteText(editor, "abxxxcd");
            // select xxx in "<p>ab[xxx]cd</p>""
            const p = editor.editable.querySelector("p");
            const selection = {
                anchorNode: p.childNodes[1],
                anchorOffset: 2,
                focusNode: p.childNodes[1],
                focusOffset: 5,
            };
            setSelection(selection);
            // paste url
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="${imgUrl}">${imgUrl}</a>[]cd</p>`
            );
        });

        test("should restore selection after pasting image URL followed by UNDO (1)", async () => {
            const { el, editor } = await setupEditor("<p>[abc]</p>");
            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick first command (Embed image)
            await press("Enter");
            // Undo
            undo(editor);
            expect(getContent(el)).toBe("<p>[abc]</p>");
        });

        test("should restore selection after pasting image URL followed by UNDO (2)", async () => {
            const { el, editor } = await setupEditor("<p>[abc]</p>");

            pasteText(editor, imgUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            // Undo
            undo(editor);
            expect(getContent(el)).toBe("<p>[abc]</p>");
        });
    });
});

describe("youtube video", () => {
    const config = { Plugins: [...MAIN_PLUGINS, ...NO_EMBEDDED_COMPONENTS_FALLBACK_PLUGINS] };
    describe("range collapsed", () => {
        beforeEach(() => {
            onRpc("/html_editor/video_url/data", async (request) => {
                const { params } = await request.json();
                return { embed_url: params.video_url };
            });
        });

        test("should paste and transform a youtube URL in a p (1)", async () => {
            const { el, editor } = await setupEditor("<p>ab[]cd</p>", { config });
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");
            // Wait for the getYoutubeVideoElement promise to resolve.
            await tick();
            expect(getContent(el)).toBe(
                `<p>ab</p><div data-oe-expression="${videoUrl}" class="media_iframe_video" contenteditable="false"><div class="css_editable_mode_display"></div><div class="media_iframe_video_size" contenteditable="false"></div><iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen" src="${videoUrl}"></iframe></div><p>[]cd</p>`
            );
        });

        test("should paste and transform a youtube URL in a span (1)", async () => {
            const { el, editor } = await setupEditor('<p>a<span class="a">b[]c</span>d</p>', {
                config,
            });
            pasteText(editor, "https://youtu.be/dQw4w9WgXcQ");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");
            // Wait for the getYoutubeVideoElement promise to resolve.
            await tick();
            expect(getContent(el)).toBe(
                '<p>a<span class="a">b</span></p><div data-oe-expression="https://youtu.be/dQw4w9WgXcQ" class="media_iframe_video" contenteditable="false"><div class="css_editable_mode_display"></div><div class="media_iframe_video_size" contenteditable="false"></div><iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen" src="https://youtu.be/dQw4w9WgXcQ"></iframe></div><p><span class="a">[]c</span>d</p>'
            );
        });

        test("should paste and not transform a youtube URL in a existing link", async () => {
            const { el, editor, plugins } = await setupEditor(
                '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                { config }
            );
            pasteText(editor, "https://youtu.be/dQw4w9WgXcQ");
            // Ensure the powerbox is active
            const powerbox = plugins.get("powerbox");
            expect(powerbox.overlay.isOpen).not.toBe(true);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                '<p>a<a href="http://existing.com">bhttps://youtu.be/dQw4w9WgXcQ[]c</a>d</p>'
            );
        });

        test("should paste a youtube URL as a link in a p (1)", async () => {
            const url = "https://youtu.be/dQw4w9WgXcQ";
            const { el, editor } = await setupEditor("<p>[]</p>", { config });
            pasteText(editor, url);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(`<p><a href="${url}">${url}</a>[]</p>`);
        });

        test("should not revert a history step when pasting a youtube URL as a link (1)", async () => {
            const url = "https://youtu.be/dQw4w9WgXcQ";
            const { el, editor } = await setupEditor("<p>[]</p>", { config });
            // paste text to have a history step recorded
            pasteText(editor, "*should not disappear*");
            pasteText(editor, url);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>*should not disappear*<a href="${url}">${url}</a>[]</p>`
            );
        });
    });

    describe("range not collapsed", () => {
        beforeEach(() => {
            onRpc("/html_editor/video_url/data", async (request) => {
                const { params } = await request.json();
                return { embed_url: params.video_url };
            });
        });

        test("should paste and transform a youtube URL in a p (2)", async () => {
            const { el, editor } = await setupEditor("<p>ab[xxx]cd</p>", { config });
            pasteText(editor, "https://youtu.be/dQw4w9WgXcQ");
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");
            // Wait for the getYoutubeVideoElement promise to resolve.
            await tick();
            expect(getContent(el)).toBe(
                '<p>ab</p><div data-oe-expression="https://youtu.be/dQw4w9WgXcQ" class="media_iframe_video" contenteditable="false"><div class="css_editable_mode_display"></div><div class="media_iframe_video_size" contenteditable="false"></div><iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen" src="https://youtu.be/dQw4w9WgXcQ"></iframe></div><p>[]cd</p>'
            );
        });

        test("should paste and transform a youtube URL in a span (2)", async () => {
            const { el, editor } = await setupEditor(
                '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                { config }
            );
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");
            // Wait for the getYoutubeVideoElement promise to resolve.
            await tick();
            expect(getContent(el)).toBe(
                `<p>a<span class="a">b</span></p><div data-oe-expression="${videoUrl}" class="media_iframe_video" contenteditable="false"><div class="css_editable_mode_display"></div><div class="media_iframe_video_size" contenteditable="false"></div><iframe frameborder="0" contenteditable="false" allowfullscreen="allowfullscreen" src="${videoUrl}"></iframe></div><p><span class="a">[]c</span>d</p>`
            );
        });

        test("should paste and not transform a youtube URL in a existing link", async () => {
            const { el, editor, plugins } = await setupEditor(
                '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                { config }
            );
            pasteText(editor, videoUrl);
            // Ensure the powerbox is active
            const powerbox = plugins.get("powerbox");
            expect(powerbox.overlay.isOpen).not.toBe(true);
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>a<a href="http://existing.com">b${videoUrl}[]c</a>d</p>`
            );
        });

        test("should paste a youtube URL as a link in a p (2)", async () => {
            const { el, editor } = await setupEditor("<p>ab[xxx]cd</p>", { config });
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="${videoUrl}">${videoUrl}</a>[]cd</p>`
            );
        });

        test("should not revert a history step when pasting a youtube URL as a link (2)", async () => {
            const { el, editor } = await setupEditor("<p>[]</p>", { config });
            // paste text (to have a history step recorded)
            pasteText(editor, "abxxxcd");
            // select xxx in "<p>ab[xxx]cd</p>"
            const p = editor.editable.querySelector("p");
            const selection = {
                anchorNode: p.childNodes[1],
                anchorOffset: 2,
                focusNode: p.childNodes[1],
                focusOffset: 5,
            };
            setSelection(selection);
            setSelection(selection);

            // paste url
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            expect(cleanLinkArtifacts(getContent(el))).toBe(
                `<p>ab<a href="${videoUrl}">${videoUrl}</a>[]cd</p>`
            );
        });

        test("should restore selection after pasting video URL followed by UNDO (1)", async () => {
            const { el, editor } = await setupEditor("<p>[abc]</p>", { config });
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Force powerbox validation on the default first choice
            await press("Enter");
            // Undo
            undo(editor);
            expect(getContent(el)).toBe("<p>[abc]</p>");
        });

        test("should restore selection after pasting video URL followed by UNDO (2)", async () => {
            const { el, editor } = await setupEditor("<p>[abc]</p>", { config });
            pasteText(editor, videoUrl);
            await animationFrame();
            await expectElementCount(".o-we-powerbox", 1);
            // Pick the second command (Paste as URL)
            await press("ArrowDown");
            await press("Enter");
            // Undo
            undo(editor);
            expect(getContent(el)).toBe("<p>[abc]</p>");
        });
    });
});

describe("youtube video with embedded components", () => {
    beforeEach(() => {
        onRpc("/html_editor/video_url/data", async (request) => {
            const { params } = await request.json();
            return { platform: "youtube", video_id: params.video_url.split("v=")[1] };
        });
    });
    const config = {
        Plugins: [...MAIN_PLUGINS, ...EMBEDDED_COMPONENT_PLUGINS],
        resources: { embedded_components: MAIN_EMBEDDINGS },
    };
    test("should embed a video on youtube URL paste", async () => {
        const { editor } = await setupEditor("<p>[]<br></p>", { config });
        pasteText(editor, videoUrl);
        await waitFor(".o-we-powerbox");
        // Pick first command (Embed video)
        await press("Enter");
        await waitFor(`[data-embedded="video"] iframe`);
        expect(`[data-embedded="video"] iframe`).toHaveCount(1);
    });
    test("should paste a youtube URL as a link in a p", async () => {
        const { el, editor } = await setupEditor("<p>[]<br></p>", { config });
        pasteText(editor, videoUrl);
        await waitFor(".o-we-powerbox");
        // Pick the second command (Paste as URL)
        await press("ArrowDown");
        await press("Enter");
        expect(cleanLinkArtifacts(getContent(el))).toBe(
            `<p><a href="${videoUrl}">${videoUrl}</a>[]</p>`
        );
    });
});

describe("Odoo editor own html", () => {
    test("should paste html as is", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(editor, '<div class="custom-paste oe_unbreakable">b</div>');
            },
            contentAfter: '<p>a</p><div class="custom-paste oe_unbreakable">b</div><p>[]b</p>',
        });
    });

    test("should not paste unsafe content", async () => {
        await testEditor({
            contentBefore: "<p>a[]b</p>",
            stepFunction: async (editor) => {
                pasteOdooEditorHtml(editor, `<script>console.log('xss attack')</script>`);
            },
            contentAfter: "<p>a[]b</p>",
        });
    });
});

describe("editable in iframe", () => {
    test("should paste odoo-editor html", async () => {
        const { el, editor } = await setupEditor("<p>[]</p>", { props: { iframe: true } });
        pasteOdooEditorHtml(editor, `<p>text<b>bold text</b>more text</p>`);
        expect(getContent(el)).toBe("<p>text<b>bold text</b>more text[]</p>");
    });
});

describe("Paste HTML tables", () => {
    // The tests below are very sensitive to whitespaces as they do represent actual
    // whitespace text nodes in the DOM. The tests will fail if those are removed.
    test("should keep all allowed style (Excel Online)", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    `<div ccp_infra_version='3' ccp_infra_timestamp='1684505961078' ccp_infra_user_hash='540904553' ccp_infra_copy_id=''
    data-ccp-timestamp='1684505961078'>
    <html>

    <head>
        <meta http-equiv=Content-Type content="text/html; charset=utf-8">
        <meta name=ProgId content=Excel.Sheet>
        <meta name=Generator content="Microsoft Excel 15">
        <style>
            table {
                mso-displayed-decimal-separator: "\\,";
                mso-displayed-thousand-separator: "\\.";
            }

            tr {
                mso-height-source: auto;
            }

            col {
                mso-width-source: auto;
            }

            td {
                padding-top: 1px;
                padding-right: 1px;
                padding-left: 1px;
                mso-ignore: padding;
                color: black;
                font-size: 11.0pt;
                font-weight: 400;
                font-style: normal;
                text-decoration: none;
                font-family: Calibri, sans-serif;
                mso-font-charset: 0;
                text-align: general;
                vertical-align: bottom;
                border: none;
                white-space: nowrap;
                mso-rotate: 0;
            }

            .font12 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 400;
                font-style: italic;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .font13 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-style: italic;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .font33 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-style: normal;
                text-decoration: none;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
            }

            .xl87 {
                font-size: 14.0pt;
                font-family: "Roboto Mono";
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl88 {
                color: #495057;
                font-size: 10.0pt;
                font-style: italic;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
                text-align: center;
            }

            .xl89 {
                color: #495057;
                font-size: 10.0pt;
                font-style: italic;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl90 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 0;
                text-align: center;
            }

            .xl91 {
                color: #495057;
                font-size: 10.0pt;
                font-weight: 700;
                text-decoration: underline;
                text-underline-style: single;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl92 {
                color: red;
                font-size: 10.0pt;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl93 {
                color: red;
                font-size: 10.0pt;
                text-decoration: underline;
                text-underline-style: single;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
            }

            .xl94 {
                color: #495057;
                font-size: 10.0pt;
                font-family: "Odoo Unicode Support Noto";
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
                background: yellow;
                mso-pattern: black none;
            }

            .xl95 {
                color: red;
                font-size: 10.0pt;
                font-family: Arial;
                mso-generic-font-family: auto;
                mso-font-charset: 1;
                text-align: center;
                background: yellow;
                mso-pattern: black none;
                white-space: normal;
            }
        </style>
    </head>

    <body link="#0563C1" vlink="#954F72">
        <table width=398 style='border-collapse:collapse;width:299pt'><!--StartFragment-->
            <col width=187 style='width:140pt'>
            <col width=211 style='width:158pt'>
            <tr height=20 style='height:15.0pt'>
                <td width=187 height=20 class=xl88 dir=LTR style='width:140pt;height:15.0pt'><span class=font12>Italic
                        then also </span><span class=font13>BOLD</span></td>
                <td width=211 class=xl89 dir=LTR style='width:158pt'><s>Italic strike</s></td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl90 dir=LTR style='height:15.0pt'><span class=font33>Just bold </span><span
                        class=font12>Just Italic</span></td>
                <td class=xl91 dir=LTR>Bold underline</td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl92 dir=LTR style='height:15.0pt'>Color text</td>
                <td class=xl93 dir=LTR><s>Color strike and underline</s></td>
            </tr>
            <tr height=20 style='height:15.0pt'>
                <td height=20 class=xl94 dir=LTR style='height:15.0pt'>Color background</td>
                <td width=211 class=xl95 dir=LTR style='width:158pt'>Color text on color background</td>
            </tr>
            <tr height=27 style='height:20.25pt'>
                <td colspan=2 width=398 height=27 class=xl87 dir=LTR style='width:299pt;height:20.25pt'>14pt MONO TEXT
                </td>
            </tr><!--EndFragment-->
        </table>
    </body>

    </html>
</div>`
                );
            },
            contentAfter: `<table class="table table-bordered o_table">
${"            "}
${"            "}
            <tbody><tr>
                <td>Italic
                        then also BOLD</td>
                <td><s>Italic strike</s></td>
            </tr>
            <tr>
                <td>Just bold Just Italic</td>
                <td>Bold underline</td>
            </tr>
            <tr>
                <td>Color text</td>
                <td><s>Color strike and underline</s></td>
            </tr>
            <tr>
                <td>Color background</td>
                <td>Color text on color background</td>
            </tr>
            <tr>
                <td>14pt MONO TEXT
                []</td>
            </tr>
        </tbody></table>`,
        });
    });

    test("should keep all allowed style (Google Sheets)", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    `<google-sheets-html-origin>
    <style type="text/css">
        td {
            border: 1px solid #cccccc;
        }

        br {
            mso-data-placement: same-cell;
        }
    </style>
    <table xmlns="http://www.w3.org/1999/xhtml" cellspacing="0" cellpadding="0" dir="ltr" border="1"
        style="table-layout:fixed;font-size:10pt;font-family:Arial;width:0px;border-collapse:collapse;border:none">
        <colgroup>
            <col width="170" />
            <col width="187" />
        </colgroup>
        <tbody>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Odoo Unicode Support Noto;font-weight:normal;font-style:italic;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Italic then also BOLD&quot;}"
                    data-sheets-textstyleruns="{&quot;1&quot;:0,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;}}{&quot;1&quot;:17,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;,&quot;5&quot;:1}}">
                    <span style="font-size:10pt;font-family:Arial;font-style:italic;color:#495057;">Italic then also
                    </span><span
                        style="font-size:10pt;font-family:Arial;font-weight:bold;font-style:italic;color:#495057;">BOLD</span>
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-style:italic;text-decoration:line-through;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Italic strike&quot;}">Italic strike</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Odoo Unicode Support Noto;font-weight:bold;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Just bold Just italic&quot;}"
                    data-sheets-textstyleruns="{&quot;1&quot;:0,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;}}{&quot;1&quot;:10,&quot;2&quot;:{&quot;3&quot;:&quot;Arial&quot;,&quot;5&quot;:0,&quot;6&quot;:1}}">
                    <span
                        style="font-size:10pt;font-family:Arial;font-weight:bold;font-style:normal;color:#495057;">Just
                        Bold </span><span style="font-size:10pt;font-family:Arial;font-style:italic;color:#495057;">Just
                        Italic</span>
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-weight:bold;text-decoration:underline;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Bold underline&quot;}">Bold underline</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color text&quot;}"><span style="color:#ff0000;">Color text</span></td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;text-decoration:underline line-through;color:#ff0000;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color strike and underline&quot;}">Color
                    strike and underline</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;background-color:#ffff00;font-family:Odoo Unicode Support Noto;font-weight:normal;color:#495057;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color background&quot;}">Color background
                </td>
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;background-color:#ffff00;color:#ff0000;"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;Color text on color background&quot;}">Color
                    text on color background</td>
            </tr>
            <tr style="height:21px;">
                <td style="overflow:hidden;padding:2px 3px 2px 3px;vertical-align:bottom;font-family:Roboto Mono;font-size:14pt;font-weight:normal;text-align:center;"
                    rowspan="1" colspan="2"
                    data-sheets-value="{&quot;1&quot;:2,&quot;2&quot;:&quot;14pt MONO TEXT&quot;}">14pt MONO TEXT</td>
            </tr>
        </tbody>
    </table>
</google-sheets-html-origin>`
                );
            },
            contentAfter: `<table class="table table-bordered o_table">
${"        "}
${"            "}
${"            "}
${"        "}
        <tbody>
            <tr>
                <td>
                    Italic then also
                    BOLD
                </td>
                <td>Italic strike</td>
            </tr>
            <tr>
                <td>
                    Just
                        Bold Just
                        Italic
                </td>
                <td>Bold underline</td>
            </tr>
            <tr>
                <td>Color text</td>
                <td>Color
                    strike and underline</td>
            </tr>
            <tr>
                <td>Color background
                </td>
                <td>Color
                    text on color background</td>
            </tr>
            <tr>
                <td>14pt MONO TEXT[]</td>
            </tr>
        </tbody>
    </table>`,
        });
    });

    test("should keep all allowed style (Libre Office)", async () => {
        await testEditor({
            contentBefore: "<p>[]</p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    `<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
<html>

<head>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    <title></title>
    <meta name="generator" content="LibreOffice 6.4.7.2 (Linux)" />
    <style type="text/css">
        body,
        div,
        table,
        thead,
        tbody,
        tfoot,
        tr,
        th,
        td,
        p {
            font-family: "Arial";
            font-size: x-small
        }

        a.comment-indicator:hover+comment {
            background: #ffd;
            position: absolute;
            display: block;
            border: 1px solid black;
            padding: 0.5em;
        }

        a.comment-indicator {
            background: red;
            display: inline-block;
            border: 1px solid black;
            width: 0.5em;
            height: 0.5em;
        }

        comment {
            display: none;
        }
    </style>
</head>

<body>
    <table cellspacing="0" border="0">
        <colgroup width="212"></colgroup>
        <colgroup width="209"></colgroup>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left"><i>Italic then also BOLD</i></td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><i><s>Italic strike</s></i></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left"><b>Just bold Just italic</b></td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><b><u>Bold underline</u></b></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left">
                <font color="#FF0000">Color text</font>
            </td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left"><u><s>
                        <font color="#FF0000">Color strike and underline</font>
                    </s></u></td>
        </tr>
        <tr>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                height="20" align="left" bgcolor="#FFFF00">Color background</td>
            <td style="border-top: 1px solid #000000; border-bottom: 1px solid #000000; border-left: 1px solid #000000; border-right: 1px solid #000000"
                align="left" bgcolor="#FFFF00">
                <font color="#FF0000">Color text on color background</font>
            </td>
        </tr>
        <tr>
            <td colspan=2 height="26" align="center" valign=middle>
                <font face="Andale Mono" size=4>14pt MONO TEXT</font>
            </td>
        </tr>
    </table>
</body>

</html>`
                );
            },
            contentAfter: `<table class="table table-bordered o_table">
${"        "}
${"        "}
        <tbody><tr>
            <td><i>Italic then also BOLD</i></td>
            <td><i><s>Italic strike</s></i></td>
        </tr>
        <tr>
            <td><b>Just bold Just italic</b></td>
            <td><b><u>Bold underline</u></b></td>
        </tr>
        <tr>
            <td>
                Color text
            </td>
            <td><u><s>
                        Color strike and underline
                    </s></u></td>
        </tr>
        <tr>
            <td>Color background</td>
            <td>
                Color text on color background
            </td>
        </tr>
        <tr>
            <td>
                14pt MONO TEXT[]
            </td>
        </tr>
    </tbody></table>`,
        });
    });

    test("should apply default table classes (table, table-bordered, o_table) on paste", async () => {
        await testEditor({
            contentBefore: `
                <p>[]<br></p>
            `,
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    unformat(`
                        <table>
                            <tbody>
                                <tr>
                                    <td></td>
                                </tr>
                            </tbody>
                        </table>
                    `)
                );
            },
            contentAfter: unformat(`
                <table class="table table-bordered o_table">
                    <tbody>
                        <tr>
                            <td><p>[]<br></p></td>
                        </tr>
                    </tbody>
                </table>
            `),
        });
    });

    test("should move all rows from thead to tbody", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    unformat(`
                        <table>
                            <thead>
                                <tr>
                                    <th>1</th>
                                    <th>2</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr>
                                    <td>1</td>
                                    <td>2</td>
                                </tr>
                                <tr>
                                    <td>1</td>
                                    <td>2</td>
                                </tr>
                            </tbody>
                        </table>
                    `)
                );
            },
            contentAfter: unformat(`
                        <table class="table table-bordered o_table">
                            <tbody>
                                <tr>
                                    <th>1</th>
                                    <th>2</th>
                                </tr>
                                <tr>
                                    <td>1</td>
                                    <td>2</td>
                                </tr>
                                <tr>
                                    <td>1</td>
                                    <td>2[]</td>
                                </tr>
                            </tbody>
                        </table>
                    `),
        });
    });
    test("should replace thead element with tbody", async () => {
        await testEditor({
            contentBefore: "<p>[]<br></p>",
            stepFunction: async (editor) => {
                pasteHtml(
                    editor,
                    unformat(`
                        <table>
                            <thead>
                                <tr>
                                    <th>1</th>
                                    <th>2</th>
                                </tr>
                            </thead>
                        </table>
                    `)
                );
            },
            contentAfter: unformat(`
                        <table class="table table-bordered o_table">
                            <tbody>
                                <tr>
                                    <th>1</th>
                                    <th>2[]</th>
                                </tr>
                            </tbody>
                        </table>
                    `),
        });
    });
});

describe("onDrop", () => {
    test("should drop text from htmlTransferItem", async () => {
        const { el } = await setupEditor("<p>a[b]cd</p>");
        const pElement = el.firstChild;
        const textNode = pElement.firstChild;

        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: textNode, offset: 0 }),
        });

        const dropData = new DataTransfer();
        dropData.setData("text/html", "b");
        await dispatch(pElement, "drop", { dataTransfer: dropData });
        await tick();

        expect(getContent(el)).toBe("<p>b[]acd</p>");
    });
    test("should not be able to paste inside some branded node", async () => {
        const { el } = await setupEditor(`<p data-oe-model="foo" data-oe-type="text">a[b]cd</p>`);
        const pElement = el.firstChild;
        const textNode = pElement.firstChild;

        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: textNode, offset: 3 }),
        });

        const dropData = new DataTransfer();
        dropData.setData("text/html", "x");

        await dispatch(pElement, "drop", { dataTransfer: dropData });
        await tick();

        expect(getContent(el)).toBe(`<p data-oe-model="foo" data-oe-type="text">a[b]cd</p>`);
    });
    test("should add new images form fileTransferItems", async () => {
        const { el } = await setupEditor(`<p>ab[]cd</p>`);
        const pElement = el.firstChild;
        const textNode = pElement.firstChild;

        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: textNode, offset: 3 }),
        });

        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";
        const blob = dataURItoBlob(base64Image);
        const dropData = new DataTransfer();
        const f = new File([blob], "image.png", { type: blob.type });
        dropData.items.add(f);
        await dispatch(pElement, "drop", { dataTransfer: dropData });
        await waitFor("img");
        expect(getContent(el)).toBe(
            `<p>abc<img class="img-fluid" data-file-name="image.png" src="${base64Image}">[]d</p>`
        );
    });
    test("should move an image if it originated from the editor", async () => {
        const base64Image =
            "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAIAQMAAAD+wSzIAAAABlBMVEX///+/v7+jQ3Y5AAAADklEQVQI12P4AIX8EAgALgAD/aNpbtEAAAAASUVORK5CYII=";

        const { el } = await setupEditor(
            `<p>a[<img class="img-fluid" data-file-name="image.png" src="${base64Image}">]bc</p>`
        );
        const pElement = el.firstChild;
        const imgElement = pElement.childNodes[1];
        const bcTextNode = pElement.childNodes[2];

        patchWithCleanup(document, {
            caretPositionFromPoint: () => ({ offsetNode: bcTextNode, offset: 1 }),
        });

        const dragdata = new DataTransfer();
        await dispatch(imgElement, "dragstart", { dataTransfer: dragdata });
        await animationFrame();
        const imageHTML = dragdata.getData("application/vnd.odoo.odoo-editor-node");
        expect(imageHTML).toBe(
            `<img class="img-fluid" data-file-name="image.png" src="${base64Image}">`
        );

        const dropData = new DataTransfer();
        dropData.setData(
            "text/html",
            `<meta http-equiv="Content-Type" content="text/html;charset=UTF-8"><img src="${base64Image}">`
        );
        // Simulate the application/vnd.odoo.odoo-editor-node data that the browser would do.
        dropData.setData("application/vnd.odoo.odoo-editor-node", imageHTML);
        await dispatch(pElement, "drop", { dataTransfer: dropData });
        await animationFrame();

        expect(getContent(el)).toBe(
            `<p>ab<img class="img-fluid" data-file-name="image.png" src="${base64Image}">[]c</p>`
        );
    });
});
