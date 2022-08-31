import { parseHTML } from '../../src/utils/utils.js';
import { BasicEditor, testEditor } from '../utils.js';

describe('insert HTML', () => {
    describe('collapsed selection', () => {
        it('should insert html in an empty paragraph', async () => {
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
        it('should insert html after an empty paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><br></p>[]',
                stepFunction: async editor => {
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
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
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
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
                    await editor.execCommand('insert', parseHTML('<i class="fa fa-pastafarianism"></i>'));
                },
                contentAfterEdit: '<p><i class="fa fa-pastafarianism" contenteditable="false">\u200b</i>[]<br></p>',
                contentAfter: '<p><i class="fa fa-pastafarianism"></i>[]<br></p>',
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
    });
});
