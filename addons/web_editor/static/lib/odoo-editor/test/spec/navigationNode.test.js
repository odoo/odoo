import {
    BasicEditor,
    insertText,
    nextTickFrame,
    testEditor,
    triggerEvent,
    unformat,
} from '../utils.js';

/**
 * In the following tests, a fake keydown is generated. In cases where
 * the behavior is left up to the browser, nothing will happen since that event
 * is not trusted.
 * As the code for the navigationNode is symmetrical, there is not much point in
 * doing extensive testing for both events (ArrowUp and ArrowDown). Only basic
 * cases will be tested for both to validate the symmetry.
 */
describe('NavigationNode', () => {
    describe('Selection change', () => {
        /**
         * The first part of this test re-enacts another test which proves that
         * a navigationNode is created. The second part of this test changes the
         * selection in order to remove it, so, the final result is unchanged.
         */
        it('should remove a navigationNode when the selection is set outside of it.', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div>
                        <p>[]<br></p>
                    </div>`),
                stepFunction: async editor => {
                    const sel = document.getSelection();
                    const anchorNode = sel.anchorNode;
                    triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    sel.removeAllRanges();
                    const range = document.createRange();
                    range.setStart(anchorNode, 0);
                    range.collapse(true);
                    sel.addRange(range);
                    await nextTickFrame();
                },
                contentAfter: unformat(`
                    <div>
                        <p>[]<br></p>
                    </div>`),
            });
        });
        /**
         * Same test as before, but a text is inserted in the navigationNode
         * before changing the selection.
         */
        it('should not remove a navigationNode as long as its content was modified', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div>
                        <p>[]<br></p>
                    </div>`),
                stepFunction: async editor => {
                    const sel = document.getSelection();
                    const anchorNode = sel.anchorNode;
                    triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    await insertText(editor, 'text');
                    sel.removeAllRanges();
                    const range = document.createRange();
                    range.setStart(anchorNode, 0);
                    range.collapse(true);
                    sel.addRange(range);
                    await nextTickFrame();
                },
                contentAfter: unformat(`
                    <div>
                        <p>[]<br></p>
                    </div>
                    <p>text</p>`),
            });
        });
    });
    describe('Inline nodes', () => {
        describe('ArrowDown', () => {
            it('should not create a navigationNode if the cursor is on a text node with element siblings', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <p>te[]xt<br>anothertext</p>
                        </div></div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <p>te[]xt<br>anothertext</p>
                        </div></div>`),
                });
            });
            it('should not create a navigationNode between inline text nodes', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <span>sp[]an</span><a>link</a>
                        </div></div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <span>span</span><a>link</a>
                        </div></div>
                        <p>[]<br></p>`),
                });
            });
            it('should be able to create a navigationNode from an inline text node if the next sibling is a BR', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <p>text[]<br></p>
                        </div></div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div contenteditable="false"><div contenteditable="true">
                            <p>text<br></p>
                        </div></div>
                        <p>[]<br></p>`),
                });
            });
        });
    });
    describe('One depth variance', () => {
        describe('ArrowUp', () => {
            it('should create a navigationNode when the caret is in an editable and it is the only child of its parent', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <p>[]<br></p>
                        </div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowUp' });
                    },
                    contentAfter: unformat(`
                        <p>[]<br></p>
                        <div>
                            <p><br></p>
                        </div>`),
                });
            });
        });
        describe('ArrowDown', () => {
            it('should create a navigationNode when the caret is in an editable and it is the only child of its parent', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <p>[]<br></p>
                        </div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div>
                            <p><br></p>
                        </div>
                        <p>[]<br></p>`),
                });
            });
            it('should not create a navigationNode when the caret is on a <p> and the sibling is editable', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <p>[]<br></p>
                        <div><p><br></p></div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <p>[]<br></p>
                        <div><p><br></p></div>`),
                });
            });
            it('should not create a navigationNode when the caret is in an editable and the sibling is a <p>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <p>[]<br></p>
                        </div>
                        <p><br></p>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div>
                            <p>[]<br></p>
                        </div>
                        <p><br></p>`),
                });
            });
            it('should create a navigationNode from the sibling if the sibling is not editable', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <p>[]<br></p>
                        <div contenteditable="false"><p><br></p></div>
                        <div><p><br></p></div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <p><br></p>
                        <div contenteditable="false"><p><br></p></div>
                        <p>[]<br></p>
                        <div><p><br></p></div>`),
                });
            });
            describe('In a <div>', () => {
                it('should create a navigationNode when the caret is in an editable and the sibling is editable', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <div><div>
                                    <p>[]<br></p>
                                </div>
                                <div><p><br></p></div>
                            </div>`),
                        stepFunction: async editor => {
                            triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        },
                        contentAfter: unformat(`
                            <div><div>
                                    <p><br></p>
                                </div>
                                <p>[]<br></p>
                                <div><p><br></p></div>
                            </div>`),
                    });
                });
            });
            describe('In a <td> (table)', () => {
                it('should create a navigationNode when the caret is in an editable and the sibling is editable', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <table><tbody><tr><td><div>
                                    <p>[]<br></p>
                                </div>
                                <div><p><br></p></div>
                            </td></tr></tbody></table>`),
                        stepFunction: async editor => {
                            triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                        },
                        contentAfter: unformat(`
                            <table><tbody><tr><td><div>
                                    <p><br></p>
                                </div>
                                <p>[]<br></p>
                                <div><p><br></p></div>
                            </td></tr></tbody></table>`),
                    });
                });
            });
        });
    });
    describe('Multi-depth variance', () => {
        describe('ArrowUp', () => {
            it('should not create a navigationNode in a non editable parent and should check siblings in the right direction', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true"><p><br></p></div>
                        </div>
                        <div contenteditable="false">
                            <div contenteditable="true"><p>[]<br></p></div>
                        </div>
                        <p><br></p>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowUp' });
                    },
                    contentAfter: unformat(`
                        <div contenteditable="false">
                            <div contenteditable="true"><p><br></p></div>
                        </div>
                        <p>[]<br></p>
                        <div contenteditable="false">
                            <div contenteditable="true"><p><br></p></div>
                        </div>
                        <p><br></p>`),
                });
            });
            it('should enforce moving the caret when changing editable context (because of a contenteditable=false parent) in case a navigationNode is not needed', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <p>text</p>
                            <div contenteditable="false">
                                <div contenteditable="true"><p>[]<br></p></div>
                            </div>
                        </div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowUp' });
                    },
                    contentAfter: unformat(`
                        <div>
                            <p>[]text</p>
                            <div contenteditable="false">
                                <div contenteditable="true"><p><br></p></div>
                            </div>
                        </div>`),
                });
            });
        });
        describe('ArrowDown', () => {
            it('should create a navigationNode in the first editable parent when exiting an editable which has a non-editable parent', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <div contenteditable="false">
                                <div contenteditable="true"><p>[]<br></p></div>
                            </div>
                        </div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div>
                            <div contenteditable="false">
                                <div contenteditable="true"><p><br></p></div>
                            </div>
                            <p>[]<br></p>
                        </div>`),
                });
            });
            it('should enforce moving the caret when changing editable context (because of a contenteditable=false parent) in case a navigationNode is not needed', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div>
                            <div contenteditable="false">
                                <div contenteditable="true"><p>[]<br></p></div>
                            </div>
                            <p>text</p>
                        </div>`),
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowDown' });
                    },
                    contentAfter: unformat(`
                        <div>
                            <div contenteditable="false">
                                <div contenteditable="true"><p><br></p></div>
                            </div>
                            <p>[]text</p>
                        </div>`),
                });
            });
        });
    });
});
