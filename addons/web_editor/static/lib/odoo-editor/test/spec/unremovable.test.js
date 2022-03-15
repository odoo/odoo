import {
    BasicEditor,
    deleteBackward,
    testEditor,
    unformat,
} from '../utils.js';

describe('Unremovables', () => {
    describe('deleterange', () => {
        describe('historyUndo', () => {
            it('should be unchanged after a deleterange and a historyUndo', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <p>[before</p>
                        <div class="oe_unremovable">
                            <div class="oe_unremovable" contenteditable="false"><p>noneditable</p></div>
                            <div class="oe_unremovable"><p>editable</p></div>
                        </div>
                        <p>after]</p>`),
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        editor.historyUndo();
                    },
                    contentAfter: unformat(`
                        <p>[before</p>
                        <div class="oe_unremovable">
                            <div class="oe_unremovable" contenteditable="false"><p>noneditable</p></div>
                            <div class="oe_unremovable"><p>editable</p></div>
                        </div>
                        <p>after]</p>`),
                });
            });
        });
    });
});
