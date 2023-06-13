import { BasicEditor, testEditor } from '../utils.js';

const setColor = (color, mode) => {
    return async editor => {
        await editor.execCommand('applyColor', color, mode);
    };
};

describe('applyColor', () => {
    it('should apply a color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font>b<span>c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'color'),
            contentAfter: '<p>a<font>b<span>c</span></font>' +
                '<font style="color: rgb(255, 0, 0);"><span>[def]</span></font>' +
                '<font><span>g</span>h</font>i</p>',
        });
    });
    it('should apply a background color to a slice of text in a span in a font', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<font>b<span>c[def]g</span>h</font>i</p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'backgroundColor'),
            contentAfter: '<p>a<font>b<span>c</span></font>' +
                '<font style="background-color: rgb(255, 0, 0);"><span>[def]</span></font>' +
                '<font><span>g</span>h</font>i</p>',
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
            contentAfterEdit: '<p><font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">[\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="color: rgb(255, 0, 0);">]\u200B</font></p>',
            contentAfter: '<p>[</p><p></p><p>]</p>',
        });
    });
    it('should apply a background color on empty selection', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>[<br></p><p><br></p><p>]<br></p>',
            stepFunction: setColor('rgb(255, 0, 0)', 'background-color'),
            contentAfterEdit: '<p><font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">[\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">\u200B</font></p>' +
                              '<p><font data-oe-zws-empty-inline="" style="background-color: rgb(255, 0, 0);">]\u200B</font></p>',
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
});
