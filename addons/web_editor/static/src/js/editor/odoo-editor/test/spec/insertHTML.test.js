import { parseHTML } from '../../src/utils/utils.js';
import { BasicEditor, testEditor, unformat, insertText, deleteBackward } from '../utils.js';

const span = text => {
    const span = document.createElement('span');
    span.innerText = text;
    span.classList.add('a');
    return span;
}

describe('insert HTML', () => {
    describe('collapsed selection', () => {
        it('should insert html in an empty paragraph / empty editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit:
                    '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
            });
        });
        it('should insert html between two letters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]b<br></p>',
                contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b<br></p>',
            });
        });
        it('should insert html in between naked text in the editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]b<br></p>',
                contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b<br></p>',
            });
        });
        it('should insert several html nodes in between naked text in the editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]e<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<p>b</p><p>c</p><p>d</p>'));
                },
                contentAfter: '<p>ab</p><p>c</p><p>d[]e<br></p>',
            });
        });
        it('should keep a paragraph after a div block', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<div><p>content</p></div>'));
                },
                contentAfter: '<div><p>content</p></div><p>[]<br></p>',
            });
        });
        it('should not split a pre to insert another pre but just insert the text', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<pre>abc[]<br>ghi</pre>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<pre>def</pre>'));
                },
                contentAfter: '<pre>abcdef[]<br>ghi</pre>',
            });
        });
        it('should keep an "empty" block which contains fontawesome nodes when inserting multiple nodes', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>content[]</p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<p>unwrapped</p><div><i class="fa fa-circle-o-notch"></i></div><p>culprit</p><p>after</p>'));
                },
                contentAfter: '<p>contentunwrapped</p><div><i class="fa fa-circle-o-notch"></i></div><p>culprit</p><p>after[]</p>',
            });
        });
    });
    describe('not collapsed selection', () => {
        it('should delete selection and insert html in its place', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[a]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit: '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
            });
        });
        it('should delete selection and insert html in its place (2)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[b]c<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]c<br></p>',
                contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]c<br></p>',
            });
        });
        it('should remove a fully selected table then insert a span before it', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(
                    `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: '<p>a<span class="a">TEST</span>[]l</p>',
            });
        });
        it('should only remove the text content of cells in a partly selected table', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(
                    `<table><tbody>
                        <tr><td>cd</td><td class="o_selected_td">e[f</td><td>gh</td></tr>
                        <tr><td>ij</td><td class="o_selected_td">k]l</td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: unformat(
                    `<table><tbody>
                        <tr><td>cd</td><td><span class="a">TEST</span>[]<br></td><td>gh</td></tr>
                        <tr><td>ij</td><td><br></td><td>mn</td></tr>
                        <tr><td>op</td><td>qr</td><td>st</td></tr>
                    </tbody></table>`,
                ),
            });
        });
        it('should remove some text and a table (even if the table is partly selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(
                    `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>g]h</td><td>ij</td></tr>
                    </tbody></table>
                    <p>kl</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: unformat(
                    `<p>a<span class="a">TEST</span>[]</p>
                    <p>kl</p>`,
                ),
            });
        });
        it('should remove a table and some text (even if the table is partly selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(
                    `<p>ab</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>i[j</td></tr>
                    </tbody></table>
                    <p>k]l</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: unformat(
                    `<p>ab</p>
                    <p><span class="a">TEST</span>[]l</p>`,
                ),
            });
        });
        it('should remove some text, a table and some more text', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(
                    `<p>a[b</p>
                    <table><tbody>
                        <tr><td>cd</td><td>ef</td></tr>
                        <tr><td>gh</td><td>ij</td></tr>
                    </tbody></table>
                    <p>k]l</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: `<p>a<span class="a">TEST</span>[]l</p>`,
            });
        });
        it('should remove a selection of several tables', async () => {
            await testEditor(BasicEditor, {
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
                    </tbody></table>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: `<p><span class="a">TEST</span>[]<br></p>`,
            });
        });
        it('should remove a selection including several tables', async () => {
            await testEditor(BasicEditor, {
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
                    <p>67]</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: `<p>0<span class="a">TEST</span>[]</p>`,
            });
        });
        it('should remove everything, including several tables', async () => {
            await testEditor(BasicEditor, {
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
                    <p>67]</p>`,
                ),
                stepFunction: editor => editor.execCommand('insert', span('TEST')),
                contentAfter: `<p><span class="a">TEST</span>[]<br></p>`,
            });
        });
    });
});
describe('insert text', () => {
    describe('not collapsed selection', () => {
        it('should insert a character in a fully selected font in a heading, preserving its style', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1><font style="background-color: red;">[abc</font><br></h1><p>]def</p>',
                stepFunction: async editor => insertText(editor, 'g'),
                contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
            });
            await testEditor(BasicEditor, {
                contentBefore: '<h1><font style="background-color: red;">[abc</font><br></h1><p>]def</p>',
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await insertText(editor, 'g');
                },
                contentAfter: '<h1><font style="background-color: red;">g[]</font><br></h1><p>def</p>',
            });
        });
    });
});
