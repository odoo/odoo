import { BasicEditor, testEditor } from '../utils.js';

describe('insert HTML', () => {
    describe('collapsed selection', () => {
        it('should insert html in an empty paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit:
                    '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
            });
        });
        it('should insert html after an empty paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><br></p>[]',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit:
                    '<p><br></p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]',
                contentAfter: '<p><br></p><i class="fa fa-pastafarianism"></i>[]',
            });
        });
        it('should insert html between two letters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]b<br></p>',
                contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]b<br></p>',
            });
        });
        it('should insert html in an empty editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit: '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
            });
        });
        it('should insert html in between naked text in the editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
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
                    await editor.execCommand('insertHTML', '<p>b</p><p>c</p><p>d</p>');
                },
                contentAfter: '<p>ab</p><p>c</p><p>d[]e<br></p>',
            });
        });
        it('should keep a paragraph after a div block', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<div><p>content</p></div>');
                },
                contentAfter: '<div><p>content</p></div><p>[]<br></p>',
            });
        });
        it('should not split a pre to insert another pre but just insert the text', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<pre>abc[]<br>ghi</pre>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<pre>def</pre>');
                },
                contentAfter: '<pre>abcdef[]<br>ghi</pre>',
            });
        });
    });
    describe('not collapsed selection', () => {
        it('should delete selection and insert html in its place', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[a]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit: '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
            });
        });
        it('should delete selection and insert html in its place (2)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[b]c<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfterEdit:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]c<br></p>',
                contentAfter: '<p>a<i class="fa fa-pastafarianism"></i>[]c<br></p>',
            });
        });
    });
});
