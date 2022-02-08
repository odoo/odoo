import { BasicEditor, testEditor } from '../utils.js';

describe('insetHTML', () => {
    describe('collapsed selection', () => {
        it('should insert html in an empty paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[]<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter:
                    '<p><i class="fa fa-pastafarianism" contenteditable="false">​</i>[]<br></p>',
            });
        });
        it('should insert html after an empty paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><br></p>[]',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter:
                    '<p><br></p><i class="fa fa-pastafarianism" contenteditable="false">​</i>[]',
            });
        });
        it('should insert html between two letters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[]b<br></p>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter:
                    '<p>a<i class="fa fa-pastafarianism" contenteditable="false">​</i>[]b<br></p>',
            });
        });
        it('should insert html in an empty editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[]<br>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter: '<i class="fa fa-pastafarianism" contenteditable="false">​</i>[]<br>',
            });
        });
        it('should insert html in between naked text in the editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: 'a[]b<br>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter:
                    'a<i class="fa fa-pastafarianism" contenteditable="false">​</i>[]b<br>',
            });
        });
        it('should insert several html nodes in between naked text in the editable', async () => {
            await testEditor(BasicEditor, {
                contentBefore: 'a[]e<br>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<p>b</p><p>c</p><p>d</p>');
                },
                contentAfter: 'a<p>b</p><p>c</p><p>d</p>[]e<br>',
            });
        });
    });
    describe('not collapsed selection', () => {
        it('should delete selection and insert html in its place', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '[a]<br>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter: '<i class="fa fa-pastafarianism" contenteditable="false">​</i>[]<br>',
            });
        });
        it('should delete selection and insert html in its place', async () => {
            await testEditor(BasicEditor, {
                contentBefore: 'a[b]c<br>',
                stepFunction: async editor => {
                    await editor.execCommand('insertHTML', '<i class="fa fa-pastafarianism"></i>');
                },
                contentAfter:
                    'a<i class="fa fa-pastafarianism" contenteditable="false">​</i>[]c<br>',
            });
        });
    });
});
