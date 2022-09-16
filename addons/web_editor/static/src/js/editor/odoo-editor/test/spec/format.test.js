import { BasicEditor, testEditor, setTestSelection, Direction } from '../utils.js';
import { applyInlineStyle } from '../../src/commands/commands.js';

const bold = async editor => {
    await editor.execCommand('bold');
};
const italic = async editor => {
    await editor.execCommand('italic');
};
const underline = async editor => {
    await editor.execCommand('underline');
};
const strikeThrough = async editor => {
    await editor.execCommand('strikeThrough');
};

describe('Format', () => {
    const b = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="font-weight: bolder;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    const notB = (content, weight, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="font-weight: ${weight || 'normal'};"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    describe('bold', () => {
        it('should make a few characters bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: bold,
                contentAfter: `<p>ab${b(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${b(`ab[cde]fg`)}</p>`,
                stepFunction: bold,
                contentAfter: `<p>${b(`ab${notB(`[cde]`)}fg`)}</p>`,
            });
        });
        it('should make two paragraphs bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: bold,
                contentAfter: `<p>${b(`[abc`)}</p><p>${b(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${b(`[abc`)}</p><p>${b(`def]`)}</p>`,
                stepFunction: bold,
                contentAfter: `<p>${notB(`[abc`)}</p><p>${notB(`def]`, 400)}</p>`,
            });
        });
        it('should make a whole heading bold after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${notB(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: bold,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: `<h1>${b(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not bold after a triple click (heading is considered bold)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: bold,
                contentAfter: `<h1>${notB(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with bold text fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${b(`[ab`)}</p><p>c]d</p>`,
                stepFunction: bold,
                contentAfter: `<p>${b(`[ab`)}</p><p>${b(`c]`)}d</p>`,
            });
        });
        it('should make a selection with bold text in the middle fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${b(`b`)}</p><p>${b(`c`)}d]e</p>`,
                stepFunction: bold,
                contentAfter: `<p>${b(`[ab`)}</p><p>${b(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with bold text fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${notB(`[ab`)}</h1><p>${b(`c]d`)}</p>`,
                stepFunction: bold,
                contentAfter: `<h1>${b(`[ab`)}</h1><p>${b(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: bold,
                contentAfterEdit: `<p>ab${b(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${b(`ab[]cd`)}</p>`,
                stepFunction: bold,
                contentAfterEdit: `<p>${b(`ab${notB(`[]\u200B`, undefined, 'first')}cd`)}</p>`,
                contentAfter: `<p>${b(`ab[]cd`)}</p>`,
            });
        });
    });
    const i = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="font-style: italic;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    const notI = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="font-style: normal;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    describe('italic', () => {
        it('should make a few characters italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[cde]fg</p>`,
                stepFunction: italic,
                contentAfter: `<p>ab${i(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${i(`ab[cde]fg`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${i(`ab${notI(`[cde]`)}fg`)}</p>`,
            });
        });
        it('should make two paragraphs italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: italic,
                contentAfter: `<p>${i(`[abc`)}</p><p>${i(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${i(`[abc`)}</p><p>${i(`def]`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${notI(`[abc`)}</p><p>${notI(`def]`)}</p>`,
            });
        });
        it('should make a whole heading italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>[ab</h1><p>]cd</p>`,
                stepFunction: italic,
                contentAfter: `<h1>${i(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${i(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: italic,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: `<h1>${notI(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with italic text fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${i(`[ab`)}</p><p>c]d</p>`,
                stepFunction: italic,
                contentAfter: `<p>${i(`[ab`)}</p><p>${i(`c]`)}d</p>`,
            });
        });
        it('should make a selection with italic text in the middle fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${i(`b`)}</p><p>${i(`c`)}d]e</p>`,
                stepFunction: italic,
                contentAfter: `<p>${i(`[ab`)}</p><p>${i(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with italic text fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[ab</p><p>${i(`c]d`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${i(`[ab`)}</p><p>${i(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: italic,
                contentAfterEdit: `<p>ab${i(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${i(`ab[]cd`)}</p>`,
                stepFunction: italic,
                contentAfterEdit: `<p>${i(`ab${notI(`[]\u200B`, 'first')}cd`)}</p>`,
                contentAfter: `<p>${i(`ab[]cd`)}</p>`,
            });
        });
    });
    const u = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="text-decoration-line: underline;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    describe('underline', () => {
        it('should make a few characters underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[cde]fg</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${u(`ab[cde]fg`)}</p>`,
                stepFunction: underline,
                contentAfter: `<p>${u(`ab[`)}cde]${u(`fg`)}</p>`,
            });
        });
        it('should make two paragraphs underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: underline,
                contentAfter: `<p>${u(`[abc`)}</p><p>${u(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${u(`[abc`)}</p><p>${u(`def]`)}</p>`,
                stepFunction: underline,
                contentAfter: '<p>[abc</p><p>def]</p>',
            });
        });
        it('should make a whole heading underline after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>[ab</h1><p>]cd</p>`,
                stepFunction: underline,
                contentAfter: `<h1>${u(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not underline after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${u(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: underline,
                contentAfter: `<h1>[ab]</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with underline text fully underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${u(`[ab`)}</p><p>c]d</p>`,
                stepFunction: underline,
                contentAfter: `<p>${u(`[ab`)}</p><p>${u(`c]`)}d</p>`,
            });
        });
        it('should make a selection with underline text in the middle fully underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${u(`b`)}</p><p>${u(`c`)}d]e</p>`,
                stepFunction: underline,
                contentAfter: `<p>${u(`[ab`)}</p><p>${u(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with underline text fully underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[ab</h1><p>${u(`c]d`)}</p>`,
                stepFunction: underline,
                contentAfter: `<p>${u(`[ab`)}</p><p>${u(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${u(`ab[]cd`)}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>${u(`ab`)}<span data-oe-zws-empty-inline="">\u200B[]</span>${u(`cd`)}</p>`,
                contentAfter: `<p>${u(`ab`)}[]${u(`cd`)}</p>`,
            });
        });
    });
    const s = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="text-decoration-line: line-through;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
    describe('strikeThrough', () => {
        it('should make a few characters strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[cde]fg</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>ab${s(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${s(`ab[cde]fg`)}</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`ab[`)}cde]${s(`fg`)}</p>`,
            });
        });
        it('should make a few characters strikeThrough then remove style inside', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[c d]ef</p>`,
                stepFunction: async editor => {
                    await strikeThrough(editor);
                    const styleSpan = editor.editable.querySelector('span[style="text-decoration-line: line-through;"]').childNodes[0];
                    const selection = {
                        anchorNode: styleSpan,
                        anchorOffset: 1,
                        focusNode: styleSpan,
                        focusOffset: 2,
                        direction: Direction.FORWARD,
                    };
                    await setTestSelection(selection);
                    await strikeThrough(editor);
                },
                contentAfter: `<p>ab${s(`c[`)} ]${s(`d`)}ef</p>`,
            });
        });
        it('should make strikeThrough then more then remove', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>abc[ ]def</p>`,
                stepFunction: async editor => {
                    await strikeThrough(editor);
                    const pElem = editor.editable.querySelector('p').childNodes;
                    const selection = {
                        anchorNode: pElem[0],
                        anchorOffset: 2,
                        focusNode: pElem[2],
                        focusOffset: 1,
                        direction: Direction.FORWARD,
                    };
                    await setTestSelection(selection);
                    await strikeThrough(editor);
                },
                contentAfter: `<p>ab${s(`[c d]`)}ef</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>abc[ ]def</p>`,
                stepFunction: async editor => {
                    await strikeThrough(editor);
                    const pElem = editor.editable.querySelector('p').childNodes;
                    const selection = {
                        anchorNode: pElem[0],
                        anchorOffset: 2,
                        focusNode: pElem[2],
                        focusOffset: 1,
                        direction: Direction.FORWARD,
                    };
                    await setTestSelection(selection);
                    await strikeThrough(editor);
                    await strikeThrough(editor);
                },
                contentAfter: `<p>ab[c d]ef</p>`,
            });
        });
        it('should make two paragraphs strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`[abc`)}</p><p>${s(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${s(`[abc`)}</p><p>${s(`def]`)}</p>`,
                stepFunction: strikeThrough,
                contentAfter: '<p>[abc</p><p>def]</p>',
            });
        });
        it('should make a whole heading strikeThrough after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>[ab</h1><p>]cd</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<h1>${s(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not strikeThrough after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${s(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<h1>[ab]</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with strikeThrough text fully strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${s(`[ab`)}</p><p>c]d</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`[ab`)}</p><p>${s(`c]`)}d</p>`,
            });
        });
        it('should make a selection with strikeThrough text in the middle fully strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${s(`b`)}</p><p>${s(`c`)}d]e</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`[ab`)}</p><p>${s(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with strikeThrough text fully strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[ab</h1><p>${s(`c]d`)}</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`[ab`)}</p><p>${s(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: strikeThrough,
                contentAfterEdit: `<p>ab${s(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${s(`ab[]cd`)}</p>`,
                stepFunction: strikeThrough,
                contentAfterEdit: `<p>${s(`ab`)}<span data-oe-zws-empty-inline="">\u200B[]</span>${s(`cd`)}</p>`,
                contentAfter: `<p>${s(`ab`)}[]${s(`cd`)}</p>`,
            });
        });
    });
    describe('underline + strikeThrough', () => {
        it('should get ready to write in strikeThrough without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`\u200b[]`, 'last')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd`))}[]${u(s(`ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(`\u200b[]`, 'first')}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`, 'first'), 'first')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd`))}[]${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`, 'first'))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`\u200b[]`, 'last')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd`))}[]${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`ghi[]`))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(u(`ghi`) + `<span data-oe-zws-empty-inline="">\u200b[]</span>`)}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd`))}${s(u(`ghi`) + `[]`)}${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, strikeThrough)', async () => {
            const uselessSpan = content => `<span>${content}</span>`; // TODO: clean
            const uselessU = u(''); // TODO: clean
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd[]ef`))}</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'A');
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'B');
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'C');
                },
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`A${u(`B`)}${uselessSpan(`C[]`)}${uselessU}`)}${u(s(`ef`))}</p>`,
            });
        });
    });
    describe('underline + italic', () => {
        const iAndU = (content, zws) => `<span${zws === 'first' ? ' data-oe-zws-empty-inline=""' : ''} style="font-style: italic; text-decoration-line: underline;"${zws === 'last' ? ' data-oe-zws-empty-inline=""' : ''}>${content}</span>`;
        it('should get ready to write in italic and underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${iAndU(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic, after changing one\'s mind about underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${i(`\u200B[]`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${i(`\u200B[]`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                },
                contentAfterEdit: `<p>ab${i(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(i(`cd`))}${i(`\u200b[]`, 'last')}${u(i(`ef`))}</p>`,
                contentAfter: `<p>ab${u(i(`cd`))}[]${u(i(`ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(`\u200b[]`)}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(i(`cd`))}${iAndU(`[]\u200b`, 'last')}${u(i(`ef`))}</p>`,
                contentAfter: `<p>ab${u(i(`cd`))}[]${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(u(`[]\u200b`))}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(i(`cd`))}${i(`\u200b[]`, 'last')}${u(i(`ef`))}</p>`,
                contentAfter: `<p>ab${u(i(`cd`))}[]${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(u(`ghi[]`))}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(i(`cd`))}${i(u(`ghi`) + `<span data-oe-zws-empty-inline="">\u200b[]</span>`)}${u(i(`ef`))}</p>`,
                contentAfter: `<p>ab${u(i(`cd`))}${i(u(`ghi`) + `[]`)}${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, italic)', async () => {
            const uselessSpan = content => `<span>${content}</span>`;
            const uselessU = u(''); // TODO: clean
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd[]ef`))}</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'A');
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'B');
                    await editor.execCommand('underline');
                    await editor.execCommand('insert', 'C');
                },
                contentAfter: `<p>ab${u(i(`cd`))}${i(`A${u(`B`)}${uselessSpan(`C[]`)}${uselessU}`)}${u(i(`ef`))}</p>`,
            });
        });
    });
});

describe('applyInlineStyle', () => {
    it('should apply style to selection only', async () => {
        await testEditor(BasicEditor, {
            contentBefore: '<p>a<span>[b<span>c]d</span>e</span>f</p>',
            stepFunction: editor => applyInlineStyle(editor, (el) => el.style.color = 'tomato'),
            contentAfter: '<p>a<span><span style="color: tomato;">[b</span><span><span style="color: tomato;">c]</span>d</span>e</span>f</p>',
        });
    });
});

describe('setTagName', () => {
    describe('to paragraph', () => {
        it('should turn a heading 1 into a paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>ab[]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'p'),
                contentAfter: '<p>ab[]cd</p>',
            });
        });
        it('should turn a heading 1 into a paragraph (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b]c</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'p'),
                contentAfter: '<p>a[b]c</p>',
            });
        });
        it('should turn a heading 1, a paragraph and a heading 2 into three paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b</h1><p>cd</p><h2>e]f</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'p'),
                contentAfter: '<p>a[b</p><p>cd</p><p>e]f</p>',
            });
        });
        it.skip('should turn a heading 1 into a paragraph after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><h2>]cd</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'p'),
                contentAfter: '<p>[ab</p><h2>]cd</h2>',
            });
        });
        it('should not turn a div into a paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div>[ab]</div>',
                stepFunction: editor => editor.execCommand('setTag', 'p'),
                contentAfter: '<div><p>[ab]</p></div>',
            });
        });
    });
    describe('to heading 1', () => {
        it('should turn a paragraph into a heading 1', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<h1>ab[]cd</h1>',
            });
        });
        it('should turn a paragraph into a heading 1 (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[b]c</p>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<h1>a[b]c</h1>',
            });
        });
        it('should turn a paragraph, a heading 1 and a heading 2 into three headings 1', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a[b</p><h1>cd</h1><h2>e]f</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<h1>a[b</h1><h1>cd</h1><h1>e]f</h1>',
            });
        });
        it.skip('should turn a paragraph into a heading 1 after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[ab</p><h2>]cd</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<h1>[ab</h1><h2>]cd</h2>',
            });
        });
        it('should not turn a div into a heading 1', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div>[ab]</div>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<div><h1>[ab]</h1></div>',
            });
        });
        it('should remove the background image while turning a p>font into a heading 1>span', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div><p><font class="text-gradient" style="background-image: linear-gradient(135deg, rgb(255, 204, 51) 0%, rgb(226, 51, 255) 100%);">[ab]</font></p></div>',
                stepFunction: editor => editor.execCommand('setTag', 'h1'),
                contentAfter: '<div><h1><span style="">[ab]</span></h1></div>',
            });
        });
    });
    describe('to heading 2', () => {
        it('should turn a heading 1 into a heading 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>ab[]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h2'),
                contentAfter: '<h2>ab[]cd</h2>',
            });
        });
        it('should turn a heading 1 into a heading 2 (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b]c</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h2'),
                contentAfter: '<h2>a[b]c</h2>',
            });
        });
        it('should turn a heading 1, a heading 2 and a paragraph into three headings 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b</h1><h2>cd</h2><p>e]f</p>',
                stepFunction: editor => editor.execCommand('setTag', 'h2'),
                contentAfter: '<h2>a[b</h2><h2>cd</h2><h2>e]f</h2>',
            });
        });
        it.skip('should turn a paragraph into a heading 2 after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[ab</p><h1>]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h2'),
                contentAfter: '<h2>[ab</h2><h1>]cd</h1>',
            });
        });
        it('should not turn a div into a heading 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div>[ab]</div>',
                stepFunction: editor => editor.execCommand('setTag', 'h2'),
                contentAfter: '<div><h2>[ab]</h2></div>',
            });
        });
    });
    describe('to heading 3', () => {
        it('should turn a heading 1 into a heading 3', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>ab[]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h3'),
                contentAfter: '<h3>ab[]cd</h3>',
            });
        });
        it('should turn a heading 1 into a heading 3 (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b]c</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h3'),
                contentAfter: '<h3>a[b]c</h3>',
            });
        });
        it('should turn a heading 1, a paragraph and a heading 2 into three headings 3', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b</h1><p>cd</p><h2>e]f</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'h3'),
                contentAfter: '<h3>a[b</h3><h3>cd</h3><h3>e]f</h3>',
            });
        });
        it.skip('should turn a paragraph into a heading 3 after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[ab</p><h1>]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'h3'),
                contentAfter: '<h3>[ab</h3><h1>]cd</h1>',
            });
        });
        it('should not turn a div into a heading 3', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div>[ab]</div>',
                stepFunction: editor => editor.execCommand('setTag', 'h3'),
                contentAfter: '<div><h3>[ab]</h3></div>',
            });
        });
    });
    describe('to pre', () => {
        it('should turn a heading 1 into a pre', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>ab[]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'pre'),
                contentAfter: '<pre>ab[]cd</pre>',
            });
        });
        it('should turn a heading 1 into a pre (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b]c</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'pre'),
                contentAfter: '<pre>a[b]c</pre>',
            });
        });
        it('should turn a heading 1 a pre and a paragraph into three pres', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b</h1><pre>cd</pre><p>e]f</p>',
                stepFunction: editor => editor.execCommand('setTag', 'pre'),
                contentAfter: '<pre>a[b</pre><pre>cd</pre><pre>e]f</pre>',
            });
        });
    });
    describe('to blockquote', () => {
        it('should turn a blockquote into a paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>ab[]cd</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'blockquote'),
                contentAfter: '<blockquote>ab[]cd</blockquote>',
            });
        });
        it('should turn a heading 1 into a blockquote (character selected)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b]c</h1>',
                stepFunction: editor => editor.execCommand('setTag', 'blockquote'),
                contentAfter: '<blockquote>a[b]c</blockquote>',
            });
        });
        it('should turn a heading 1, a paragraph and a heading 2 into three blockquote', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>a[b</h1><p>cd</p><h2>e]f</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'blockquote'),
                contentAfter:
                    '<blockquote>a[b</blockquote><blockquote>cd</blockquote><blockquote>e]f</blockquote>',
            });
        });
        it.skip('should turn a heading 1 into a blockquote after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><h2>]cd</h2>',
                stepFunction: editor => editor.execCommand('setTag', 'blockquote'),
                contentAfter: '<blockquote>[ab</blockquote><h2>]cd</h2>',
            });
        });
        it('should not turn a div into a blockquote', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<div>[ab]</div>',
                stepFunction: editor => editor.execCommand('setTag', 'blockquote'),
                contentAfter: '<div><blockquote>[ab]</blockquote></div>',
            });
        });
    });
});
