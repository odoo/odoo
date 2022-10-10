import { OdooEditor } from '../../src/OdooEditor.js';
import { getTraversedNodes } from '../../src/utils/utils.js';
import {
    BasicEditor,
    deleteBackward,
    deleteForward,
    insertLineBreak,
    insertParagraphBreak,
    insertText,
    redo,
    testEditor,
    undo,
    unformat,
    triggerEvent,
} from '../utils.js';

async function twoDeleteForward(editor) {
    await deleteForward(editor);
    await deleteForward(editor);
}

describe('Editor', () => {
    describe('init', () => {
        describe('No orphan inline elements compatibility mode', () => {
            it('should transform root <br> into <p>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: 'ab<br>c',
                    contentAfter: '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p>',
                });
            });
            it('should keep <br> if necessary', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: 'ab<br><br>c',
                    contentAfter: '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;">c</p>',
                });
            });
            it('should keep multiple conecutive <br> if necessary', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: 'ab<br><br><br><br>c',
                    contentAfter: '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;"><br></p><p style="margin-bottom: 0px;">c</p>',
                });
            });
            it('should transform complex <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: 'ab<br>c<br>d<span class="keep">xxx</span>e<br>f',
                    contentAfter: '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p><p style="margin-bottom: 0px;">d<span class="keep">xxx</span>e</p><p style="margin-bottom: 0px;">f</p>',
                });
            });
            it('should transform complex <br> + keep li ', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: 'ab<br>c<ul><li>d</li><li>e</li></ul> f<br>g',
                    contentAfter: '<p style="margin-bottom: 0px;">ab</p><p style="margin-bottom: 0px;">c</p><ul><li>d</li><li>e</li></ul><p style="margin-bottom: 0px;"> f</p><p style="margin-bottom: 0px;">g</p>',
                });
            });
            it('should not transform <br> inside <p>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<br>c</p>',
                    contentAfter: '<p>ab<br>c</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<br>c</p><p>d<br></p>',
                    contentAfter: '<p>ab<br>c</p><p>d<br></p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: 'xx<p>ab<br>c</p>d<br>yy',
                    contentAfter: '<p style="margin-bottom: 0px;">xx</p><p>ab<br>c</p><p style="margin-bottom: 0px;">d</p><p style="margin-bottom: 0px;">yy</p>',
                });
            });
            it('should not transform indentation', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: `
    <p>ab</p>  
    <p>c</p>`,
                    contentAfter: `
    <p>ab</p>  
    <p>c</p>`,
                });
            });
            it('should transform root .fa', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab</p><i class="fa fa-beer"></i><p>c</p>',
                    contentAfter: '<p>ab</p><p style="margin-bottom: 0px;"><i class="fa fa-beer"></i></p><p>c</p>',
                });
            });
        });
    });
    describe('deleteForward', () => {
        describe('Selection collapsed', () => {
            describe('Basic', () => {
                it('should do nothing', async () => {
                    // TODO the addition of <br/> "correction" part was judged
                    // unnecessary to enforce, the rest of the test still makes
                    // sense: not removing the unique <p/> and keeping the
                    // cursor at the right place.
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[]</p>',
                    //     stepFunction: deleteForward,
                    //     contentAfter: '<p>[]</p>',
                    // });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: deleteForward,
                    //     // The <br> is there only to make the <p> visible.
                    //     // It does not exist in VDocument and selecting it
                    //     // has no meaning in the DOM.
                    //     contentAfter: '<p>[]<br></p>',
                    // });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>abc[]</p>',
                    });
                });
                it('should delete the first character in a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>[]bc</p>',
                    });
                });
                it('should delete a character within a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[]bc</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>a[]c</p>',
                    });
                });
                it('should delete the last character in a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]c</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>ab[]</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab []c</p>',
                        stepFunction: deleteForward,
                        // The space should be converted to an unbreakable space
                        // so it is visible.
                        contentAfter: '<p>ab&nbsp;[]</p>',
                    });
                });
                it('should merge a paragraph into an empty paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<br></p><p>abc</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>[]abc</p>',
                    });
                });
                it('should merge P node correctly ', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>a<p>b[]</p><p>c</p>d</div>',
                        stepFunction: deleteForward,
                        contentAfter: '<div>a<p>b[]c</p>d</div>',
                    });
                });
                it('should merge node correctly', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>a<span>b[]</span><p>c</p>d</div>',
                        stepFunction: deleteForward,
                        contentAfter: '<div>a<span>b[]</span>c<br>d</div>',
                    });
                });
                it('should merge SPAN node correctly ', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>a<span>bc[]</span><span>de</span>f</div>',
                        stepFunction: deleteForward,
                        contentAfter: '<div>a<span>bc[]e</span>f</div>',
                    });
                });
                it('should merge diferent element correctly', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>a<span>b[]</span><p>c</p>d</div>',
                        stepFunction: deleteForward,
                        contentAfter: '<div>a<span>b[]</span>c<br>d</div>',
                    });
                });
                it('should ignore ZWS', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]\u200Bc</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>ab[]</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>de[]\u200B</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>de[]</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]\u200Bf</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>[]<br></p>',
                    });
                });
                it('should delete through ZWS and Empty Inline', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[]b<span class="style">c</span>de</p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await deleteForward(editor);
                            await deleteForward(editor);
                        },
                        contentAfter: '<p>a[]e</p>',
                    });
                });
                it('ZWS: should delete element content but keep cursor in', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<span class="style">[]cd</span>ef</p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await deleteForward(editor);
                        },
                        contentAfterEdit: '<p>ab<span class="style" data-oe-zws-empty-inline="">[]\u200B</span>ef</p>',
                        contentAfter: '<p>ab<span class="style">[]\u200B</span>ef</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<span class="style">[]cd</span>ef</p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await deleteForward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p>ab<span class="style">x[]</span>ef</p>',
                    });
                });
                it('should ignore ZWS and merge', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span><b>ab</b></p>',
                        contentBeforeEdit: '<p><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span><b>ab</b></p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><b>x[]b</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span><span>cd</span></p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><span>x[]d</span></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span><br><b>ef</b></p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><b>x[]ef</b></p>',
                    });
                });
                it('should not break unbreakables', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `<div class="oe_unbreakable">abc</div></div></div></div>`,
                        stepFunction: deleteForward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `<div class="oe_unbreakable">abc</div></div></div></div>`,
                    });
                });
                it('should remove empty unbreakable', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div class="accolade"><div><p>ABC</p></div><div class="colibri">X[]</div></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<div class="accolade"><div><p>AB[]</p></div></div>',
                    });
                });
                it('should not remove empty Bootstrap column', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><div><p>ABC</p></div><div class="col">X[]</div></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<div><div><p>ABC</p></div><div class="col">[]<br></div></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><div><p>ABC</p></div><div class="col-12">X[]</div></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<div><div><p>ABC</p></div><div class="col-12">[]<br></div></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><div><p>ABC</p></div><div class="col-lg-3">X[]</div></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<div><div><p>ABC</p></div><div class="col-lg-3">[]<br></div></div>',
                    });
                });
                it('should remove empty unbreakable  (formated 1)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div><div><p>ABC</p></div><div>
X[]
</div></div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<div><div><p>AB[]</p></div></div>',
                    });
                });
                it('should remove empty unbreakable (formated 2)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div>
                                            <div>
                                                <p>ABC</p>
                                            </div>
                                            <div>X[]</div>
                                        </div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: `<div>
                                            <div>
                                                <p>AB[]</p></div></div>`,
                    });
                });
                it('should remove empty unbreakable (formated 3)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div>
                                            <div>
                                                <p>ABC</p>
                                            </div>
                                            <div>
                                                X[]
                                            </div>
                                        </div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: `<div>
                                            <div>
                                                <p>AB[]</p></div></div>`,
                    });
                });
                it('should remove contenteditable="false"', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div>[]<span contenteditable="false">abc</span>def</div>`,
                        stepFunction: async editor => {
                            await deleteForward(editor);
                        },
                        contentAfter: `<div>[]def</div>`,
                    });
                });
                it('should remove contenteditable="False"', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div>[]<span contenteditable="False">abc</span>def</div>`,
                        stepFunction: async editor => {
                            await deleteForward(editor);
                        },
                        contentAfter: `<div>[]def</div>`,
                    });
                });
            });
            describe('white spaces', () => {
                describe('no intefering spaces', () => {
                    it('should delete a br line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]<br>def</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                    });
                    it('should delete a line break and merge the <p>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]</p><p>def</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                    });
                });
                describe('intefering spaces', () => {
                    it('should delete a br line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]<br> def</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                    });
                    it('should merge the two <p>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]</p> <p>def</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]</p> <p>def</p> orphan node',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]def</p><p style="margin-bottom: 0px;"> orphan node</p>',
                        });
                    });
                    it('should delete the space if the second <p> is display inline', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div>abc[] <p style="display: inline">def</p></div>',
                            stepFunction: deleteForward,
                            contentAfter: '<div>abc[]<p style="display: inline">def</p></div>',
                        });
                    });
                    it('should delete the space between the two <span>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><span>abc[]</span> <span>def</span></div>',
                            stepFunction: deleteForward,
                            contentAfter: '<div><span>abc[]def</span></div>',
                        });
                    });
                    it('should delete the space before a <span>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div>abc[] <span>def</span></div>',
                            stepFunction: deleteForward,
                            contentAfter: '<div>abc[]<span>def</span></div>',
                        });
                    });
                });
                describe('intefering spaces, multiple deleteForward', () => {
                    it('should delete a br line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]x<br> def</p>',
                            stepFunction: twoDeleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                    });
                    it('should merge the two <p>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]x</p> <p>def</p>',
                            stepFunction: twoDeleteForward,
                            contentAfter: '<p>abc[]def</p>',
                        });
                    });
                    it('should delete the space if the second <p> is display inline', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div>abc[]x <p style="display: inline">def</p></div>',
                            stepFunction: twoDeleteForward,
                            contentAfter: '<div>abc[]<p style="display: inline">def</p></div>',
                        });
                    });
                    it('should delete the space between the two <span>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><span>abc[]x</span> <span>def</span></div>',
                            stepFunction: twoDeleteForward,
                            contentAfter: '<div><span>abc[]def</span></div>',
                        });
                    });
                    it('should delete the space before a <span>', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div>abc[]x <span>def</span></div>',
                            stepFunction: twoDeleteForward,
                            contentAfter: '<div>abc[]<span>def</span></div>',
                        });
                    });
                });
            });
            describe('Line breaks', () => {
                describe('Single', () => {
                    it('should delete a leading line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>[]<br>abc</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>[]abc</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>[]<br> abc</p>',
                            stepFunction: deleteForward,
                            // The space after the <br> is expected to be parsed
                            // away, like it is in the DOM.
                            contentAfter: '<p>[]abc</p>',
                        });
                    });
                    it('should delete a line break within a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]<br>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab[]cd</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab []<br>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab []cd</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]<br> cd</p>',
                            stepFunction: deleteForward,
                            // The space after the <br> is expected to be parsed
                            // away, like it is in the DOM.
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                    it('should delete a trailing line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[]<br><br></p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc []<br><br></p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc&nbsp;[]</p>',
                        });
                    });
                    it('should delete a character and a line break, emptying a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>[]a<br><br></p><p>bcd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>[]<br></p><p>bcd</p>',
                        });
                    });
                    it('should delete a character before a trailing line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]c<br><br></p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab[]<br><br></p>',
                        });
                    });
                });
                describe('Consecutive', () => {
                    it('should merge a paragraph into a paragraph with 4 <br>', async () => {
                        // 1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab</p><p><br><br><br>[]cd</p>',
                        });
                        // 2-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>',
                            stepFunction: deleteForward,
                            // This should be identical to 1
                            contentAfter: '<p>ab</p><p><br><br><br>[]cd</p>',
                        });
                    });
                    it('should delete a trailing line break', async () => {
                        // 3-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab</p><p><br><br>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete a trailing line break, then merge a paragraph into a paragraph with 3 <br>', async () => {
                        // 3-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p><br><br>[]cd</p>',
                        });
                    });
                    it('should delete a line break', async () => {
                        // 4-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab</p><p><br>[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks', async () => {
                        // 4-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p><br>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks, then merge a paragraph into a paragraph with 2 <br>', async () => {
                        // 4-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p><br>[]cd</p>',
                        });
                    });
                    it('should delete a line break', async () => {
                        // 5-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab</p><p>[]<br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks', async () => {
                        // 5-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete three line breaks (emptying a paragraph)', async () => {
                        // 5-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete three line breaks, then merge a paragraph into an empty parargaph', async () => {
                        // 5-4
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]cd</p>',
                        });
                    });
                    it('should merge a paragraph with 4 <br> into a paragraph with text', async () => {
                        // 6-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]</p><p><br><br><br><br></p><p>cd</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>ab[]<br><br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should merge a paragraph with 4 <br> into a paragraph with text, then delete a line break', async () => {
                        // 6-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]</p><p><br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab[]<br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should merge a paragraph with 4 <br> into a paragraph with text, then delete two line breaks', async () => {
                        // 6-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]</p><p><br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should merge a paragraph with 4 <br> into a paragraph with text, then delete three line breaks', async () => {
                        // 6-4
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]</p><p><br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab[]</p><p>cd</p>',
                        });
                    });
                    it('should merge a paragraph with 4 <br> into a paragraph with text, then delete three line breaks, then merge two paragraphs with text', async () => {
                        // 6-5
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]</p><p><br><br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                });
            });
            describe('Pre', () => {
                it('should delete a character in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]cd</pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>ab[]d</pre>',
                    });
                });
                it('should delete a character in a pre (space before)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>     ab[]cd</pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>     ab[]d</pre>',
                    });
                });
                it('should delete a character in a pre (space after)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]cd     </pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>ab[]d     </pre>',
                    });
                });
                it('should delete a character in a pre (space before and after)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>     ab[]cd     </pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>     ab[]d     </pre>',
                    });
                });
                it('should delete a space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>  []   ab</pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>  []  ab</pre>',
                    });
                });
                it('should delete a newline in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]\ncd</pre>',
                        stepFunction: deleteForward,
                        contentAfter: '<pre>ab[]cd</pre>',
                    });
                });
                it('should delete all leading space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>[]     ab</pre>',
                        stepFunction: async BasicEditor => {
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                        },
                        contentAfter: '<pre>[]ab</pre>',
                    });
                });
                it('should delete all trailing space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]     </pre>',
                        stepFunction: async BasicEditor => {
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                            await deleteForward(BasicEditor);
                        },
                        contentAfter: '<pre>ab[]</pre>',
                    });
                });
            });
            describe('Formats', () => {
                it('should delete a character after a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc[]</b>def</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p><b>abc[]</b>ef</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc</b>[]def</p>',
                        stepFunction: deleteForward,
                        // The selection is normalized so we only have one way
                        // to represent a position.
                        contentAfter: '<p><b>abc[]</b>ef</p>',
                    });
                });
            });
            describe('Merging different types of elements', () => {
                it('should merge a paragraph with text into a heading1 with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>ab[]</h1><p>cd</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<h1>ab[]cd</h1>',
                    });
                });
                it('should merge an empty paragraph into a heading1 with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>ab[]</h1><p><br></p>',
                        stepFunction: deleteForward,
                        contentAfter: '<h1>ab[]</h1>',
                    });
                });
                it('should merge a heading1 with text into an empty paragraph (keeping the heading)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br>[]</p><h1>ab</h1>',
                        stepFunction: deleteForward,
                        // JW cAfter: '<h1>[]ab</h1>',
                        contentAfter: '<p>[]ab</p>',
                    });
                });
                it('should merge a text following a paragraph (keeping the text)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]</p>cd',
                        stepFunction: deleteForward,
                        contentAfter: '<p>ab[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]</p>cd<p>ef</p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p>ab[]cd</p><p>ef</p>',
                    });
                });
            });
            describe('With attributes', () => {
                it('should merge a paragraph without class into an empty paragraph with a class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p class="a"><br>[]</p><p>abc</p>',
                        stepFunction: deleteForward,
                        // JW cAfter: '<p>[]abc</p>',
                        contentAfter: '<p class="a">[]abc</p>',
                    });
                });
                it('should merge two paragraphs with spans of same classes', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">dom to[]</span></p><p><span class="a">edit</span></p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p><span class="a">dom to[]edit</span></p>',
                    });
                });
                it('should merge two paragraphs with spans of different classes without merging the spans', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">dom to[]</span></p><p><span class="b">edit</span></p>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<p><span class="a">dom to[]</span><span class="b">edit</span></p>',
                    });
                });
                it('should merge two paragraphs of different classes, each containing spans of the same class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p class="a"><span class="b">ab[]</span></p><p class="c"><span class="b">cd</span></p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p class="a"><span class="b">ab[]cd</span></p>',
                    });
                });
                it('should merge two paragraphs of different classes, each containing spans of different classes without merging the spans', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p class="a"><span class="b">ab[]</span></p><p class="c"><span class="d">cd</span></p>',
                        stepFunction: deleteForward,
                        contentAfter:
                            '<p class="a"><span class="b">ab[]</span><span class="d">cd</span></p>',
                    });
                });
                it('should delete a line break between two spans with bold and merge these formats', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span><b>ab[]</b></span><br/><span><b>cd</b></span></p>',
                        stepFunction: deleteForward,
                        contentAfter: '<p><span><b>ab[]cd</b></span></p>',
                    });
                });
                it('should delete a character in a span with bold, then a line break between two spans with bold and merge these formats', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span><b>a[]b</b></span><br><span><b><br>cde</b></span></p>',
                        stepFunction: async editor => {
                            await deleteForward(editor);
                            await deleteForward(editor);
                        },
                        contentAfter: '<p><span><b>a[]<br>cde</b></span></p>',
                    });
                });
            });
            describe('POC extra tests', () => {
                it('should not remove a table without selecting it', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(
                            `<p>ab[]</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                        stepFunction: deleteForward,
                        contentAfter: unformat(
                            `<p>ab[]</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                    });
                });
                it('should not merge a table into its next sibling', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij[]</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                        stepFunction: deleteForward,
                        contentAfter: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij[]</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                    });
                });
                it('should delete an image that is displayed as a block', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`<div>a[b<img style="display: block;"/>c]d</div>`),
                        stepFunction: editor => editor._applyCommand('oDeleteBackward'),
                        contentAfter: unformat(`<div>a[]d</div>`),
                    });
                });
            });
        });
        describe('Selection not collapsed', () => {
            it('should delete part of the text within a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd]ef</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>ab[]ef</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd[ef</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>ab[]ef</p>',
                });
            });
            it('should merge node correctly', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<span>b[c</span><p>d]e</p>f</div>',
                    stepFunction: deleteForward,
                    contentAfter: '<div>a<span>b[]</span>e<br>f</div>',
                });
            });
            it('should delete part of the text across two paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: deleteForward,
                    contentAfter: '<div>a<p>b[]e</p>f</div>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b]c</p><p>d[e</p>f</div>',
                    stepFunction: deleteForward,
                    contentAfter: '<div>a<p>b[]e</p>f</div>',
                });
            });
            it('should delete empty nodes ', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><font>[abcdef]</font></h1>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>[]<br></h1>',
                });
            });
            it('should not delete styling nodes if not selected', async () => {
                // deleteForward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="style-class">[bcde]</span>f</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>a<span class="style-class">[]\u200B</span>f</p>',
                });
                // deleteBackward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<span class="style-class">[bcde]</span>f</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>a<span class="style-class">[]\u200B</span>f</p>',
                });
            });
            it('should delete styling nodes when delete if empty', async () => {
                // deleteBackward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab <span class="style-class">[cd]</span> ef</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        await deleteBackward(editor);
                    },
                    contentAfter: '<p>ab[]&nbsp;ef</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>uv<span class="style-class">[wx]</span>yz</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        await deleteBackward(editor);
                    },
                    contentAfter: '<p>u[]yz</p>',
                });
                // deleteForward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab <span class="style-class">[cd]</span> ef</p>',
                    stepFunction: async editor => {
                        await deleteForward(editor);
                        await deleteForward(editor);
                    },
                    contentAfter: '<p>ab []ef</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>uv<span class="style-class">[wx]</span>yz</p>',
                    stepFunction: async editor => {
                        await deleteForward(editor);
                        await deleteForward(editor);
                    },
                    contentAfter: '<p>uv[]z</p>',
                });
            });
            it('should delete across two paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd</p><p>ef]gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>ab[]gh</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd</p><p>ef[gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>ab[]gh</p>',
                });
            });
            it('should delete all the text in a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]abc[</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>[]<br></p>',
                });
            });
            it('should delete a complex selection accross format nodes and multiple paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab[cd</b></p><p><b>ef<br/>gh</b>ij<i>kl]</i>mn</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p><b>ab[]</b>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab[cd</b></p><p><b>ef<br/>gh</b>ij<i>k]l</i>mn</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p><b>ab[]</b><i>l</i>mn</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab]cd</b></p><p><b>ef<br/>gh</b>ij<i>kl[</i>mn</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p><b>ab[]</b>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab]cd</b></p><p><b>ef<br/>gh</b>ij<i>k[l</i>mn</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p><b>ab[]</b><i>l</i>mn</p>',
                });
            });
            it('should delete all contents of a complex DOM with format nodes and multiple paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>[abcd</b></p><p><b>ef<br/>gh</b>ij<i>kl</i>mn]</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>]abcd</b></p><p><b>ef<br/>gh</b>ij<i>kl</i>mn[</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>[]<br></p>',
                });
            });
            it('should delete a selection accross a heading1 and a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>ab [cd</h1><p>ef]gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>ab []gh</h1>',
                });
                // // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>ab ]cd</h1><p>ef[gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>ab []gh</h1>',
                });
            });
            it('should delete a selection from the beginning of a heading1 with a format to the middle of a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><b>[abcd</b></h1><p>ef]gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[<b>abcd</b></h1><p>ef]gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><b>]abcd</b></h1><p>ef[gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>]<b>abcd</b></h1><p>ef[gh</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<h1>[]gh</h1>',
                });
            });
            it('should not break unbreakables', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                        `<div class="oe_unbreakable"><div class="oe_unbreakable">a[bc</div>` +
                        `<div class="oe_unbreakable">de]f</div></div></div></div>`,
                    stepFunction: deleteForward,
                    contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                        `<div class="oe_unbreakable"><div class="oe_unbreakable">a[]</div>` +
                        `<div class="oe_unbreakable">f</div></div></div></div>`,
                });
                await testEditor(BasicEditor, {
                    contentBefore:
                        '<p class="oe_unbreakable">a[bc</p><p class="oe_unbreakable">de]f</p>',
                    stepFunction: deleteForward,
                    contentAfter:
                        '<p class="oe_unbreakable">a[]</p><p class="oe_unbreakable">f</p>', // JW without oe_breakable classes of course
                });
            });
            it('should delete a heading (triple click delete)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[abc</h1><p>]def</p>',
                    stepFunction: deleteForward,
                    // JW cAfter: '<p>[]def</p>',
                    contentAfter: '<h1>[]<br></h1><p>def</p>',
                });
            });
            it('should empty an inline unremovable but remain in it', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<b class="oe_unremovable">[cd]</b>ef</p>',
                    stepFunction: deleteForward,
                    contentAfter: '<p>ab<b class="oe_unremovable">[]\u200B</b>ef</p>',
                });
            });
        });
    });

    describe('deleteBackward', () => {
        describe('Selection collapsed', () => {
            describe('Basic', () => {
                it('should do nothing', async () => {
                    // TODO the addition of <br/> "correction" part was judged
                    // unnecessary to enforce, the rest of the test still makes
                    // sense: not removing the unique <p/> and keeping the
                    // cursor at the right place.
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]</p>',
                    });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: deleteBackward,
                    //     // The <br> is there only to make the <p> visible.
                    //     // It does not exist in VDocument and selecting it
                    //     // has no meaning in the DOM.
                    //     contentAfter: '<p>[]<br></p>',
                    // });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]abc</p>',
                    });
                });
                it('should delete the first character in a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[]bc</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]bc</p>',
                    });
                });
                it('should delete a character within a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]c</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>a[]c</p>',
                    });
                });
                it('should delete the last character in a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab c[]</p>',
                        stepFunction: deleteBackward,
                        // The space should be converted to an unbreakable space
                        // so it is visible.
                        contentAfter: '<p>ab&nbsp;[]</p>',
                    });
                });
                it('should merge a paragraph into an empty paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br></p><p>[]abc</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]abc</p>',
                    });
                });
                it('should merge node correctly', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>a<span>b</span><p>[]c</p>d</div>',
                        stepFunction: deleteBackward,
                        contentAfter: '<div>a<span>b[]</span>c<br>d</div>',
                    });
                });
                it('should ignore ZWS', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab\u200B[]c</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>a[]c</p>',
                    });
                });
                it('should keep inline block', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>ab</p><br><span>c[]</span></div>',
                        stepFunction: deleteBackward,
                        contentAfterEdit: '<div><p>ab</p><br><span data-oe-zws-empty-inline="">[]\u200B</span></div>',
                        contentAfter: '<div><p>ab</p><br>[]</div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>uv</p><br><span class="style">w[]</span></div>',
                        stepFunction: deleteBackward,
                        contentAfterEdit: '<div><p>uv</p><br><span class="style" data-oe-zws-empty-inline="">[]\u200B</span></div>',
                        contentAfter: '<div><p>uv</p><br><span class="style">[]\u200B</span></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>cd</p><br><span>e[]</span></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfterEdit: '<div><p>cd</p><br><span>x[]</span></div>',
                        contentAfter: '<div><p>cd</p><br><span>x[]</span></div>',
                    });
                });
                it('should delete through ZWS and Empty Inline', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<span class="style">c</span>d[]e</p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<p>a[]e</p>',
                    });
                });
                it('ZWS: should delete element content but keep cursor in', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>uv<i style="color:red">w[]</i>xy</p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'i');
                        },
                        contentAfterEdit: '<p>uv<i style="color:red">i[]</i>xy</p>',
                        contentAfter: '<p>uv<i style="color:red">i[]</i>xy</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<span class="style">cd[]</span>ef</p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfterEdit: '<p>ab<span class="style" data-oe-zws-empty-inline="">[]\u200B</span>ef</p>',
                        contentAfter: '<p>ab<span class="style">[]\u200B</span>ef</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<span class="style">cd[]</span>ef</p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfterEdit: '<p>ab<span class="style">x[]</span>ef</p>',
                        contentAfter: '<p>ab<span class="style">x[]</span>ef</p>',
                    });
                });
                it('should ignore ZWS and merge', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab</b><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><b>ax[]</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span>cd</span><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><span>cx[]</span></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ef</b><br><span class="removeme" data-oe-zws-empty-inline="">[]\u200B</span></p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<p><b>efx[]</b></p>',
                    });
                });
                it('should ignore ZWS and merge', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>ab</p><span>[]\u200B</span></div>',
                        stepFunction: deleteBackward,
                        contentAfter: '<div><p>ab[]</p></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>cd</p><br><span>[]\u200B</span></div>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await insertText(editor, 'x');
                        },
                        contentAfter: '<div><p>cd</p>x[]</div>',
                    });
                });
                it('should not break unbreakables', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `<div class="oe_unbreakable">abc</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `<div class="oe_unbreakable">abc</div></div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[ab</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">e]f</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `<div class="oe_unbreakable">f</div></div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[b</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">e]f</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[]</div>` +
                            `<div class="oe_unbreakable">f</div></div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[b</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">ef]</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[]</div>` +
                            `</div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[ab</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">ef]</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `</div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[ab</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">ef</div></div>` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">gh</div>` +
                            `<div class="oe_unbreakable">ij</div>` +
                            `<div class="oe_unbreakable">k]l</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">[]<br></div>` +
                            `</div><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable">l</div></div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[b</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">ef</div></div>` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">gh</div>` +
                            `<div class="oe_unbreakable">ij</div>` +
                            `<div class="oe_unbreakable">k]l</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[]</div>` +
                            `</div><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable">l</div></div></div></div>`,
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[b</div>` +
                            `<div class="oe_unbreakable">cd</div>` +
                            `<div class="oe_unbreakable">ef</div></div>` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">gh</div>` +
                            `<div class="oe_unbreakable">ij</div>` +
                            `<div class="oe_unbreakable">kl]</div></div></div></div>`,
                        stepFunction: editor => deleteBackward(editor),
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable">a[]</div>` +
                            `</div></div></div>`,
                    });
                });
                it('should merge the following inline text node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc</p>[]def',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>abc[]def</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc</p>[]def<p>ghi</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>abc[]def</p><p>ghi</p>',
                    });
                });
                it('should delete starting white space and merge paragraphs', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<p>mollis.</p><p>\n <i>[]Pe</i><i>lentesque</i></p>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<p>mollis.[]<i>Pelentesque</i></p>`,
                    });
                });
                it('should remove contenteditable="false"', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div><span contenteditable="false">abc</span>[]def</div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                        },
                        contentAfter: `<div>[]def</div>`,
                    });
                });
                it('should remove contenteditable="False"', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div><span contenteditable="False">abc</span>[]def</div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                        },
                        contentAfter: `<div>[]def</div>`,
                    });
                });
                it('should remove contenteditable="false" at the beggining of a P', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<p>abc</p><div contenteditable="false">def</div><p>[]ghi</p>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                        },
                        contentAfter: `<p>abc</p><p>[]ghi</p>`,
                    });
                });
                it('should remove a fontawesome', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div><p>abc</p><span class="fa"></span><p>[]def</p></div>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                        },
                        contentAfter: `<div><p>abc</p><p>[]def</p></div>`,
                    });
                });
                it('should remove a media element', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<p>abc</p><div class="o_image"></div><p>[]def</p>`,
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                        },
                        contentAfter: `<p>abc</p><p>[]def</p>`,
                    });
                });
            });
            describe('Line breaks', () => {
                describe('Single', () => {
                    it('should delete a leading line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p><br>[]abc</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>[]abc</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p><br>[] abc</p>',
                            stepFunction: deleteBackward,
                            // The space after the <br> is expected to be parsed
                            // away, like it is in the DOM.
                            contentAfter: '<p>[]abc</p>',
                        });
                    });
                    it('should delete a line break within a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab<br>[]cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab[]cd</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab <br>[]cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab []cd</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab<br>[] cd</p>',
                            stepFunction: deleteBackward,
                            // The space after the <br> is expected to be parsed
                            // away, like it is in the DOM.
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                    it('should delete a trailing line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc<br><br>[]</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc<br>[]<br></p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc <br><br>[]</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc&nbsp;[]</p>',
                        });
                    });
                    it('should delete a character and a line break, emptying a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>aaa</p><p><br>a[]</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>aaa</p><p>[]<br></p>',
                        });
                    });
                    it('should delete a character after a trailing line break', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab<br>c[]</p>',
                            stepFunction: deleteBackward,
                            // A new <br> should be insterted, to make the first one
                            // visible.
                            contentAfter: '<p>ab<br>[]<br></p>',
                        });
                    });
                });
                describe('Consecutive', () => {
                    it('should merge a paragraph with 4 <br> into a paragraph with text', async () => {
                        // 1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>[]<br><br><br><br></p><p>cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab[]<br><br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete a line break', async () => {
                        // 2-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab</p><p>[]<br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete a line break, then merge a paragraph with 3 <br> into a paragraph with text', async () => {
                        // 2-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br>[]<br><br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab[]<br><br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete a line break', async () => {
                        // 3-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab</p><p><br>[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks', async () => {
                        // 3-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks, then merge a paragraph with 3 <br> into a paragraph with text', async () => {
                        // 3-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br>[]<br><br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab[]<br><br></p><p>cd</p>',
                        });
                    });
                    it('should delete a line break when several', async () => {
                        // 4-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>',
                            stepFunction: deleteBackward,
                            // A trailing line break is rendered as two <br>.
                            contentAfter: '<p>ab</p><p><br><br>[]<br></p><p>cd</p>',
                        });
                        // 5-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>',
                            stepFunction: deleteBackward,
                            // This should be identical to 4-1
                            contentAfter: '<p>ab</p><p><br><br>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete two line breaks', async () => {
                        // 4-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            // A trailing line break is rendered as two <br>.
                            contentAfter: '<p>ab</p><p><br>[]<br></p><p>cd</p>',
                        });
                        // 5-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            // This should be identical to 4-2
                            contentAfter: '<p>ab</p><p><br>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete three line breaks (emptying a paragraph)', async () => {
                        // 4-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]<br></p><p>cd</p>',
                        });
                        // 5-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            // This should be identical to 4-3
                            contentAfter: '<p>ab</p><p>[]<br></p><p>cd</p>',
                        });
                    });
                    it('should delete three line breaks, then merge an empty parargaph into a paragraph with text', async () => {
                        // 4-4
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br>[]<br></p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            // This should be identical to 4-4
                            contentAfter: '<p>ab[]</p><p>cd</p>',
                        });
                        // 5-4
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br>[]</p><p>cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab[]</p><p>cd</p>',
                        });
                    });
                    it('should merge a paragraph into a paragraph with 4 <br>', async () => {
                        // 6-1
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br></p><p>[]cd</p>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>ab</p><p><br><br><br>[]cd</p>',
                        });
                    });
                    it('should merge a paragraph into a paragraph with 4 <br>, then delete a trailing line break', async () => {
                        // 6-2
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br></p><p>[]cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab</p><p><br><br>[]cd</p>',
                        });
                    });
                    it('should merge a paragraph into a paragraph with 4 <br>, then delete two line breaks', async () => {
                        // 6-3
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br></p><p>[]cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab</p><p><br>[]cd</p>',
                        });
                    });
                    it('should merge a paragraph into a paragraph with 4 <br>, then delete three line breaks', async () => {
                        // 6-4
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br></p><p>[]cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab</p><p>[]cd</p>',
                        });
                    });
                    it('should merge a paragraph into a paragraph with 4 <br>, then delete three line breaks, then merge two paragraphs with text', async () => {
                        // 6-5
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p><br><br><br><br></p><p>[]cd</p>',
                            stepFunction: async editor => {
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                                await deleteBackward(editor);
                            },
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                });
            });
            describe('Pre', () => {
                it('should delete a character in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]cd</pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>a[]cd</pre>',
                    });
                });
                it('should delete a character in a pre (space before)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>     ab[]cd</pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>     a[]cd</pre>',
                    });
                });
                it('should delete a character in a pre (space after)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]cd     </pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>a[]cd     </pre>',
                    });
                });
                it('should delete a character in a pre (space before and after)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>     ab[]cd     </pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>     a[]cd     </pre>',
                    });
                });
                it('should delete a space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>   []  ab</pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>  []  ab</pre>',
                    });
                });
                it('should delete a newline in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab\n[]cd</pre>',
                        stepFunction: deleteBackward,
                        contentAfter: '<pre>ab[]cd</pre>',
                    });
                });
                it('should delete all leading space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>     []ab</pre>',
                        stepFunction: async BasicEditor => {
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                        },
                        contentAfter: '<pre>[]ab</pre>',
                    });
                });
                it('should delete all trailing space in a pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab     []</pre>',
                        stepFunction: async BasicEditor => {
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                            await deleteBackward(BasicEditor);
                        },
                        contentAfter: '<pre>ab[]</pre>',
                    });
                });
            });
            describe('Formats', () => {
                it('should delete a character before a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc<b>[]def</b></p>',
                        stepFunction: deleteBackward,
                        // The selection is normalized so we only have one way
                        // to represent a position.
                        contentAfter: '<p>ab[]<b>def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]<b>def</b></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]<b>def</b></p>',
                    });
                });
            });
            describe('Merging different types of elements', () => {
                it('should merge a paragraph with text into a paragraph with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab</p><p>[]cd</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]cd</p>',
                    });
                });
                it('should merge a paragraph with formated text into a paragraph with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>aa</p><p>[]a<i>bbb</i></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>aa[]a<i>bbb</i></p>',
                    });
                });
                it('should merge a paragraph with text into a heading1 with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>ab</h1><p>[]cd</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<h1>ab[]cd</h1>',
                    });
                });
                it('should merge an empty paragraph into a heading1 with text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>ab</h1><p>[]<br></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<h1>ab[]</h1>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>ab</h1><p><br>[]</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<h1>ab[]</h1>',
                    });
                });
                it('should merge a heading1 with text into an empty paragraph (keeping the heading)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br></p><h1>[]ab</h1>',
                        stepFunction: deleteBackward,
                        // JW cAfter: '<h1>[]ab</h1>',
                        contentAfter: '<p>[]ab</p>',
                    });
                });
                it('should merge with previous node (default behaviour)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<jw-block-a>a</jw-block-a><jw-block-b>[]b</jw-block-b>',
                        stepFunction: deleteBackward,
                        contentAfter: '<jw-block-a>a[]b</jw-block-a>',
                    });
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<jw-block-a>a</jw-block-a><jw-block-b>[<br>]</jw-block-b>',
                    //     stepFunction: deleteBackward,
                    //     contentAfter: '<jw-block-a>a[]</jw-block-a>',
                    // });
                });
                it('should merge nested elements (default behaviour)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<jw-block-a><jw-block-b>ab</jw-block-b></jw-block-a><jw-block-c><jw-block-d>[]cd</jw-block-d></jw-block-c>',
                        stepFunction: deleteBackward,
                        contentAfter: '<jw-block-a><jw-block-b>ab[]cd</jw-block-b></jw-block-a>',
                    });
                    // await testEditor(BasicEditor, {
                    //     contentBefore:
                    //         '<jw-block-a><jw-block-b>ab</jw-block-b></jw-block-a><jw-block-c><jw-block-d>[<br>]</jw-block-d></jw-block-c>',
                    //     stepFunction: deleteBackward,
                    //     contentAfter: '<jw-block-a><jw-block-b>ab[]</jw-block-b></jw-block-a>',
                    // });
                });
                it('should not break unbreakables', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable"><br></div>` +
                            `<div class="oe_unbreakable">[]abc</div></div></div></div>`,
                        stepFunction: deleteBackward,
                        contentAfter: `<div class="oe_unbreakable"><div class="oe_unbreakable">` +
                            `<div class="oe_unbreakable"><div class="oe_unbreakable"><br></div>` +
                            `<div class="oe_unbreakable">[]abc</div></div></div></div>`,
                    });
                });
                it('should merge a text preceding a paragraph (removing the paragraph)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>ab<p>[]cd</p></div>',
                        stepFunction: deleteBackward,
                        contentAfter: '<div>ab[]cd</div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>ab<p>[]cd</p>ef</div>',
                        stepFunction: deleteBackward,
                        contentAfter: '<div>ab[]cd<br>ef</div>',
                    });
                });
            });
            describe('With attributes', () => {
                it('should merge a paragraph without class into an empty paragraph with a class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p class="a"><br></p><p>[]abc</p>',
                        stepFunction: deleteBackward,
                        // JW cAfter: '<p>[]abc</p>',
                        contentAfter: '<p class="a">[]abc</p>',
                    });
                });
                it('should merge two paragraphs with spans of same classes', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">ab</span></p><p><span class="a">[]cd</span></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p><span class="a">ab[]cd</span></p>',
                    });
                });
                it('should merge two paragraphs with spans of different classes without merging the spans', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">ab</span></p><p><span class="b">[]cd</span></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p><span class="a">ab[]</span><span class="b">cd</span></p>',
                    });
                });
                it('should merge two paragraphs of different classes, each containing spans of the same class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p class="a"><span class="b">ab</span></p><p class="c"><span class="b">[]cd</span></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p class="a"><span class="b">ab[]cd</span></p>',
                    });
                });
                it('should merge two paragraphs of different classes, each containing spans of different classes without merging the spans', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p class="a"><span class="b">ab</span></p><p class="c"><span class="d">[]cd</span></p>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<p class="a"><span class="b">ab[]</span><span class="d">cd</span></p>',
                    });
                });
                it('should delete a line break between two spans with bold and merge these formats', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span><b>ab</b></span><br/><span><b>[]cd</b></span></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p><span><b>ab[]cd</b></span></p>',
                    });
                });
                it('should delete a character in a span with bold, then a line break between two spans with bold and merge these formats', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span><b>ab<br></b></span><br><span><b>c[]de</b></span></p>',
                        stepFunction: async editor => {
                            await deleteBackward(editor);
                            await deleteBackward(editor);
                        },
                        contentAfter: '<p><span><b>ab<br>[]de</b></span></p>',
                    });
                });
            });
            describe('POC extra tests', () => {
                it('should delete an unique space between letters', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab []cd</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]cd</p>',
                    });
                });
                it('should delete the first character in a paragraph (2)', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[] bc</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]&nbsp;bc</p>',
                    });
                });
                it('should delete a space', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab [] de</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]de</p>',
                    });
                });
                it('should delete a one letter word', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab c[] de</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab []&nbsp;de</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab [c] de</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab&nbsp;[] de</p>',
                    });
                });
                it('should delete an empty paragraph in a table cell', () =>
                    testEditor(BasicEditor, {
                        contentBefore:
                            '<table><tbody><tr><td><p>a<br></p><p>[]<br></p></td></tr></tbody></table>',
                        stepFunction: deleteBackward,
                        contentAfter: '<table><tbody><tr><td><p>a[]</p></td></tr></tbody></table>',
                    }));
                it('should fill empty block with a <br>', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[]</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]<br></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><img>[]</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]<br></p>',
                    });
                });
                it('should merge a paragraph with text into a paragraph with text removing spaces', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab   </p>    <p>   []cd</p>',
                        stepFunction: deleteBackward,
                        // This is a tricky case: the spaces after ab are
                        // visible on Firefox but not on Chrome... to be
                        // consistent we enforce the space removal here but
                        // maybe not a good idea... see next case ->
                        contentAfter: '<p>ab[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab   <br></p>    <p>   []cd</p>',
                        stepFunction: deleteBackward,
                        // This is the same visible case as the one above. The
                        // difference is that here the space after ab is visible
                        // on both Firefox and Chrome, so it should stay
                        // visible.
                        contentAfter: '<p>ab   []cd</p>',
                    });
                });
                it('should remove a br and remove following spaces', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<br><b>[]   </b>cd</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab<br><b>[]   x</b>cd</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>ab[]<b>x</b>cd</p>',
                    });
                });
                it('should ignore empty inline node between blocks being merged', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><p>abc</p><i> </i><p>[]def</p></div>',
                        stepFunction: deleteBackward,
                        contentAfter: '<div><p>abc[]def</p></div>',
                    });
                });
                it('should merge in nested paragraphs and remove invisible inline content', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<custom-block style="display: block;"><p>ab</p>    </custom-block><p>[]c</p>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<custom-block style="display: block;"><p>ab[]c</p></custom-block>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<custom-block style="display: block;"><p>ab</p> <i> </i> </custom-block><p>[]c</p>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<custom-block style="display: block;"><p>ab[]c</p></custom-block>',
                    });
                });
                it('should not merge in nested blocks if inline content afterwards', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<custom-block style="display: block;"><p>ab</p>de</custom-block><p>[]fg</p>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<custom-block style="display: block;"><p>ab</p>de[]fg</custom-block>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<custom-block style="display: block;"><p>ab</p><img></custom-block><p>[]fg</p>',
                        stepFunction: deleteBackward,
                        contentAfter:
                            '<custom-block style="display: block;"><p>ab</p><img>[]fg</custom-block>',
                    });
                });
                it('should move paragraph content to empty block', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc</p><h1><br></h1><p>[]def</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>abc</p><h1>[]def</h1>',
                    });
                });
                it('should remove only one br between contents', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc<br>[]<br>def</p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>abc[]<br>def</p>',
                    });
                });
                it('should remove an empty block instead of merging it', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br></p><p>[]<br></p>',
                        stepFunction: deleteBackward,
                        contentAfter: '<p>[]<br></p>',
                    });
                });
                it('should not remove a table without selecting it', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>[]kl</p>`,
                        ),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>[]kl</p>`,
                        ),
                    });
                });
                it('should not merge a table into its previous sibling', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>[]cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                        stepFunction: deleteBackward,
                        contentAfter: unformat(
                            `<p>ab</p>
                            <table><tbody>
                                <tr><td>[]cd</td><td>ef</td></tr>
                                <tr><td>gh</td><td>ij</td></tr>
                            </tbody></table>
                            <p>kl</p>`,
                        ),
                    });
                });
            });
        });
        describe('Selection not collapsed', () => {
            it('ZWS : should keep inline block', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div><p>ab <span class="style">[c]</span> d</p></div>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                    },
                    contentAfterEdit: '<div><p>ab <span class="style" data-oe-zws-empty-inline="">[]\u200B</span> d</p></div>',
                    contentAfter: '<div><p>ab <span class="style">[]\u200B</span> d</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div><p>ab <span class="style">[c]</span> d</p></div>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        await insertText(editor, 'x');
                    },
                    contentAfterEdit: '<div><p>ab <span class="style">x[]</span> d</p></div>',
                    contentAfter: '<div><p>ab <span class="style">x[]</span> d</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div><p>ab<span class="style">[c]</span>d</p></div>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        await insertText(editor, 'x');
                    },
                    contentAfterEdit: '<div><p>ab<span class="style">x[]</span>d</p></div>',
                    contentAfter: '<div><p>ab<span class="style">x[]</span>d</p></div>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<div><p>ab <span class="style">[cde]</span> f</p></div>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                        await insertText(editor, 'x');
                    },
                    contentAfterEdit: '<div><p>ab <span class="style">x[]</span> f</p></div>',
                    contentAfter: '<div><p>ab <span class="style">x[]</span> f</p></div>',
                });
            });
            it('should merge node correctly (1)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<span>b[c</span><p>d]e</p>f<br>g</div>',
                    stepFunction: deleteBackward,
                    // FIXME ?? : Maybe this should bing the content inside the <p>
                    // Instead of removing the <p>,
                    // ex : <div><p>a<span>b[]</span>e</p>f<br>g</div>
                    contentAfter: '<div>a<span>b[]</span>e<br>f<br>g</div>',
                });
            });
            it('should merge node correctly (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><span>d]e</span>f<p>xxx</p></div>',
                    stepFunction: deleteBackward,
                    contentAfter: '<div>a<p>b[]<span>e</span>f</p><p>xxx</p></div>',
                });
            });
            it('should delete part of the text within a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd]ef</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]ef</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd[ef</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]ef</p>',
                });
            });
            it('should delete across two paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd</p><p>ef]gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]gh</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd</p><p>ef[gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]gh</p>',
                });
            });
            it('should delete part of the text across two paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b[c</p><p>d]e</p>f</div>',
                    stepFunction: deleteBackward,
                    contentAfter: '<div>a<p>b[]e</p>f</div>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<div>a<p>b]c</p><p>d[e</p>f</div>',
                    stepFunction: deleteBackward,
                    contentAfter: '<div>a<p>b[]e</p>f</div>',
                });
            });
            it('should delete all the text in a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abc]</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]abc[</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>[]<br></p>',
                });
            });
            it('should delete a complex selection accross format nodes and multiple paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab[cd</b></p><p><b>ef<br/>gh</b>ij<i>kl]</i>mn</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p><b>ab[]</b>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab[cd</b></p><p><b>ef<br/>gh</b>ij<i>k]l</i>mn</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p><b>ab[]</b><i>l</i>mn</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab]cd</b></p><p><b>ef<br/>gh</b>ij<i>kl[</i>mn</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p><b>ab[]</b>mn</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>ab]cd</b></p><p><b>ef<br/>gh</b>ij<i>k[l</i>mn</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p><b>ab[]</b><i>l</i>mn</p>',
                });
            });
            it('should delete all contents of a complex DOM with format nodes and multiple paragraphs', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>[abcd</b></p><p><b>ef<br/>gh</b>ij<i>kl</i>mn]</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p><b>]abcd</b></p><p><b>ef<br/>gh</b>ij<i>kl</i>mn[</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>[]<br></p>',
                });
            });
            it('should delete a selection accross a heading1 and a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>ab [cd</h1><p>ef]gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>ab []gh</h1>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>ab ]cd</h1><p>ef[gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>ab []gh</h1>',
                });
            });
            it('should delete a selection from the beginning of a heading1 with a format to the middle of a paragraph', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><b>[abcd</b></h1><p>ef]gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[<b>abcd</b></h1><p>ef]gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<h1><b>]abcd</b></h1><p>ef[gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>[]gh</h1>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>]<b>abcd</b></h1><p>ef[gh</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<h1>[]gh</h1>',
                });
            });
            it('should delete a heading (triple click backspace)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<h1>[abc</h1><p>]def</p>',
                    stepFunction: deleteBackward,
                    // JW cAfter: '<p>[]def</p>',
                    contentAfter: '<h1>[]<br></h1><p>def</p>',
                });
            });
            it('should delete last character of paragraph, ignoring the selected paragraph break', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[c</p><p>]def</p>',
                    // This type of selection (typically done with a triple
                    // click) is "corrected" before remove so triple clicking
                    // doesn't remove a paragraph break.
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]</p><p>def</p>',
                });
            });
            it('should delete first character of paragraph, as well as selected paragraph break', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>abc[</p><p>d]ef</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>abc[]ef</p>',
                });
            });
            it('should delete last character of paragraph, ignoring the selected paragraph break leading to an unbreakable', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[c</p><p t="unbreak">]def</p>',
                    // This type of selection (typically done with a triple
                    // click) is "corrected" before remove so triple clicking
                    // doesn't remove a paragraph break.
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab[]</p><p t="unbreak">def</p>',
                });
            });
            it('should delete first character of unbreakable, ignoring selected paragraph break', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>abc[</p><p t="unbreak">d]ef</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>abc[]</p><p t="unbreak">ef</p>',
                });
            });
            it('should remove a fully selected table', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(
                        `<p>a[b</p>
                        <table><tbody>
                            <tr><td>cd</td><td>ef</td></tr>
                            <tr><td>gh</td><td>ij</td></tr>
                        </tbody></table>
                        <p>k]l</p>`,
                    ),
                    stepFunction: deleteBackward,
                    contentAfter: '<p>a[]l</p>',
                });
            });
            it('should only remove the text content and full rows a partly selected table', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(
                        `<p>a[b</p>
                        <table><tbody>
                            <tr><td>cd</td><td>ef</td></tr>
                            <tr><td>g]h</td><td>ij</td></tr>
                        </tbody></table>
                        <p>kl</p>`,
                    ),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(
                        `<p>a[]</p>
                        <table><tbody>
                            <tr><td>h</td><td>ij</td></tr>
                        </tbody></table>
                        <p>kl</p>`,
                    ),
                });
            });
            it('should empty an inline unremovable but remain in it', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<b class="oe_unremovable">[cd]</b>ef</p>',
                    stepFunction: deleteBackward,
                    contentAfter: '<p>ab<b class="oe_unremovable">[]\u200B</b>ef</p>',
                });
            });
        });
    });

    describe('deleterange', () => {
        it('should remove element which is contenteditable=true even if their parent is contenteditable=false', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <p>before[o</p>
                    <div contenteditable="false">
                        <div contenteditable="true"><p>intruder</p></div>
                    </div>
                    <p>o]after</p>`),
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <p>before[]after</p>`),
            });
        });
        it('should extend the range to fully include contenteditable=false that are partially selected at the end of the range', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <p>before[o</p>
                    <div contenteditable="false">
                        <div contenteditable="true"><p>intruder]</p></div>
                    </div>
                    <p>after</p>`),
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <p>before[]</p><p>after</p>`),
            });
        });
        it('should extend the range to fully include contenteditable=false that are partially selected at the start of the range', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <p>before</p>
                    <div contenteditable="false">
                        <div contenteditable="true"><p>[intruder</p></div>
                    </div>
                    <p>o]after</p>`),
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: unformat(`
                    <p>before[]after</p>`),
            });
        });
    });

    describe('CTRL+Backspace', () => {
        it('should not remove the last p with ctrl+backspace', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`<p>[]<br></p>`),
                stepFunction: async editor => {
                    editor.editable.addEventListener('keydown', ev => {
                        // simulation of the browser default behavior
                        if (ev.key === 'Backspace' && ev.ctrlKey === true && !ev.defaultPrevented) {
                            const sel = document.getSelection();
                            sel.anchorNode.remove();
                        }
                    });
                    triggerEvent(editor.editable, 'keydown', { key: 'Backspace', ctrlKey: true });
                },
                contentAfter: unformat(`<p>[]<br></p>`),
            });
        });
        it('should not remove the last p enclosed in a contenteditable=false with ctrl+backspace', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <p>text</p>
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>`),
                stepFunction: async editor => {
                    editor.editable.addEventListener('keydown', ev => {
                        // simulation of the browser default behavior
                        if (ev.key === 'Backspace' && ev.ctrlKey === true && !ev.defaultPrevented) {
                            const sel = document.getSelection();
                            sel.anchorNode.remove();
                        }
                    });
                    triggerEvent(editor.editable, 'keydown', { key: 'Backspace', ctrlKey: true });
                },
                contentAfter: unformat(`
                    <p>text</p>
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>`),
            });
        });
        it('should add a <p><br></p> element when deleting the last child of the editable with ctrl+backspace', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <blockquote>
                        []<br>
                    </blockquote>`),
                stepFunction: async editor => {
                    triggerEvent(editor.editable, 'keydown', { key: 'Backspace', ctrlKey: true });
                },
                contentAfter: unformat(`<p>[]<br></p>`),
            });
        });
        it('should add a <p><br></p> element when deleting the last child of an element with ctrl+backspace', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <blockquote>
                            []<br>
                        </blockquote>
                    </div></div>`),
                stepFunction: async editor => {
                    triggerEvent(editor.editable, 'keydown', { key: 'Backspace', ctrlKey: true });
                },
                contentAfter: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <p>[]<br></p>
                    </div></div>`),
            });
        });
        it('should correctly rollback a CTRL+BACKSPACE if the element should not have been removed', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <blockquote class="oe_unremovable">
                            []<br>
                        </blockquote>
                    </div></div>`),
                stepFunction: async editor => {
                    triggerEvent(editor.editable, 'keydown', { key: 'Backspace', ctrlKey: true });
                },
                contentAfter: unformat(`
                    <div contenteditable="false"><div contenteditable="true">
                        <blockquote class="oe_unremovable">
                            []<br>
                        </blockquote>
                    </div></div>`),
            });
        });
        it('should transform the last space of a container to an &nbsp; after removing the last word through deleteRange', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a [b]</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a&nbsp;[]</p>`,
            });
        });
    });

    describe('insertParagraphBreak', () => {
        describe('Selection collapsed', () => {
            describe('Basic', () => {
                it('should duplicate an empty paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<br></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><br></p><p>[]<br></p>',
                    });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: insertParagraphBreak,
                    //     contentAfter: '<p><br></p><p>[]<br></p>',
                    // });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br>[]</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><br></p><p>[]<br></p>',
                    });
                });
                it('should insert an empty paragraph before a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><br></p><p>[]abc</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[] abc</p>',
                        stepFunction: insertParagraphBreak,
                        // JW cAfter: '<p><br></p><p>[]abc</p>',
                        contentAfter: '<p><br></p><p>[] abc</p>',
                    });
                });
                it('should split a paragraph in two', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>ab</p><p>[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab []cd</p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p>ab&nbsp;</p><p>[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[] cd</p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p>ab</p><p>[]&nbsp;cd</p>',
                    });
                });
                it('should insert an empty paragraph after a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>abc</p><p>[]<br></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[] </p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>abc</p><p>[]<br></p>',
                    });
                });
            });
            describe('Pre', () => {
                it('should insert a line break within the pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>ab[]cd</pre>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<pre>ab<br>[]cd</pre>',
                    });
                });
                it('should insert a new paragraph after the pre', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<pre>abc[]</pre>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<pre>abc</pre><p>[]<br></p>',
                    });
                });
            });
            describe('Consecutive', () => {
                it('should duplicate an empty paragraph twice', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<br></p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p><br></p><p><br></p><p>[]<br></p>',
                    });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: async (editor) => {
                    //         await insertParagraphBreak(editor);
                    //         await insertParagraphBreak(editor);
                    //     },
                    //     contentAfter: '<p><br></p><p><br></p><p>[]<br></p>',
                    // });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><br>[]</p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p><br></p><p><br></p><p>[]<br></p>',
                    });
                });
                it('should insert two empty paragraphs before a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p><br></p><p><br></p><p>[]abc</p>',
                    });
                });
                it('should split a paragraph in three', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p>ab</p><p><br></p><p>[]cd</p>',
                    });
                });
                it('should split a paragraph in four', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p>ab</p><p><br></p><p><br></p><p>[]cd</p>',
                    });
                });
                it('should insert two empty paragraphs after a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: async editor => {
                            await insertParagraphBreak(editor);
                            await insertParagraphBreak(editor);
                        },
                        contentAfter: '<p>abc</p><p><br></p><p>[]<br></p>',
                    });
                });
            });
            describe('Format', () => {
                it('should split a paragraph before a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]<b>def</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>abc</p><p><b>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to []<b>
                        contentBefore: '<p>abc<b>[]def</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>abc</p><p><b>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc <b>[]def</b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible (because it's after a
                        // <br>).
                        contentAfter: '<p>abc&nbsp;</p><p><b>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc<b>[] def </b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible (because it's before a
                        // <br>).
                        // JW cAfter: '<p>abc</p><p><b>[]&nbsp;def</b></p>',
                        contentAfter: '<p>abc</p><p><b>[]&nbsp;def </b></p>',
                    });
                });
                it('should split a paragraph after a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc</b>[]def</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><b>abc</b></p><p>[]def</p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to </b>[]
                        contentBefore: '<p><b>abc[]</b>def</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><b>abc</b></p><p>[]def</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc[]</b> def</p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p><b>abc</b></p><p>[]&nbsp;def</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc []</b>def</p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible (because it's before a
                        // <br>).
                        contentAfter: '<p><b>abc&nbsp;</b></p><p>[]def</p>',
                    });
                });
                it('should split a paragraph at the beginning of a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<b>abc</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><br></p><p><b>[]abc</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to []<b>
                        contentBefore: '<p><b>[]abc</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><br></p><p><b>[]abc</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>[] abc</b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space should have been parsed away.
                        // JW cAfter: '<p><br></p><p><b>[]abc</b></p>',
                        contentAfter: '<p><br></p><p><b>[] abc</b></p>',
                    });
                });
                it('should split a paragraph within a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab[]cd</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><b>ab</b></p><p><b>[]cd</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab []cd</b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p><b>ab&nbsp;</b></p><p><b>[]cd</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab[] cd</b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p><b>ab</b></p><p><b>[]&nbsp;cd</b></p>',
                    });
                });
                it('should split a paragraph at the end of a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc</b>[]</p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><b>abc</b></p><p>[]<br></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to </b>[]
                        contentBefore: '<p><b>abc[]</b></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p><b>abc</b></p><p>[]<br></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc[] </b></p>',
                        stepFunction: insertParagraphBreak,
                        // The space should have been parsed away.
                        contentAfter: '<p><b>abc</b></p><p>[]<br></p>',
                    });
                });
                it('should insert line breaks outside the edges of an anchor', async () => {
                    const pressEnter = editor => {
                        editor.document.execCommand('insertParagraph');
                    };
                    await testEditor(BasicEditor, {
                        contentBefore: '<div>ab<a>[]cd</a></div>',
                        stepFunction: pressEnter,
                        contentAfter: '<div>ab<br><a>[]cd</a></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><a>a[]b</a></div>',
                        stepFunction: pressEnter,
                        contentAfter: '<div><a>a<br>[]b</a></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><a>ab[]</a></div>',
                        stepFunction: pressEnter,
                        contentAfter: '<div><a>ab</a><br>[]<br></div>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<div><a>ab[]</a>cd</div>',
                        stepFunction: pressEnter,
                        contentAfter: '<div><a>ab</a><br>[]cd</div>',
                    });
                });
            });
            describe('With attributes', () => {
                it('should insert an empty paragraph before a paragraph with a span with a class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">ab</span></p><p><span class="b">[]cd</span></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter:
                            '<p><span class="a">ab</span></p><p><br></p><p><span class="b">[]cd</span></p>',
                    });
                });
                it('should split a paragraph with a span with a bold in two', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span><b>ab[]cd</b></span></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter:
                            '<p><span><b>ab</b></span></p><p><span><b>[]cd</b></span></p>',
                    });
                });
                it('should split a paragraph at its end, with a paragraph after it, and both have the same class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p class="a">a[]</p><p class="a"><br></p>',
                        stepFunction: insertParagraphBreak,
                        contentAfter:
                            '<p class="a">a</p><p class="a">[]<br></p><p class="a"><br></p>',
                    });
                });
            });
            describe('POC extra tests', () => {
                it('should duplicate an empty h1', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<h1>[]<br></h1>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<h1><br></h1><p>[]<br></p>',
                    });
                });
            });
        });
        describe('Selection not collapsed', () => {
            it('should delete the first half of a paragraph, then split it', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[ab]cd</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p><br></p><p>[]cd</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]ab[cd</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p><br></p><p>[]cd</p>',
                });
            });
            it('should delete part of a paragraph, then split it', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p>a</p><p>[]d</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a]bc[d</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p>a</p><p>[]d</p>',
                });
            });
            it('should delete the last half of a paragraph, then split it', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd]</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p>ab</p><p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd[</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p>ab</p><p>[]<br></p>',
                });
            });
            it('should delete all contents of a paragraph, then split it', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abcd]</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p><br></p><p>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]abcd[</p>',
                    stepFunction: insertParagraphBreak,
                    contentAfter: '<p><br></p><p>[]<br></p>',
                });
            });
        });
    });

    describe('ZWS', () => {
        it('should insert a char into an empty span without removing the zws', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<span>[]\u200B</span>cd</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'x');
                },
                contentAfter: '<p>ab<span>x[]\u200B</span>cd</p>',
            });
        });
        it('should insert a char into an empty span surrounded by space without removing the zws', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab <span>[]\u200B</span> cd</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'x');
                },
                contentAfter: '<p>ab <span>x[]\u200B</span> cd</p>',
            });
        });
        it('should insert a char into a data-oe-zws-empty-inline span removing the zws and data-oe-zws-empty-inline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'x');
                },
                contentAfter: '<p>ab<span>x[]</span>cd</p>',
            });
        });
        it('should insert a char into a data-oe-zws-empty-inline span surrounded by space without removing the zws and data-oe-zws-empty-inline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab<span data-oe-zws-empty-inline="">[]\u200B</span>cd</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'x');
                },
                contentAfter: '<p>ab<span>x[]</span>cd</p>',
            });
        });
    });

    describe('insertLineBreak', () => {
        describe('Selection collapsed', () => {
            describe('Basic', () => {
                it('should insert a <br> into an empty paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<br></p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p><br>[]<br></p>',
                    });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: insertLineBreak,
                    //     contentAfter: '<p><br>[]<br></p>',
                    // });
                    // TODO to check: the cursor cannot be in that position...
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p><br>[]</p>',
                    //     stepFunction: insertLineBreak,
                    //     contentAfter: '<p><br>[]<br></p>',
                    // });
                });
                it('should insert a <br> at the beggining of a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p><br>[]abc</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[] abc</p>',
                        stepFunction: insertLineBreak,
                        // The space should have been parsed away.
                        contentAfter: '<p><br>[]abc</p>',
                    });
                });
                it('should insert a <br> within text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p>ab<br>[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab []cd</p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's before a <br>).
                        contentAfter: '<p>ab&nbsp;<br>[]cd</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[] cd</p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's after a <br>).
                        contentAfter: '<p>ab<br>[]&nbsp;cd</p>',
                    });
                });
                it('should insert a line break (2 <br>) at the end of a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: insertLineBreak,
                        // The second <br> is needed to make the first
                        // one visible.
                        contentAfter: '<p>abc<br>[]<br></p>',
                    });
                });
            });
            describe('Consecutive', () => {
                it('should insert two <br> at the beggining of an empty paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<br></p>',
                        stepFunction: async editor => {
                            await insertLineBreak(editor);
                            await insertLineBreak(editor);
                        },
                        contentAfter: '<p><br><br>[]<br></p>',
                    });
                    // TODO this cannot actually be tested currently as a
                    // backspace/delete in that case is not even detected
                    // (no input event to rollback)
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p>[<br>]</p>',
                    //     stepFunction: async (editor) => {
                    //         await insertLineBreak(editor);
                    //         await insertLineBreak(editor);
                    //     },
                    //     contentAfter: '<p><br><br>[]<br></p>',
                    // });
                    // TODO seems like a theoretical case, if needed it could
                    // be about checking at the start of the shift-enter if
                    // we are not between left-state BR and right-state block.
                    // await testEditor(BasicEditor, {
                    //     contentBefore: '<p><br>[]</p>',
                    //     stepFunction: async (editor) => {
                    //         await insertLineBreak(editor);
                    //         await insertLineBreak(editor);
                    //     },
                    //     contentAfter: '<p><br><br>[]<br></p>',
                    // });
                });
                it('should insert two <br> at the beggining of a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]abc</p>',
                        stepFunction: async editor => {
                            await insertLineBreak(editor);
                            await insertLineBreak(editor);
                        },
                        contentAfter: '<p><br><br>[]abc</p>',
                    });
                });
                it('should insert two <br> within text', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: async editor => {
                            await insertLineBreak(editor);
                            await insertLineBreak(editor);
                        },
                        contentAfter: '<p>ab<br><br>[]cd</p>',
                    });
                });
                it('should insert two line breaks (3 <br>) at the end of a paragraph', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]</p>',
                        stepFunction: async editor => {
                            await insertLineBreak(editor);
                            await insertLineBreak(editor);
                        },
                        // the last <br> is needed to make the first one
                        // visible.
                        contentAfter: '<p>abc<br><br>[]<br></p>',
                    });
                });
            });
            describe('Format', () => {
                it('should insert a <br> before a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc[]<b>def</b></p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p>abc<br><b>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to []<b>
                        contentBefore: '<p>abc<b>[]def</b></p>',
                        stepFunction: insertLineBreak,
                        // JW cAfter: '<p>abc<br><b>[]def</b></p>',
                        contentAfter: '<p>abc<b><br>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc <b>[]def</b></p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's before a <br>).
                        contentAfter: '<p>abc&nbsp;<b><br>[]def</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>abc<b>[] def </b></p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's before a <br>).
                        contentAfter: '<p>abc<b><br>[]&nbsp;def </b></p>',
                    });
                });
                it('should insert a <br> after a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc</b>[]def</p>',
                        stepFunction: insertLineBreak,
                        // JW cAfter: '<p><b>abc[]<br></b>def</p>',
                        contentAfter: '<p><b>abc</b><br>[]def</p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to </b>[]
                        contentBefore: '<p><b>abc[]</b>def</p>',
                        stepFunction: insertLineBreak,
                        // JW cAfter: '<p><b>abc[]<br></b>def</p>',
                        contentAfter: '<p><b>abc<br>[]</b>def</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc[]</b> def</p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so
                        // it is visible (because it's after a <br>).
                        // Visually, the caret does show _after_ the line
                        // break.
                        // JW cAfter: '<p><b>abc[]<br></b>&nbsp;def</p>',
                        contentAfter: '<p><b>abc<br>[]</b>&nbsp;def</p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc []</b>def</p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's before a <br>).
                        contentAfter: '<p><b>abc&nbsp;<br>[]</b>def</p>',
                    });
                });
                it('should insert a <br> at the beginning of a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>[]<b>abc</b></p>',
                        stepFunction: insertLineBreak,
                        // JW cAfter: '<p><b><br>[]abc</b></p>',
                        contentAfter: '<p><br><b>[]abc</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to []<b>
                        contentBefore: '<p><b>[]abc</b></p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p><b><br>[]abc</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>[] abc</b></p>',
                        stepFunction: insertLineBreak,
                        // The space should have been parsed away.
                        contentAfter: '<p><b><br>[]abc</b></p>',
                    });
                });
                it('should insert a <br> within a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab[]cd</b></p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p><b>ab<br>[]cd</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab []cd</b></p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking space so it
                        // is visible (because it's before a <br>).
                        contentAfter: '<p><b>ab&nbsp;<br>[]cd</b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>ab[] cd</b></p>',
                        stepFunction: insertLineBreak,
                        // The space is converted to a non-breaking
                        // space so it is visible.
                        contentAfter: '<p><b>ab<br>[]&nbsp;cd</b></p>',
                    });
                });
                it('should insert a line break (2 <br>) at the end of a format node', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc</b>[]</p>',
                        stepFunction: insertLineBreak,
                        // The second <br> is needed to make the first
                        // one visible.
                        // JW cAfter: '<p><b>abc<br>[]<br></b></p>',
                        contentAfter: '<p><b>abc</b><br>[]<br></p>',
                    });
                    await testEditor(BasicEditor, {
                        // That selection is equivalent to </b>[]
                        contentBefore: '<p><b>abc[]</b></p>',
                        stepFunction: insertLineBreak,
                        // The second <br> is needed to make the first
                        // one visible.
                        contentAfter: '<p><b>abc<br>[]<br></b></p>',
                    });
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><b>abc[] </b></p>',
                        stepFunction: insertLineBreak,
                        // The space should have been parsed away.
                        // The second <br> is needed to make the first
                        // one visible.
                        contentAfter: '<p><b>abc<br>[]<br></b></p>',
                    });
                });
            });
            describe('With attributes', () => {
                it('should insert a line break before a span with class', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<p><span class="a">dom to</span></p><p><span class="b">[]edit</span></p>',
                        stepFunction: insertLineBreak,
                        contentAfter:
                            '<p><span class="a">dom to</span></p><p><span class="b"><br>[]edit</span></p>',
                    });
                });
                it('should insert a line break within a span with a bold', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p><span><b>ab[]cd</b></span></p>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<p><span><b>ab<br>[]cd</b></span></p>',
                    });
                });
            });
        });
        describe('Selection not collapsed', () => {
            it('should delete the first half of a paragraph, then insert a <br>', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[ab]cd</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p><br>[]cd</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]ab[cd</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p><br>[]cd</p>',
                });
            });
            it('should delete part of a paragraph, then insert a <br>', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p>a<br>[]d</p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a]bc[d</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p>a<br>[]d</p>',
                });
            });
            it('should delete the last half of a paragraph, then insert a line break (2 <br>)', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[cd]</p>',
                    stepFunction: insertLineBreak,
                    // the second <br> is needed to make the first one
                    // visible.
                    contentAfter: '<p>ab<br>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]cd[</p>',
                    stepFunction: insertLineBreak,
                    // the second <br> is needed to make the first one
                    // visible.
                    contentAfter: '<p>ab<br>[]<br></p>',
                });
            });
            it('should delete all contents of a paragraph, then insert a line break', async () => {
                // Forward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[abcd]</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p><br>[]<br></p>',
                });
                // Backward selection
                await testEditor(BasicEditor, {
                    contentBefore: '<p>]abcd[</p>',
                    stepFunction: insertLineBreak,
                    contentAfter: '<p><br>[]<br></p>',
                });
            });
        });
    });

    describe('getTraversedNodes', () => {
        it('should return the anchor node of a collapsed selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div><p>a[]bc</p><div>def</div></div>',
                stepFunction: editor => {
                    window.chai
                        .expect(
                            getTraversedNodes(editor.editable).map(node =>
                                node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName,
                            ),
                        )
                        .to.eql(['abc']);
                },
            });
        });
        it('should return the nodes traversed in a cross-blocks selection', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div><p>a[bc</p><div>d]ef</div></div>',
                stepFunction: editor => {
                    window.chai
                        .expect(
                            getTraversedNodes(editor.editable).map(node =>
                                node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName,
                            ),
                        )
                        .to.eql(['abc', 'DIV', 'def']);
                },
            });
        });
        it('should return the nodes traversed in a cross-blocks selection with hybrid nesting', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div><section><p>a[bc</p></section><div>d]ef</div></section>',
                stepFunction: editor => {
                    window.chai
                        .expect(
                            getTraversedNodes(editor.editable).map(node =>
                                node.nodeType === Node.TEXT_NODE ? node.textContent : node.nodeName,
                            ),
                        )
                        .to.eql(['abc', 'DIV', 'def']);
                },
            });
        });
    });

    describe('automatic link creation when typing a space after an url', () => {
        it('should transform url after space', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a http://test.com b http://test.com[] c http://test.com d</p>',
                stepFunction: async (editor) => {
                    editor.testMode = false;
                    const selection = document.getSelection();
                    const anchorOffset = selection.anchorOffset;
                    const p = editor.editable.querySelector('p');
                    const textNode = p.childNodes[0];
                    triggerEvent(editor.editable, 'keydown', {key: ' ', code: 'Space'});
                    textNode.textContent = "a http://test.com b http://test.com\u00a0 c http://test.com d";
                    selection.extend(textNode, anchorOffset + 1);
                    selection.collapseToEnd();
                    triggerEvent(editor.editable, 'input', {data: ' ', inputType: 'insertText' });
                    triggerEvent(editor.editable, 'keyup', {key: ' ', code: 'Space'});
                },
                contentAfter: '<p>a http://test.com b <a href="http://test.com">http://test.com</a>&nbsp;[] c http://test.com d</p>',
            });
        });
        it('should not transform url after two space', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a http://test.com b http://test.com [] c http://test.com d</p>',
                stepFunction: async (editor) => {
                    editor.testMode = false;
                    const selection = document.getSelection();
                    const anchorOffset = selection.anchorOffset;
                    const p = editor.editable.querySelector('p');
                    const textNode = p.childNodes[0];
                    triggerEvent(editor.editable, 'keydown', {key: ' ', code: 'Space'});
                    textNode.textContent = "a http://test.com b http://test.com \u00a0 c http://test.com d";
                    selection.extend(textNode, anchorOffset + 1);
                    selection.collapseToEnd();
                    triggerEvent(editor.editable, 'input', {data: ' ', inputType: 'insertText' });
                    triggerEvent(editor.editable, 'keyup', {key: ' ', code: 'Space'});
                },
                contentAfter: '<p>a http://test.com b http://test.com &nbsp;[] c http://test.com d</p>',
            });
        });
    });

    describe('history', () => {
        describe('undo', () => {
            it('should undo a backspace', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                    },
                    contentAfter: '<p>ab []cd</p>',
                });
            });
            it('should undo a backspace, then do nothing on undo', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        undo(editor); // <p>ab []cd</p> (nothing to undo)
                    },
                    contentAfter: '<p>ab []cd</p>',
                });
            });
        });
        describe('redo', () => {
            it('should undo, then redo a backspace', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        redo(editor); // <p>ab[]cd</p>
                    },
                    contentAfter: '<p>ab[]cd</p>',
                });
            });
            it('should undo, then redo a backspace, then undo again to get back to the starting point', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        redo(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                    },
                    contentAfter: '<p>ab []cd</p>',
                });
            });
            it('should undo, then redo a backspace, then do nothing on redo', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        redo(editor); // <p>ab[]cd</p>
                        redo(editor); // <p>ab[]cd</p> (nothing to redo)
                    },
                    contentAfter: '<p>ab[]cd</p>',
                });
            });
            it('should undo, then undo, then redo, then redo two backspaces, then do nothing on redo, then undo', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        await deleteBackward(editor); // <p>a[]cd</p>
                        undo(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        redo(editor); // <p>ab[]cd</p>
                        redo(editor); // <p>a[]cd</p>
                        redo(editor); // <p>a[]cd</p> (nothing to redo)
                    },
                    contentAfter: '<p>a[]cd</p>',
                });
            });
            it('should 2x undo, then 2x redo, then 2x undo, then 2x redo a backspace', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab []cd</p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor); // <p>ab[]cd</p>
                        undo(editor); // <p>ab []cd</p>
                        undo(editor); // <p>ab []cd</p> (nothing to undo)
                        redo(editor); // <p>ab[]cd</p>
                        redo(editor); // <p>ab[]cd</p> (nothing to redo)
                        undo(editor); // <p>ab []cd</p>
                        undo(editor); // <p>ab []cd</p> (nothing to undo)
                        redo(editor); // <p>ab[]cd</p>
                        redo(editor); // <p>ab[]cd</p> (nothing to redo)
                    },
                    contentAfter: '<p>ab[]cd</p>',
                });
            });
            it('should type a, b, c, undo x2, d, undo x2, redo x2', async () => {
                await testEditor(OdooEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'a');
                        await insertText(editor, 'b');
                        await insertText(editor, 'c');
                        undo(editor);
                        undo(editor);
                        await insertText(editor, 'd');
                        undo(editor);
                        undo(editor);
                        redo(editor);
                        redo(editor);
                    },
                    contentAfter: '<p>ad[]</p>',
                });
            });
            it('should type a, b, c, undo x2, d, undo, redo x2', async () => {
                await testEditor(OdooEditor, {
                    contentBefore: '<p>[]</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'a');
                        await insertText(editor, 'b');
                        await insertText(editor, 'c');
                        undo(editor);
                        undo(editor);
                        await insertText(editor, 'd');
                        undo(editor);
                        redo(editor);
                        redo(editor);
                    },
                    contentAfter: '<p>ad[]</p>',
                });
            });
        });
        describe('revertCurrentStep', () => {
            it('should not lose initially nested style', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<span style="color: tomato;">c</span>d]e</p>',
                    stepFunction: async editor => {
                        // simulate preview
                        editor.historyPauseSteps();
                        editor.execCommand('bold');
                        editor.historyUnpauseSteps();
                        // simulate preview's reset
                        editor.historyRevertCurrentStep(); // back to initial state
                    },
                    contentAfter: '<p>a[b<span style="color: tomato;">c</span>d]e</p>',
                });
            });
        });
        describe('step', () => {
            it('should allow insertion of nested contenteditable="true"', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: `<div contenteditable="false"></div>`,
                    stepFunction: async editor => {
                        const editable = '<div contenteditable="true">abc</div>';
                        editor.editable.querySelector('div').innerHTML = editable;
                        editor.historyStep();
                    },
                    contentAfter: `<div contenteditable="false"><div contenteditable="true">abc</div></div>`,
                });
            });
        });
    });

    describe('columnize', () => {
        const columnsContainer = contents => `<div class="container o_text_columns"><div class="row">${contents}</div></div>`;
        const column = (size, contents) => `<div class="col-lg-${size}">${contents}</div>`;
        describe('2 columns', () => {
            it('should do nothing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>[]ef</h1><ul><li>gh</li></ul>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 2),
                    contentAfter: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>[]ef</h1><ul><li>gh</li></ul>')
                    ),
                });
            });
            it('should turn text into 2 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[]abcd</p>',
                    stepFunction: editor => editor.execCommand('columnize', 2),
                    contentAfter: columnsContainer(
                        column(6, '<p>[]abcd</p>') +
                        column(6, '<p><br></p>')
                    ) + '<p><br></p>',
                });
            });
            it('should turn 3 columns into 2 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<h1>e[]f</h1>') +
                        column(4, '<ul><li>gh</li></ul>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 2),
                    contentAfter: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>e[]f</h1><ul><li>gh</li></ul>')
                    ),
                });
            });
            it('should turn 4 columns into 2 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<h1>ef</h1>') +
                        column(3, '<ul><li>gh</li></ul>') +
                        column(3, '<p>i[]j</p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 2),
                    contentAfter: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>ef</h1><ul><li>gh</li></ul><p>i[]j</p>')
                    ),
                });
            });
        });
        describe('3 columns', () => {
            it('should do nothing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<p><br></p>') +
                        column(4, '<p>[]<br></p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 3),
                    contentAfter: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<p><br></p>') +
                        column(4, '<p>[]<br></p>')
                    ),
                });
            });
            it('should turn text into 3 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: editor => editor.execCommand('columnize', 3),
                    contentAfter: columnsContainer(
                        column(4, '<p>ab[]cd</p>') +
                        column(4, '<p><br></p>') +
                        column(4, '<p><br></p>')
                    ) + '<p><br></p>',
                });
            });
            it('should turn 2 columns into 3 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>ef</h1><ul><li>g[]h</li></ul>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 3),
                    contentAfter: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<h1>ef</h1><ul><li>g[]h</li></ul>') +
                        column(4, '<p><br></p>')
                    ),
                });
            });
            it('should turn 4 columns into 3 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<h1>e[]f</h1>') +
                        column(3, '<ul><li>gh</li></ul>') +
                        column(3, '<p>ij</p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 3),
                    contentAfter: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<h1>e[]f</h1>') +
                        column(4, '<ul><li>gh</li></ul><p>ij</p>')
                    ),
                });
            });
        });
        describe('4 columns', () => {
            it('should do nothing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p>[]<br></p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 4),
                    contentAfter: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p>[]<br></p>')
                    ),
                });
            });
            it('should turn text into 4 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>abcd[]</p>',
                    stepFunction: editor => editor.execCommand('columnize', 4),
                    contentAfter: columnsContainer(
                        column(3, '<p>abcd[]</p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p><br></p>')
                    ) + '<p><br></p>',
                });
            });
            it('should turn 2 columns into 4 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>[]ef</h1><ul><li>gh</li></ul>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 4),
                    contentAfter: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<h1>[]ef</h1><ul><li>gh</li></ul>') +
                        column(3, '<p><br></p>') +
                        column(3, '<p><br></p>')
                    ),
                });
            });
            it('should turn 3 columns into 4 columns', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<h1>ef[]</h1>') +
                        column(4, '<ul><li>gh</li></ul><p>ij</p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 4),
                    contentAfter: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<h1>ef[]</h1>') +
                        column(3, '<ul><li>gh</li></ul><p>ij</p>') +
                        column(3, '<p><br></p>')
                    ),
                });
            });
        });
        describe('remove columns', () => {
            it('should do nothing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: editor => editor.execCommand('columnize', 0),
                    contentAfter: '<p>ab[]cd</p>',
                });
            });
            it('should turn 2 columns into text', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(6, '<p>abcd</p>') +
                        column(6, '<h1>[]ef</h1><ul><li>gh</li></ul>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 0),
                    contentAfter: '<p>abcd</p><h1>[]ef</h1><ul><li>gh</li></ul>',
                });
            });
            it('should turn 3 columns into text', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(4, '<p>abcd</p>') +
                        column(4, '<h1>ef[]</h1>') +
                        column(4, '<ul><li>gh</li></ul><p>ij</p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 0),
                    contentAfter: '<p>abcd</p><h1>ef[]</h1><ul><li>gh</li></ul><p>ij</p>',
                });
            });
            it('should turn 4 columns into text', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: columnsContainer(
                        column(3, '<p>abcd</p>') +
                        column(3, '<h1>ef</h1>') +
                        column(3, '<ul><li>gh</li></ul><p>ij</p>') +
                        column(3, '<p>[]<br></p>')
                    ),
                    stepFunction: editor => editor.execCommand('columnize', 0),
                    contentAfter: '<p>abcd</p><h1>ef</h1><ul><li>gh</li></ul><p>ij</p><p>[]<br></p>',
                });
            });
        });
        describe('complex', () => {
            it('should turn text into 2 columns, then 3, 4, 3, 2 and text again', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]cd</p>',
                    stepFunction: editor => {
                        editor.execCommand('columnize', 2);
                        editor.execCommand('columnize', 3);
                        editor.execCommand('columnize', 4);
                        editor.execCommand('columnize', 3);
                        editor.execCommand('columnize', 2);
                        editor.execCommand('columnize', 0);
                    },
                    // A paragraph was created for each column + after them and
                    // they were all kept.
                    contentAfter: '<p>ab[]cd</p><p><br></p><p><br></p><p><br></p><p><br></p>',
                });
            });
            it('should not add a container when one already exists', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<div class="container"><div class="row"><div class="col">' +
                                       '<p>ab[]cd</p>' +
                                   '</div></div></div>',
                    stepFunction: editor => editor.execCommand('columnize', 2),
                    contentAfter: '<div class="container"><div class="row"><div class="col">' +
                                      '<div class="o_text_columns"><div class="row">' + // no "container" class
                                          '<div class="col-lg-6">' +
                                              '<p>ab[]cd</p>' +
                                          '</div>' +
                                          '<div class="col-lg-6"><p><br></p></div>' +
                                      '</div></div>' +
                                      '<p><br></p>' +
                                  '</div></div></div>',
                })
            });
        });
    });

    describe('tables', () => {
        describe('add children', () => {
            describe('row', () => {
                describe('above', async () => {
                    it('should add a row above the top row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef[]</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addRow', 'before'),
                            contentAfter: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;"><br></td>' +
                                            '<td style="width: 25px;"><br></td>' +
                                            '<td style="width: 30px;"><br></td>' +
                                        '</tr>' +
                                        '<tr style="height: 20px;">' +
                                            '<td style="">ab</td>' +
                                            '<td style="">cd</td>' +
                                            '<td style="">ef[]</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                    it('should add a row above the middle row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef[]</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addRow', 'before'),
                            contentAfter: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef[]</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                });
                describe('below', () => {
                    it('should add a row below the bottom row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef[]</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addRow', 'after'),
                            contentAfter: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef[]</td>' +
                                        '</tr>' +
                                        '<tr style="height: 20px;">' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                    it('should add a row below the middle row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef[]</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addRow', 'after'),
                            contentAfter: '<table><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 20px;">ab</td>' +
                                            '<td style="width: 25px;">cd</td>' +
                                            '<td style="width: 30px;">ef[]</td>' +
                                        '</tr>' +
                                        '<tr style="height: 20px;">' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                            '<td><br></td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                });
            });
            describe('column', () => {
                describe('left', () => {
                    it('should add a column left of the leftmost column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 40px;">ab[]</td>' +
                                            '<td style="width: 50px;">cd</td>' +
                                            '<td style="width: 60px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addColumn', 'before'),
                            contentAfter: '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 32px;"><br></td>' +
                                            '<td style="width: 32px;">ab[]</td>' +
                                            '<td style="width: 40px;">cd</td>' +
                                            '<td style="width: 45px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td><br></td>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                    it('should add a column left of the middle column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 50px;">ab</td>' +
                                            '<td style="width: 65px;">cd</td>' +
                                            '<td style="width: 85px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd[]</td>' +
                                            '<td>ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 40px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addColumn', 'before'),
                            contentAfter: '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 38px;">ab</td>' +
                                            '<td style="width: 50px;"><br></td>' +
                                            '<td style="width: 50px;">cd</td>' +
                                            '<td style="width: 61px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td><br></td>' +
                                            '<td>cd[]</td>' +
                                            '<td>ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 40px;">' +
                                            '<td>ab</td>' +
                                            '<td><br></td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                });
                describe('right', () => {
                    it('should add a column right of the rightmost column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 40px;">ab</td>' +
                                            '<td style="width: 50px;">cd</td>' +
                                            '<td style="width: 60px;">ef[]</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addColumn', 'after'),
                            contentAfter: '<table style="width: 150px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 29px;">ab</td>' +
                                            '<td style="width: 36px;">cd</td>' +
                                            '<td style="width: 41px;">ef[]</td>' +
                                            // size was slightly adjusted to
                                            // preserve table width in view on
                                            // fractional division results
                                            '<td style="width: 43px;"><br></td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                            '<td><br></td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                    it('should add a column right of the middle column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 50px;">ab</td>' +
                                            '<td style="width: 65px;">cd</td>' +
                                            '<td style="width: 85px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd[]</td>' +
                                            '<td>ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 40px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('addColumn', 'after'),
                            contentAfter: '<table style="width: 200px;"><tbody><tr style="height: 20px;">' +
                                            '<td style="width: 38px;">ab</td>' +
                                            '<td style="width: 50px;">cd</td>' +
                                            '<td style="width: 50px;"><br></td>' +
                                            '<td style="width: 61px;">ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 30px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd[]</td>' +
                                            '<td><br></td>' +
                                            '<td>ef</td>' +
                                        '</tr>' +
                                        '<tr style="height: 40px;">' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td><br></td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                        });
                    });
                });
            });
        });
        describe('tab', () => {
            it('should add a new row on press tab at the end of a table', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<table><tbody><tr style="height: 20px;"><td style="width: 20px;">ab</td><td>cd</td><td>ef[]</td></tr></tbody></table>',
                    stepFunction: async editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                    contentAfter: '<table><tbody><tr style="height: 20px;"><td style="width: 20px;">ab</td><td>cd</td><td>ef</td></tr><tr style="height: 20px;"><td>[]<br></td><td><br></td><td><br></td></tr></tbody></table>',
                });
            });
        });
        describe('rectangular selections', () => {
            describe('select a full table on cross over', () => {
                describe('select', () => {
                    it('should select some characters and a table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>',
                            contentAfterEdit: '<p>a[bc</p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td">a]b</td>' +
                                                '<td class="o_selected_td">cd</td>' +
                                                '<td class="o_selected_td">ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should select a table and some characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr><td>ab</td><td>cd</td><td>e[f</td></tr></tbody></table><p>a]bc</p>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">ab</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">e[f</td></tr></tbody></table><p>a]bc</p>',
                        });
                    });
                    it('should select some characters, a table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>a]bc</p>',
                            contentAfterEdit: '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">ab</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">ef</td></tr></tbody></table><p>a]bc</p>',
                        });
                    });
                    it('should select some characters, a table, some more characters and another table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>abc</p><table><tbody><tr><td>a]b</td><td>cd</td><td>ef</td></tr></tbody></table>',
                            contentAfterEdit: '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">ab</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">ef</td></tr></tbody></table>' +
                                            '<p>abc</p><table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">a]b</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">ef</td></tr></tbody></table>',
                        });
                    });
                    it('should select some characters, a table, some more characters, another table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>abc</p><table><tbody><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table><p>a]bc</p>',
                            contentAfterEdit: '<p>a[bc</p><table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">ab</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">ef</td></tr></tbody></table>' +
                                            '<p>abc</p><table class="o_selected_table"><tbody><tr>' +
                                            '<td class="o_selected_td">ab</td>' +
                                            '<td class="o_selected_td">cd</td>' +
                                            '<td class="o_selected_td">ef</td></tr></tbody></table><p>a]bc</p>',
                        });
                    });
                });
                describe('toggleFormat', () => {
                    it('should apply bold to some characters and a table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr>' +
                                                '<td>a]b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<p>a<strong>[bc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef]</strong></td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply bold to a table and some characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>e[f</td>' +
                                            '</tr></tbody></table><p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef</strong></td>' +
                                            '</tr></tbody></table>' +
                                            '<p><strong>a]</strong>bc</p>',
                        });
                    });
                    it('should apply bold to some characters, a table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<p>a<strong>[bc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef</strong></td>' +
                                            '</tr></tbody></table>' +
                                            '<p><strong>a]</strong>bc</p>',
                        });
                    });
                    it('should apply bold to some characters, a table, some more characters and another table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>abc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>a]b</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<p>a<strong>[bc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef</strong></td>' +
                                            '</tr></tbody></table>' +
                                            '<p><strong>abc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef]</strong></td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply bold to some characters, a table, some more characters, another table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>abc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<p>a<strong>[bc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef</strong></td>' +
                                            '</tr></tbody></table>' +
                                            '<p><strong>abc</strong></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef</strong></td>' +
                                            '</tr></tbody></table>' +
                                            '<p><strong>a]</strong>bc</p>',
                        });
                    });
                });
                describe('color', () => {
                    it('should apply a color to some characters and a table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p><table><tbody><tr>' +
                                                '<td>a]b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<p>a<font style="color: aquamarine;">[bc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">a]b</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply a color to a table and some characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>e[f</td>' +
                                            '</tr></tbody></table><p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">e[f</td>' +
                                            '</tr></tbody></table>' +
                                            '<p><font style="color: aquamarine;">a]</font>bc</p>',
                        });
                    });
                    it('should apply a color to some characters, a table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<p>a<font style="color: aquamarine;">[bc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>' +
                                            '<p><font style="color: aquamarine;">a]</font>bc</p>',
                        });
                    });
                    it('should apply a color to some characters, a table, some more characters and another table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>abc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>a]b</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<p>a<font style="color: aquamarine;">[bc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>' +
                                            '<p><font style="color: aquamarine;">abc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">a]b</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply a color to some characters, a table, some more characters, another table and some more characters', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[bc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>abc</p>' +
                                        '<table><tbody><tr>' +
                                            '<td>ab</td>' +
                                            '<td>cd</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>' +
                                        '<p>a]bc</p>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<p>a<font style="color: aquamarine;">[bc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>' +
                                            '<p><font style="color: aquamarine;">abc</font></p>' +
                                            '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                            '</tr></tbody></table>' +
                                            '<p><font style="color: aquamarine;">a]</font>bc</p>',
                        });
                    });
                });
            });
            describe('select columns on cross over', () => {
                describe('select', () => {
                    it('should select two columns', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr><td>a[b</td><td>c]d</td><td>ef</td></tr></tbody></table>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td">a[b</td>' +
                                                '<td class="o_selected_td">c]d</td>' +
                                                '<td>ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should select a whole row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr><td>a[b</td><td>cd</td><td>e]f</td></tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td">a[b</td>' +
                                                '<td class="o_selected_td">cd</td>' +
                                                '<td class="o_selected_td">e]f</td>' +
                                            '</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                        });
                    });
                    it('should select a whole column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                        '<tr><td>a[b</td><td>cd</td><td>ef</td></tr>' +
                                        '<tr><td>ab</td><td>cd</td><td>ef</td></tr>' +
                                        '<tr><td>a]b</td><td>cd</td><td>ef</td></tr>' +
                                    '</tbody></table>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">a[b</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">ab</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">a]b</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should select from (0,0) to (1,1) in a 3x3 table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                        '<tr><td>a[b</td><td>cd</td><td>ef</td></tr>' +
                                        '<tr><td>ab</td><td>c]d</td><td>ef</td></tr>' +
                                        '<tr><td>ab</td><td>cd</td><td>ef</td></tr>' +
                                    '</tbody></table>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">a[b</td>' +
                                                    '<td class="o_selected_td">cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">ab</td>' +
                                                    '<td class="o_selected_td">c]d</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td>ab</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should select a whole table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                        '<tr><td>a[b</td><td>cd</td><td>ef</td></tr>' +
                                        '<tr><td>ab</td><td>cd</td><td>ef</td></tr>' +
                                        '<tr><td>ab</td><td>cd</td><td>e]f</td></tr>' +
                                    '</tbody></table>',
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">a[b</td>' +
                                                    '<td class="o_selected_td">cd</td>' +
                                                    '<td class="o_selected_td">ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">ab</td>' +
                                                    '<td class="o_selected_td">cd</td>' +
                                                    '<td class="o_selected_td">ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td">ab</td>' +
                                                    '<td class="o_selected_td">cd</td>' +
                                                    '<td class="o_selected_td">e]f</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                });
                describe('toggleFormat', () => {
                    it('should apply bold to two columns', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                            '<td>a[b</td>' +
                                            '<td>c]d</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd]</strong></td>' +
                                                '<td>ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply bold to a whole row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                            '<td>a[b</td>' +
                                            '<td>cd</td>' +
                                            '<td>e]f</td>' +
                                        '</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                '<td class="o_selected_td"><strong>ef]</strong></td>' +
                                            '</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                        });
                    });
                    it('should apply bold to a whole column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>a]b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>ab]</strong></td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should apply bold from (0,0) to (1,1) in a 3x3 table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>c]d</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                    '<td class="o_selected_td"><strong>cd]</strong></td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td>ab</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should apply bold to a whole table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>e]f</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('bold'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>[ab</strong></td>' +
                                                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                    '<td class="o_selected_td"><strong>ef</strong></td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td"><strong>ab</strong></td>' +
                                                    '<td class="o_selected_td"><strong>cd</strong></td>' +
                                                    '<td class="o_selected_td"><strong>ef]</strong></td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                });
                describe('color', () => {
                    it('should apply a color to two columns', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                            '<td>a[b</td>' +
                                            '<td>c]d</td>' +
                                            '<td>ef</td>' +
                                        '</tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">a[b</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">c]d</td>' +
                                                '<td>ef</td>' +
                                            '</tr></tbody></table>',
                        });
                    });
                    it('should apply a color to a whole row', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody><tr>' +
                                            '<td>a[b</td>' +
                                            '<td>cd</td>' +
                                            '<td>e]f</td>' +
                                        '</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody><tr>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">a[b</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                '<td class="o_selected_td" style="color: aquamarine;">e]f</td>' +
                                            '</tr><tr><td>ab</td><td>cd</td><td>ef</td></tr></tbody></table>',
                        });
                    });
                    it('should apply a color to a whole column', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>a]b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">a[b</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">a]b</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should apply a color from (0,0) to (1,1) in a 3x3 table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>c]d</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">a[b</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">c]d</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td>ab</td>' +
                                                    '<td>cd</td>' +
                                                    '<td>ef</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                    it('should apply a color to a whole table', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<table><tbody>' +
                                            '<tr>' +
                                                '<td>a[b</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>ef</td>' +
                                            '</tr>' +
                                            '<tr>' +
                                                '<td>ab</td>' +
                                                '<td>cd</td>' +
                                                '<td>e]f</td>' +
                                            '</tr>' +
                                        '</tbody></table>',
                            stepFunction: async editor => editor.execCommand('applyColor', 'aquamarine', 'color'),
                            contentAfterEdit: '<table class="o_selected_table"><tbody>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">a[b</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ef</td>' +
                                                '</tr>' +
                                                '<tr>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">ab</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">cd</td>' +
                                                    '<td class="o_selected_td" style="color: aquamarine;">e]f</td>' +
                                                '</tr>' +
                                            '</tbody></table>',
                        });
                    });
                });
            });
        });
    });

    // Note that arrow keys test have a contentAfter that is not reflective of
    // reality. The browser doesn't apply the selection change after triggering
    // an event programmatically so what we are testing here is that if a custom
    // behavior has to happen _before_ the browser's behavior, we do indeed have
    // it.
    describe('arrow keys', () => {
        describe('ArrowRight', () => {
            it('should move past a zws (collapsed)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]<span>\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight'});
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>c[]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>[]\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight'});
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>c[]d</p>'
                });
            });
            it('should select a zws', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[ab]<span>\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>[ab<span>\u200B]</span>cd</p>',
                    // Final state: '<p>[ab<span>\u200B</span>c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>[ab<span>]\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>[ab<span>\u200B]</span>cd</p>',
                    // Final state: '<p>[ab<span>\u200B</span>c]d</p>'
                });
            });
            it('should select a zws (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b]<span>\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>a[b<span>\u200B]</span>cd</p>',
                    // Final state: '<p>a[b<span>\u200B</span>c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<span>]\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>a[b<span>\u200B]</span>cd</p>',
                    // Final state: '<p>a[b<span>\u200B</span>c]d</p>'
                });
            });
            it('should select a zws (3)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[]<span>\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab[<span>\u200B]</span>cd</p>',
                    // Final state: '<p>ab[<span>\u200B</span>c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>[]\u200B</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>[\u200B]</span>cd</p>',
                    // Final state: '<p>ab<span>[\u200B</span>c]d</p>'
                });
            });
            it('should select a zws backwards', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>]\u200B[</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>[c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>]\u200B</span>[cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>[c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]<span>\u200B</span>[cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>[c]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]<span>\u200B[</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B[]</span>cd</p>',
                    // Final state: '<p>ab<span>\u200B</span>[c]d</p>'
                });
            });
            it('should select a zws backwards (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>]\u200B</span>c[d</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B]</span>c[d</p>',
                    // Final state: '<p>ab<span>\u200B</span>c[]d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab]<span>\u200B</span>c[d</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowRight', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>\u200B]</span>c[d</p>',
                    // Final state: '<p>ab<span>\u200B</span>c[]d</p>'
                });
            });
        });
        describe('ArrowLeft', () => {
            it('should move past a zws (collapsed)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B[]</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft'});
                    },
                    contentAfter: '<p>ab<span>[]\u200B</span>cd</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B</span>[]cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft'});
                    },
                    contentAfter: '<p>ab<span>[]\u200B</span>cd</p>',
                });
            });
            it('should select a zws backwards', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B[]</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B[</span>cd</p>',
                    // Final state: '<p>a]b<span>\u200B[</span>cd</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B</span>[]cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B[</span>cd</p>',
                    // Final state: '<p>a]b<span>\u200B[</span>cd</p>'
                });
            });
            it('should select a zws backwards (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B</span>]cd[</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B</span>cd[</p>',
                    // Final state: '<p>a]b<span>\u200B</span>cd[</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B]</span>cd[</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B</span>cd[</p>',
                    // Final state: '<p>a]b<span>\u200B</span>cd[</p>'
                });
            });
            it('should select a zws backwards (3)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B</span>]c[d</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B</span>c[d</p>',
                    // Final state: '<p>a]b<span>\u200B</span>c[d</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>\u200B]</span>c[d</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>]\u200B</span>c[d</p>',
                    // Final state: '<p>a]b<span>\u200B</span>c[d</p>'
                });
            });
            it('should deselect a zws', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>[\u200B]</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>[]\u200B</span>cd</p>',
                    // Final state: '<p>a]b<span>[\u200B</span>cd</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab<span>[\u200B</span>]cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab<span>[]\u200B</span>cd</p>',
                    // Final state: '<p>a]b<span>[\u200B</span>cd</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[<span>\u200B]</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab[<span>]\u200B</span>cd</p>',
                    // Final state: '<p>a]b[<span>\u200B</span>cd</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab[<span>\u200B</span>]cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>ab[<span>]\u200B</span>cd</p>',
                    // Final state: '<p>a]b[<span>\u200B</span>cd</p>'
                });
            });
            it('should deselect a zws (2)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<span>\u200B]</span>cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>a[b<span>]\u200B</span>cd</p>',
                    // Final state: '<p>a[]b<span>\u200B</span>cd</p>'
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<span>\u200B</span>]cd</p>',
                    stepFunction: async editor => {
                        triggerEvent(editor.editable, 'keydown', { key: 'ArrowLeft', shiftKey: true });
                    },
                    contentAfter: '<p>a[b<span>]\u200B</span>cd</p>',
                    // Final state: '<p>a[]b<span>\u200B</span>cd</p>'
                });
            });
        });
    });

    describe('markdown', () => {
        describe('inline code', () => {
            it('should convert text into inline code (start)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>`ab[]cd</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>\u200B<code class="o_inline_code">ab</code>\u200B[]cd</p>',
                });
            });
            it('should convert text into inline code (middle)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab`cd[]ef</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]ef</p>',
                });
            });
            it('should convert text into inline code (end)', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab`cd[]</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>ab<code class="o_inline_code">cd</code>\u200B[]</p>',
                });
            });
            it('should convert text into inline code and leave an earlier and a later backtick alone', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a`b`cd[]e`f</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>a`b<code class="o_inline_code">cd</code>\u200B[]e`f</p>',
                });
            });
            it('should not convert text into inline code when traversing HTMLElements', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab`c<strong>d</strong>e[]fg</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>ab`c<strong>d</strong>e`[]fg</p>',
                });
            });
            it('should not convert text into inline code when interrupted by linebreak', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>ab`c<br>d[]ef</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>ab`c<br>d`[]ef</p>',
                });
            });
            it('should not convert text into inline code when inside inline code', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<code class="o_inline_code">b`cd[]e</code>f</p>',
                    stepFunction: async editor => insertText(editor, '`'),
                    contentAfter: '<p>a<code class="o_inline_code">b`cd`[]e</code>f</p>',
                });
            });
        });
    });
});
