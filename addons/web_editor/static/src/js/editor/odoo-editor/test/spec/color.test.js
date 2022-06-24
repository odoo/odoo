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
});
