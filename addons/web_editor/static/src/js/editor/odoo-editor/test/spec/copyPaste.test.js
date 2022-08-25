import {
    BasicEditor,
    testEditor
} from "../utils.js";
import {CLIPBOARD_WHITELISTS} from "../../src/OdooEditor.js";

// Mock an paste event and send it to the editor.
const pasteData = async function (editor, text, type) {
    var mockEvent = {
        dataType: 'text/plain',
        data: text,
        clipboardData: {
            getData: (datatype) => type === datatype ? text : null,
            files: [],
            items: [],
        },
        preventDefault: () => {},
    };
    await editor._onPaste(mockEvent);
};

const pasteText = async (editor, text) => pasteData(editor, text, 'text/plain');
const pasteHtml = async (editor, html) => pasteData(editor, html, 'text/html');

describe('Copy and paste', () => {
    describe('Html Paste cleaning', () => {
        describe('whitelist', async () => {
            it('should keep whitelisted Tags tag', async () => {
                for (const node of CLIPBOARD_WHITELISTS.nodes) {
                    if (!['TABLE', 'THEAD', 'TH', 'TBODY', 'TR', 'TD', 'IMG', 'BR', 'LI', '.fa'].includes(node)) {
                        const isInline = ['I', 'B', 'U', 'EM', 'STRONG', 'IMG', 'BR', 'A'].includes(node)
                        const html = isInline ? `a<${node.toLowerCase()}>b</${node.toLowerCase()}>c` : `a</p><${node.toLowerCase()}>b</${node.toLowerCase()}><p>c`;

                        await testEditor(BasicEditor, {
                            contentBefore: '<p>123[]4</p>',
                            stepFunction: async editor => {
                                await pasteHtml(editor, `a<${node.toLowerCase()}>b</${node.toLowerCase()}>c`);
                            },
                            contentAfter: '<p>123' + html + '[]4</p>',
                        });
                    }
                }

            });
            it('should keep whitelisted Tags tag (2)', async () => {
                const tagsToKeep = [
                    'a<img src="http://www.imgurl.com/img.jpg">d', // img tag
                    'a<br>b' // br tags
                ];

                for (const tagToKeep of tagsToKeep) {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>123[]</p>',
                        stepFunction: async editor => {
                            await pasteHtml(editor, tagToKeep);
                        },
                        contentAfter: '<p>123' + tagToKeep + '[]</p>',
                    });
                }
            });
            it('should keep tables Tags tag and add classes', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<table><thead><tr><th>h</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table>d');
                    },
                    contentAfter: '<p>123a</p><table class="table table-bordered"><thead><tr><th>h</th></tr></thead><tbody><tr><td>b</td></tr></tbody></table><p>d[]</p>',
                });
            });
            it('should not keep span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<span>bc</span>d');
                    },
                    contentAfter: '<p>123abcd[]</p>',
                });
            });
            it('should not keep orphan LI', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<li>bc</li>d');
                    },
                    contentAfter: '<p>123a</p><p>bc</p><p>d[]</p>',
                });
            });
            it('should keep LI in UL', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<ul><li>bc</li></ul>d');
                    },
                    contentAfter: '<p>123a</p><ul><li>bc</li></ul><p>d[]</p>',
                });
            });
            it('should keep P and B and not span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]xx</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<p>bc</p>d<span>e</span>f<b>g</b>h');
                    },
                    contentAfter: '<p>123a</p><p>bc</p><p>def<b>g</b>h[]xx</p>',
                });
            });
            it('should keep styled span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<span style="text-decoration: underline">bc</span>d');
                    },
                    contentAfter: '<p>123a<span style="text-decoration: underline">bc</span>d[]</p>',
                });
            });
        });
    });
    describe('Simple text', () => {
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'x');
                    },
                    contentAfter: '<p>x[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>abx[]cd</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'xyz 123');
                    },
                    contentAfter: '<p>abxyz 123[]cd</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x    y');
                    },
                    contentAfter: '<p>abx    y[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span>bx[]c</span>d</p>',
                });
            });
            // TODO: We might want to have it consider \n as paragraph breaks
            // instead of linebreaks but that would be an opinionated choice.
            it('should paste text and understand \n newlines', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br/></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'a\nb\nc\nd');
                    },
                    contentAfter: '<p>a<br>b<br>c<br>d[]<br></p>',
                });
            });
            it('should paste text and understand \r\n newlines', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br/></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'a\r\nb\r\nc\r\nd');
                    },
                    contentAfter: '<p>a<br>b<br>c<br>d[]<br></p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>ax[]d</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'xyz 123');
                    },
                    contentAfter: '<p>axyz 123[]d</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x    y');
                    },
                    contentAfter: '<p>ax    y[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'y');
                    },
                    contentAfter: '<p>a<span>by[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>a<p>bx[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'y');
                    },
                    contentAfter: '<div>a<p>by[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>ab<span>cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'y');
                    },
                    contentAfter: '<div>ay[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>1a<p>bx[]<span>e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>2a<span>bx[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Simple html span', () => {
        const simpleHtmlCharX = '<span style="color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">x</span>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>x[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>abx[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>ax[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<p>bx[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ab<span>cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ax[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]<span>e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<span>bx[]</span>e<br>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>3a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>3a<p>bx[]e</p>f</div>',
                });
            });
        });
    });
    describe('Simple html p', () => {
        const simpleHtmlCharX = '<p>x</p>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>x[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>abx[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>ax[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span>bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<p>bx[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ab<span>cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ax[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]<span>e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<span>bx[]</span>e<br>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>3a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>3a<p>bx[]e</p>f</div>',
                });
            });
        });
    });
    describe('Complex html span', () => {
        const complexHtmlData = '<span style="color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">1</span><b style="box-sizing: border-box; font-weight: bolder; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">23</b><span style="color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;"><span> </span>4</span>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1<b>23</b>&nbsp;4[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab1<b>23</b>&nbsp;4[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b>&nbsp;4[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a1<b>23</b>&nbsp;4[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b>&nbsp;4[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b>&nbsp;4[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b>&nbsp;4[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>ab<span>c1<b>23</b>&nbsp;4[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a1<b>23</b>&nbsp;4[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<b>23</b>&nbsp;4[]<span>e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span>b1<b>23</b>&nbsp;4[]</span>e<br>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>3a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>3a<p>b1<b>23</b>&nbsp;4[]e</p>f</div>',
                });
            });
        });
    });
    describe('Complex html p', () => {
        const complexHtmlData = '<p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">12</p><p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">34</p>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>12</p><p>34[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab12</p><p>34[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span>34[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a12</p><p>34[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span>34[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1a<span>b12</span></p><p><span>34[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a<span>b12</span></p><p><span>34[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b12</p><p>34[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b12</p><p>34[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span>c12<br>34[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a12<br>34[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span>c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span>c12</span></p><p><span>34[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span>c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a12</p><p>34[]<span>d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    // FIXME: Bringing `e` and `f` into the `<p>` is a tradeOff
                    // Should we change it ? How ? Might warrant a discution.
                    // possible alt contentAfter : <div>1a<p>b12</p>34[]<span>e</span>f</div>
                    contentAfter: '<div>1a<p>b12</p><p>34[]<span>e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span>b12<br>34[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Complex html 3 p', () => {
        const complexHtmlData = '<p>1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6</p>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span>5<i>X</i>6[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span>5<i>X</i>6[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1a<span>b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span>5<i>X</i>6[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a<span>b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span>5<i>X</i>6[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span>c1<i>X</i>2</span><p>3<i>X</i>4</p><span>5<i>X</i>6[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a1<i>X</i>2<p>3<i>X</i>4</p>5<i>X</i>6[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span>c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span>c1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span>5<i>X</i>6[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span>c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span>d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span>e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span>b1<i>X</i>2</span><p>3<i>X</i>4</p><span>5<i>X</i>6[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Complex html p+i', () => {
        const complexHtmlData = '<p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">12</p><p style="box-sizing: border-box; margin-top: 0px; margin-bottom: 1rem; color: rgb(0, 0, 0); font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-size: 16px; font-style: normal; font-variant-ligatures: normal; font-variant-caps: normal; font-weight: 400; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; background-color: rgb(255, 255, 255); text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;"><i style="box-sizing: border-box;">ii</i></p>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>12</p><p><i>ii</i>[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab12</p><p><i>ii</i>[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span><i>ii</i>[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a12</p><p><i>ii</i>[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span><i>ii</i>[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span><i>ii</i>[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b12</span></p><p><span><i>ii[]</i>e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b12</p><p><i>ii</i>[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b12</p><p><i>ii</i>[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span>c12<i><br>ii</i>[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a12<i><br>ii</i>[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span>c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span>c12</span></p><p><span><i>ii</i>[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span>c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a12</p><p><i>ii</i>[]<span>d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b12</p><p><i>ii</i>[]<span>e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span>b12<i><br>ii</i>[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Complex html 3p+b', () => {
        const complexHtmlData = '<p>1<b>23</b></p><p>zzz</p><p>45<b>6</b>7</p>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b></span></p><p>zzz</p><p><span>45<b>6</b>7[]c</span>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b></span></p><p>zzz</p><p><span>45<b>6</b>7[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span><span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b></span></p><p>zzz</p><p><span>45<b>6</b>7[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[c</span>- -<span>d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span>b1<b>23</b></span></p><p>zzz</p><p><span>45<b>6</b>7[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1ab<span>c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span>c1<b>23</b></span><p>zzz</p><span>45<b>6</b>7[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span>c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a1<b>23</b><p>zzz</p>45<b>6</b>7[]<span>d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span>d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]<span>e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span>b1<b>23</b></span><p>zzz</p><span>45<b>6</b>7[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Special cases', () => {
        describe('lists', async () => {
            it('should paste a list in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>12[]34</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>abc</li><li>def</li><li>ghi</li></ul>');
                    },
                    contentAfter: '<p>12</p><ul><li>abc</li><li>def</li><li>ghi</li></ul>[]<p>34</p>',
                });
            });
            it('should paste the text of an li into another li', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>123</li></ul>');
                    },
                    contentAfter: '<ul><li>abc</li><li>de123[]f</li><li>ghi</li></ul>',
                });
            });
            it('should paste the text of an li into another li, and the text of another li into the next li', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>123</li><li>456</li></ul>');
                    },
                    contentAfter: '<ul><li>abc</li><li>de123</li><li>456[]f</li><li>ghi</li></ul>',
                });
            });
            it('should paste the text of an li into another li, insert a new li, and paste the text of a third li into the next li', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>abc</li><li>de[]f</li><li>ghi</li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>123</li><li>456</li><li>789</li></ul>');
                    },
                    contentAfter: '<ul><li>abc</li><li>de123</li><li>456</li><li>789[]f</li><li>ghi</li></ul>',
                });
            });
            it('should paste the text of an li into another li and insert a new li at the end of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>123</li><li>456</li></ul>');
                    },
                    contentAfter: '<ul><li>abc</li><li>def</li><li>ghi123</li><li>456[]</li></ul>',
                });
            });
            it('should insert a new li at the beginning of a list and paste the text of another li into the next li', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>[]abc</li><li>def</li><li>ghi</li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>123</li><li>456</li></ul>');
                    },
                    contentAfter: '<ul><li>123</li><li>456[]abc</li><li>def</li><li>ghi</li></ul>',
                });
            });
        });
    });

    describe('link', () => {
        describe('range collapsed', async () => {
            it('should paste and transform an URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>ab<a href="http://www.xyz.com">http://www.xyz.com</a>[]cd</p>',
                });
            });
            it('should paste and transform an URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<span>b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
                });
            });
            it('should paste and not transform an URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttp://www.xyz.com[]c</a>d</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'random');
                    },
                    contentAfter: '<p>a<a href="http://existing.com">brandom[]c</a>d</p>',
                });
            });
            it('should paste and transform an URL in a existing link if pasting valid url', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.xyz.xdc');
                    },
                    contentAfter: '<p>a<a href="https://www.xyz.xdcc">https://www.xyz.xdc[]c</a>d</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[].com</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'oom');
                    },
                    contentAfter: '<p>a<a href="https://boom.com">boom[].com</a>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste and transform an URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[xxx]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>ab<a href="http://www.xyz.com">http://www.xyz.com</a>[]cd</p>',
                });
            });
            it('should paste and transform an URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<span>b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
                });
            });
            it('should paste and not transform an URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttp://www.xyz.com[]c</a>d</p>',
                });
            });
        });
    });
    describe('images', () => {
        describe('range collapsed', async () => {
            it('should paste and transform an image URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>ab<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]cd</p>',
                });
            });
            it('should paste and transform an image URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<span>b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</span>d</p>',
                });
            });
            it('should paste and transform an image URL in an existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<a href="http://existing.com">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</a>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste and transform an image URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[xxx]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>ab<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]cd</p>',
                });
            });
            it('should paste and transform an image URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<span>b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</span>d</p>',
                });
            });
            it('should paste and transform an image URL inside an existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<a href="http://existing.com">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</a>d</p>',
                });
            });
        });
    });
    describe('youtube video', () => {
        describe('range collapsed', async () => {
            it('should paste and transform a youtube URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>ab<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]cd</p>',
                });
            });
            it('should paste and transform a youtube URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://youtu.be/dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<span>b<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]c</span>d</p>',
                });
            });
            it('should paste and not transform a youtube  URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://youtu.be/dQw4w9WgXcQ');
                        // Ensure the powerbox is not active
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttps://youtu.be/dQw4w9WgXcQ[]c</a>d</p>',
                });
            });
        });
        describe('range not collapsed', async () => {
            it('should paste and transform a youtube URL in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[xxx]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://youtu.be/dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>ab<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]cd</p>',
                });
            });
            it('should paste and transform a youtube URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span>b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
                    },
                    contentAfter: '<p>a<span>b<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]c</span>d</p>',
                });
            });
            it('should paste and not transform a youtube URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
                        // Ensure the powerbox is not active
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttps://www.youtube.com/watch?v=dQw4w9WgXcQ[]c</a>d</p>',
                });
            });
        });
    });
});
