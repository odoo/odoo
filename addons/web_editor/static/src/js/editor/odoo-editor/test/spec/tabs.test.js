import {
    BasicEditor,
    deleteBackward,
    deleteForward,
    insertText,
    triggerEvent,
    testEditor,
} from '../utils.js';

describe('Tabs', () => {
    const oeTab =  (size = '40px', contenteditable = true) => {
        return `<span class="oe-tabs"${contenteditable ? '' : ' contenteditable="false"'} style="width: ${size};">\u0009</span>\u200B`
    };
    describe('insert Tabulation', () => {
        it('should insert a tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab('32.8906px', false)}[]b</p>`,
                contentAfter: `<p>a${oeTab('32.8906px')}[]b</p>`,
            });
        });
        it('should clear selection and insert a tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[xxx]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab('32.8906px', false)}[]b</p>`,
                contentAfter: `<p>a${oeTab('32.8906px')}[]b</p>`,
            });
        });
        it('should insert two tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab('32.8906px', false)}${oeTab('40px', false)}[]b</p>`,
                contentAfter: `<p>a${oeTab('32.8906px')}${oeTab()}[]b</p>`,
            });
        });
        it('should insert two tab character with one char between', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                    await insertText(editor,'a');
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab('32.8906px', false)}a${oeTab('32.8906px', false)}[]b</p>`,
                contentAfter: `<p>a${oeTab('32.8906px')}a${oeTab('32.8906px')}[]b</p>`,
            });
        });
    });
    describe('delete backward Tabulation', () => {
        it('should remove one tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]${oeTab('32.8906px')}b</p>`,
            });
        });
        it('should remove two tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}${oeTab()}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}${oeTab()}[]${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]${oeTab('32.8906px')}b</p>`,
            });
        });
        it('should remove three tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}${oeTab()}${oeTab()}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
        });
    });
    describe('delete forward Tabulation', () => {
        it('should remove one tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab('32.8906px')}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a${oeTab('32.8906px')}[]b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab('32.8906px')}${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]${oeTab('32.8906px')}b3</p>`,
            });
        });
        it('should remove two tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab('32.8906px')}${oeTab()}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab('32.8906px')}${oeTab()}${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]${oeTab('32.8906px')}b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a${oeTab('32.8906px')}[]b3</p>`,
            });
        });
        it('should remove three tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab('32.8906px')}${oeTab()}${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
        });
    });
    describe('delete mixxed Tabulation', () => {
        it('should remove all tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}${oeTab()}[]${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteForward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b3</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab('32.8906px')}[]${oeTab()}${oeTab()}b4</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteBackward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b4</p>`,
            });
        });
    });
});
