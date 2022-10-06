import { isSelectionFormat } from '../../src/utils/utils.js';
import { BasicEditor, testEditor, setTestSelection, Direction, nextTick, unformat } from '../utils.js';

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
const setFontSize = size => editor => editor.execCommand('setFontSize', size);

const switchDirection = editor => editor.execCommand('switchDirection');

describe('Format', () => {
    const getZwsTag = (tagName, {style} = {}) => {
        const styleAttr = style ? ` style="${style}"` : '';
        return (content, zws) => {
            const zwsFirstAttr = zws === 'first' ? ' oe-zws-empty-inline=""' : '';
            const zwsLastAttr = zws === 'last' ? ' oe-zws-empty-inline=""' : '';
            return `<${tagName}${zwsFirstAttr}${styleAttr}${zwsLastAttr}>${content}</${tagName}>`
        };
    }

    const span = getZwsTag('span');

    const strong = getZwsTag('strong');
    const notStrong = getZwsTag('span', {style: 'font-weight: normal;'});
    const spanBold = getZwsTag('span', {style: 'font-weight: bolder;'});
    const b = getZwsTag('b');
    const repeatWithBoldTags = async (cb) => {
        for (const fn of [spanBold, b, strong]) {
            await cb(fn);
        }
    }

    const em = getZwsTag('em');

    const u = getZwsTag('u');

    const s = getZwsTag('s');


    describe('bold', () => {
        it('should make a few characters bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: bold,
                contentAfter: `<p>ab${strong(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`ab[cde]fg`)}</p>`,
                stepFunction: bold,
                contentAfter: `<p>${strong(`ab`)}[cde]${strong(`fg`)}</p>`,
            });
        });
        it('should make two paragraphs bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: bold,
                contentAfter: `<p>${strong(`[abc`)}</p><p>${strong(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`[abc`)}</p><p>${strong(`def]`)}</p>`,
                stepFunction: bold,
                contentAfter: `<p>[abc</p><p>def]</p>`,
            });
        });
        it('should make a whole heading bold after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${notStrong(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: bold,
                contentAfter: `<h1>[ab]</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not bold after a triple click (heading is considered bold)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: bold,
                contentAfter: `<h1>${notStrong(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with bold text fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`[ab`)}</p><p>c]d</p>`,
                stepFunction: bold,
                contentAfter: `<p>${strong(`[ab`)}</p><p>${strong(`c]`)}d</p>`,
            });
        });
        it('should make a selection with bold text in the middle fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${strong(`b`)}</p><p>${strong(`c`)}d]e</p>`,
                stepFunction: bold,
                contentAfter: `<p>${strong(`[ab`)}</p><p>${strong(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with bold text fully bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${notStrong(`[ab`)}</h1><p>${strong(`c]d`)}</p>`,
                stepFunction: bold,
                contentAfter: `<h1>[ab</h1><p>${strong(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: bold,
                contentAfterEdit: `<p>ab${strong(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`ab[]cd`)}</p>`,
                stepFunction: bold,
                contentAfterEdit: `<p>${strong(`ab`)}${span(`[]\u200B`, 'first')}${strong(`cd`)}</p>`,
                contentAfter: `<p>${strong(`ab[]cd`)}</p>`,
            });
        });


        it('should remove a bold tag that was redondant while performing the command', async () => {
            await repeatWithBoldTags(async (tag) => {
                await testEditor(BasicEditor, {
                    contentBefore: `<p>a${tag(`b${tag(`[c]`)}d`)}e</p>`,
                    stepFunction: bold,
                    contentAfter: `<p>a${tag('b')}[c]${tag('d')}e</p>`,
                });
            });
        });
        it('should remove a bold tag that was redondant with different tags while performing the command', async () => {
            await testEditor(BasicEditor, {
                contentBefore: unformat(`<p>
                    a
                    <span style="font-weight: bolder;">
                        b
                        <strong>c<b>[d]</b>e</strong>
                        f
                    </span>
                    g
                </p>`),
                stepFunction: bold,
                contentAfter: unformat(`<p>
                    a
                    <span style="font-weight: bolder;">b<strong>c</strong></span>
                    [d]
                    <span style="font-weight: bolder;"><strong>e</strong>f</span>
                    g
                </p>`),
            });
        });

        describe('inside container or inline with class already bold', () => {
            it('should force the font-weight to normal with an inline with class', async () => {
                await testEditor(BasicEditor, {
                    styleContent: `.boldClass { font-weight: bold; }`,
                    contentBefore: `<div>a<span class="boldClass">[b]</span>c</div>`,
                    stepFunction: bold,
                    contentAfter: `<div>a<span class="boldClass"><span style="font-weight: normal;">[b]</span></span>c</div>`,
                });
            });

            it('should force the font-weight to normal', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: `<h1>a[b]c</h1>`,
                    stepFunction: bold,
                    contentAfter: `<h1>a<span style="font-weight: normal;">[b]</span>c</h1>`,
                });
            });

            it('should force the font-weight to normal while removing redundant tag', async () => {
                await repeatWithBoldTags(async (tag) => {
                    await testEditor(BasicEditor, {
                        contentBefore: `<h1>a${tag('[b]')}c</h1>`,
                        stepFunction: bold,
                        contentAfter: `<h1>a<span style="font-weight: normal;">[b]</span>c</h1>`,
                    });
                });
            });
        });
        describe('inside container font-weight: 500 and strong being strong-weight: 500', () => {
            it('should remove the redundant strong style and add span with a bolder font-weight', async () => {
                await testEditor(BasicEditor, {
                    styleContent: `h1, strong {font-weight: 500;}`,
                    contentBefore: `<h1>a${strong(`[b]`)}c</h1>`,
                    stepFunction: bold,
                    contentAfter: `<h1>a<span style="font-weight: bolder;">[b]</span>c</h1>`,
                });
            });
        });
    });
    describe('bold and italic inside container already bold', () => {
        it('should remove the redundant strong style and add span with a bolder font-weight', async () => {
            await testEditor(BasicEditor, {
                styleContent: `h1 {font-weight: bold;}`,
                contentBefore: `<h1>a[b]c</h1>`,
                stepFunction: (editor) => {
                    editor.execCommand('italic');
                    editor.execCommand('bold');
                    editor.execCommand('italic');
                },
                contentAfter: `<h1>a<span style="font-weight: normal;">[b]</span>c</h1>`,
            });
        });
    });

    describe('italic', () => {
        it('should make a few characters italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[cde]fg</p>`,
                stepFunction: italic,
                contentAfter: `<p>ab${em(`[cde]`)}fg</p>`,
            });
        });
        it('should make a few characters not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${em(`ab[cde]fg`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${em(`ab`)}[cde]${em(`fg`)}</p>`,
            });
        });
        it('should make two paragraphs italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>[abc</p><p>def]</p>',
                stepFunction: italic,
                contentAfter: `<p>${em(`[abc`)}</p><p>${em(`def]`)}</p>`,
            });
        });
        it('should make two paragraphs not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${em(`[abc`)}</p><p>${em(`def]`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>[abc</p><p>def]</p>`,
            });
        });
        it('should make a whole heading italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>[ab</h1><p>]cd</p>`,
                stepFunction: italic,
                contentAfter: `<h1>${em(`[ab]`)}</h1><p>cd</p>`,
            });
        });
        it('should make a whole heading not italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<h1>${em(`[ab`)}</h1><p>]cd</p>`,
                stepFunction: italic,
                contentAfter: `<h1>[ab]</h1><p>cd</p>`,
            });
        });
        it('should make a selection starting with italic text fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${em(`[ab`)}</p><p>c]d</p>`,
                stepFunction: italic,
                contentAfter: `<p>${em(`[ab`)}</p><p>${em(`c]`)}d</p>`,
            });
        });
        it('should make a selection with italic text in the middle fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[a${em(`b`)}</p><p>${em(`c`)}d]e</p>`,
                stepFunction: italic,
                contentAfter: `<p>${em(`[ab`)}</p><p>${em(`cd]`)}e</p>`,
            });
        });
        it('should make a selection ending with italic text fully italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>[ab</p><p>${em(`c]d`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${em(`[ab`)}</p><p>${em(`c]d`)}</p>`,
            });
        });
        it('should get ready to type in italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: italic,
                contentAfterEdit: `<p>ab${em(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to type in not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${em(`ab[]cd`)}</p>`,
                stepFunction: italic,
                contentAfterEdit: `<p>${em(`ab`)}${span(`[]\u200B`, 'first')}${em(`cd`)}</p>`,
                contentAfter: `<p>${em(`ab[]cd`)}</p>`,
            });
        });
    });
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
                contentAfter: `<p>${u(`ab`)}[cde]${u(`fg`)}</p>`,
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
                contentAfterEdit: `<p>${u(`ab`)}${span(`[]\u200B`, 'first')}${u(`cd`)}</p>`,
                contentAfter: `<p>${u(`ab[]cd`)}</p>`,
            });
        });
    });
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
                contentAfter: `<p>${s(`ab`)}[cde]${s(`fg`)}</p>`,
            });
        });
        it('should make a few characters strikeThrough then remove style inside', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[c d]ef</p>`,
                stepFunction: async editor => {
                    await strikeThrough(editor);
                    const styleSpan = editor.editable.querySelector('s').childNodes[0];
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
                contentAfter: `<p>ab${s(`c`)}[ ]${s(`d`)}ef</p>`,
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
                contentAfterEdit: `<p>${s(`ab`)}${span(`[]\u200B`, 'first')}${s(`cd`)}</p>`,
                contentAfter: `<p>${s(`ab[]cd`)}</p>`,
            });
        });
        it('should do nothing when a block already has a line-through decoration', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p style="text-decoration: line-through;">a[b]c</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p style="text-decoration: line-through;">a[b]c</p>`,
            });
        });
    });

    describe('underline + strikeThrough', () => {
        it('should get ready to write in strikeThrough without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`[]\u200b`, 'last')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd[]ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(`\u200b[]`, 'first')}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`, 'first'), 'first')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd[]ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`, 'first'))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`[]\u200b`, 'last')}${u(s(`ef`))}</p>`,
                contentAfter: `<p>ab${u(s(`cd[]ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`ghi[]`))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`${u(`ghi`)}`)}${s(`[]\u200b`, 'first')}${u(s(`ef`))}</p>`,
                // The reason the cursor is after the tag <s> is because when the editor get's cleaned, the zws tag gets deleted.
                contentAfter: `<p>ab${u(s(`cd`))}${s(u(`ghi`))}[]${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, strikeThrough)', async () => {
            const uselessU = u(''); // TODO: clean
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd[]ef`))}</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'A');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'B');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'C');
                },
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`A${u(`B`)}C[]${uselessU}`)}${u(s(`ef`))}</p>`,
            });
        });
        it('should remove only underline decoration on a span', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p><span style="text-decoration: underline line-through;">[a]</span></p>`,
                stepFunction: underline,
                contentAfter: `<p><span style="text-decoration: line-through;">[a]</span></p>`,
            });
        });
    });
    describe('underline + italic', () => {
        it('should get ready to write in italic and underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${em(u(`[]\u200B`, 'first'), 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic, after changing one\'s mind about underline (two consecutive at the end)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${em(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic, after changing one\'s mind about underline (separated by italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfterEdit: `<p>ab${em(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic, after changing one\'s mind about underline (two consecutive at the beginning)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                },
                contentAfterEdit: `<p>ab${em(`[]\u200B`, 'first')}cd</p>`,
                contentAfter: `<p>ab[]cd</p>`,
            });
        });
        it('should get ready to write in italic without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(em(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(em(`cd`))}${em(`[]\u200b`, 'last')}${u(em(`ef`))}</p>`,
                contentAfter: `<p>ab${u(em(`cd[]ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(em(`cd`))}${em(`[]\u200b`)}${u(em(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(em(`cd`))}${em(u(`[]\u200b`, 'last'))}${u(em(`ef`))}</p>`,
                contentAfter: `<p>ab${u(em(`cd`))}${em(`[]`)}${u(em(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(em(`cd`))}${em(u(`[]\u200b`))}${u(em(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(em(`cd`))}${em(`[]\u200b`, 'last')}${u(em(`ef`))}</p>`,
                contentAfter: `<p>ab${u(em(`cd[]ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(em(`cd`))}${em(u(`ghi[]`))}${u(em(`ef`))}</p>`,
                stepFunction: underline,
                contentAfterEdit: `<p>ab${u(em(`cd`))}${em(u(`ghi`))}<em oe-zws-empty-inline="">[]\u200b</em>${u(em(`ef`))}</p>`,
                // The reason the cursor is after the tag <s> is because when the editor get's cleaned, the zws tag gets deleted.
                contentAfter: `<p>ab${u(em(`cd`))}${em(u(`ghi`))}[]${u(em(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, italic)', async () => {
            const uselessU = u(''); // TODO: clean
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(em(`cd[]ef`))}</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'A');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'B');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'C');
                },
                contentAfter: `<p>ab${u(em(`cd`))}${em(`A${u(`B`)}C[]${uselessU}`)}${u(em(`ef`))}</p>`,
            });
        });
    });

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
        it('should get ready to type with a different font size', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: setFontSize('36px'),
                contentAfterEdit: `<p>ab<span oe-zws-empty-inline="" style="font-size: 36px;">[]\u200B</span>cd</p>`,
                contentAfter: '<p>ab[]cd</p>',
            });
        });
        it('should change the font-size for a character in an inline that has a font-size', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a<span style="font-size: 10px;">b[c]d</span>e</p>`,
                stepFunction: setFontSize('20px'),
                contentAfter:   unformat(`<p>
                                    a
                                    <span style="font-size: 10px;">b</span>
                                    <span style="font-size: 20px;">[c]</span>
                                    <span style="font-size: 10px;">d</span>
                                    e
                                </p>`),
            });
        });
        it('should change the font-size of a character with multiples inline ancestors having a font-size', async () => {
            await testEditor(BasicEditor, {
                contentBefore:   unformat(`<p>
                                    a
                                    <span style="font-size: 10px;">
                                        b
                                        <span style="font-size: 20px;">c[d]e</span>
                                        f
                                    </span>
                                    g
                                </p>`),
                stepFunction: setFontSize('30px'),
                contentAfter:   unformat(`<p>
                                    a
                                    <span style="font-size: 10px;">
                                        b
                                        <span style="font-size: 20px;">c</span>
                                    </span>
                                    <span style="font-size: 30px;">[d]</span>
                                    <span style="font-size: 10px;">
                                        <span style="font-size: 20px;">e</span>
                                        f
                                    </span>
                                    g
                                </p>`),
            });
        });
        it('should remove a redundant font-size', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p style="font-size: 10px">b<span style="font-size: 10px;">[c]</span>d</p>',
                stepFunction: setFontSize('10px'),
                contentAfter: '<p style="font-size: 10px">b[c]d</p>',
            });
        });
    });

    it('should add style to a span parent of an inline', async () => {
        await testEditor(BasicEditor, {
            contentBefore: `<p>a<span style="background-color: black;">${strong(`[bc]`)}</span>d</p>`,
            stepFunction: setFontSize('10px'),
            contentAfter: `<p>a<span style="background-color: black; font-size: 10px;">${strong(`[bc]`)}</span>d</p>`,
        });
    });

    describe('isSelectionFormat', () => {
        it('return false for isSelectionFormat when partially selecting 2 text node, the anchor is formated and focus is not formated', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`a[b`)}</p><p>c]d</p>`,
                stepFunction: (editor) => {
                    window.chai.expect(isSelectionFormat(editor.editable, 'bold')).to.be.equal(false);
                },
            });
        });
        it('return false for isSelectionFormat when partially selecting 2 text node, the anchor is not formated and focus is formated', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${strong(`a]b`)}</p><p>c[d</p>`,
                stepFunction: (editor) => {
                    window.chai.expect(isSelectionFormat(editor.editable, 'bold')).to.be.equal(false);
                },
            });
        });
        it('return false for isSelectionFormat when selecting 3 text node, the anchor and focus not formated and the text node in between formated', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[b</p><p>${strong(`c`)}</p><p>d]e</p>`,
                stepFunction: (editor) => {
                    window.chai.expect(isSelectionFormat(editor.editable, 'bold')).to.be.equal(false);
                },
            });
        });
    });
    describe('switchDirection', () => {
        it('should switch direction on a collapsed range', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: switchDirection,
                contentAfter: `<p dir="rtl">a[]b</p>`,
            });
        });
        it('should switch direction on an uncollapsed range', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[b]c</p>`,
                stepFunction: switchDirection,
                contentAfter: `<p dir="rtl">a[b]c</p>`,
            });
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
        it('should not add paragraph tag when selection is changed to normal in list', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li><h1>[abcd]</h1></li></ul>',
                stepFunction: editor => editor.execCommand('setTag', "p"),
                contentAfter: `<ul><li>[abcd]</li></ul>`
            });
        });
        it('should not add paragraph tag to normal text in list', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<ul><li>[abcd]</li></ul>',
                stepFunction: editor => editor.execCommand('setTag', "p"),
                contentAfter: `<ul><li>[abcd]</li></ul>`
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
