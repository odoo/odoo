import {
    BasicEditor,
    click,
    deleteBackward,
    deleteForward,
    insertLineBreak,
    insertParagraphBreak,
    insertText,
    indentList,
    outdentList,
    testEditor,
    toggleCheckList,
    toggleOrderedList,
    toggleUnorderedList,
    unformat,
} from '../utils.js';

describe('List', () => {
    describe('toggleList', () => {
        describe('Range collapsed', () => {
            describe('Unordered', () => {
                describe('Insert', () => {
                    it('should turn an empty paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>[]<br></p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                    it('should turn a paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]cd</p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>ab[]cd</li></ul>',
                        });
                    });
                    it('should turn a heading into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<h1>ab[]cd</h1>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li><h1>ab[]cd</h1></li></ul>',
                        });
                    });
                    it('should turn a paragraph in a div into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><p>ab[]cd</p></div>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<div><ul><li>ab[]cd</li></ul></div>',
                        });
                    });
                    it('should turn a paragraph with formats into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter:
                                '<ul><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                        });
                    });
                });
                describe('Remove', () => {
                    it('should turn an empty list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>[]<br></li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>[]<br></p>',
                        });
                    });
                    it('should turn a list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab[]cd</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                    it('should turn a list into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li><h1>ab[]cd</h1></li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<h1>ab[]cd</h1>',
                        });
                    });
                    it('should turn a list item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ul><li>cd</li><li>ef[]gh</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><ul><li>cd</li></ul><p>ef[]gh</p>',
                        });
                    });
                    it('should turn a list with formats into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                        });
                    });
                    it('should turn nested list items into paragraphs', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: unformat(`
                                <ul>
                                    <li>a</li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[]b</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li>c</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>`),
                            stepFunction: toggleUnorderedList,
                            contentAfter: unformat(`
                                <ul>
                                    <li>a</li>
                                </ul>
                                <p>[]b</p>
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li>c</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>`),
                        });
                    });
                });
                describe('Transform', () => {
                    it('should turn an empty ordered list into an unordered list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>[]<br></li></ol>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                    it('should turn an empty ordered list into an unordered list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                });
            });
            describe('Ordered', () => {
                describe('Insert', () => {
                    it('should turn an empty paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>[]<br></p>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>[]<br></li></ol>',
                        });
                    });
                    it('should turn a paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]cd</p>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>ab[]cd</li></ol>',
                        });
                    });
                    it('should turn a heading into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<h1>ab[]cd</h1>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li><h1>ab[]cd</h1></li></ol>',
                        });
                    });
                    it('should turn a paragraph in a div into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><p>ab[]cd</p></div>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<div><ol><li>ab[]cd</li></ol></div>',
                        });
                    });
                    it('should turn a paragraph with formats into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                            stepFunction: toggleOrderedList,
                            contentAfter:
                                '<ol><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ol>',
                        });
                    });
                });
                describe('Remove', () => {
                    it('should turn an empty list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>[]<br></li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>[]<br></p>',
                        });
                    });
                    it('should turn a list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab[]cd</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                    it('should turn a list into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li><h1>ab[]cd</h1></li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<h1>ab[]cd</h1>',
                        });
                    });
                    it('should turn a list item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ol><li>cd</li><li>ef[]gh</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><ol><li>cd</li></ol><p>ef[]gh</p>',
                        });
                    });
                    it('should turn a list with formats into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                        });
                    });
                });
            });
            describe('Checklist', () => {
                describe('Insert', () => {
                    it('should turn an empty paragraph into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<p>[]<br></p>',
                            stepFunction: toggleCheckList,
                            // JW cAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                            contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                        });
                    });
                    it('should turn a paragraph into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<p>ab[]cd</p>',
                            stepFunction: toggleCheckList,
                            // JW cAfter: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                            contentAfter: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                        });
                    });
                    it('should turn a heading into a checklist', async () => {
                            await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<h1>ab[]cd</h1>',
                            stepFunction: toggleCheckList,
                            // JW cAfter: '<ul class="o_checklist"><li><h1>ab[]cd</h1></li></ul>',
                            contentAfter: '<ul class="o_checklist"><li><h1>ab[]cd</h1></li></ul>',
                        });
                    });
                    it('should turn a paragraph in a div into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<div><p>ab[]cd</p></div>',
                            stepFunction: toggleCheckList,
                            // JW cAfter: '<div><ul class="o_checklist"><li>ab[]cd</li></ul></div>',
                            contentAfter: '<div><ul class="o_checklist"><li>ab[]cd</li></ul></div>',
                        });
                    });
                    it('should turn a paragraph with formats into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                            stepFunction: toggleCheckList,
                            // JW cAfter: '<ul class="o_checklist"><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                            contentAfter:
                                '<ul class="o_checklist"><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                        });
                    });
                    it('should turn a paragraph between 2 checklist into a checklist item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>d[]ef</p><ul class="o_checklist"><li class="o_checked">ghi</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>d[]ef</li><li class="o_checked">ghi</li></ul>',
                        });
                    });
                    it('should turn a unordered list into a checklist betweet 2 checklist inside a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">abc</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">def</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>g[]hi</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">jkl</li>
                                        </ul>
                                    </li>
                                </ul>`),
                            stepFunction: toggleCheckList,
                            contentAfter: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">abc</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">def</li>
                                            <li>g[]hi</li>
                                            <li class="o_checked">jkl</li>
                                        </ul>
                                    </li>
                                </ul>`),
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">abc</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">def</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li class="a">g[]hi</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">jkl</li>
                                        </ul>
                                    </li>
                                </ul>`),
                            stepFunction: toggleCheckList,
                            contentAfter: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">abc</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">def</li>
                                            <li class="a">g[]hi</li>
                                            <li class="o_checked">jkl</li>
                                        </ul>
                                    </li>
                                </ul>`),
                        });
                    });
                    it('should remove the list-style when change the list style', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                <ul>
                                    <li style="list-style: cambodian;">a[]</li>
                                </ul>`),
                            stepFunction: toggleCheckList,
                            contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>a[]</li>
                            </ul>`),
                        });
                    });
                });
                it('should add a unique id on a new checklist', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>ab[]cd</p>',
                        stepFunction: editor => {
                            toggleCheckList(editor);
                            const id = editor.editable.querySelector('li[id^=checklist-id-]').getAttribute('id');
                            window.chai.expect(editor.editable.innerHTML).to.be.equal(
                                `<ul class="o_checklist"><li id="${id}">abcd</li></ul>`
                            );
                        },
                    });
                });
                describe('Remove', () => {
                    it('should turn an empty list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>[]<br></p>',
                        });
                    });
                    it('should turn a checklist into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>ab[]cd</p>',
                        });
                    });
                    it('should turn a checklist into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul class="o_checklist"><li><h1>ab[]cd</h1></li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<h1>ab[]cd</h1>',
                        });
                    });
                    it('should turn a checklist item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p>ab</p><ul class="o_checklist"><li>cd</li><li>ef[]gh</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<p>ab</p><ul class="o_checklist"><li>cd</li></ul><p>ef[]gh</p>',
                        });
                    });
                    it('should turn a checklist with formats into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul class="o_checklist"><li><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<p><span><b>ab</b></span> <span><i>cd</i></span> ef[]gh</p>',
                        });
                    });
                    it('should turn nested list items into paragraphs', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">a</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">[]b</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="oe-nested">
                                                <ul class="o_checklist">
                                                    <li class="o_checked">c</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>`),
                            stepFunction: toggleCheckList,
                            contentAfter: unformat(`
                                <ul class="o_checklist">
                                    <li class="o_checked">a</li>
                                </ul>
                                <p>[]b</p>
                                <ul class="o_checklist">
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="oe-nested">
                                                <ul class="o_checklist">
                                                    <li class="o_checked">c</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>`),
                        });
                    });
                });
            });
        });

        describe('Range not collapsed', () => {
            describe('Unordered', () => {
                describe('Insert', () => {
                    it('should turn a paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>cd[ef]gh</p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><ul><li>cd[ef]gh</li></ul>',
                        });
                    });
                    it('should turn a heading into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><h1>cd[ef]gh</h1>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><ul><li><h1>cd[ef]gh</h1></li></ul>',
                        });
                    });
                    it('should turn two paragraphs into a list with two items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><ul><li>cd[ef</li><li>gh]ij</li></ul>',
                        });
                    });
                    it('should turn two paragraphs in a div into a list with two items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><p>ab[cd</p><p>ef]gh</p></div>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<div><ul><li>ab[cd</li><li>ef]gh</li></ul></div>',
                        });
                    });
                    it('should turn a paragraph and a list item into two list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[b</p><ul><li>c]d</li><li>ef</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>a[b</li><li>c]d</li><li>ef</li></ul>',
                        });
                    });
                    it('should turn a list item and a paragraph into two list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab</li><li>c[d</li></ul><p>e]f</p>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>ab</li><li>c[d</li><li>e]f</li></ul>',
                        });
                    });
                    it('should turn a list, a paragraph and another list into one list with three list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>a[b</li></ul><p>cd</p><ul><li>e]f</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>a[b</li><li>cd</li><li>e]f</li></ul>',
                        });
                    });
                    it('should turn a list item, a paragraph and another list into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>ab<li>c[d</li></ul><p>ef</p><ul><li>g]h</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ul>',
                        });
                    });
                    it('should turn a list, a paragraph and a list item into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>a[b</li></ul><p>cd</p><ul><li>e]f</li><li>gh</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<ul><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ul>',
                        });
                    });
                });
                describe('Remove', () => {
                    it('should turn a list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ul><li>cd[ef]gh</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><p>cd[ef]gh</p>',
                        });
                    });
                    it('should turn a list into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ul><li><h1>cd[ef]gh</h1></li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><h1>cd[ef]gh</h1>',
                        });
                    });
                    it('should turn a list into two paragraphs', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ul><li>cd[ef</li><li>gh]ij</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                        });
                    });
                    it('should turn a list item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ul><li>cd</li><li>ef[gh]ij</li></ul>',
                            stepFunction: toggleUnorderedList,
                            contentAfter: '<p>ab</p><ul><li>cd</li></ul><p>ef[gh]ij</p>',
                        });
                    });
                });
            });
            describe('Ordered', () => {
                describe('Insert', () => {
                    it('should turn a paragraph into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>cd[ef]gh</p>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><ol><li>cd[ef]gh</li></ol>',
                        });
                    });
                    it('should turn a heading into a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><h1>cd[ef]gh</h1>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><ol><li><h1>cd[ef]gh</h1></li></ol>',
                        });
                    });
                    it('should turn two paragraphs into a list with two items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><ol><li>cd[ef</li><li>gh]ij</li></ol>',
                        });
                    });
                    it('should turn two paragraphs in a div into a list with two items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<div><p>ab[cd</p><p>ef]gh</p></div>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<div><ol><li>ab[cd</li><li>ef]gh</li></ol></div>',
                        });
                    });
                    it('should turn a paragraph and a list item into two list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>a[b</p><ol><li>c]d</li><li>ef</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>a[b</li><li>c]d</li><li>ef</li></ol>',
                        });
                    });
                    it('should turn a list item and a paragraph into two list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab</li><li>c[d</li></ol><p>e]f</p>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>ab</li><li>c[d</li><li>e]f</li></ol>',
                        });
                    });
                    it('should turn a list, a paragraph and another list into one list with three list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>a[b</li></ol><p>cd</p><ol><li>e]f</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>a[b</li><li>cd</li><li>e]f</li></ol>',
                        });
                    });
                    it('should turn a list item, a paragraph and another list into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>ab<li>c[d</li></ol><p>ef</p><ol><li>g]h</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ol>',
                        });
                    });
                    it('should turn a list, a paragraph and a list item into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>a[b</li></ol><p>cd</p><ol><li>e]f</li><li>gh</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<ol><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ol>',
                        });
                    });
                });
                describe('Remove', () => {
                    it('should turn a list into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ol><li>cd[ef]gh</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><p>cd[ef]gh</p>',
                        });
                    });
                    it('should turn a list into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ol><li><h1>cd[ef]gh</h1></li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><h1>cd[ef]gh</h1>',
                        });
                    });
                    it('should turn a list into two paragraphs', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ol><li>cd[ef</li><li>gh]ij</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                        });
                    });
                    it('should turn a list item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab</p><ol><li>cd</li><li>ef[gh]ij</li></ol>',
                            stepFunction: toggleOrderedList,
                            contentAfter: '<p>ab</p><ol><li>cd</li></ol><p>ef[gh]ij</p>',
                        });
                    });
                });
            });
            describe('Checklist', () => {
                describe('Insert', () => {
                    it('should turn a paragraph into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<p>ab</p><p>cd[ef]gh</p>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>ab</p><ul class="o_checklist"><li>cd[ef]gh</li></ul>',
                        });
                    });
                    it('should turn a heading into a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<p>ab</p><h1>cd[ef]gh</h1>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<p>ab</p><ul class="o_checklist"><li><h1>cd[ef]gh</h1></li></ul>',
                        });
                    });
                    it('should turn two paragraphs into a checklist with two items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<p>ab</p><ul class="o_checklist"><li>cd[ef</li><li>gh]ij</li></ul>',
                        });
                    });
                    it('should turn two paragraphs in a div into a checklist with two items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<div><p>ab[cd</p><p>ef]gh</p></div>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<div><ul class="o_checklist"><li>ab[cd</li><li>ef]gh</li></ul></div>',
                        });
                    });
                    it('should turn a paragraph and a checklist item into two list items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p>a[b</p><ul class="o_checklist"><li class="o_checked">c]d</li><li>ef</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li>a[b</li><li class="o_checked">c]d</li><li>ef</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p>a[b</p><ul class="o_checklist"><li class="o_checked">c]d</li><li class="o_checked">ef</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li>a[b</li><li class="o_checked">c]d</li><li class="o_checked">ef</li></ul>',
                        });
                    });
                    it('should turn a checklist item and a paragraph into two list items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab</li><li class="o_checked">c[d</li></ul><p>e]f</p>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li>ab</li><li class="o_checked">c[d</li><li>e]f</li></ul>',
                        });
                    });
                    it('should turn a checklist, a paragraph and another list into one list with three list items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>a[b</li></ul><p>cd</p><ul class="o_checklist"><li class="o_checked">e]f</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li>a[b</li><li>cd</li><li class="o_checked">e]f</li></ul>',
                        });
                    });
                    it('should turn a checklist item, a paragraph and another list into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab<li>c[d</li></ul><p>ef</p><ul class="o_checklist"><li class="o_checked">g]h</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab</li><li>c[d</li><li>ef</li><li class="o_checked">g]h</li></ul>',
                        });
                    });
                    it('should turn a checklist, a paragraph and a checklist item into one list with all three as list items', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">a[b</li></ul><p>cd</p><ul class="o_checklist"><li class="o_checked">e]f</li><li>gh</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">a[b</li><li>cd</li><li class="o_checked">e]f</li><li>gh</li></ul>',
                        });
                    });
                });
                describe('Remove', () => {
                    it('should turn a checklist into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>ab</p><ul class="o_checklist"><li>cd[ef]gh</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>ab</p><p>cd[ef]gh</p>',
                        });
                    });
                    it('should turn a checklist into a heading', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>ab</p><ul class="o_checklist"><li><h1>cd[ef]gh</h1></li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>ab</p><h1>cd[ef]gh</h1>',
                        });
                    });
                    it('should turn a checklist into two paragraphs', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>ab</p><ul class="o_checklist"><li>cd[ef</li><li>gh]ij</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter: '<p>ab</p><p>cd[ef</p><p>gh]ij</p>',
                        });
                    });
                    it('should turn a checklist item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p>ab</p><ul class="o_checklist"><li class="o_checked">cd</li><li class="o_checked">ef[gh]ij</li></ul>',
                            stepFunction: toggleCheckList,
                            contentAfter:
                                '<p>ab</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><p>ef[gh]ij</p>',
                        });
                    });
                });
            });
            describe('Mixed', () => {
                it('should turn an ordered list into an unordered list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ol><li>a[b]c</li></ol>',
                        stepFunction: toggleUnorderedList,
                        contentAfter: '<ul><li>a[b]c</li></ul>',
                    });
                });
                it('should turn an unordered list into an ordered list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>a[b]c</li></ul>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>a[b]c</li></ol>',
                    });
                });
                it('should turn a paragraph and an unordered list item into an ordered list and an unordered list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<p>a[b</p><ul><li>c]d</li><li>ef</li></ul>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>a[b</li><li>c]d</li><li>ef</li></ol>',
                    });
                });
                it('should turn a p, an ul list with ao. one nested ul, and another p into one ol with a nested ol', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <p>a[b</p>
                            <ul>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>ef</li>
                                    </ul>
                                </li>
                                <li>gh</li>
                            </ul>
                            <p>i]j</p>`),
                        stepFunction: toggleOrderedList,
                        contentAfter: unformat(`
                            <ol>
                                <li>a[b</li>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ef</li>
                                    </ol>
                                </li>
                                <li>gh</li>
                                <li>i]j</li>
                            </ol>`),
                    });
                });
                it('should turn an unordered list item and a paragraph into two list items within an ordered list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab</li><li>c[d</li></ul><p>e]f</p>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>ab</li><li>c[d</li><li>e]f</li></ol>',
                    });
                });
                it('should turn an unordered list, a paragraph and an ordered list into one ordered list with three list items', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>a[b</li></ul><p>cd</p><ol><li>e]f</li></ol>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>a[b</li><li>cd</li><li>e]f</li></ol>',
                    });
                });
                it('should turn an unordered list item, a paragraph and an ordered list into one ordered list with all three as list items', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab<li>c[d</li></ul><p>ef</p><ol><li>g]h</li></ol>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>ab</li><li>c[d</li><li>ef</li><li>g]h</li></ol>',
                    });
                });
                it('should turn an ordered list, a paragraph and an unordered list item into one ordered list with all three as list items', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore:
                            '<ol><li>a[b</li></ol><p>cd</p><ul><li>e]f</li><li>gh</li></ul>',
                        stepFunction: toggleOrderedList,
                        contentAfter: '<ol><li>a[b</li><li>cd</li><li>e]f</li><li>gh</li></ol>',
                    });
                });
                it('should turn an unordered list within an unordered list into an ordered list within an unordered list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li>ab</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>c[d</li>
                                        <li>e]f</li>
                                    </ul>
                                </li>
                                <li>gh</li>
                            </ul>`),
                        stepFunction: toggleOrderedList,
                        contentAfter: unformat(`
                            <ul>
                                <li>ab</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>c[d</li>
                                        <li>e]f</li>
                                    </ol>
                                </li>
                                <li>gh</li>
                            </ul>`),
                    });
                });
                it('should turn an unordered list with mixed nested elements into an ordered list with only unordered elements', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li>a[b</li>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>ef</li>
                                        <li>gh</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>ij</li>
                                                <li>kl</li>
                                                <li class="oe-nested">
                                                    <ul>
                                                        <li>mn</li>
                                                    </ul>
                                                </li>
                                                <li>op</li>
                                            </ol>
                                        </li>
                                    </ul>
                                </li>
                                <li>q]r</li>
                                <li>st</li>
                            </ul>`),
                        stepFunction: toggleOrderedList,
                        contentAfter: unformat(`
                            <ol>
                                <li>a[b</li>
                                <li>cd</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>ef</li>
                                        <li>gh</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>ij</li>
                                                <li>kl</li>
                                                <li class="oe-nested">
                                                    <ol>
                                                        <li>mn</li>
                                                    </ol>
                                                </li>
                                                <li>op</li>
                                            </ol>
                                        </li>
                                    </ol>
                                </li>
                                <li>q]r</li>
                                <li>st</li>
                            </ol>`),
                    });
                });
                it('should convert within mixed lists', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li>a</li>
                                <li>b</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>c</li>
                                        <li>d</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>[]e</li>
                                                <li>f</li>
                                                <li class="oe-nested">
                                                    <ul>
                                                        <li>g</li>
                                                    </ul>
                                                </li>
                                                <li>h</li>
                                            </ul>
                                        </li>
                                    </ol>
                                </li>
                                <li>q]r</li>
                                <li>st</li>
                            </ul>`),
                        stepFunction: toggleOrderedList,
                        contentAfter: unformat(`
                            <ul>
                                <li>a</li>
                                <li>b</li>
                                <li class="oe-nested">
                                    <ol>
                                        <li>c</li>
                                        <li>d</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>[]e</li>
                                                <li>f</li>
                                                <li class="oe-nested">
                                                    <ul>
                                                        <li>g</li>
                                                    </ul>
                                                </li>
                                                <li>h</li>
                                            </ol>
                                        </li>
                                    </ol>
                                </li>
                                <li>q]r</li>
                                <li>st</li>
                            </ul>`),
                    });
                });
                it('should turn an unordered list into a checklist', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: '<ul><li>a[b]c</li></ul>',
                        stepFunction: toggleCheckList,
                        contentAfter: '<ul class="o_checklist"><li>a[b]c</li></ul>',
                    });
                });
                it('should turn an unordered list into a checklist just after a checklist', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore:
                            '<ul class="o_checklist"><li class="o_checked">abc</li></ul><ul><li>d[e]f</li></ul>',
                        stepFunction: toggleCheckList,
                        contentAfter:
                            '<ul class="o_checklist"><li class="o_checked">abc</li><li>d[e]f</li></ul>',
                    });
                });
                it('should turn an unordered list into a checklist just after a checklist and inside a checklist', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">title</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">abc</li>
                                    </ul>
                                </li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: toggleCheckList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">title</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">abc</li>
                                        <li>d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                });
            });
        });
    });
    describe('toggleChecked', () => {
        it('should do nothing if do not click on the checkbox', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>1</li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left + 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>1</li>
                    </ul>`),
            });
        });
        it('should check a simple item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>1</li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">1</li>
                    </ul>`),
            });
        });
        it('should uncheck a simple item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">1</li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>1</li>
                    </ul>`),
            });
        });
        it('should check an empty item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li><br></li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked"><br></li>
                    </ul>`),
            });
        });
        it('should uncheck an empty item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li><br></li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked"><br></li>
                    </ul>`),
            });
        });
        it('should check a nested item and the previous checklist item used as title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                <ul class="o_checklist">
                    <li>2</li>
                    <li class="oe-nested">
                        <ul class="o_checklist">
                            <li class="o_checked">2.1</li>
                            <li>2.2</li>
                        </ul>
                    </li>
                </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[2];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                <ul class="o_checklist">
                    <li>2</li>
                    <li class="oe-nested">
                        <ul class="o_checklist">
                            <li class="o_checked">2.1</li>
                            <li class="o_checked">2.2</li>
                        </ul>
                    </li>
                </ul>`),
            });
        });
        it('should uncheck a nested item and the previous checklist item used as title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                <ul class="o_checklist">
                    <li class="o_checked">2</li>
                    <li class="oe-nested">
                        <ul class="o_checklist">
                            <li class="o_checked">2.1</li>
                            <li class="o_checked">2.2</li>
                        </ul>
                    </li>
                </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[2];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                <ul class="o_checklist">
                    <li class="o_checked">2</li>
                    <li class="oe-nested">
                        <ul class="o_checklist">
                            <li class="o_checked">2.1</li>
                            <li>2.2</li>
                        </ul>
                    </li>
                </ul>`),
            });
        });
        it('should check a nested item and the wrapper wrapper title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li>3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[3];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li class="o_checked">3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
        it('should uncheck a nested item and the wrapper wrapper title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.1.1</li>
                                        <li class="o_checked">3.1.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[3];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.1.1</li>
                                        <li>3.1.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
        it('should check all nested checklist item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                        <ul class="o_checklist">
                            <li>3</li>
                            <li class="oe-nested">
                                <ul class="o_checklist">
                                    <li>3.1</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">3.1.1</li>
                                            <li>3.1.2</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">3.2.1</li>
                                            <li>3.2.2</li>
                                        </ul>
                                    </li>
                                    <li>3.3</li>
                                </ul>
                            </li>
                        </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.1.1</li>
                                        <li>3.1.2</li>
                                        <li class="o_checked">3.2.1</li>
                                        <li>3.2.2</li>
                                    </ul>
                                </li>
                                <li>3.3</li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
        it('should uncheck all nested checklist item', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                        <ul class="o_checklist">
                            <li class="o_checked">3</li>
                            <li class="oe-nested">
                                <ul class="o_checklist">
                                    <li class="o_checked">3.1</li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">3.1.1</li>
                                            <li class="o_checked">3.1.2</li>
                                        </ul>
                                    </li>
                                    <li class="oe-nested">
                                        <ul class="o_checklist">
                                            <li class="o_checked">3.2.1</li>
                                            <li class="o_checked">3.2.2</li>
                                        </ul>
                                    </li>
                                    <li class="o_checked">3.3</li>
                                </ul>
                            </li>
                        </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[0];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.1.1</li>
                                        <li class="o_checked">3.1.2</li>
                                        <li class="o_checked">3.2.1</li>
                                        <li class="o_checked">3.2.2</li>
                                    </ul>
                                </li>
                                <li class="o_checked">3.3</li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
        it('should check all nested checklist item and update wrapper title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li>3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li>3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[1];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li>3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li>3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
        it('should uncheck all nested checklist items and update wrapper title', async () => {
            await testEditor(BasicEditor, {
                removeCheckIds: true,
                contentBefore: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li class="o_checked">3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li class="o_checked">3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
                stepFunction: async editor => {
                    const lis = editor.editable.querySelectorAll(
                        '.o_checklist > li:not([class^="oe-nested"])',
                    );
                    const li = lis[1];
                    await click(li, { clientX: li.getBoundingClientRect().left - 10 });
                },
                contentAfter: unformat(`
                    <ul class="o_checklist">
                        <li class="o_checked">3</li>
                        <li class="oe-nested">
                            <ul class="o_checklist">
                                <li>3.1</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">3.2.1</li>
                                        <li class="o_checked">3.2.2</li>
                                    </ul>
                                </li>
                            </ul>
                        </li>
                    </ul>`),
            });
        });
    });
    describe('VDocument', () => {
        describe('deleteForward', () => {
            describe('Selection collapsed', () => {
                describe('Basic', () => {
                    it('should do nothing', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>[]<br></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]</li></ul></li></ul>',
                        });
                    });
                    it('should delete the first character in a list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc</li><li>[]defg</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc</li><li>[]efg</li></ul>',
                        });
                    });
                    it('should delete a character within a list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc</li><li>de[]fg</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc</li><li>de[]g</li></ul>',
                        });
                    });
                    it('should delete the last character in a list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc</li><li>def[]g</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc</li><li>def[]</li></ul>',
                        });
                    });
                    it('should remove the only character in a list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>[]a</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li><p>[]a</p></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                    it('should merge a list item with its next list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc[]</li><li>def</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc[]def</li></ul>',
                        });
                        // With another list item before.
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc</li><li>def[]</li><li>ghi</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc</li><li>def[]ghi</li></ul>',
                        });
                        // Where the list item to merge into is empty, with an
                        // empty list item before.
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li><br></li><li>[]<br></li><li>abc</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li><br></li><li>[]abc</li></ul>',
                        });
                    });
                    it('should rejoin sibling lists', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>a[]</li></ul><p>b</p><ul><li>c</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>a[]b</li><li>c</li></ul>',
                        });
                    });
                    it('should rejoin multi-level sibling lists', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                        });
                    });
                    it('should only rejoin same-level lists', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li>c[]</li>
                                    </ol>
                                    <p>d</p>
                                    <ol>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>e</li>
                                            </ol>
                                        </li>
                                        <li>f</li>
                                    </ol>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li>c[]d</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>e</li>
                                            </ol>
                                        </li>
                                        <li>f</li>
                                    </ol>`),
                        });
                    });
                    it('should not convert mixed lists on rejoin', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>a[]</li></ol><p>b</p><ul><li>c</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>a[]b</li></ol><ul><li>c</li></ul>',
                        });
                    });
                    it('should not convert mixed multi-level lists on rejoin', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]</li>
                                            </ul>
                                        </li>
                                    </ol>
                                    <p>c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                            </ul>
                                        </li>
                                    </ol>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                        });
                    });
                    it('should delete the first character in a checklist item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]defg</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]efg</li></ul>',
                        });
                    });
                    it('should delete a character within a checklist item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>de[]fg</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>de[]g</li></ul>',
                        });
                    });
                    it('should delete the last character in a checklist item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]g</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]</li></ul>',
                        });
                    });
                    it('should remove the only character in a checklist', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">[]a</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><p>[]a</p></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                    });
                    it('should merge a checklist item with its next list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc[]</li><li>def</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                        });
                        // With another list item before.
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]</li><li class="o_checked">ghi</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li>def[]ghi</li></ul>',
                        });
                        // Where the list item to merge into is empty, with an
                        // empty list item before.
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li><br></li><li>[]<br></li><li>abc</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li><br></li><li>[]abc</li></ul>',
                        });
                    });
                    it('should rejoin sibling lists', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">a[]</li></ul><p>b</p><ul class="o_checklist"><li class="o_checked">c</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">a[]b</li><li class="o_checked">c</li></ul>',
                        });
                    });
                    it('should rejoin multi-level sibling lists', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b[]</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>c</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b[]c</li>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                        });
                    });
                    it('should only rejoin same-level lists', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">c[]</li>
                                    </ul>
                                    <p>d</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">c[]d</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                        });
                    });
                    it('should not convert mixed lists on rejoin', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">a[]</li></ul><p>b</p><ul><li>c</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul><ul><li>c</li></ul>',
                        });
                    });
                    it('should not convert mixed multi-level lists on rejoin', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li class="o_checked">b[]</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            stepFunction: deleteForward,
                            contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li class="o_checked">b[]c</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                        });
                    });
                });
                describe('Indented', () => {
                    it('should merge an indented list item into a non-indented list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>abc[]</li><li class="oe-nested"><ol><li>def</li><li>ghi</li></ol></li></ol>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter:
                                '<ol><li>abc[]def</li><li class="oe-nested"><ol><li>ghi</li></ol></li></ol>',
                        });
                    });
                    it('should merge a non-indented list item into an indented list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li class="oe-nested"><ul><li>abc[]</li></ul></li><li>def</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul><li class="oe-nested"><ul><li>abc[]def</li></ul></li></ul>',
                        });
                    });
                    it('should merge the only item in an indented list into a non-indented list item and remove the now empty indented list', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>abc[]</li><li class="oe-nested"><ul><li>def</li></ul></li></ul>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<ul><li>abc[]def</li></ul>',
                        });
                    });
                    it('should merge an indented list item into a non-indented list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>abc[]</li><li class="oe-nested"><ul class="o_checklist"><li>def</li><li class="o_checked">ghi</li></ul></li></ul>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter:
                                '<ul class="o_checklist"><li>abc[]def</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
                        });
                    });
                    it('should merge the only item in an indented list into a non-indented list item and remove the now empty indented list', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>abc[]</li><li class="oe-nested"><ul class="o_checklist"><li>def</li></ul></li></ul>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<ul class="o_checklist"><li>abc[]def</li></ul>',
                        });
                    });
                });
                describe('Complex merges', () => {
                    it('should merge a list item into a paragraph', async () => {
                        // Note: Not perfect but consistent with backspace, to change this, we should change backspace
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>ab[]cd</p><ul><li>ef</li><li>gh</li></ul>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter: '<p>ab[]ef</p><ul><li>gh</li></ul>',
                        });
                    });
                    it('should merge a paragraph into a list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>abc[]</li></ul><p>def</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>abc[]def</li></ul>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>abc</li><li><b>de</b>fg[]</li><li><b>hij</b>klm</li><li>nop</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
                        });
                    });
                    it('should merge a paragraph starting with bold text into a list item with ending without formatting', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                        });
                    });
                    it('should merge a paragraph starting with bold text into a list item with ending with italic text', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                        });
                    });
                    it('should merge a checklist item into a paragraph', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<p>ab[]cd</p><ul class="o_checklist"><li class="o_checked">ef</li><li class="o_checked">gh</li></ul>',
                            stepFunction: async editor => {
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                                await deleteForward(editor);
                            },
                            contentAfter:
                                '<p>ab[]ef</p><ul class="o_checklist"><li class="o_checked">gh</li></ul>',
                        });
                    });
                    it('should merge a paragraph into a checklist item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc[]</li></ul><p>def</p>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                        });
                    });
                    it('should treat two blocks in a checklist item (checked/unchecked) as two list items and merge them', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li><h2>def[]</h2><h3>ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            // unchecked folowed by checked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li class="o_checked"><h4>klm</h4></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]</h2><h3>ghi</h3></li><li><h4>klm</h4></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            // checked folowed by unchecked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]</li><li><b>hij</b>klm</li><li>nop</li></ul>',
                            stepFunction: deleteForward,
                            // all checked
                            contentAfter:
                                '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
                        });
                    });
                    it('should merge a bold list item (checked/unchecked) into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]</li><li class="o_checked"><b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                            stepFunction: deleteForward,
                            // all checked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]<b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]</li><li><b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                            stepFunction: deleteForward,
                            // only the removed li are unchecked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]<b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]</li><li class="o_checked"><b>hij</b>klm</li><li>nop</li></ul>',
                            stepFunction: deleteForward,
                            // only the removed li are checked
                            contentAfter:
                                '<ul class="o_checklist"><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
                        });
                    });
                    it('should merge a paragraph starting with bold text into a checklist item with ending without formatting', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]</li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            // kepp checked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                        });
                    });
                    it('should merge a paragraph starting with bold text into a checklist item with ending with italic text', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i></li></ul><p><b>ghi</b>jkl</p>',
                            stepFunction: deleteForward,
                            // kepp checked
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                        });
                    });
                });
                describe('Complex merges with some containers parsed in list item', () => {
                    it('should treat two blocks in a list item and keep the blocks', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><p>abc</p></li><li><p>def[]</p><p>ghi</p></li><li><p>klm</p></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul><li><p>abc</p></li><li><p>def[]ghi</p></li><li><p>klm</p></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><h1>abc</h1></li><li><h2>def[]</h2><h3>ghi</h3></li><li><h4>klm</h4></li></ul>',
                            stepFunction: deleteForward,
                            // Paragraphs in list items are treated as nonsense.
                            // Headings aren't, as they do provide extra information.
                            contentAfter:
                                '<ul><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>',
                        });
                    });
                    it('should merge a bold list item (checked/unchecked) into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li><p><b>de</b>fg[]</p><p><b>hij</b>klm</p></li><li class="o_checked"><p>nop</p></li></ul>',
                            stepFunction: deleteForward,
                            // Two paragraphs in a checklist item = Two list items.
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li><p><b>de</b>fg[]<b>hij</b>klm</p></li><li class="o_checked"><p>nop</p></li></ul>',
                        });
                    });
                    it('should treat two blocks in a checklist item and keep the blocks', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li><p>def[]</p><p>ghi</p></li><li class="o_checked"><p>klm</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li><p>def[]ghi</p></li><li class="o_checked"><p>klm</p></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]</h2><h3>ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]ghi</h2></li><li class="o_checked"><h4>klm</h4></li></ul>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul><li><p>abc</p></li><li><p><b>de</b>fg[]</p><p><b>hij</b>klm</p></li><li><p>nop</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul><li><p>abc</p></li><li><p><b>de</b>fg[]<b>hij</b>klm</p></li><li><p>nop</p></li></ul>',
                        });
                    });
                });
            });
            describe('Selection not collapsed', () => {
                // Note: All tests on ordered lists should be duplicated
                // with unordered lists and checklists, and vice versae.
                describe('Ordered', () => {
                    it('should delete text within a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab[cd]ef</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]ef</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab]cd[ef</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]ef</li></ol>',
                        });
                    });
                    it('should delete all the text in a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>[abc]</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>[]<br></li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>]abc[</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>[]<br></li></ol>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab[cd</li><li>ef]gh</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab]cd</li><li>ef[gh</li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>ab[cd</li><li class="oe-nested"><ol><li>ef]gh</li></ol></li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>ab]cd</li><li class="oe-nested"><ol><li>ef[gh</li></ol></li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                    });
                    it('should delete a list', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[</p><ol><li><p>def]</p></li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc]</p><ol><li><p>def[</p></li></ol>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display:block;"><ol><li>fg</li><li>h]i</li><li>jk</li></ol></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display:block;"><ol><li>jk</li></ol></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display:block;"><ol><li>fg</li><li>h[i</li><li>jk</li></ol></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display:block;"><ol><li>jk</li></ol></custom-block>',
                        });
                    });
                });
                describe('Unordered', () => {
                    it('should delete text within a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab[cd]ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]ef</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab]cd[ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]ef</li></ul>',
                        });
                    });
                    it('should delete all the text in a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>[abc]</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>]abc[</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab[cd</li><li>ef]gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab]cd</li><li>ef[gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete a list', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[</p><ul><li><p>def]</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc]</p><ul><li><p>def[</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
                        });
                    });
                });
                describe('Checklist', () => {
                    it('should delete text within a checklist item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd]ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<ul class="o_checklist"><li>ab[cd]ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]ef</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd[ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<ul class="o_checklist"><li>ab]cd[ef</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]ef</li></ul>',
                        });
                    });
                    it('should delete all the text in a checklist item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">[abc]</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<ul class="o_checklist"><li>[abc]</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">]abc[</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore: '<ul class="o_checklist"><li>]abc[</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li>ef]gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab[cd</li><li>ef]gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li>ef[gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab]cd</li><li>ef[gh</li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li>ef]gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            // The indented list's parent gets rendered as
                            // checked because its only child is checked.
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            // The indented list's parent gets rendered as
                            // checked because its only child is checked. When
                            // we remove that child, the checklist gets
                            // unchecked because it becomes independant again.
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li>ef[gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            // The indented list's parent gets rendered as
                            // checked because its only child is checked.
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li>ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                            stepFunction: deleteForward,
                            // The indented list's parent gets rendered as
                            // checked because its only child is checked. When
                            // we remove that child, the checklist gets
                            // unchecked because it becomes independant again.
                            contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete a checklist', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>abc[</p><ul class="o_checklist"><li><p>def]</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>abc]</p><ul class="o_checklist"><li><p>def[</p></li></ul>',
                            stepFunction: deleteForward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">fg</li><li>h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li class="o_checked">h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li class="o_checked">h[i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul class="o_checklist"><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteForward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul class="o_checklist"><li>jk</li></ul></custom-block>',
                        });
                    });
                });
                describe('Mixed', () => {
                    describe('Ordered to unordered', () => {
                        it('should delete across an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>ab[cd</li></ol><ul><li>ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>ab]cd</li></ol><ul><li>ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                        });
                        it('should delete across an ordered list item and an unordered list item within an ordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                        });
                        it('should delete an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul><li>cd</li></ul><ol><li>ef]</li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul><li>cd</li></ul><ol><li>ef[</li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Unordered to ordered', () => {
                        it('should delete across an unordered list and an ordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>ab[cd</li></ul><ol><li>ef]gh</li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>ab]cd</li></ul><ol><li>ef[gh</li></ol>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an unordered list item and an ordered list item within an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li><li class="oe-nested"><ol><li>ef]gh</li></ol></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li><li class="oe-nested"><ol><li>ef[gh</li></ol></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ol><li>cd</li></ol><ul><li>ef]</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ol><li>cd</li></ol><ul><li>ef[</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Checklist to unordered', () => {
                        it('should delete across an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li class="o_checked">ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab[cd</li></ul><ul><li class="o_checked">ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li class="o_checked">ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab]cd</li></ul><ul><li class="o_checked">ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an checklist list item and an unordered list item within an checklist list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="oe-nested"><ul><li class="o_checked">ef]gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="oe-nested"><ul><li class="o_checked">ef[gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul class="o_checklist"><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Unordered to checklist', () => {
                        it('should delete across an unordered list and an checklist list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li></ul><ul class="o_checklist"><li>ef[gh</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an unordered list item and an checklist list item within an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef]</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef[</li></ul>',
                                stepFunction: deleteForward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                });
            });
        });
        describe('deleteBackward', () => {
            describe('Selection collapsed', () => {
                // Note: All tests on ordered lists should be duplicated
                // with unordered lists and checklists, and vice versae.
                describe('Ordered', () => {
                    describe('Basic', () => {
                        it('should convert to paragraph', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><br>[]</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ol><li>[]abc</li></ol></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]abc</li></ol>',
                            });
                        });
                        it('should delete the first character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li><li>d[]efg</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc</li><li>[]efg</li></ol>',
                            });
                        });
                        it('should delete a character within a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li><li>de[]fg</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc</li><li>d[]fg</li></ol>',
                            });
                        });
                        it('should delete the last character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li><li>defg[]</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc</li><li>def[]</li></ol>',
                            });
                        });
                        it('should remove the only character in a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>a[]</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]<br></li></ol>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><p>a[]</p></li></ol>',
                                stepFunction: deleteBackward,
                                // Paragraphs in list items are treated as nonsense.
                                contentAfter: '<ol><li>[]<br></li></ol>',
                            });
                        });
                        it('should merge a list item with its previous list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li><li>[]def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc[]def</li></ol>',
                            });
                            // With another list item after.
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li><li>[]def</li><li>ghi</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc[]def</li><li>ghi</li></ol>',
                            });
                            // Where the list item to merge into is empty, with an
                            // empty list item before.
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><br></li><li><br></li><li>[]abc</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li><br></li><li>[]abc</li></ol>',
                            });
                        });
                        it('should rejoin sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>a</li></ol><p>[]b</p><ol><li>c</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>a[]b</li><li>c</li></ol>',
                            });
                        });
                        it('should rejoin multi-level sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            });
                        });
                        it('should only rejoin same-level lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li>c</li>
                                    </ol>
                                    <p>[]d</p>
                                    <ol>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>e</li>
                                            </ol>
                                        </li>
                                        <li>f</li>
                                    </ol>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li>c[]d</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>e</li>
                                            </ol>
                                        </li>
                                        <li>f</li>
                                    </ol>`),
                            });
                        });
                        it('should not convert mixed lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>a</li></ol><p>[]b</p><ul><li>c</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>a[]b</li></ol><ul><li>c</li></ul>',
                            });
                        });
                        it('should not convert mixed multi-level lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                    </ol>
                                    <p>[]c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                            </ul>
                                        </li>
                                    </ol>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            });
                        });
                    });
                    describe('Indented', () => {
                        it('should merge an indented list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>[]def</li><li>ghi</li></ol></li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ol><li>abc[]def</li><li class="oe-nested"><ol><li>ghi</li></ol></li></ol>',
                            });
                        });
                        it('should merge a non-indented list item into an indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ol><li>abc</li></ol></li><li>[]def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ol><li class="oe-nested"><ol><li>abc[]def</li></ol></li></ol>',
                            });
                        });
                        it('should merge the only item in an indented list into a non-indented list item and remove the now empty indented list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>[]def</li></ol></li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li>abc[]def</li></ol>',
                            });
                        });
                        it('should outdent a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ol><li>[]abc</li></ol></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]abc</li></ol>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>abc</p><ol><li class="oe-nested"><ol><li>[]def</li></ol></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ol><li>[]def</li></ol>',
                            });
                        });
                        it.skip('should outdent while nested within a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li><div>abc</div></li><li><div><div>[]def</div></div></li></ol>',
                                stepFunction: deleteBackward,
                                // TODO: the additional DIV used to represent
                                // the LI. The ideal result would be:
                                //contentAfter: '<ol><li><div>abc</div></li></ol><div><div>[]def</div></div>',
                                contentAfter:
                                    '<ol><li><div>abc</div></li></ol><div><div><div>[]def</div></div></div>',
                            });
                            // With a div before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<div>abc</div><ol><li><div><div>[]def</div></div></li></ol>',
                                stepFunction: deleteBackward,
                                // TODO: the additional DIV used to represent
                                // the LI. The ideal result would be:
                                // contentAfter: '<div>abc</div><div><div>[]def</div></div>',
                                contentAfter:
                                    '<div>abc</div><div><div><div>[]def</div></div></div>',
                            });
                        });
                        it('should not outdent while nested within a list item if the list is unbreakable', async () => {
                            // Only one LI.
                            await testEditor(BasicEditor, {
                                contentBefore: '<p>abc</p><ol t="1"><li>[]def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ol t="1"><li>[]def</li></ol>',
                            });
                            // First LI.
                            // await testEditor(BasicEditor, {
                            //     contentBefore:
                            //         '<ol t="1"><li><div><div>[]abc</div></div></li><li>def</li></ol>',
                            //     stepFunction: deleteBackward,
                            //     contentAfter:
                            //         '<ol t="1"><li><div><div>[]abc</div></div></li><li>def</li></ol>',
                            // });
                            // // In the middle.
                            // await testEditor(BasicEditor, {
                            //     contentBefore:
                            //         '<ol><li><div>abc</div></li><li t="1"><div><div>[]def</div></div></li><li>ghi</li></ol>',
                            //     stepFunction: deleteBackward,
                            //     contentAfter:
                            //         '<ol><li><div>abc</div></li><li t="1"><div><div>[]def</div></div></li><li>ghi</li></ol>',
                            // });
                            // // Last LI.
                            // await testEditor(BasicEditor, {
                            //     contentBefore:
                            //         '<ol><li>abc</li><li t="1"><div><div>[]def</div></div></li></ol>',
                            //     stepFunction: deleteBackward,
                            //     contentAfter:
                            //         '<ol><li>abc</li><li t="1"><div><div>[]def</div></div></li></ol>',
                            // });
                            // // With a div before the list:
                            // await testEditor(BasicEditor, {
                            //     contentBefore:
                            //         '<div>abc</div><ol><li>def</li><li t="1"><div><div>[]ghi</div></div></li><li>jkl</li></ol>',
                            //     stepFunction: deleteBackward,
                            //     contentAfter:
                            //         '<div>abc</div><ol><li>def</li><li t="1"><div><div>[]ghi</div></div></li><li>jkl</li></ol>',
                            // });
                        });
                        it('should outdent an empty list item within a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>[]<br></li><li><br></li></ol></li><li>def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ol><li>abc</li><li>[]<br></li><li class="oe-nested"><ol><li><br></li></ol></li><li>def</li></ol>',
                            });
                        });
                        it('should outdent an empty list within a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>[]<br></li></ol></li><li>def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc</li><li>[]<br></li><li>def</li></ol>',
                            });
                        });
                        it('should outdent an empty list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ol><li><br>[]</li></ol></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]<br></li></ol>',
                            });
                        });
                        it("should outdent a list to the point that it's a paragraph", async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>[]<br></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore: '<p><br></p><ol><li>[]<br></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p><br></p><p>[]<br></p>',
                            });
                        });
                    });
                    describe('Complex merges', () => {
                        it('should merge a list item into a paragraph', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<p>abcd</p><ol><li>ef[]gh</li><li>ij</li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<p>abcd[]gh</p><ol><li>ij</li></ol>',
                            });
                        });
                        it('should merge a paragraph into a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc</li></ol><p>[]def</p>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc[]def</li></ol>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending without formatting', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li><i>abc</i>def</li></ol><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li><i>abc</i>def[]<b>ghi</b>jkl</li></ol>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending with italic text', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li><b>abc</b><i>def</i></li></ol><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ol><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ol>',
                            });
                        });
                    });
                });
                describe('Unordered', () => {
                    describe('Basic', () => {
                        it('should do nothing', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><br>[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]abc</li></ul>',
                            });
                        });
                        it('should delete the first character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li><li>d[]efg</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>[]efg</li></ul>',
                            });
                        });
                        it('should delete a character within a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li><li>de[]fg</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>d[]fg</li></ul>',
                            });
                        });
                        it('should delete the last character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li><li>defg[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>def[]</li></ul>',
                            });
                        });
                        it('should remove the only character in a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>a[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]<br></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><p>a[]</p></li></ul>',
                                stepFunction: deleteBackward,
                                // Paragraphs in list items are treated as nonsense.
                                contentAfter: '<ul><li>[]<br></li></ul>',
                            });
                        });
                        it('should merge a list item with its previous list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc[]def</li></ul>',
                            });
                            // With another list item after.
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li><li>[]def</li><li>ghi</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc[]def</li><li>ghi</li></ul>',
                            });
                            // Where the list item to merge into is empty, with an
                            // empty list item before.
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><br></li><li><br></li><li>[]abc</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li><br></li><li>[]abc</li></ul>',
                            });
                        });
                        it('should rejoin sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>a</li></ul><p>[]b</p><ul><li>c</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>a[]b</li><li>c</li></ul>',
                            });
                        });
                        it('should rejoin multi-level sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            });
                        });
                        it('should only rejoin same-level lists', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                        <li>c</li>
                                    </ul>
                                    <p>[]d</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>e</li>
                                            </ul>
                                        </li>
                                        <li>f</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                        <li>c[]d</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>e</li>
                                            </ul>
                                        </li>
                                        <li>f</li>
                                    </ul>`),
                            });
                        });
                        it('should not convert mixed lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>a</li></ul><p>[]b</p><ol><li>c</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>a[]b</li></ul><ol><li>c</li></ol>',
                            });
                        });
                        it('should not convert mixed multi-level lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ol>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ol>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b[]c</li>
                                            </ol>
                                        </li>
                                    </ul>
                                    <ol>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ol>`),
                            });
                        });
                    });
                    describe('Indented', () => {
                        it('should merge an indented list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>abc</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>[]def</li>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ul>`),
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: unformat(`
                                    <ul>
                                        <li>abc[]def</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ul>`),
                            });
                        });
                        it('should merge a non-indented list item into an indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li class="oe-nested"><ul><li>abc[]def</li></ul></li></ul>',
                            });
                        });
                        it('should merge the only item in an indented list into a non-indented list item and remove the now empty indented list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>abc[]def</li></ul>',
                            });
                        });
                        it('should outdent a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]abc</li></ul>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>abc</p><ul><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ul><li>[]def</li></ul>',
                            });
                        });
                        it('should outdent an empty list item within a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li>abc</li><li>[]<br></li><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty list within a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul><li>[]<br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>[]<br></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul><li><br>[]</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]<br></li></ul>',
                            });
                        });
                        it("should outdent a list to the point that it's a paragraph", async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>[]<br></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore: '<p><br></p><ul><li>[]<br></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p><br></p><p>[]<br></p>',
                            });
                        });
                    });
                    describe('Complex merges', () => {
                        it('should merge a list item into a paragraph', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<p>abcd</p><ul><li>ef[]gh</li><li>ij</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<p>abcd[]gh</p><ul><li>ij</li></ul>',
                            });
                        });
                        it('should merge a paragraph into a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc</li></ul><p>[]def</p>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc[]def</li></ul>',
                            });
                        });
                        it('should merge a bold list item into a non-formatted list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li><b>de</b>fg</li><li><b>[]hij</b>klm</li><li>nop</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li>abc</li><li><b>de</b>fg[]<b>hij</b>klm</li><li>nop</li></ul>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending without formatting', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><i>abc</i>def</li></ul><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending with italic text', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><b>abc</b><i>def</i></li></ul><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                            });
                        });
                    });
                });
                describe('Checklist', () => {
                    describe('Basic', () => {
                        it('should remove the list and turn into p', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul class="o_checklist"><li><br>[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><br>[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">[]abc</li></ul>',
                            });
                        });
                        it('should delete the first character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">d[]efg</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]efg</li></ul>',
                            });
                        });
                        it('should delete a character within a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">de[]fg</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">d[]fg</li></ul>',
                            });
                        });
                        it('should delete the last character in a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">defg[]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">def[]</li></ul>',
                            });
                        });
                        it('should remove the only character in a list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">a[]</li></ul>',
                                stepFunction: deleteBackward,
                                // keep checked because contains the paragraph
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><p>a[]</p></li></ul>',
                                stepFunction: deleteBackward,
                                // Paragraphs in list items are treated as nonsense.
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                            });
                        });
                        it('should merge a list item with its previous list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>abc</li><li class="o_checked">[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul class="o_checklist"><li>abc[]def</li></ul>',
                            });
                            // With another list item after.
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li><li class="o_checked">ghi</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li><li>ghi</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li><li>ghi</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]def</li><li class="o_checked">ghi</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li><li class="o_checked">ghi</li></ul>',
                            });
                            // Where the list item to merge into is empty, with an
                            // empty list item before.
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li><br></li><li><br></li><li class="o_checked">[]abc</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li><br></li><li>[]abc</li></ul>',
                            });
                        });
                        it('should rejoin sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">a</li></ul><p>[]b</p><ul class="o_checklist"><li class="o_checked">c</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">a[]b</li><li class="o_checked">c</li></ul>',
                            });
                        });
                        it('should rejoin multi-level sibling lists', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">d</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b[]c</li>
                                                <li class="o_checked">d</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">e</li>
                                    </ul>`),
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b[]c</li>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">e</li>
                                    </ul>`),
                            });
                        });
                        it('should only rejoin same-level lists', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">c</li>
                                    </ul>
                                    <p>[]d</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">c[]d</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li>c</li>
                                    </ul>
                                    <p>[]d</p>
                                    <ul class="o_checklist">
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">b</li>
                                            </ul>
                                        </li>
                                        <li>c[]d</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">e</li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">f</li>
                                    </ul>`),
                            });
                        });
                        it('should not convert mixed lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">a</li></ul><p>[]b</p><ul><li>c</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul><ul><li>c</li></ul>',
                            });
                        });
                        it('should not convert mixed multi-level lists on rejoin', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <p>[]c</p>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">a</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>b[]c</li>
                                            </ul>
                                        </li>
                                    </ul>
                                    <ul>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>d</li>
                                            </ul>
                                        </li>
                                        <li>e</li>
                                    </ul>`),
                            });
                        });
                    });
                    describe('Indented', () => {
                        it('should merge an indented list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
                            });
                        });
                        it('should merge a non-indented list item into an indented list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li><li class="o_checked">[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]def</li></ul></li></ul>',
                            });
                        });
                        it('should merge the only item in an indented list into a non-indented list item and remove the now empty indented list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                            });
                        });
                        it('should outdent a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">[]abc</li></ul>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p>abc</p><ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<p>abc</p><ul class="o_checklist"><li class="o_checked">[]def</li></ul>',
                            });
                        });
                        it.skip('should outdent while nested within a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li><li class="o_checked"><div><div>[]def</div></div></li></ul>',
                                stepFunction: deleteBackward,
                                // TODO: the additional DIV used to represent
                                // the LI. The ideal result would be:
                                // contentAfter: '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li></ul><div><div>[]def</div></div>',
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked"><div>abc</div></li></ul><div><div><div>[]def</div></div></div>',
                            });
                            // With a div before the list:
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<div>abc</div><ul class="o_checklist"><li class="o_checked"><div><div>[]def</div></div></li></ul>',
                                stepFunction: deleteBackward,
                                // TODO: the additional DIV used to represent
                                // the LI. The ideal result would be:
                                // contentAfter: '<div>abc</div><div><div>[]def</div></div>',
                                contentAfter:
                                    '<div>abc</div><div><div><div>[]def</div></div></div>',
                            });
                        });
                        it('should outdent an empty list item within a list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li>abc</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>[]<br></li>
                                                <li><br></li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">def</li>
                                    </ul>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li>abc</li>
                                        <li>[]<br></li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li><br></li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">def</li>
                                    </ul>`),
                            });
                        });
                        it('should outdent an empty list within a list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li>[]<br></li></ul></li><li class="o_checked">def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li>abc</li><li>[]<br></li><li class="o_checked">def</li></ul>',
                            });
                        });
                        it('should outdent an empty list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul class="o_checklist"><li class="o_checked"><br>[]</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                            });
                        });
                        it("should outdent a list to the point that it's a paragraph", async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: '<ul class="o_checklist"><li>[]<br></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>[]<br></p>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p><br></p><ul class="o_checklist"><li>[]<br></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p><br></p><p>[]<br></p>',
                            });
                        });
                    });
                    describe('Complex merges', () => {
                        it('should merge a list item into a paragraph', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p>abcd</p><ul class="o_checklist"><li class="o_checked">ef[]gh</li><li class="o_checked">ij</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<p>abcd[]gh</p><ul class="o_checklist"><li class="o_checked">ij</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p>abcd</p><ul class="o_checklist"><li>ef[]gh</li><li class="o_checked">ij</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<p>abc[]gh</p><ul class="o_checklist"><li class="o_checked">ij</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p>abcd</p><ul class="o_checklist"><li class="o_checked">ef[]gh</li><li>ij</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<p>abc[]gh</p><ul class="o_checklist"><li>ij</li></ul>',
                            });
                        });
                        it('should merge a paragraph into a list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]def</p>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                            });
                        });
                        it('should merge a bold list item into a non-formatted list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg</li><li class="o_checked"><b>[]hij</b>klm</li><li class="o_checked">nop</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="o_checked"><b>de</b>fg[]<b>hij</b>klm</li><li class="o_checked">nop</li></ul>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending without formatting', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def</li></ul><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked"><i>abc</i>def[]<b>ghi</b>jkl</li></ul>',
                            });
                        });
                        it('should merge a paragraph starting with bold text into a list item with ending with italic text', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def</i></li></ul><p><b>[]ghi</b>jkl</p>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked"><b>abc</b><i>def[]</i><b>ghi</b>jkl</li></ul>',
                            });
                        });
                    });
                });
                describe('Mixed', () => {
                    describe('Ordered to unordered', () => {
                        it('should merge an ordered list into an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>a</li></ul><ol><li>[]b</li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>a</li></ul><ol><li><p>[]b</p></li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><p>a</p></li></ul><ol><li>[]b</li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li><p>a[]b</p></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><p>a</p></li></ul><ol><li><p>[]b</p></li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li><p>a[]b</p></li></ul>',
                            });
                        });
                        it('should merge an ordered list item that is in an unordered list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ol><li>[]def</li><li>ghi</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li>abc</li><li>[]def</li><li class="oe-nested"><ol><li>ghi</li></ol></li></ul>',
                            });
                        });
                        it('should merge an ordered list item into an unordered list item that is in the same ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ol><li class="oe-nested"><ul><li>abc[]def</li></ul></li></ol>',
                            });
                        });
                        it('should merge the only item in an ordered list that is in an unordered list into a list item that is in the same unordered list, and remove the now empty ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ol><li>[]def</li></ol></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>abc[]def</li></ul>',
                            });
                        });
                        it('should outdent an ordered list item that is within a unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ol><li>[]abc</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]abc</li></ul>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>abc</p><ul><li class="oe-nested"><ol><li>[]def</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ul><li>[]def</li></ul>',
                            });
                        });
                        it('should outdent an empty ordered list item within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ol><li>[]<br></li><li><br></li></ol></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li>abc</li><li>[]<br></li><li class="oe-nested"><ol><li><br></li></ol></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty ordered list within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ol><li>[]<br></li></ol></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>[]<br></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty ordered list within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ol><li><br>[]</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]<br></li></ul>',
                            });
                        });
                    });
                    describe('Unordered to ordered', () => {
                        it('should merge an unordered list into an ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>a</li></ol><ul><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li>a[]b</li></ol>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>a</li></ol><ul><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li>a[]b</li></ol>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><p>a</p></li></ol><ul><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li><p>a[]b</p></li></ol>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li><p>a</p></li></ol><ul><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li><p>a[]b</p></li></ol>',
                            });
                        });
                        it('should merge an unordered list item that is in an ordered list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ol>
                                        <li>abc</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>[]def</li>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ol>`),
                                stepFunction: deleteBackward,
                                contentAfter: unformat(`
                                    <ol>
                                        <li>abc</li>
                                        <li>[]def</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ol>`),
                            });
                        });
                        it('should merge an unordered list item into an ordered list item that is in the same unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ol><li>abc</li></ol></li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li class="oe-nested"><ol><li>abc[]def</li></ol></li></ul>',
                            });
                        });
                        it('should merge the only item in an unordered list that is in an ordered list into a list item that is in the same ordered list, and remove the now empty unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ul><li>[]def</li></ul></li></ol>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ol><li>abc[]def</li></ol>',
                            });
                        });
                        it('should outdent an unordered list item that is within a ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ul><li>[]abc</li></ul></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]abc</li></ol>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>abc</p><ol><li class="oe-nested"><ul><li>[]def</li></ul></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ol><li>[]def</li></ol>',
                            });
                        });
                        it('should outdent an empty unordered list item within an ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ol><li>abc</li><li>[]<br></li><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ol>',
                            });
                        });
                        it('should outdent an empty unordered list within an ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ul><li>[]<br></li></ul></li><li>def</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>abc</li><li>[]<br></li><li>def</li></ol>',
                            });
                        });
                        it('should outdent an empty unordered list within an ordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="oe-nested"><ul><li><br>[]</li></ul></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>[]<br></li></ol>',
                            });
                        });
                    });
                    describe('Checklist to unordered', () => {
                        it('should merge an checklist list into an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>a</li></ul><ul class="o_checklist"><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>a</li></ul><ul class="o_checklist"><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><p>a</p></li></ul><ul class="o_checklist"><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li><p>a[]b</p></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><p>a</p></li></ul><ul class="o_checklist"><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li><p>a[]b</p></li></ul>',
                            });
                        });
                        it('should merge an checklist list item that is in an unordered list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li><li class="o_checked">ghi</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ul><li>abc[]def</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ghi</li></ul></li></ul>',
                            });
                        });
                        it('should merge an checklist list item into an unordered list item that is in the same checklist list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul><li>abc</li></ul></li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul><li>abc[]def</li></ul></li></ul>',
                            });
                        });
                        it('should merge the only item in an checklist list that is in an unordered list into a checklist item that is in the same unordered list, and remove the now empty checklist list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: '<ul><li>abc[]def</li></ul>',
                            });
                        });
                        it('should outdent an checklist list item that is within a unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li class="o_checked">[]abc</li></ul>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>abc</p><ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">[]def</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>abc</p><ul><li class="o_checked">[]def</li></ul>',
                            });
                        });
                        it('should outdent an empty checklist list item within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li>abc</li><li>[]<br></li><li class="oe-nested"><ul class="o_checklist"><li><br></li></ul></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty checklist list within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li>[]<br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>abc</li><li>[]<br></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty checklist list within an unordered list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul class="o_checklist"><li><br>[]</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>[]<br></li></ul>',
                            });
                        });
                    });
                    describe('Unordered to checklist', () => {
                        it('should merge an unordered list into an checklist list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">a</li></ul><ul><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">a</li></ul><ul><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                // Paragraphs in list items are treated as nonsense.
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">a[]b</li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><p>a</p></li></ul><ul><li>[]b</li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                // Paragraphs in list items are kept unless empty
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked"><p>a[]b</p></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><p>a</p></li></ul><ul><li><p>[]b</p></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                // Paragraphs in list items are kept unless empty
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked"><p>a[]b</p></li></ul>',
                            });
                        });
                        it('should merge an unordered list item that is in an checklist list item into a non-indented list item', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">abc</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>[]def</li>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ul>`),
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">abc[]def</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>ghi</li>
                                            </ul>
                                        </li>
                                    </ul>`),
                            });
                        });
                        it('should merge an unordered list item into an checklist list item that is in the same unordered list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc</li></ul></li><li>[]def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">abc[]def</li></ul></li></ul>',
                            });
                        });
                        it('should merge the only item in an unordered list that is in an checklist list into a checklist item that is in the same checklist list, and remove the now empty unordered list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                                stepFunction: async editor => {
                                    await deleteBackward(editor);
                                    await deleteBackward(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]def</li></ul>',
                            });
                        });
                        it('should outdent an unordered list item that is within a checklist list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul><li>[]abc</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul class="o_checklist"><li>[]abc</li></ul>',
                            });
                            // With a paragraph before the list:
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<p>abc</p><ul class="o_checklist"><li class="oe-nested"><ul><li>[]def</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<p>abc</p><ul class="o_checklist"><li>[]def</li></ul>',
                            });
                        });
                        it('should outdent an empty unordered list item within an checklist list (o_checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul><li>[]<br></li><li><br></li></ul></li><li class="o_checked">def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]<br></li><li class="oe-nested"><ul><li><br></li></ul></li><li class="o_checked">def</li></ul>',
                            });
                        });
                        it('should outdent an empty unordered list item within an checklist list (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>abc</li><li class="oe-nested"><ul><li>[]<br></li><li><br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li>abc</li><li>[]<br></li><li class="oe-nested"><ul><li><br></li></ul></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty unordered list within an checklist list (checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul><li>[]<br></li></ul></li><li class="o_checked">def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]<br></li><li class="o_checked">def</li></ul>',
                            });
                        });
                        it('should outdent an empty unordered list within an checklist list (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>abc</li><li class="oe-nested"><ul><li>[]<br></li></ul></li><li>def</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li>abc</li><li>[]<br></li><li>def</li></ul>',
                            });
                        });
                        it('should outdent an empty unordered list within an otherwise empty checklist list', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="oe-nested"><ul><li><br>[]</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul class="o_checklist"><li>[]<br></li></ul>',
                            });
                        });
                    });
                });
                describe('Complex merges with some containers parsed in list item', () => {
                    it('should treat two blocks in a list item and keep blocks', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li><p>abc</p></li><li><p>def</p><p>[]ghi</p></li><li><p>klm</p></li></ol>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ol><li><p>abc</p></li><li><p>def[]ghi</p></li><li><p>klm</p></li></ol>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li><h1>abc</h1></li><li><h2>def</h2><h3>[]ghi</h3></li><li><h4>klm</h4></li></ol>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            // Headings aren't, as they do provide extra information.
                            contentAfter:
                                '<ol><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ol>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li><p>abc</p></li><li><p><b>de</b>fg</p><p><b>[]hij</b>klm</p></li><li><p>nop</p></li></ol>',
                            stepFunction: deleteBackward,
                            // Two paragraphs in a list item = Two list items.
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ol><li><p>abc</p></li><li><p><b>de</b>fg[]<b>hij</b>klm</p></li><li><p>nop</p></li></ol>',
                        });
                    });
                    it('should treat two blocks in a list item and keep blocks', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><p>abc</p></li><li><p>def</p><p>[]ghi</p></li><li><p>klm</p></li></ul>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul><li><p>abc</p></li><li><p>def[]ghi</p></li><li><p>klm</p></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><h1>abc</h1></li><li><h2>def</h2><h3>[]ghi</h3></li><li><h4>klm</h4></li></ul>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            // Headings aren't, as they do provide extra information.
                            contentAfter:
                                '<ul><li><h1>abc</h1></li><li><h2>def[]ghi</h2></li><li><h4>klm</h4></li></ul>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li><p>abc</p></li><li><p><b>de</b>fg</p><p><b>[]hij</b>klm</p></li><li><p>nop</p></li></ul>',
                            stepFunction: deleteBackward,
                            // Two paragraphs in a list item = Two list items.
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul><li><p>abc</p></li><li><p><b>de</b>fg[]<b>hij</b>klm</p></li><li><p>nop</p></li></ul>',
                        });
                    });
                    it('should treat two blocks in a list item and keep blocks', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li class="o_checked"><p>def</p><p>[]ghi</p></li><li class="o_checked"><p>klm</p></li></ul>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li class="o_checked"><p>def[]ghi</p></li><li class="o_checked"><p>klm</p></li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def</h2><h3>[]ghi</h3></li><li class="o_checked"><h4>klm</h4></li></ul>',
                            stepFunction: deleteBackward,
                            // Paragraphs in list items are treated as nonsense.
                            // Headings aren't, as they do provide extra information.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><h1>abc</h1></li><li class="o_checked"><h2>def[]ghi</h2></li><li class="o_checked"><h4>klm</h4></li></ul>',
                        });
                    });
                    it('should merge a bold list item into a non-formatted list item', async () => {
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li class="o_checked"><p><b>de</b>fg</p><p><b>[]hij</b>klm</p></li><li class="o_checked"><p>nop</p></li></ul>',
                            stepFunction: deleteBackward,
                            // Two paragraphs in a list item = Two list items.
                            // Paragraphs in list items are treated as nonsense.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked"><p>abc</p></li><li class="o_checked"><p><b>de</b>fg[]<b>hij</b>klm</p></li><li class="o_checked"><p>nop</p></li></ul>',
                        });
                    });
                });
            });
            describe('Selection not collapsed', () => {
                // Note: All tests on ordered lists should be duplicated
                // with unordered lists and checklists, and vice versae.
                describe('Ordered', () => {
                    it('should delete text within a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab[cd]ef</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]ef</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab]cd[ef</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]ef</li></ol>',
                        });
                    });
                    it('should delete all the text in a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>[abc]</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>[]<br></li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>]abc[</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>[]<br></li></ol>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab[cd</li><li>ef]gh</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ol><li>ab]cd</li><li>ef[gh</li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>ab[cd</li><li class="oe-nested"><ol><li>ef]gh</li></ol></li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ol><li>ab]cd</li><li class="oe-nested"><ol><li>ef[gh</li></ol></li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ol><li>ab[]gh</li></ol>',
                        });
                    });
                    it('should delete a list', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[</p><ol><li><p>def]</p></li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc]</p><ol><li><p>def[</p></li></ol>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ol><li>fg</li><li>h]i</li><li>jk</li></ol></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ol><li>jk</li></ol></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ol><li>fg</li><li>h[i</li><li>jk</li></ol></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ol><li>jk</li></ol></custom-block>',
                        });
                    });
                });
                describe('Unordered', () => {
                    it('should delete text within a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab[cd]ef</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]ef</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab]cd[ef</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]ef</li></ul>',
                        });
                    });
                    it('should delete all the text in a list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>[abc]</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>]abc[</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>[]<br></li></ul>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab[cd</li><li>ef]gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<ul><li>ab]cd</li><li>ef[gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<ul><li>ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<ul><li>ab[]gh</li></ul>',
                        });
                    });
                    it('should delete a list', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc[</p><ul><li><p>def]</p></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore: '<p>abc]</p><ul><li><p>def[</p></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a list item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h]i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display: block;"><ul><li>fg</li><li>h[i</li><li>jk</li></ul></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display: block;"><ul><li>jk</li></ul></custom-block>',
                        });
                    });
                });
                describe('Checklist', () => {
                    it('should delete text within a checklist item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd]ef</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd[ef</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]ef</li></ul>',
                        });
                    });
                    it('should delete all the text in a checklist item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">[abc]</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">]abc[</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">[]<br></li></ul>',
                        });
                    });
                    it('should delete across two list items', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="o_checked">ef]gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li>ef]gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="o_checked">ef[gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li>ef[gh</li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                    });
                    it('should delete across an unindented list item and an indented list item', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li>ef]gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            // The indented list cannot be unchecked while its
                            // parent is checked: it gets checked automatically
                            // as a result. So "efgh" gets rendered as checked.
                            // Given that the parent list item was explicitely
                            // set as "checked", that status is preserved.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li>ef[gh</li></ul></li></ul>',
                            stepFunction: deleteBackward,
                            // The indented list cannot be unchecked while its
                            // parent is checked: it gets checked automatically
                            // as a result. So "efgh" gets rendered as checked.
                            // Given that the parent list item was explicitely
                            // set as "checked", that status is preserved.
                            contentAfter:
                                '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                        });
                    });
                    it('should delete a checklist', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>abc[</p><ul class="o_checklist"><li class="o_checked"><p>def]</p></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            contentBefore:
                                '<p>abc]</p><ul class="o_checklist"><li class="o_checked"><p>def[</p></li></ul>',
                            stepFunction: deleteBackward,
                            contentAfter: '<p>abc[]</p>',
                        });
                    });
                    it('should merge the contents of a checklist item within a block into a heading, and leave the rest of its list as it is', async () => {
                        // Forward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a[b</h1><p>de</p><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">fg</li><li class="o_checked">h]i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                        // Backward selection
                        await testEditor(BasicEditor, {
                            removeCheckIds: true,
                            contentBefore:
                                '<h1>a]b</h1><p>de</p><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">fg</li><li class="o_checked">h[i</li><li class="o_checked">jk</li></ul></custom-block>',
                            stepFunction: deleteBackward,
                            contentAfter:
                                '<h1>a[]i</h1><custom-block style="display:block;"><ul class="o_checklist"><li class="o_checked">jk</li></ul></custom-block>',
                        });
                    });
                });
                describe('Mixed', () => {
                    describe('Ordered to unordered', () => {
                        it('should delete across an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>ab[cd</li></ol><ul><li>ef]gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>ab]cd</li></ol><ul><li>ef[gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                        });
                        it('should delete across an ordered list item and an unordered list item within an ordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ol><li>ab[]gh</li></ol>',
                            });
                        });
                        it('should delete an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul><li>cd</li></ul><ol><li>ef]</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul><li>cd</li></ul><ol><li>ef[</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Unordered to ordered', () => {
                        it('should delete across an unordered list and an ordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>ab[cd</li></ul><ol><li>ef]gh</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>ab]cd</li></ul><ol><li>ef[gh</li></ol>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an unordered list item and an ordered list item within an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li><li class="oe-nested"><ol><li>ef]gh</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li><li class="oe-nested"><ol><li>ef[gh</li></ol></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an ordered list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ol><li>cd</li></ol><ul><li>ef]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ol><li>cd</li></ol><ul><li>ef[</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Checklist to unordered', () => {
                        it('should delete across an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li></ul><ul><li>ef]gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li></ul><ul><li>ef[gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an checklist list item and an unordered list item within an checklist list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[cd</li><li class="oe-nested"><ul><li>ef]gh</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab]cd</li><li class="oe-nested"><ul><li>ef[gh</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul><li>cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                    describe('Unordered to checklist', () => {
                        it('should delete across an unordered list and an checklist list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li></ul><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li></ul><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete across an unordered list item and an checklist list item within an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab[cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef]gh</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>ab]cd</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">ef[gh</li></ul></li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<ul><li>ab[]gh</li></ul>',
                            });
                        });
                        it('should delete an checklist list and an unordered list', async () => {
                            // Forward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab[</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef]</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                            // Backward selection
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<p>ab]</p><ul class="o_checklist"><li class="o_checked">cd</li></ul><ul><li>ef[</li></ul>',
                                stepFunction: deleteBackward,
                                contentAfter: '<p>ab[]</p>',
                            });
                        });
                    });
                });
            });
            it('shoud merge list item in the previous breakable sibling', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <p>a[bc</p>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <p>a[]ef</p>
                        <ol>
                            <li>ghi</li>
                        </ol>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <custom-block style="display: block;">
                            <p>a[bc</p>
                        </custom-block>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <custom-block style="display: block;">
                            <p>a[]ef</p>
                        </custom-block>
                        <ol>
                            <li>ghi</li>
                        </ol>`),
                });
            });
            it('shoud not merge list item in the previous unbreakable sibling', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <p class="oe_unbreakable">a[bc</p>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <p class="oe_unbreakable">a[]</p>
                        <p>ef</p>
                        <ol>
                            <li>ghi</li>
                        </ol>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <div class="oe_unbreakable">
                            <p>a[bc</p>
                        </div>
                        <ol>
                            <li>d]ef</li>
                            <li>ghi</li>
                        </ol>`),
                    stepFunction: deleteBackward,
                    contentAfter: unformat(`
                        <div class="oe_unbreakable">
                            <p>a[]</p>
                        </div>
                        <p>ef</p>
                        <ol>
                            <li>ghi</li>
                        </ol>`),
                });
            });
        });
        describe('insertParagraphBreak', () => {
            describe('Selection collapsed', () => {
                describe('Ordered', () => {
                    describe('Basic', () => {
                        it('should add an empty list item before a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>[]abc</li></ol>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ol><li><br></li><li>[]abc</li></ol>',
                            });
                        });
                        it('should split a list item in two', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>ab[]cd</li></ol>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ol><li>ab</li><li>[]cd</li></ol>',
                            });
                        });
                        it('should add an empty list item after a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc[]</li></ol>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ol><li>abc</li><li>[]<br></li></ol>',
                            });
                        });
                        it('should indent an item in an ordered list and add value (with dom mutations)', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li>c[]</li>
                                    </ol>`),
                                stepFunction: async editor => {
                                    const ol = editor.editable.querySelector('ol');
                                    const li = document.createElement('li');
                                    const br = document.createElement('br');
                                    li.append(br);
                                    ol.insertBefore(li, ol.lastElementChild);
                                    await editor.execCommand('oEnter'); // new line
                                },
                                contentAfter: unformat(`
                                    <ol>
                                        <li>a</li>
                                        <li class="oe-nested">
                                            <ol>
                                                <li>b</li>
                                            </ol>
                                        </li>
                                        <li><br></li>
                                        <li>c</li>
                                        <li>[]<br></li>
                                    </ol>`),
                            });
                        });
                    });
                    describe('Removing items', () => {
                        it('should add an empty list item at the end of a list, then remove it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li>abc[]</li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter: '<ol><li>abc</li></ol><p>[]<br></p>',
                            });
                        });
                        it('should add an empty list item at the end of an indented list, then remove it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>def[]</li></ol></li><li>ghi</li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ol><li>abc</li><li class="oe-nested"><ol><li>def</li></ol></li><li>[]<br></li><li>ghi</li></ol>',
                            });
                        });
                        it('should remove a list with p', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><p>[]<br></p></li></ol>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                        it('should remove a list set to bold', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li><p><b>[]<br></b></p></li></ol>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                    });
                    describe('With attributes', () => {
                        it('should add two list items at the end of a list with a class', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol class="a"><li>abc[]</li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ol class="a"><li>abc</li><li>b</li><li>[]<br></li></ol>',
                            });
                        });
                        it('should add two list items with a class at the end of a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ol><li class="a">abc[]</li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ol><li class="a">abc</li><li class="a">b</li><li class="a">[]<br></li></ol>',
                            });
                        });
                        it('should create list items after one with a block in it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li class="a"><custom-block style="display: block;">abc[]</custom-block></li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ol><li class="a"><custom-block style="display: block;">abc</custom-block></li>' +
                                    '<li class="a"><custom-block style="display: block;">b</custom-block></li>' +
                                    '<li class="a"><custom-block style="display: block;">[]<br></custom-block></li></ol>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ol><li><custom-block class="a" style="display: block;">abc[]</custom-block></li></ol>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ol><li><custom-block class="a" style="display: block;">abc</custom-block></li>' +
                                    '<li><custom-block class="a" style="display: block;">b</custom-block></li>' +
                                    '<li><custom-block class="a" style="display: block;">[]<br></custom-block></li></ol>',
                            });
                        });
                        it('should add two list items with a font at the end of a list within a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li>ab</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li>
                                                    <font style="color: red;">cd[]</font>
                                                </li>
                                            </ul>
                                        </li>
                                        <li>ef</li>
                                    </ul>`),
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter: unformat(`
                                    <ul>
                                        <li>ab</li>
                                        <li class="oe-nested">
                                            <ul>
                                                <li><font style="color: red;">cd</font></li>
                                                <li>b</li>
                                                <li>[]<br></li>
                                            </ul>
                                        </li>
                                        <li>ef</li>
                                    </ul>`),
                            });
                        });
                    });
                });
                describe('Unordered', () => {
                    describe('Basic', () => {
                        it('should add an empty list item before a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>[]abc</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ul><li><br></li><li>[]abc</li></ul>',
                            });
                        });
                        it('should split a list item in two', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>ab[]cd</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ul><li>ab</li><li>[]cd</li></ul>',
                            });
                        });
                        it('should add an empty list item after a list item', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc[]</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<ul><li>abc</li><li>[]<br></li></ul>',
                            });
                        });
                    });
                    describe('Removing items', () => {
                        it('should add an empty list item at the end of a list, then remove it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li>abc[]</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter: '<ul><li>abc</li></ul><p>[]<br></p>',
                            });
                        });
                        it('should add an empty list item at the end of an indented list, then remove it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li>abc</li><li class="oe-nested"><ul><li>def[]</li></ul></li><li>ghi</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul><li>abc</li><li class="oe-nested"><ul><li>def</li></ul></li><li>[]<br></li><li>ghi</li></ul>',
                            });
                        });
                        it('should remove a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><p>[]<br></p></li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                        it('should remove a list set to bold', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li><p><b>[]<br></b></p></li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                    });
                    describe('With attributes', () => {
                        it('should add two list items at the end of a list with a class', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul class="a"><li>abc[]</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul class="a"><li>abc</li><li>b</li><li>[]<br></li></ul>',
                            });
                        });
                        it('should add two list items with a class at the end of a list', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: '<ul><li class="a">abc[]</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul><li class="a">abc</li><li class="a">b</li><li class="a">[]<br></li></ul>',
                            });
                        });
                        it('should create list items after one with a block in it', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li class="a"><custom-block style="display: block;">abc[]</custom-block></li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul><li class="a"><custom-block style="display: block;">abc</custom-block></li>' +
                                    '<li class="a"><custom-block style="display: block;">b</custom-block></li>' +
                                    '<li class="a"><custom-block style="display: block;">[]<br></custom-block></li></ul>',
                            });
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul><li><custom-block class="a" style="display: block;">abc[]</custom-block></li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertText(editor, 'b');
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul><li><custom-block class="a" style="display: block;">abc</custom-block></li>' +
                                    '<li><custom-block class="a" style="display: block;">b</custom-block></li>' +
                                    '<li><custom-block class="a" style="display: block;">[]<br></custom-block></li></ul>',
                            });
                        });
                        it('should keep the list-style when add li', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore: unformat(`
                                    <ul>
                                        <li style="list-style: cambodian;">a[]</li>
                                    </ul>`),
                                stepFunction: insertParagraphBreak,
                                contentAfter: unformat(`
                                <ul>
                                    <li style="list-style: cambodian;">a</li>
                                    <li style="list-style: cambodian;">[]<br></li>
                                </ul>`),
                            });
                        });
                    });
                });
                describe('Checklist', () => {
                    describe('Basic', () => {
                        it('should add an empty list item before a checklist item (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: '<ul class="o_checklist"><li>[]abc</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li><br></li><li>[]abc</li></ul>',
                            });
                        });
                        it('should add an empty list item before a checklist item (checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: '<ul class="o_checklist"><li>[]abc</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li><br></li><li>[]abc</li></ul>',
                            });
                        });
                        it('should split a checklist item in two (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore: '<ul class="o_checklist"><li>ab[]cd</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li>ab</li><li>[]cd</li></ul>',
                            });
                        });
                        it('should split a checklist item in two (checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">ab[]cd</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">ab</li><li>[]cd</li></ul>',
                            });
                        });
                        it('should add an empty list item after a checklist item (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]<br></li></ul>',
                            });
                        });
                        it('should add an empty list item after a checklist item (checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]</li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li>[]<br></li></ul>',
                            });
                        });
                    });
                    describe('Removing items', () => {
                        it('should add an empty list item at the end of a checklist, then remove it', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc[]</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li></ul><p>[]<br></p>',
                            });
                        });
                        it('should add an empty list item at the end of an indented list, then outdent it (checked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">def[]</li></ul></li><li class="o_checked">ghi</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li class="o_checked">abc</li><li class="oe-nested"><ul class="o_checklist"><li class="o_checked">def</li></ul></li><li>[]<br></li><li class="o_checked">ghi</li></ul>',
                            });
                        });
                        it('should add an empty list item at the end of an indented list, then outdent it (unchecked)', async () => {
                            await testEditor(BasicEditor, {
                                removeCheckIds: true,
                                contentBefore:
                                    '<ul class="o_checklist"><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li>def[]</li></ul></li><li class="o_checked">ghi</li></ul>',
                                stepFunction: async editor => {
                                    await insertParagraphBreak(editor);
                                    await insertParagraphBreak(editor);
                                },
                                contentAfter:
                                    '<ul class="o_checklist"><li>abc</li><li class="oe-nested"><ul class="o_checklist"><li>def</li></ul></li><li>[]<br></li><li class="o_checked">ghi</li></ul>',
                            });
                        });
                        it('should remove a checklist', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><p>[]<br></p></li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                        it('should remove a checklist set to bold', async () => {
                            await testEditor(BasicEditor, {
                                contentBefore:
                                    '<ul class="o_checklist"><li class="o_checked"><p><b>[]<br></b></p></li></ul>',
                                stepFunction: insertParagraphBreak,
                                contentAfter: '<p>[]<br></p>',
                            });
                        });
                    });
                    describe('With attributes', () => {
                        describe('after unchecked item', () => {
                            it('should add two list items at the end of a checklist with a class', async () => {
                                await testEditor(BasicEditor, {
                                    contentBefore: '<ul class="checklist a"><li>abc[]</li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="checklist a"><li>abc</li><li>d</li><li>[]<br></li></ul>',
                                });
                            });
                            it('should add two list items with a class at the end of a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li class="a">abc[]</li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li class="a">abc</li><li class="a">d</li><li class="a">[]<br></li></ul>',
                                });
                            });
                            it('should create list items after one with a block in it', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li class="a"><custom-block style="display: block;">abc[]</custom-block></li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li class="a"><custom-block style="display: block;">abc</custom-block></li>' +
                                        '<li class="a"><custom-block style="display: block;">d</custom-block></li>' +
                                        '<li class="a"><custom-block style="display: block;">[]<br></custom-block></li></ul>',
                                });
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li><custom-block class="a" style="display: block;">abc[]</custom-block></li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li><custom-block class="a" style="display: block;">abc</custom-block></li>' +
                                        '<li><custom-block class="a" style="display: block;">d</custom-block></li>' +
                                        '<li><custom-block class="a" style="display: block;">[]<br></custom-block></li></ul>',
                                });
                            });
                            it('should add two list items with a font at the end of a checklist within a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li>ab</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li>
                                                    <font style="color: red;">cd[]</font>
                                                </li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">ef</li>
                                    </ul>`),
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, '0');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li>ab</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li><font style="color: red;">cd</font></li>
                                                <li>0</li>
                                                <li>[]<br></li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">ef</li>
                                    </ul>`),
                                });
                            });
                        });
                        describe('after checked item', () => {
                            // TODO: do not clone the `IsChecked` modifier
                            // on split (waiting for `preserve` property of
                            // `Modifier`).
                            it('should add two list items at the end of a checklist with a class', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="checklist a"><li class="o_checked">abc[]</li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="checklist a"><li class="o_checked">abc</li><li>d</li><li>[]<br></li></ul>',
                                });
                            });
                            it('should add two list items with a class at the end of a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li class="a o_checked">abc[]</li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li class="a o_checked">abc</li><li class="a">d</li><li class="a">[]<br></li></ul>',
                                });
                            });
                            it.skip('should add two list items with a class and a div at the end of a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li class="a o_checked"><div>abc[]</div></li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li class="a o_checked"><div>abc</div></li><li class="a"><div>d</div></li><li class="a"><div>[]<br></div></li></ul>',
                                });
                            });
                            it.skip('should add two list items with a div with a class at the end of a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore:
                                        '<ul class="o_checklist"><li class="o_checked"><div class="a">abc[]</div></li></ul>',
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, 'd');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter:
                                        '<ul class="o_checklist"><li class="o_checked"><div class="a">abc</div></li><li><div class="a">d</div></li><li><div class="a">[]<br></div></li></ul>',
                                });
                            });
                            it('should add two list items with a font at the end of a checklist within a checklist', async () => {
                                await testEditor(BasicEditor, {
                                    removeCheckIds: true,
                                    contentBefore: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">ab</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked">
                                                    <font style="color: red;">cd[]</font>
                                                </li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">ef</li>
                                    </ul>`),
                                    stepFunction: async editor => {
                                        await insertParagraphBreak(editor);
                                        await insertText(editor, '0');
                                        await insertParagraphBreak(editor);
                                    },
                                    contentAfter: unformat(`
                                    <ul class="o_checklist">
                                        <li class="o_checked">ab</li>
                                        <li class="oe-nested">
                                            <ul class="o_checklist">
                                                <li class="o_checked"><font style="color: red;">cd</font></li>
                                                <li>0</li>
                                                <li>[]<br></li>
                                            </ul>
                                        </li>
                                        <li class="o_checked">ef</li>
                                    </ul>`),
                                });
                            });
                        });
                    });
                });
                describe('Mixed', () => {
                    describe('Ordered to unordered', () => {});
                    describe('Unordered to ordered', () => {});
                });
            });
            describe('Selection not collapsed', () => {
                it('should delete part of a list item, then split it', async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[cd]ef</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]ef</li></ul>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab]cd[ef</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]ef</li></ul>',
                    });
                });
                it('should delete all contents of a list item, then split it', async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>[abc]</li></ul>',
                        stepFunction: insertParagraphBreak,
                        // JW cAfter: '<ul><li><br></li><li>[]<br></li></ul>',
                        contentAfter: '<p>[]<br></p>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>]abc[</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<p>[]<br></p>',
                        // JW cAfter: '<ul><li><br></li><li>[]<br></li></ul>',
                    });
                });
                it("should delete across two list items, then split what's left", async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[cd</li><li>ef]gh</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]gh</li></ul>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab]cd</li><li>ef[gh</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]gh</li></ul>',
                    });
                });
                it('should delete part of a checklist item, then split it', async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[cd]ef</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]ef</li></ul>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab]cd[ef</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]ef</li></ul>',
                    });
                });
                it('should delete all contents of a checklist item, then split it', async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>[abc]</li></ul>',
                        stepFunction: insertParagraphBreak,
                        // JW cAfter: '<ul><li><br></li><li>[]<br></li></ul>',
                        contentAfter: '<p>[]<br></p>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>]abc[</li></ul>',
                        stepFunction: insertParagraphBreak,
                        // JW cAfter: '<ul><li><br></li><li>[]<br></li></ul>',
                        contentAfter: '<p>[]<br></p>',
                    });
                });
                it("should delete across two list items, then split what's left", async () => {
                    // Forward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[cd</li><li>ef]gh</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]gh</li></ul>',
                    });
                    // Backward selection
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab]cd</li><li>ef[gh</li></ul>',
                        stepFunction: insertParagraphBreak,
                        contentAfter: '<ul><li>ab</li><li>[]gh</li></ul>',
                    });
                });
            });
        });
        describe('insertLineBreak', () => {
            describe('Selection collapsed', () => {
                it('should insert a <br> into an empty list item', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>[]<br></li></ul>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<ul><li><br>[]<br></li></ul>',
                    });
                });
                it('should insert a <br> at the beggining of a list item', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>[]abc</li></ul>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<ul><li><br>[]abc</li></ul>',
                    });
                });
                it('should insert a <br> within a list item', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[]cd</li></ul>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<ul><li>ab<br>[]cd</li></ul>',
                    });
                });
                it('should insert a line break (2 <br>) at the end of a list item', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>abc[]</li></ul>',
                        stepFunction: insertLineBreak,
                        // The second <br> is needed to make the first
                        // one visible.
                        contentAfter: '<ul><li>abc<br>[]<br></li></ul>',
                    });
                });
            });
            describe('Selection not collapsed', () => {
                it('should delete part of a list item, then insert a <br>', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: '<ul><li>ab[cd]ef</li></ul>',
                        stepFunction: insertLineBreak,
                        contentAfter: '<ul><li>ab<br>[]ef</li></ul>',
                    });
                });
            });
        });
        describe('indent', () => {
            describe('Checklist', () => {
                it('should indent a checklist', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">a[b]c</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">a[b]c</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>a[b]c</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>a[b]c</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                });
                it('should indent a checklist and previous ligne become the "title"', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="o_checked">d[e]f</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                    <li class="o_checked">d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li>d[e]f</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li>d[e]f</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                    <li>d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="o_checked">d[e]f</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                    <li class="o_checked">d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                });
                it('should indent a checklist and merge it with previous siblings', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">def</li>
                                    </ul>
                                </li>
                                <li class="o_checked">g[h]i</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">def</li>
                                        <li class="o_checked">g[h]i</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });

                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>def</li>
                                    </ul>
                                </li>
                                <li class="o_checked">g[h]i</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>def</li>
                                        <li class="o_checked">g[h]i</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">def</li>
                                    </ul>
                                </li>
                                <li>g[h]i</li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">def</li>
                                        <li>g[h]i</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                });
                it('should indent a checklist and merge it with next siblings', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="o_checked">d[e]f</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">d[e]f</li>
                                        <li class="o_checked">ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="o_checked">d[e]f</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">d[e]f</li>
                                        <li class="o_checked">ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li>d[e]f</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>d[e]f</li>
                                        <li>ghi</li>
                                    </ul>
                                </li>
                            </ul>`),
                    });
                });
            });
            describe('Regular list', () => {
                it('should indent a regular list empty item', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li>abc</li>
                                <li>[]</li>
                            </ul>
                            <p>def</p>`),
                        stepFunction: indentList,
                        contentAfter: unformat(`
                            <ul>
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>[]</li>
                                    </ul>
                                </li>
                            </ul>
                            <p>def</p>`),
                    });
                });
                it('should indent a regular list empty item after an insertParagraphBreak', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li>abc[]</li>
                            </ul>
                            <p>def</p>`),
                        stepFunction: async editor => {
                            await editor.execCommand('oEnter');
                            await editor.execCommand('oTab');
                        },
                        contentAfter: unformat(`
                            <ul>
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul>
                                        <li>[]<br></li>
                                    </ul>
                                </li>
                            </ul>
                            <p>def</p>`),
                    });
                });
            });
        });
        describe('outdent', () => {
            describe('Regular list', () => {
                it('should remove the list-style when outdent the list', async () => {
                    await testEditor(BasicEditor, {
                        contentBefore: unformat(`
                            <ul>
                                <li style="list-style: cambodian;">
                                    <ul>
                                        <li>a[b]c</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: outdentList,
                        contentAfter: unformat(`
                            <ul>
                                <li style="list-style: cambodian;"></li>
                                <li>a[b]c</li>
                            </ul>`),
                    });
                });
            });
            describe('Checklist', () => {
                it('should outdent a checklist', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">a[b]c</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: outdentList,
                        contentAfter: unformat(`
                        <ul class="o_checklist">
                            <li class="o_checked">a[b]c</li>
                        </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>a[b]c</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: outdentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>a[b]c</li>
                            </ul>`),
                    });
                });
                it('should outdent a checklist and previous line as "title"', async () => {
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li class="o_checked">d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: outdentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li class="o_checked">abc</li>
                                <li class="o_checked">d[e]f</li>
                            </ul>`),
                    });
                    await testEditor(BasicEditor, {
                        removeCheckIds: true,
                        contentBefore: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li class="oe-nested">
                                    <ul class="o_checklist">
                                        <li>d[e]f</li>
                                    </ul>
                                </li>
                            </ul>`),
                        stepFunction: outdentList,
                        contentAfter: unformat(`
                            <ul class="o_checklist">
                                <li>abc</li>
                                <li>d[e]f</li>
                            </ul>`),
                    });
                });
            });
        });
    });
    describe('indent', () => {
        describe('with selection collapsed', () => {
            it('should indent the first element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a[]</li>
                    <li>b</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>a[]</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
                });
            });
            it('should indent the last element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[]b</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                </ul>`),
                });
            });
            it('should indent multi-level', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>
                        a
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]b</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                });
            });
            it('should indent the last element of a list with proper with unordered list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ol>
                    <li>a</li>
                    <li>[]b</li>
                </ol>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ol>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>[]b</li>
                        </ol>
                    </li>
                </ol>`),
                });
            });
            it('should indent the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[]b</li>
                    <li>c</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                        </ul>
                    </li>
                    <li>
                        c
                    </li>
                </ul>`),
                });
            });
            it('should indent even if the first element of a list is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>[]a</li>
                    <li>b</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>[]a</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
                });
            });
            it('should indent only one element of a list with sublist', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>c</li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[]b</li>
                            <li>c</li>
                        </ul>
                    </li>
                </ul>`),
                });
            });
            it('should convert mixed lists', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>c</li>
                        </ol>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>[]b</li>
                            <li>c</li>
                        </ol>
                    </li>
                </ul>`),
                });
            });
            it('should rejoin after indent', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ol>
                    <li class="oe-nested">
                        <ol>
                            <li>a</li>
                        </ol>
                    </li>
                    <li>
                        []b
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>c</li>
                        </ol>
                    </li>
                </ol>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ol>
                    <li class="oe-nested">
                        <ol>
                            <li>a</li>
                            <li>[]b</li>
                            <li>c</li>
                        </ol>
                    </li>
                </ol>`),
                });
            });
        });
        describe('with selection', () => {
            it('should indent the first element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>[a]</li>
                    <li>b</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li class="oe-nested">
                        <ul>
                            <li>[a]</li>
                        </ul>
                    </li>
                    <li>b</li>
                </ul>`),
                });
            });
            it('should indent the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[b]</li>
                    <li>c</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b]</li>
                        </ul>
                    </li>
                    <li>
                        c
                    </li>
                </ul>`),
                });
            });
            it('should indent multi-level', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b]</li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[b]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                });
            });
            it('should indent two multi-levels', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c]</li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b</li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>c]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li>[b
                                    </li><li class="oe-nested">
                                        <ul>
                                            <li>c]</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[b</li>
                                            <li class="oe-nested">
                                                <ul>
                                                    <li>c]</li>
                                                </ul>
                                            </li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </li>
                </ul>`),
                });
            });
            it('should indent multiples list item in the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>[b</li>
                    <li>c]</li>
                    <li>d</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>[b</li>
                            <li>c]</li>
                        </ul>
                    </li>
                    <li>
                        d
                    </li>
                </ul>`),
                });
            });
            it('should indent multiples list item with reversed range', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>]b</li>
                    <li>c[</li>
                    <li>d</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>]b</li>
                            <li>c[</li>
                        </ul>
                    </li>
                    <li>
                        d
                    </li>
                </ul>`),
                });
            });
            it('should indent multiples list item in the middle element of a list with sublist', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ul>
                            <li>c</li>
                        </ul>
                    </li>
                    <li>d]</li>
                    <li>e</li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ul>
                            <li>
                                [b
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c</li>
                                </ul>
                            </li>
                            <li>d]</li>
                        </ul>
                    </li>
                    <li>e</li>
                </ul>`),
                });
            });
            it('should indent with mixed lists', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                <ul>
                    <li>a</li>
                    <li>
                        [b
                    </li><li class="oe-nested">
                        <ol>
                            <li>]c</li>
                        </ol>
                    </li>
                </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                <ul>
                    <li>
                        a
                    </li>
                    <li class="oe-nested">
                        <ol>
                            <li>
                                [b
                            </li>
                            <li class="oe-nested">
                                <ol>
                                    <li>]c</li>
                                </ol>
                            </li>
                        </ol>
                    </li>
                </ul>`),
                });
            });
            it('should indent nested list and list with elements in a upper level than the rangestart', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>a</li>
                            <li>
                                b
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c</li>
                                    <li>[d</li>
                                </ul>
                            </li>
                            <li>
                                e
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>f</li>
                                    <li>g</li>
                                </ul>
                            </li>
                            <li>h]</li>
                            <li>i</li>
                        </ul>`),
                    stepFunction: indentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>
                                b
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>
                                        c
                                    </li>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[d</li>
                                        </ul>
                                    </li>
                                    <li>
                                    e
                                    </li>
                                    <li class="oe-nested">
                                    <ul>
                                        <li>f</li>
                                        <li>g</li>
                                    </ul>
                                </li>
                                <li>h]</li>
                                </ul>
                            </li>
                            <li>i</li>
                        </ul>`),
                });
            });
        });
    });
    describe('outdent', () => {
        describe('with selection collapsed', () => {
            it('should outdent the last element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                            </li><li class="oe-nested">
                                <ul>
                                    <li>[]b</li>
                                </ul>
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>[]b</li>
                        </ul>`),
                });
            });
            it('should outdent the last element of a list with proper with unordered list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ol>
                            <li>
                                a
                            </li>
                            <li class="oe-nested">
                                <ol>
                                    <li>[]b</li>
                                </ol>
                            </li>
                        </ol>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ol>
                            <li>a</li>
                            <li>[]b</li>
                        </ol>`),
                });
            });
            it('should outdent the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]b</li>
                                </ul>
                            </li>
                            <li>
                                c
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>[]b</li>
                            <li>c</li>
                        </ul>`),
                });
            });
            it('should outdent if the first element of a list is selected', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>[]a</li>
                            <li>b</li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <p>[]a</p>
                        <ul>
                            <li>b</li>
                        </ul>`),
                });
            });
            it('should outdent the last element of a list with sublist', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li class="oe-nested">
                                        <ul>
                                            <li>[]c</li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>
                                a
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]c</li>
                                </ul>
                            </li>
                        </ul>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>[]c</li>
                                </ul>
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>
                                a
                            </li>
                            <li>[]c</li>
                        </ul>`),
                });
            });
        });
        describe('with selection', () => {
            it('should outdent the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                            </li><li class="oe-nested">
                                <ul>
                                    <li>[b]</li>
                                </ul>
                            </li>
                            <li>
                                c
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>[b]</li>
                            <li>c</li>
                        </ul>`),
                });
            });
            it('should inoutdentdent multiples list item in the middle element of a list', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                                <ul>
                                    <li>[b</li>
                                    <li>c]</li>
                                </ul>
                            </li>
                            <li>
                                d
                            </li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>[b</li>
                            <li>c]</li>
                            <li>d</li>
                        </ul>`),
                });
            });
            it('should outdent multiples list item in the middle element of a list with sublist', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                                <ul>
                                    <li>
                                        [b
                                        <ul>
                                            <li>c</li>
                                        </ul>
                                    </li>
                                    <li>d]</li>
                                </ul>
                            </li>
                            <li>e</li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>
                                [b
                            </li>
                            <li class="oe-nested">
                                <ul>
                                    <li>c</li>
                                </ul>
                            </li>
                            <li>d]</li>
                            <li>e</li>
                        </ul>`),
                });
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>
                                a
                                <ul>
                                    <li>
                                        b
                                        <ul>
                                            <li>[c</li>
                                        </ul>
                                    </li>
                                    <li>d]</li>
                                </ul>
                            </li>
                            <li>e</li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>
                                a
                                <ul>
                                    <li>b</li>
                                    <li>[c</li>
                                </ul>
                            </li>
                            <li>d]</li>
                            <li>e</li>
                        </ul>`),
                });
            });
            it('should outdent nested list and list with elements in a upper level than the rangestart', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: unformat(`
                        <ul>
                            <li>a</li>
                            <li>
                                b
                                <ul>
                                    <li>
                                        c
                                        <ul>
                                            <li>[d</li>
                                        </ul>
                                    </li>
                                    <li>
                                    e
                                    <ul>
                                        <li>f</li>
                                        <li>g</li>
                                    </ul>
                                </li>
                                <li>h]</li>
                                </ul>
                            </li>
                            <li>i</li>
                        </ul>`),
                    stepFunction: outdentList,
                    contentAfter: unformat(`
                        <ul>
                            <li>a</li>
                            <li>b
                                <ul>
                                    <li>c</li>
                                    <li>[d</li>
                                </ul>
                            </li>
                            <li>e</li>
                            <li class="oe-nested">
                                <ul>
                                    <li>f</li>
                                    <li>g</li>
                                </ul>
                            </li>
                            <li>h]</li>
                            <li>i</li>
                        </ul>`),
                });
            });
        });
    });
});
