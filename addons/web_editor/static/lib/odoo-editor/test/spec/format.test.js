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
    describe('italic', () => {
        it('should make a few characters italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: italic,
                contentAfter: '<p>ab<span style="font-style: italic;">[cde]</span>fg</p>',
            });
        });
        it('should make a few characters not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="font-style: italic;">ab[cde]fg</span></p>',
                stepFunction: italic,
                contentAfter: '<p><span style="font-style: italic;">ab<span style="font-style: normal;">[cde]</span>fg</span></p>',
            });
        });
        it('should make a whole heading italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: italic,
                contentAfter: '<h1><span style="font-style: italic;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should make a whole heading not italic after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1><span style="font-style: italic;">[ab</span></h1><p>]cd</p>',
                stepFunction: italic,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: '<h1><span style="font-style: normal;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should get ready to type in italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: italic,
                contentAfter: '<p>ab<span style="font-style: italic;">[]\u200B</span>cd</p>',
            });
        });
        it('should get ready to type in not italic', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="font-style: italic;">ab[]cd</span></p>',
                stepFunction: italic,
                contentAfter: '<p><span style="font-style: italic;">ab<span style="font-style: normal;">[]\u200B</span>cd</span></p>',
            });
        });
    });
    describe('underline', () => {
        it('should make a few characters underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: underline,
                contentAfter: '<p>ab<span style="text-decoration-line: underline;">[cde]</span>fg</p>',
            });
        });
        it('should make a few characters not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="text-decoration-line: underline;">ab[cde]fg</span></p>',
                stepFunction: underline,
                contentAfter: '<p><span style="text-decoration-line: underline;">ab<span style="text-decoration-line: none;">[cde]</span>fg</span></p>',
            });
        });
        it('should make a whole heading underline after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: underline,
                contentAfter: '<h1><span style="text-decoration-line: underline;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should make a whole heading not underline after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1><span style="text-decoration-line: underline;">[ab</span></h1><p>]cd</p>',
                stepFunction: underline,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: '<h1><span style="text-decoration-line: none;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should get ready to type in underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: underline,
                contentAfter: '<p>ab<span style="text-decoration-line: underline;">[]\u200B</span>cd</p>',
            });
        });
        it('should get ready to type in not underline', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="text-decoration-line: underline;">ab[]cd</span></p>',
                stepFunction: underline,
                contentAfter: '<p><span style="text-decoration-line: underline;">ab<span style="text-decoration-line: none;">[]\u200B</span>cd</span></p>',
            });
        });
    });
    describe('strikeThrough', () => {
        it('should make a few characters strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[cde]fg</p>',
                stepFunction: strikeThrough,
                contentAfter: '<p>ab<span style="text-decoration-line: line-through;">[cde]</span>fg</p>',
            });
        });
        it('should make a few characters not strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="text-decoration-line: line-through;">ab[cde]fg</span></p>',
                stepFunction: strikeThrough,
                contentAfter: '<p><span style="text-decoration-line: line-through;">ab<span style="text-decoration-line: none;">[cde]</span>fg</span></p>',
            });
        });
        it('should make a whole heading strikeThrough after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1>[ab</h1><p>]cd</p>',
                stepFunction: strikeThrough,
                contentAfter: '<h1><span style="text-decoration-line: line-through;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should make a whole heading not strikeThrough after a triple click', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<h1><span style="text-decoration-line: line-through;">[ab</span></h1><p>]cd</p>',
                stepFunction: strikeThrough,
                // TODO: ideally should restore regular h1 without span instead.
                contentAfter: '<h1><span style="text-decoration-line: none;">[ab]</span></h1><p>cd</p>',
            });
        });
        it('should get ready to type in strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>ab[]cd</p>',
                stepFunction: strikeThrough,
                contentAfter: '<p>ab<span style="text-decoration-line: line-through;">[]\u200B</span>cd</p>',
            });
        });
        it('should get ready to type in not strikeThrough', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><span style="text-decoration-line: line-through;">ab[]cd</span></p>',
                stepFunction: strikeThrough,
                contentAfter: '<p><span style="text-decoration-line: line-through;">ab<span style="text-decoration-line: none;">[]\u200B</span>cd</span></p>',
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
