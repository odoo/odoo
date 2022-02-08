import { BasicEditor, testEditor } from '../utils.js';

const setFontSize = size => {
    return async editor => {
        await editor.execCommand('setFontSize', size);
    };
};

describe('FontSize', () => {
    describe('setFontSize', () => {
        it('should change the font size of a few characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: setFontSize('10px'),
                contentAfter: '<p>ab<span style="font-size: 10px;">[cde]</span>fg</p>',
            });
        });
        it('should change the font size of a whole heading after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: setFontSize('36px'),
                contentAfter: '<h1><span style="font-size: 36px;">[ab]</span></h1><p>cd</p>',
            });
        });
    });
});
