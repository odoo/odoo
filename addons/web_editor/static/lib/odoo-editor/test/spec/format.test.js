import { BasicEditor, testEditor } from '../utils.js';
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
    const b = content => `<span style="font-weight: bolder;">${content}</span>`;
    const notB = (content, weight) => `<span style="font-weight: ${weight || 'normal'};">${content}</span>`;
    describe('bold', () => {
        it('should make a few characters bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: bold,
                contentAfter: '<p>ab<span style="font-weight: bolder;">[cde]</span>fg</p>',
            });
        });
        it('should make a few characters not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="font-weight: bolder;">ab[cde]fg</span></p>',
                stepFunction: bold,
                contentAfter: '<p><span style="font-weight: bolder;">ab<span style="font-weight: 400;">[cde]</span>fg</span></p>',
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
                contentBefore: `<p>${notB(`[abc`)}</p><p>${notB(`def]`, 400)}</p>`,
            });
        });
        it('should make a whole heading bold after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1><span style="font-weight: normal;">[ab</span></h1><p>]cd</p>',
                stepFunction: bold,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: '<h1><span style="font-weight: bolder;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should make a whole heading not bold after a triple click (heading is considered bold)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: bold,
                contentAfter: '<h1><span style="font-weight: normal;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should get ready to type in bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: bold,
                contentAfter: '<p>ab<span style="font-weight: bolder;">[]\u200B</span>cd</p>',
            });
        });
        it('should get ready to type in not bold', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="font-weight: bolder;">ab[]cd</span></p>',
                stepFunction: bold,
                contentAfter: '<p><span style="font-weight: bolder;">ab<span style="font-weight: 400;">[]\u200B</span>cd</span></p>',
            });
        });
    });
    const i = content => `<span style="font-style: italic;">${content}</span>`;
    const notI = content => `<span style="font-style: normal;">${content}</span>`;
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
                contentBefore: `<p>${notI(`[abc`)}</p><p>${notI(`def]`)}</p>`,
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
        it('should get ready to type in italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: italic,
                contentAfter: `<p>ab${i(`[]\u200B`)}cd</p>`,
            });
        });
        it('should get ready to type in not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${i(`ab[]cd`)}</p>`,
                stepFunction: italic,
                contentAfter: `<p>${i(`ab${notI(`[]\u200B`)}cd`)}</p>`,
            });
        });
    });
    const u = content => `<span style="text-decoration-line: underline;">${content}</span>`;
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
        it('should get ready to type in underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(`[]\u200B`)}cd</p>`,
            });
        });
        it('should get ready to type in not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${u(`ab[]cd`)}</p>`,
                stepFunction: underline,
                contentAfter: `<p>${u(`ab`)}\u200B[]${u(`cd`)}</p>`,
            });
        });
    });
    const s = content => `<span style="text-decoration-line: line-through;">${content}</span>`;
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
        it('should get ready to type in strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>ab${s(`[]\u200B`)}cd</p>`,
            });
        });
        it('should get ready to type in not strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${s(`ab[]cd`)}</p>`,
                stepFunction: strikeThrough,
                contentAfter: `<p>${s(`ab`)}\u200B[]${s(`cd`)}</p>`,
            });
        });
    });
    describe('underline + strikeThrough', () => {
        it('should get ready to write in strikeThrough without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(s(`cd`))}${s(`\u200b[]`)}${u(s(`ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(`\u200b[]`)}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`))}${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`[]\u200b`))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(s(`cd`))}${s(`\u200b[]`)}${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, strikeThrough)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(s(`cd`))}${s(u(`ghi[]`))}${u(s(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(s(`cd`))}${s(u(`ghi`) + `\u200b[]`)}${u(s(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, strikeThrough)', async () => {
            const uselessSpan = u(''); // TODO: clean
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
                contentAfterEdit: `<p>ab${u(s(`cd`))}${s(`A${u(`B`)}C[]${uselessSpan}`)}${u(s(`ef`))}</p>`,
            });
        });
    });
    describe('underline + italic', () => {
        const iAndU = content => `<span style="font-style: italic; text-decoration-line: underline;">${content}</span>`;
        it('should get ready to write in italic and underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfter: `<p>ab${iAndU(`[]\u200B`)}cd</p>`,
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
                contentAfter: `<p>ab${i(`\u200B[]`)}cd</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                    await editor.execCommand('underline');
                },
                contentAfter: `<p>ab${i(`\u200B[]`)}cd</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab[]cd</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('underline');
                    await editor.execCommand('italic');
                },
                contentAfter: `<p>ab${i(`[]\u200B`)}cd</p>`,
            });
        });
        it('should get ready to write in italic without underline (underline was first)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd[]ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(i(`cd`))}${i(`\u200b[]`)}${u(i(`ef`))}</p>`,
            });
        });
        it('should restore underline after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(`\u200b[]`)}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(i(`cd`))}${iAndU(`[]\u200b`)}${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(u(`[]\u200b`))}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(i(`cd`))}${i(`\u200b[]`)}${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline after restoring it and writing after removing it (collapsed, italic)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd`))}${i(u(`ghi[]`))}${u(i(`ef`))}</p>`,
                stepFunction: underline,
                contentAfter: `<p>ab${u(i(`cd`))}${i(u(`ghi`) + `\u200b[]`)}${u(i(`ef`))}</p>`,
            });
        });
        it('should remove underline, write, restore underline, write, remove underline again, write (collapsed, italic)', async () => {
            const uselessSpan = u(''); // TODO: clean
            await testEditor(BasicEditor, {
                contentBefore: `<p>ab${u(i(`cd[]ef`))}</p>`,
                stepFunction: async editor => {
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'A');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'B');
                    await editor.execCommand('underline');
                    await editor.execCommand('insertText', 'C');
                },
                contentAfterEdit: `<p>ab${u(i(`cd`))}${i(`A${u(`B`)}C[]${uselessSpan}`)}${u(i(`ef`))}</p>`,
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
