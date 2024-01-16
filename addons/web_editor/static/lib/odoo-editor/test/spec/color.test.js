import { BasicEditor, testEditor } from '../utils.js';

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
            contentAfter: '<p>[</p><p></p><p>]</p>',
        });
    });
    it('should apply a background color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'background-color'),
            contentAfterEdit: '<p>[<font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p>]<font oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>',
            contentAfter: '<p>[</p><p></p><p>]</p>',
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
