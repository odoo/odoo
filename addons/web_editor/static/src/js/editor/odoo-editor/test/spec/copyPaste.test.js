/** @odoo-module */

import {
    BasicEditor,
    testEditor,
    triggerEvent,
    undo,
    setTestSelection,
    Direction,
    nextTick,
    pasteText,
    pasteHtml,
    pasteOdooEditorHtml,
    unformat,
} from "../utils.js";
import { CLIPBOARD_WHITELISTS, setSelection } from "../../src/OdooEditor.js";

describe('Copy', () => {
    describe('range collapsed', async () => {
        it('should ignore copying an empty selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'copy', { clipboardData });
                    // Check that nothing was set as clipboard content
                    window.chai.expect(clipboardData.types.length).to.be.equal(0);
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    clipboardData.setData('text/plain', 'should stay');
                    await triggerEvent(editor.editable, 'copy', { clipboardData });
                    // Check that clipboard data was not overwritten
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('should stay');
                },
            });
        });
    });
    describe('range not collapsed', async () => {
        it('should copy a selection as text/plain, text/html and text/odoo-editor', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[bcd]e</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('bcd');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p>bcd</p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p>bcd</p>');
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc<br>efg]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('abc\nefg');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p>abc<br>efg</p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p>abc<br>efg</p>');
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: `]<table><tbody><tr><td><ul><li>a[</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>`,
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('a');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<table><tbody><tr><td><ul><li>a</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<table><tbody><tr><td><ul><li>a</li><li>b</li><li>c</li></ul></td><td><br></td></tr></tbody></table>');
                },
            });
        });
        it('should wrap the selected text with clones of ancestors up to a block element to keep styles', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[<span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span>]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('Test Test');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p><span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span></p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p><span style="font-size: 16px;">Test</span> <span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">Test</font></span></p>');
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<p><strong><em><u><font class="text-o-color-1">hello [there]</font></u></em></strong></p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('there');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p><strong><em><u><font class="text-o-color-1">there</font></u></em></strong></p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p><strong><em><u><font class="text-o-color-1">there</font></u></em></strong></p>');
                },
            });
        });
        it('should copy the selection as a single list item', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li>[First]</li><li>Second</li>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('First');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('First');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('First');
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li>First [List]</li><li>Second</li>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('List');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('List');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('List');
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li><span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">[First]</font></span></li><li>Second</li>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('First');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">First</font></span>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<span style="font-size: 48px;"><font style="color: rgb(255, 0, 0);">First</font></span>');
                },
            });
        })
        it('should copy the selection as a list with multiple list items', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li>[First</li><li>Second]</li>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    triggerEvent(editor.editable, 'copy', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('First\nSecond');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<ul><li>First</li><li>Second</li></ul>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<ul><li>First</li><li>Second</li></ul>');
                },
            });
        });
    });
});
describe('Cut', () => {
    describe('range collapsed', async () => {
        it('should ignore cutting an empty selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'cut', { clipboardData });
                    // Check that nothing was set as clipboard content
                    window.chai.expect(clipboardData.types.length).to.be.equal(0);
                },
            });
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    clipboardData.setData('text/plain', 'should stay');
                    await triggerEvent(editor.editable, 'cut', { clipboardData });
                    // Check that clipboard data was not overwritten
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('should stay');
                },
            });
        });
    });
    describe('range not collapsed', async () => {
        it('should cut a selection as text/plain, text/html and text/odoo-editor', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[bcd]e</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'cut', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('bcd');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p>bcd</p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p>bcd</p>');
                },
                contentAfter: '<p>a[]e</p>',
            });
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc<br>efg]</p>',
                stepFunction: async editor => {
                    const clipboardData = new DataTransfer();
                    await triggerEvent(editor.editable, 'cut', { clipboardData });
                    window.chai.expect(clipboardData.getData('text/plain')).to.be.equal('abc\nefg');
                    window.chai.expect(clipboardData.getData('text/html')).to.be.equal('<p>abc<br>efg</p>');
                    window.chai.expect(clipboardData.getData('text/odoo-editor')).to.be.equal('<p>abc<br>efg</p>');
                },
                contentAfter: '<p>[]<br></p>',
            });
        });
        it('should cut selection and register it as a history step', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[bcd]e</p>',
                stepFunction: async editor => {
                    const historyStepsCount = editor._historySteps.length;
                    await triggerEvent(editor.editable, 'cut', { clipboardData: new DataTransfer() });
                    window.chai.expect(editor._historySteps.length).to.be.equal(historyStepsCount + 1);
                    undo(editor);
                },
                contentAfter: '<p>a[bcd]e</p>',
            });
        });
        it('should not restore cut content when cut followed by delete forward', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]bcde</p>',
                stepFunction: async editor => {
                    // Set selection to a[bcd]e.
                    const selection = editor.document.getSelection();
                    selection.extend(selection.anchorNode, 4);
                    await triggerEvent(editor.editable, 'cut', { clipboardData: new DataTransfer() });
                    await triggerEvent(editor.editable, 'input', {
                        inputType: 'deleteContentForward'
                    });
                },
                contentAfter: '<p>a[]</p>',
            });
        });
    });
});

