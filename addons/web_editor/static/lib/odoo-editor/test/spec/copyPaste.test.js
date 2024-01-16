import {
    BasicEditor,
    testEditor,
    triggerEvent,
    setTestSelection,
    Direction,
    pasteHtml,
    pasteText,
} from "../utils.js";
import {CLIPBOARD_WHITELISTS} from "../../src/OdooEditor.js";

describe('Copy and paste', () => {
    describe('Html Paste cleaning', () => {
        describe('whitelist', async () => {
            it('should keep whitelisted Tags tag', async () => {
                for (const node of CLIPBOARD_WHITELISTS.nodes) {
                    if (!['TABLE', 'THEAD', 'TH', 'TBODY', 'TR', 'TD', 'IMG', 'BR', 'LI', '.fa'].includes(node)) {
                        const isInline = ['I', 'B', 'U', 'S', 'EM', 'STRONG', 'IMG', 'BR', 'A', 'FONT'].includes(node);
                        const html = isInline ? `a<${node.toLowerCase()}>b</${node.toLowerCase()}>c` : `a</p><${node.toLowerCase()}>b</${node.toLowerCase()}><p>c`;

                        await testEditor(BasicEditor, {
                            contentBefore: '<p>123[]4</p>',
                            stepFunction: async editor => {
                                await pasteHtml(editor, `a<${node.toLowerCase()}>b</${node.toLowerCase()}>c`);
                            },
                            contentAfter: '<p>123' + html.replace(/<\/?font>/g, '') + '[]4</p>',
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
                    contentAfter: '<p>abx&nbsp; &nbsp; y[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
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
                    contentAfter: '<p>ax&nbsp; &nbsp; y[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'y');
                    },
                    contentAfter: '<p>a<span class="a">by[]e</span>f</p>',
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
                    contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'y');
                    },
                    contentAfter: '<div>ay[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'x');
                    },
                    contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
                });
            });
        });
    });
    describe('Simple html span', () => {
        const simpleHtmlCharX = '<span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">x</span>';
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
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
                    contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ax[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<p>a<span class="a">bx[]e</span>f</p>',
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
                    contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ab<span class="a">cx[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>ax[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>1a<p>bx[]<span class="a">e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, simpleHtmlCharX);
                    },
                    contentAfter: '<div>2a<span class="a">bx[]</span>e<br>f</div>',
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
        const complexHtmlData = '<span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;">1</span><b style="box-sizing: border-box; font-weight: bolder; font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial;">23</b><span style="font-family: -apple-system, BlinkMacSystemFont, &quot;Segoe UI&quot;, Roboto, &quot;Helvetica Neue&quot;, Arial, &quot;Noto Sans&quot;, sans-serif, &quot;Apple Color Emoji&quot;, &quot;Segoe UI Emoji&quot;, &quot;Segoe UI Symbol&quot;, &quot;Noto Color Emoji&quot;; font-variant-ligatures: normal; font-variant-caps: normal; letter-spacing: normal; orphans: 2; text-align: left; text-indent: 0px; text-transform: none; white-space: normal; widows: 2; word-spacing: 0px; -webkit-text-stroke-width: 0px; text-decoration-thickness: initial; text-decoration-style: initial; text-decoration-color: initial; display: inline !important; float: none;"><span> </span>4</span>';
        describe('range collapsed', async () => {
            it('should paste a text at the beginning of a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1<b style="font-weight: bolder">23</b>&nbsp;4[]abcd</p>',
                });
            });
            it('should paste a text in a p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>ab1<b style="font-weight: bolder">23</b>&nbsp;4[]cd</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b style="font-weight: bolder">23</b>&nbsp;4[]c</span>d</p>',
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
                    contentAfter: '<p>a1<b style="font-weight: bolder">23</b>&nbsp;4[]d</p>',
                });
            });
            it('should paste a text in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two p', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</p>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p>- -<p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a<p>b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</p>f</div>',
                });
            });
            it('should paste a text when selection leave a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>ab<span class="a">c1<b style="font-weight: bolder">23</b>&nbsp;4[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a1<b style="font-weight: bolder">23</b>&nbsp;4[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<b style="font-weight: bolder">23</b>&nbsp;4[]<span class="a">e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b1<b style="font-weight: bolder">23</b>&nbsp;4[]</span>e<br>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>3a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>3a<p>b1<b style="font-weight: bolder">23</b>&nbsp;4[]e</p>f</div>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a">34[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a<span class="a">b12</span></p><p><span class="a">34[]e</span>f</p>',
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
                    contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span class="a">c12<br>34[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a12<br>34[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span class="a">c12</span></p><p><span class="a">34[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a12</p><p>34[]<span class="a">d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    // FIXME: Bringing `e` and `f` into the `<p>` is a tradeOff
                    // Should we change it ? How ? Might warrant a discussion.
                    // possible alt contentAfter : <div>1a<p>b12</p>34[]<span>e</span>f</div>
                    contentAfter: '<div>1a<p>b12</p><p>34[]<span class="a">e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b12<br>34[]</span>e<br>f</div>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a<span class="a">b1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]e</span>f</p>',
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
                    contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span class="a">c1<i>X</i>2</span><p>3<i>X</i>4</p><span class="a">5<i>X</i>6[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a1<i>X</i>2<p>3<i>X</i>4</p>5<i>X</i>6[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span class="a">c1<i>X</i>2</span></p><p>3<i>X</i>4</p><p><span class="a">5<i>X</i>6[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span class="a">d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<i>X</i>2</p><p>3<i>X</i>4</p><p>5<i>X</i>6[]<span class="a">e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b1<i>X</i>2</span><p>3<i>X</i>4</p><span class="a">5<i>X</i>6[]</span>e<br>f</div>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii</i>[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b12</span></p><p><span class="a"><i>ii[]</i>e</span>f</p>',
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
                    contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span class="a">c12<i><br>ii</i>[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a12<i><br>ii</i>[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection leave a span (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>1ab<span class="a">c[d</span>e]f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>1ab<span class="a">c12</span></p><p><span class="a"><i>ii</i>[]</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>2a[b<span class="a">c]d</span>ef</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>2a12</p><p><i>ii</i>[]<span class="a">d</span>ef</p>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b12</p><p><i>ii</i>[]<span class="a">e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b12<i><br>ii</i>[]</span>e<br>f</div>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b></span></p><p>zzz</p><p><span class="a">45<b>6</b>7[]e</span>f</p>',
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
                    contentBefore: '<div>1ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1ab<span class="a">c1<b>23</b></span><p>zzz</p><span class="a">45<b>6</b>7[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a1<b>23</b><p>zzz</p>45<b>6</b>7[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<b>23</b></p><p>zzz</p><p>45<b>6</b>7[]<span class="a">e</span>f</p></div>',
                });
            });
            it('should paste a text when selection across two element (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b1<b>23</b></span><p>zzz</p><span class="a">45<b>6</b>7[]</span>e<br>f</div>',
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
                    contentAfter: '<p>12</p><ul><li>abc</li><li>def</li><li>ghi</li></ul><p>[]34</p>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<span class="a">b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
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
            it('should replace link for new content when pasting in an empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#" oe-zws-empty-inline="">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc');
                    },
                    contentAfter: '<p>abc[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>xy<a href="#" oe-zws-empty-inline="">\u200B[]</a>z</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc');
                    },
                    contentAfter: '<p>xyabc[]z</p>',
                });
            });
            it('should paste and transform plain text content over an empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc www.odoo.com xyz');
                    },
                    contentAfter: '<p>abc <a href="https://www.odoo.com">www.odoo.com</a> xyz[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'odoo.com\ngoogle.com');
                    },
                    contentAfter: '<p><a href="https://odoo.com">odoo.com</a><br><a href="https://google.com">google.com</a>[]<br></p>',
                });
            });
            it('should paste html content over an empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>');
                    },
                    contentAfter: '<p><a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>[]</p>',
                });
            });
            it('should paste and transform URL among text', async () => {
                const url = 'https://www.odoo.com';
                const imgUrl = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                const videoUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${url} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${url}">${url}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${imgUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${videoUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${videoUrl}">${videoUrl}</a> def[]</p>`,
                });
            });
            it('should paste and transform multiple URLs', async () => {
                const url = 'https://www.odoo.com';
                const imgUrl = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                const videoUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `${url} ${videoUrl} ${imgUrl}`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `${url} abc ${videoUrl} def ${imgUrl}`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p><a href="${url}">${url}</a> abc <a href="${videoUrl}">${videoUrl}</a> def <a href="${imgUrl}">${imgUrl}</a>[]</p>`,
                });
            });
            it('should paste plain text inside non empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">a[]b</a></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<span>123</span>');
                    },
                    contentAfter: '<p><a href="#">a123[]b</a></p>',
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
                    contentBefore: '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://www.xyz.com');
                    },
                    contentAfter: '<p>a<span class="a">b<a href="http://www.xyz.com">http://www.xyz.com</a>[]c</span>d</p>',
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
            it('should restore selection when pasting plain text followed by UNDO', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'def');
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'www.odoo.com');
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'def www.odoo.com xyz');
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
            });
            it('should restore selection after pasting HTML followed by UNDO', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>');
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
            });
            it('should paste and transform URLs among text or multiple URLs', async () => {
                const url = 'https://www.odoo.com';
                const imgUrl = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                const videoUrl = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${url} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${url}">${url}</a> def[]<br></p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${imgUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]<br></p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${videoUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${videoUrl}">${videoUrl}</a> def[]<br></p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `${url} ${videoUrl} ${imgUrl}`);
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]<br></p>`,
                });
            });
            it('should paste and transform URL over the existing url', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[<a href="http://www.xyz.com">http://www.xyz.com</a>]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.xyz.xdc ');
                    },
                    contentAfter: '<p>ab<a href="https://www.xyz.xdc">https://www.xyz.xdc</a> []cd</p>',
                });
            });
            it('should paste plain text content over a link if all of its contents is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="#">[xyz]</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'bc');
                    },
                    contentAfter: '<p>abc[]d</p>',
                });
            });
            it('should paste and transform plain text content over a link if all of its contents is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[xyz]</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'www.odoo.com');
                    },
                    contentAfter: '<p><a href="https://www.odoo.com">www.odoo.com</a>[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[xyz]</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc www.odoo.com xyz');
                    },
                    contentAfter: '<p>abc <a href="https://www.odoo.com">www.odoo.com</a> xyz[]</p>',
                });
            });
            it('should paste html content over a link if all of its contents is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[xyz]</a></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>');
                    },
                    contentAfter: '<p><a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>[]</p>',
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
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>ab<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]cd</p>',
                });
            });
            it('should paste and transform an image URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>a<span class="a">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</span>d</p>',
                });
            });
            it('should paste and transform an image URL in an existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</a>d</p>',
                });
            });
            it('should paste an image URL as a link in a p', async () => {
                const url = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p><a href="${url}">${url}</a>[]</p>`,
                });
            });
            it('should not revert a history step when pasting an image URL as a link', async () => {
                const url = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        // paste text to have a history step recorded
                        await pasteText(editor, "*should not disappear*");
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>*should not disappear*<a href="${url}">${url}</a>[]</p>`,
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
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>ab<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]cd</p>',
                });
            });
            it('should paste and transform an image URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>a<span class="a">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</span>d</p>',
                });
            });
            it('should paste and transform an image URL inside an existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Powerbox should not open
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">b<img src="https://download.odoocdn.com/icons/website/static/description/icon.png">[]c</a>d</p>',
                });
            });
            it('should paste an image URL as a link in a p', async () => {
                const url = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[xxx]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<a href="${url}">${url}</a>[]cd</p>`,
                });
            });
            it('should not revert a history step when pasting an image URL as a link', async () => {
                const url = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        // paste text (to have a history step recorded)
                        await pasteText(editor, "abxxxcd");
                        // select xxx in "<p>ab[xxx]cd</p>""
                        const p = editor.editable.querySelector('p')
                        let selection = {
                            direction: Direction.FORWARD,
                            anchorNode: p.childNodes[1],
                            anchorOffset: 2,
                            focusNode: p.childNodes[1],
                            focusOffset: 5,
                        }
                        setTestSelection(selection, editor.document);
                        editor._computeHistorySelection();
                        // paste url
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<a href="${url}">${url}</a>[]cd</p>`,
                });
            });
            it('should restore selection after pasting image URL followed by UNDO', async () => {
                const url = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick first command (Embed image)
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
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
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>ab<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]cd</p>',
                });
            });
            it('should paste and transform a youtube URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://youtu.be/dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>a<span class="a">b<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]c</span>d</p>',
                });
            });
            it('should paste and not transform a youtube URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://youtu.be/dQw4w9WgXcQ');
                        // Ensure the powerbox is not active
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttps://youtu.be/dQw4w9WgXcQ[]c</a>d</p>',
                });
            });
            it('should paste a youtube URL as a link in a p', async () => {
                const url = 'https://youtu.be/dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p><a href="${url}">${url}</a>[]</p>`,
                });
            });
            it('should not revert a history step when pasting a youtube URL as a link', async () => {
                const url = 'https://youtu.be/dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        // paste text to have a history step recorded
                        await pasteText(editor, "*should not disappear*");
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>*should not disappear*<a href="${url}">${url}</a>[]</p>`,
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
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>ab<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]cd</p>',
                });
            });
            it('should paste and transform a youtube URL in a span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[x<a href="http://existing.com">546</a>x]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Force commandBar validation on the default first choice
                        await editor.commandBar._currentValidate();
                    },
                    contentAfter: '<p>a<span class="a">b<iframe width="560" height="315" src="https://www.youtube.com/embed/dQw4w9WgXcQ" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen="1"></iframe>[]c</span>d</p>',
                });
            });
            it('should paste and not transform a youtube URL in a existing link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://existing.com">b[qsdqsd]c</a>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://www.youtube.com/watch?v=dQw4w9WgXcQ');
                        // Ensure the powerbox is not active
                        window.chai.expect(editor.commandBar._active).to.be.false;
                    },
                    contentAfter: '<p>a<a href="http://existing.com">bhttps://www.youtube.com/watch?v=dQw4w9WgXcQ[]c</a>d</p>',
                });
            });
            it('should paste a youtube URL as a link in a p', async () => {
                const url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[xxx]cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<a href="${url}">${url}</a>[]cd</p>`,
                });
            });
            it('should not revert a history step when pasting a youtube URL as a link', async () => {
                const url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        // paste text (to have a history step recorded)
                        await pasteText(editor, "abxxxcd");
                        // select xxx in "<p>ab[xxx]cd</p>"
                        const p = editor.editable.querySelector('p')
                        let selection = {
                            direction: Direction.FORWARD,
                            anchorNode: p.childNodes[1],
                            anchorOffset: 2,
                            focusNode: p.childNodes[1],
                            focusOffset: 5,
                        }
                        setTestSelection(selection, editor.document);
                        editor._computeHistorySelection();

                        // paste url
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick the second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<a href="${url}">${url}</a>[]cd</p>`,
                });
            });
            it('should restore selection after pasting video URL followed by UNDO', async () => {
                const url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick first command (Embed video)
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.commandBar._active).to.be.true;
                        // Pick second command (Paste as URL)
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
            });
        });
    });
});
