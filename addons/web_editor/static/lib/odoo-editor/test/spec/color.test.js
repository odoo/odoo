import { BasicEditor, testEditor, insertText } from '../utils.js';

const setColor = (color, mode) => {
    return async editor => {
        await editor.execCommand('applyColor', color, mode);
    };
};

describe('applyColor', () => {
    it('should apply a color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p>a<font class="a">b<span class="b">c</span></font>' +
                '<font class="a" style="color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
                '<font class="a"><span class="b">g</span>h</font>i</p>',
        });
    });
    it('should apply a background color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font class="a">b<span class="b">c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p>a<font class="a">b<span class="b">c</span></font>' +
                '<font class="a" style="background-color: rgb(255, 0, 0);"><span class="b">[def]</span></font>' +
                '<font class="a"><span class="b">g</span>h</font>i</p>',
        });
    });
    it('should get ready to type with a different color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>ab[]cd</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p>ab<font style="color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
        });
    });
    it('should get ready to type with a different background color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>ab[]cd</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p>ab<font style="background-color: rgb(255, 0, 0);">[]\u200B</font>cd</p>',
        });
    });
    it('should apply a color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfterEdit: '<p>[<font oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p>]<font oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>',
            contentAfter: '<p>[<br></p><p><br></p><p>]<br></p>',
        });
    });
    it('should apply a background color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'background-color'),
            contentAfterEdit: '<p>[<font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p>]<font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>',
            contentAfter: '<p>[<br></p><p><br></p><p>]<br></p>',
        });
    });
    it('should not merge line on background color change', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><strong>[abcd</strong><br><strong>efghi]</strong></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p><strong><font style="background-color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
                          '<strong><font style="background-color: rgb(255, 0, 0);">efghi]</font></strong></p>',
        });
    });
    it('should not merge line on color change', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><strong>[abcd</strong><br><strong>efghi]</strong></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p><strong><font style="color: rgb(255, 0, 0);">[abcd</font></strong><br>' +
                          '<strong><font style="color: rgb(255, 0, 0);">efghi]</font></strong></p>',
        });
    });
    it('should remove font tag after removing font color', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(255, 0, 0);">[abcabc]</font></p>',
            stepFunction: setColor('', 'color'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="text-400">[abcabc]</font></p>',
            stepFunction: setColor('', 'color'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('should remove font tag after removing background color applied as style', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-color: rgb(255, 0, 0);">[abcabc]</font></p>',
            stepFunction: setColor('', 'backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font class="bg-200">[abcabc]</font></p>',
            stepFunction: setColor('', 'backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
    it('should remove font tag if font-color and background-color both are removed one by one', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(255, 0, 0);" class="bg-200">[abcabc]</font></p>',
            stepFunction: setColor('','backgroundColor'),
            stepFunction: setColor('','color'),
            contentAfter: '<p>[abcabc]</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="background-color: rgb(255, 0, 0);" class="text-900">[abcabc]</font></p>',
            stepFunction: setColor('','color'),
            stepFunction: setColor('','backgroundColor'),
            contentAfter: '<p>[abcabc]</p>',
        });
    });
});

describe('keep styles', () => {
    it('should keep styles on enter', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[]</font></p>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
                await insertText(editor, 'x');
                await editor.execCommand('oEnter');
            },
            contentAfterEdit: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></p>' +
                                '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">x</font></p>' +
                                '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);" oe-zws-empty-inline="">[]\u200b</font></p>',

            contentAfter: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></p>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">x</font></p>' +
                            '<p>[]<br></p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[]</font></h1>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
                await insertText(editor, 'x');
                await editor.execCommand('oEnter');
            },
            contentAfterEdit: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></h1>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">x</font></p>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);" oe-zws-empty-inline="">[]\u200b</font></p>',

            contentAfter: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></h1>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">x</font></p>' +
                            '<p>[]<br></p>',
        });
    });
    it('should split a paragraph and also keep styles on enter', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[]</font>cd</p>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
            },
            contentAfterEdit: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></p>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);" oe-zws-empty-inline="">[]\u200b</font>cd</p>',
            contentAfter: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></p>' +
                            '<p>[]cd</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[]</font>cd</h1>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
            },
            contentAfterEdit: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></h1>' +
                                '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);" oe-zws-empty-inline="">[]\u200b</font>cd</h1>',
            contentAfter: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></h1>' +
                            '<h1>[]cd</h1>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[] </font>cd</p>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
            },
            contentAfter: '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></p>' +
                            '<p><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">[]&nbsp;</font>cd</p>',
        });
        await testEditor(BasicEditor, {
            contentBefore: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc[] </font>cd</h1>',
            stepFunction: async editor => {
                await editor.execCommand('oEnter');
            },
            contentAfter: '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">abc</font></h1>' +
                            '<h1><font style="color: rgb(0, 255, 0) background-color: rgb(255, 0, 0);">[]&nbsp;</font>cd</h1>'
        });
    });
});