describe('Paste', () => {
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
                await testEditor(BasicEditor, {
                    contentBefore: '<p>123[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, 'a<img src="http://www.imgurl.com/img.jpg">d');
                    },
                    contentAfter: '<p>123a<img src="http://www.imgurl.com/img.jpg">d[]</p>',
                });
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
                    contentAfter: '<p>123abcd[]</p>',
                });
            });
            it('should remove unwanted styles and b tag when pasting from paragraph from gdocs', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, `<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-ddad60c5-7fff-0a8f-fdd5-c1107201fe26"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test1</span></p><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></p></b>`);
                    },
                    contentAfter: '<p>test1</p><p>test2[]</p>',
                });
            });
            it('should remove unwanted b tag and p tag with unwanted styles when pasting list from gdocs', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-5d8bcf85-7fff-ebec-8604-eedd96f2d601"><ul style="margin-top:0;margin-bottom:0;padding-inline-start:48px;"><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Google</span></p></li><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Test</span></p></li><li dir="ltr" style="list-style-type:disc;font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><p dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:0pt;" role="presentation"><span style="font-size:11pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></p></li></ul></b>');
                    },
                    contentAfter: '<ul><li>Google</li><li>Test</li><li>test2[]</li></ul>',
                });
            });
            it('should remove unwanted styles and keep tags when pasting list from gdoc', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<meta charset="utf-8"><b style="font-weight:normal;" id="docs-internal-guid-477946a8-7fff-f959-18a4-05014997e161"><ul style="margin-top:0;margin-bottom:0;padding-inline-start:48px;"><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:20pt;margin-bottom:0pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Google</span></h1></li><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:0pt;margin-bottom:6pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">Test</span></h1></li><li dir="ltr" style="list-style-type:disc;font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;" aria-level="1"><h1 dir="ltr" style="line-height:1.38;margin-top:20pt;margin-bottom:0pt;" role="presentation"><span style="font-size:20pt;font-family:Arial,sans-serif;color:#000000;background-color:transparent;font-weight:400;font-style:normal;font-variant:normal;text-decoration:none;vertical-align:baseline;white-space:pre;white-space:pre-wrap;">test2</span></h1></li></ul></b>');
                    },
                    contentAfter: '<ul><li><h1>Google</h1></li><li><h1>Test</h1></li><li><h1>test2[]</h1></li></ul>',
                });
            });
            it('should paste checklist from gdoc', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, unformat(`
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
                        `));
                    },
                    contentAfter: `<ul class="o_checklist"><li>Abc</li><li class="o_checked">def[]</li></ul>`,
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
            it('should paste text and understand \\n newlines', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br/></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'a\nb\nc\nd');
                    },
                    contentAfter: '<p style="margin-bottom: 0px;">a</p>' +
                                  '<p style="margin-bottom: 0px;">b</p>' +
                                  '<p style="margin-bottom: 0px;">c</p>' +
                                  '<p>d[]</p>',
                });
            });
            it('should paste text and understand \\r\\n newlines', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br/></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'a\r\nb\r\nc\r\nd');
                    },
                    contentAfter: '<p style="margin-bottom: 0px;">a</p>' +
                                  '<p style="margin-bottom: 0px;">b</p>' +
                                  '<p style="margin-bottom: 0px;">c</p>' +
                                  '<p>d[]</p>',
                });
            });
            it('should paste text and understand \\n newlines within UNBREAKABLE node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>[]<br></div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'a\nb\nc\nd');
                    },
                    contentAfter: '<div>a<br>b<br>c<br>d[]</div>',
                });
            });
            it('should paste text and understand \\n newlines within UNBREAKABLE node(2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div><span style="font-size: 9px;">a[]</span></div>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'b\nc\nd');
                    },
                    contentAfter: '<div><span style="font-size: 9px;">ab<br>c<br>d[]</span></div>',
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
    describe('Simple html elements containing <br>', () => {
        describe('breaking <br> elements', () => {
            it('should split h1 with <br> into seperate h1 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc<br>def<br>ghi<br>jkl</h1>');
                    },
                    contentAfter: '<h1>abc</h1><h1>def</h1><h1>ghi</h1><h1>jkl[]</h1>',
                });
            });
            it('should split h2 with <br> into seperate h2 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h2>abc<br>def<br>ghi<br>jkl</h2>');
                    },
                    contentAfter: '<h2>abc</h2><h2>def</h2><h2>ghi</h2><h2>jkl[]</h2>',
                });
            });
            it('should split h3 with <br> into seperate h3 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h3>abc<br>def<br>ghi<br>jkl</h3>');
                    },
                    contentAfter: '<h3>abc</h3><h3>def</h3><h3>ghi</h3><h3>jkl[]</h3>',
                });
            });
            it('should split h4 with <br> into seperate h4 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h4>abc<br>def<br>ghi<br>jkl</h4>');
                    },
                    contentAfter: '<h4>abc</h4><h4>def</h4><h4>ghi</h4><h4>jkl[]</h4>',
                });
            });
            it('should split h5 with <br> into seperate h5 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h5>abc<br>def<br>ghi<br>jkl</h5>');
                    },
                    contentAfter: '<h5>abc</h5><h5>def</h5><h5>ghi</h5><h5>jkl[]</h5>',
                });
            });
            it('should split h6 with <br> into seperate h6 elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h6>abc<br>def<br>ghi<br>jkl</h6>');
                    },
                    contentAfter: '<h6>abc</h6><h6>def</h6><h6>ghi</h6><h6>jkl[]</h6>',
                });
            });
            it('should split p with <br> into seperate p elements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc<br>def<br>ghi<br>jkl</p>');
                    },
                    contentAfter: '<p>abc</p><p>def</p><p>ghi</p><p>jkl[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc<br>def<br>ghi<br>jkl</p><p>mno</p>');
                    },
                    contentAfter: '<p>abc</p><p>def</p><p>ghi</p><p>jkl</p><p>mno[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc<br>def<br>ghi<br>jkl</p><p><br></p><p>mno</p>');
                    },
                    contentAfter: '<p>abc</p><p>def</p><p>ghi</p><p>jkl</p><p><br></p><p>mno[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc<br>def<br><br><br>ghi</p>');
                    },
                    contentAfter: '<p>abc</p><p>def</p><p><br></p><p><br></p><p>ghi[]</p>',
                });
            });
            it('should split multiple elements with <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc<br>def</p><h1>ghi<br>jkl</h1><h2><br></h2><h3>mno<br>pqr</h3>');
                    },
                    contentAfter: '<p>abc</p><p>def</p><h1>ghi</h1><h1>jkl</h1><h2><br></h2><h3>mno</h3><h3>pqr[]</h3>',
                });
            });
            it('should split div with <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<div>abc<br>def</div>');
                    },
                    contentAfter: '<p>abc</p><p>def[]</p>',
                });
            });
        });
        describe('not breaking <br> elements', async () => {
            it('should not split li with <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>abc<br>def</li></ul>');
                    },
                    contentAfter: '<ul><li>abc<br>def[]</li></ul>',
                });
            });
            it('should not split blockquote with <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<blockquote>abc<br>def</blockquote>');
                    },
                    contentAfter: '<blockquote>abc<br>def[]</blockquote>',
                });
            });
            it('should not split pre with <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<pre>abc<br>def</pre>');
                    },
                    contentAfter: '<pre>abc<br>def[]</pre>',
                });
            });
        });
    });
    describe('Unwrapping html element', () => {
        describe('range collapsed', async () => {
            it('should not unwrap a node when pasting on empty node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<h1>abc[]</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h2>abc</h2>');
                    },
                    contentAfter: '<h2>abc[]</h2>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h3>abc</h3>');
                    },
                    contentAfter: '<h3>abc[]</h3>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<h1>abc</h1><h2>def[]</h2>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2><h3>ghi</h3>');
                    },
                    contentAfter: '<h1>abc</h1><h2>def</h2><h3>ghi[]</h3>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p><p><br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h3>abc</h3>');
                    },
                    contentAfter: '<h3>abc[]</h3><p><br></p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]<br></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc</p><p><br></p><p><br></p>');
                    },
                    contentAfter: '<p>abc</p><p><br></p><p><br>[]</p>',
                });
            });
            it('should not unwrap a node when pasting in between different node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]op</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<p>mn</p><h1>abc[]</h1><p>op</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]op</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<p>mn</p><h1>abc</h1><h2>def[]</h2><p>op</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]op</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2><h3>ghi</h3>');
                    },
                    contentAfter: '<p>mn</p><h1>abc</h1><h2>def</h2><h3>ghi[]</h3><p>op</p>',
                });
            });
            it('should unwrap a node when pasting in between same node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>mn[]op</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<h1>mnabc[]op</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>mn[]op</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<h1>mnabc</h1><h2>def[]</h2><h1>op</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h2>mn[]op</h2>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<h2>mn</h2><h1>abc</h1><h2>def[]op</h2>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>mn[]op</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h1>def</h1><h1>ghi</h1>');
                    },
                    contentAfter: '<h1>mnabc</h1><h1>def</h1><h1>ghi[]op</h1>',
                });
            });
            it('should not unwrap a node when pasting at start of different node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]mn</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<h1>abc[]</h1><p>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]mn</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<h1>abc</h1><h2>def[]</h2><p>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]mn</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2><h3>ghi</h3>');
                    },
                    contentAfter: '<h1>abc</h1><h2>def</h2><h3>ghi[]</h3><p>mn</p>',
                });
            });
            it('should unwrap a node when pasting at start of same node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[]mn</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<h1>abc[]mn</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[]mn</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h2>abc</h2><h1>def</h1>');
                    },
                    contentAfter: '<h2>abc</h2><h1>def[]mn</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><font style="background-color: rgb(255, 0, 0);">[]mn</font></h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h1>def</h1><h1>ghi</h1>');
                    },
                    contentAfter: '<h1>abc</h1><h1>def</h1><h1><font style="background-color: rgb(255, 0, 0);">ghi[]mn</font></h1>',
                });
            });
            it('should not unwrap a node when pasting at end of different node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<p>mn</p><h1>abc[]</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<p>mn</p><h1>abc</h1><h2>def[]</h2>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>mn[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2><h3>ghi</h3>');
                    },
                    contentAfter: '<p>mn</p><h1>abc</h1><h2>def</h2><h3>ghi[]</h3>',
                });
            });
            it('should unwrap a node when pasting at end of same node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>mn[]</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1>');
                    },
                    contentAfter: '<h1>mnabc[]</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>mn[]</h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h2>def</h2>');
                    },
                    contentAfter: '<h1>mnabc</h1><h2>def[]</h2>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><font style="background-color: rgb(255, 0, 0);">mn[]</font></h1>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<h1>abc</h1><h1>def</h1><h1>ghi</h1>');
                    },
                    contentAfter: '<h1><font style="background-color: rgb(255, 0, 0);">mnabc</font></h1><h1>def</h1><h1>ghi[]</h1>',
                });
            });
            it('should not unwrap empty block nodes even when pasting on same node', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p><br></p><p><br></p><p><br></p>');
                    },
                    contentAfter: '<p>a</p><p><br></p><p><br></p><p><br>[]</p>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]c</span>d</p>',
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
                    contentBefore: '<p>a<span class="a">b[cd]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
                });
            });
            it('should paste a text when selection across two span', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span><span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="a">b[c</span>- -<span class="a">d]e</span>f</p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<p>a<span class="a">b1<b>23</b>&nbsp;4[]e</span>f</p>',
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
                    contentBefore: '<div>ab<span class="a">c[d</span>e]f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>ab<span class="a">c1<b>23</b>&nbsp;4[]</span>f</div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a[b<span class="a">c]d</span>ef</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>a1<b>23</b>&nbsp;4[]<span class="a">d</span>ef</div>',
                });
            });
            it('should paste a text when selection across two element', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>1a<p>b[c</p><span class="a">d]e</span>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>1a<p>b1<b>23</b>&nbsp;4[]<span class="a">e</span>f</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div>2a<span class="a">b[c</span><p>d]e</p>f</div>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, complexHtmlData);
                    },
                    contentAfter: '<div>2a<span class="a">b1<b>23</b>&nbsp;4[]</span>e<br>f</div>',
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
                    contentAfter: '<p>12</p><ul><li>abc</li><li>def</li><li>ghi[]</li></ul><p>34</p>',
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
            it('should correctly paste nested UL or OL elements copied from GDocs', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: `<p>[]<br></p>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
                            <ul>
                                <li>abc</li>
                                <li>def</li>
                                <ul>
                                    <li>ghi</li>
                                    <li>jkl</li>
                                </ul>
                                <ol>
                                    <li>mno</li>
                                    <li>pqr</li>
                                </ol>
                            </ul>
                        `));
                    },
                    contentAfter: unformat(`
                        <ul>
                            <li>abc</li>
                            <li>def</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>ghi</li>
                                    <li>jkl</li>
                                </ul>
                            </li>
                            <li class="oe-nested">
                                <ol>
                                    <li>mno</li>
                                    <li>pqr[]</li>
                                </ol>
                            </li>
                        </ul>
                    `),
                });
            });
            it('should convert multiple paragraphs into a checklist', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: `<ul class="o_checklist"><li>[]<br></li></ul>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
                            <p>abc</p>
                            <p>def</p>
                            <p>ghi</p>
                            <p>jkl</p>
                            <p>mno</p>
                        `));
                    },
                    contentAfter: unformat(`
                        <ul class="o_checklist">
                            <li>abc</li>
                            <li>def</li>
                            <li>ghi</li>
                            <li>jkl</li>
                            <li>mno[]</li>
                        </ul>
                    `),
                });
            });
            it('should insert a list and a p tag inside a new list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>[]<br></li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><li>abc</li><li>def</li></ul><p>ghi</p>');
                    },
                    contentAfter: '<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>',
                });
            });
            it('should insert content ending with a list inside a new list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>[]<br></li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<p>abc</p><ul><li>def</li><li>ghi</li></ul>');
                    },
                    contentAfter: '<ul><li>abc</li><li>def</li><li>ghi[]</li></ul>',
                });
            });
            it('should convert a mixed list containing a paragraph into a checklist', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: `<ul class="o_checklist"><li>[]<br></li></ul>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
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
                        `));
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
            it('should not unwrap a list twice when pasting on new list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>[]<br></li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<ul><ul><li>abc</li><li>def</li></ul></ul>');
                    },
                    contentAfter: '<ul><li class="oe-nested"><ul><li>abc</li><li>def[]</li></ul></li></ul>',
                });
            });
            it('should paste a nested list into another list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ol><li>Alpha</li><li>[]<br></li></ol>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, unformat(`
                            <ul>
                                <li>abc</li>
                                <li>def</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>123</li>
                                        <li>456</li>
                                    </ul>
                                </li>
                            </ul>
                        `));
                    },
                    contentAfter: unformat(`
                        <ol>
                            <li>Alpha</li>
                            <li>abc</li>
                            <li>def</li>
                            <li class="oe-nested">
                                <ol>
                                    <li>123</li>
                                    <li>456[]</li>
                                </ol>
                            </li>
                        </ol>
                    `),
                });
            });
            it('should paste a nested list into another list (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>Alpha</li><li>[]<br></li></ul>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, unformat(`
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
                        `));
                    },
                    contentAfter: unformat(`
                        <ul>
                            <li>Alpha</li>
                            <li class="oe-nested">
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
            it('should convert a mixed list into a ordered list', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: `<ol><li>[]<br></li></ol>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(
                            `<ul>
                                <li>ab</li>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ef</li>
                                        <li>gh</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>ij</li>
                                                <li>kl</li>
                                            </ul>
                                        </li>
                                    </ol>
                                </li>
                            </ul>
                        `));
                    },
                    contentAfter: unformat(`
                        <ol>
                            <li>ab</li>
                            <li>cd</li>
                            <li class="oe-nested">
                                <ol>
                                    <li>ef</li>
                                    <li>gh</li>
                                    <li class="oe-nested">
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
            it('should convert a mixed list starting with bullet list into a bullet list', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: `<ul><li>[]<br></li></ul>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
                            <ul>
                                <li>ab</li>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ef</li>
                                        <li>gh</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>ij</li>
                                                <li>kl</li>
                                            </ul>
                                        </li>
                                    </ol>
                                </li>
                            </ul>
                        `));
                    },
                    contentAfter: unformat(`
                        <ul>
                            <li>ab</li>
                            <li>cd</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>ef</li>
                                    <li>gh</li>
                                    <li class="oe-nested">
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
            it('should paste a mixed list starting with deeply nested bullet list into a bullet list', async () => {
                await testEditor(BasicEditor, {
                    removeCheckIds: true,
                    contentBefore: `<ul><li>[]<br></li></ul>`,
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
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
                        `));
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
            it('should paste a deeply nested list copied outside from odoo', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<ul><li>[]<br></li></ul>',
                    stepFunction:  async editor => {
                        await pasteHtml(editor, unformat(`
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
                        `));
                    },
                    contentAfter: unformat(`
                        <ul>
                            <li>ab</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>cd</li>
                                    <li>ef</li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>gh</li>
                                            <li>ij</li>
                                            <li>kl</li>
                                            <li>mn</li>
                                        </ul>
                                    </li>
                                    <li>op</li>
                                    <li>qr</li>
                                    <li class="oe-nested">
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
                    contentAfter: '<p>a<a href="http://boom.com">boom[].com</a>d</p>',
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
                await testEditor(BasicEditor, {
                    contentBefore: '<p>xy<a href="#" oe-zws-empty-inline="">\u200B[]</a>z</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'http://odoo.com');
                    },
                    contentAfter: '<p>xy<a href="http://odoo.com">http://odoo.com</a>[]z</p>',
                });
                const imageUrl = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>xy<a href="#">[]</a>z</p>',
                    contentBeforeEdit: '<p>xy\ufeff<a href="#" class="o_link_in_selection">[]\ufeff</a>\ufeffz</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, imageUrl);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the first command (Embed image)
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>xy<img src="${imageUrl}">[]z</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>xy<a href="#" oe-zws-empty-inline="">\u200B[]</a>z</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, imageUrl);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>xy<a href="${imageUrl}">${imageUrl}</a>[]z</p>`,
                });
            });
            it('should paste and transform plain text content over an empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc www.odoo.com xyz');
                    },
                    contentAfter: '<p>abc <a href="http://www.odoo.com">www.odoo.com</a> xyz[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'odoo.com\ngoogle.com');
                    },
                    contentAfter: '<p style="margin-bottom: 0px;"><a href="http://odoo.com">odoo.com</a></p>' +
                                  '<p><a href="http://google.com">google.com</a>[]</p>'
                });
            });
            it('should paste html content over an empty link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[]\u200B</a></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>');
                    },
                    contentAfter: '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="www.google.com">google.com</a>[]</p>',
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${url}">${url}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${imgUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${videoUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `${url} abc ${videoUrl} def ${imgUrl}`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${url}">${url}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${imgUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${imgUrl}">${imgUrl}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `abc ${videoUrl} def`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p>abc <a href="${videoUrl}">${videoUrl}</a> def[]</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[xyz]<br></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, `${url} ${videoUrl} ${imgUrl}`);
                        // Powerbox should not open
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
                    },
                    contentAfter: `<p><a href="${url}">${url}</a> <a href="${videoUrl}">${videoUrl}</a> <a href="${imgUrl}">${imgUrl}</a>[]</p>`,
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
                    contentAfter: '<p><a href="http://www.odoo.com">www.odoo.com</a>[]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[xyz]</a></p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'abc www.odoo.com xyz');
                    },
                    contentAfter: '<p>abc <a href="http://www.odoo.com">www.odoo.com</a> xyz[]</p>',
                });
                const imageUrl = 'https://download.odoocdn.com/icons/website/static/description/icon.png';
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<a href="http://www.xyz.com">[http://www.xyz.com]</a>cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, imageUrl);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the first command (Embed image)
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<img src="${imageUrl}">[]cd</p>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<a href="http://www.xyz.com">[http://www.xyz.com]</a>cd</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, imageUrl);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                    },
                    contentAfter: `<p>ab<a href="${imageUrl}">${imageUrl}</a>[]cd</p>`,
                });
            });
            it('should paste html content over a link if all of its contents is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">[xyz]</a></p>',
                    stepFunction: async editor => {
                        await pasteHtml(editor, '<a href="www.odoo.com">odoo.com</a><br><a href="www.google.com">google.com</a>');
                    },
                    contentAfter: '<p><a href="www.odoo.com">odoo.com</a></p><p><a href="www.google.com">google.com</a>[]</p>',
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
                    contentBefore: '<p>a<span class="a">b[]c</span>d</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, 'https://download.odoocdn.com/icons/website/static/description/icon.png');
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick first command (Embed image)
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        await nextTick();
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: async editor => {
                        await pasteText(editor, url);
                        // Ensure the powerbox is active
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Force powerbox validation on the default first choice
                        await editor.powerbox._pickCommand();
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.false;
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick the second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick first command (Embed video)
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
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
                        window.chai.expect(editor.powerbox.isOpen).to.be.true;
                        // Pick second command (Paste as URL)
                        await triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        await triggerEvent(editor.editable, 'keydown', { key: 'Enter' });
                        // Undo
                        editor.historyUndo();
                    },
                    contentAfter: '<p>[abc]</p>',
                });
            });
        });
    });
    describe('Odoo editor own html', () => {
        it('should paste html as is', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b</p>',
                stepFunction: async editor => {
                    await pasteOdooEditorHtml(editor, '<div class="custom-paste">b</div>');
                },
                contentAfter: '<p>a</p><div class="custom-paste">b</div><p>[]b</p>',
            });
        });
        it('should not paste unsafe content', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b</p>',
                stepFunction: async editor => {
                    await pasteOdooEditorHtml(editor, `<script>console.log('xss attack')</script>`);
                },
                contentAfter: '<p>a[]b</p>',
            });
        });
    });
    describe('editable in iframe', () => {
        it('should paste odoo-editor html', async () => {
            // Setup
            const testContainer = document.querySelector('#editor-test-container');
            const iframe = document.createElement('iframe');
            testContainer.append(iframe);
            const iframeDocument = iframe.contentDocument;
            const editable = iframeDocument.createElement('div');
            iframeDocument.body.append(editable);
            const editor = new BasicEditor(editable, { document: iframeDocument });

            // Action: paste
            setSelection(editable.querySelector('p'), 0);
            const clipboardData = new DataTransfer();
            clipboardData.setData('text/odoo-editor', '<p>text<b>bold text</b>more text</p>');
            await triggerEvent(editor.editable, 'paste', { clipboardData });

            // Clean-up
            editor.clean();
            editor.destroy();
            iframe.remove();

            // Assertion
            window.chai.expect(editable.innerHTML).to.be.equal(
                '<p>text<b>bold text</b>more text</p>',
                'should paste content in the paragraph'
            );
        });
    });
});
