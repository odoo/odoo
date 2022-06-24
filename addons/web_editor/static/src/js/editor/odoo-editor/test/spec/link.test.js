import { URL_REGEX, URL_REGEX_WITH_INFOS } from '../../src/OdooEditor.js';
import {
    BasicEditor,
    click,
    insertText,
    insertParagraphBreak,
    insertLineBreak,
    testEditor,
    createLink,
} from '../utils.js';

const convertToLink = createLink;
const unlink = async function (editor) {
    editor.execCommand('unlink');
};
const testUrlRegex = (url) => {
    it(`should be a link: ${url}`, () => {
        window.chai.assert.exists(url.match(URL_REGEX));
        window.chai.assert.exists(url.match(URL_REGEX_WITH_INFOS));
    });
}
const testNotUrlRegex = (url) => {
    it(`should be a link: ${url}`, () => {
        window.chai.assert.notExists(url.match(URL_REGEX));
        window.chai.assert.notExists(url.match(URL_REGEX_WITH_INFOS));
    });
}

describe('Link', () => {
    describe('regex', () => {
        testUrlRegex('http://google.com');
        testUrlRegex('https://google.com');
        testUrlRegex('http://google.com/foo#test');
        testUrlRegex('a.bcd.ef');
        testUrlRegex('a.bc.de');
        testNotUrlRegex('google.com');
        testNotUrlRegex('a.bc.d');
        testNotUrlRegex('a.b.bc');
    });
    describe('insert Link', () => {
        // This fails, but why would the cursor stay inside the link
        // if the next text insert should be outside of the link (see next test)
        describe('range collapsed', () => {
            it('should insert a link and preserve spacing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a [] c</p>',
                    stepFunction: createLink,
                    contentAfter: '<p>a <a href="#">link</a>[]c</p>',
                });
            });
            it('should insert a link and write a character after the link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]c</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                    },
                    contentAfter: '<p>a<a href="#">link</a>b[]c</p>',
                });
            });
            it('should write two characters after the link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]d</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                        await insertText(editor, 'c');
                    },
                    contentAfter: '<p>a<a href="#">link</a>bc[]d</p>',
                });
            });
            it('should insert a link and write a character after the link then create a new <p>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]c</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                        await insertParagraphBreak(editor);
                    },
                    contentAfter: '<p>a<a href="#">link</a>b</p><p>[]c</p>',
                });
            });
            it('should insert a link and write a character, a new <p> and another character', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]d</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                        await insertParagraphBreak(editor);
                        await insertText(editor, 'c');
                    },
                    contentAfter: '<p>a<a href="#">link</a>b</p><p>c[]d</p>',
                });
            });
            it('should insert a link and write a character at the end of the link then insert a <br>', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]c</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                        await insertLineBreak(editor);
                    },
                    // Writing at the end of a link writes outside the link.
                    contentAfter: '<p>a<a href="#">link</a>b<br>[]c</p>',
                });
            });
            it('should insert a link and write a character insert a <br> and another character', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[]d</p>',
                    stepFunction: async editor => {
                        await createLink(editor);
                        await insertText(editor, 'b');
                        await insertLineBreak(editor);
                        await insertText(editor, 'c');
                    },
                    // Writing at the end of a link writes outside the link.
                    contentAfter: '<p>a<a href="#">link</a>b<br>c[]d</p>',
                });
            });
            it('should insert a <br> inside a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="#">a[]b</a></p>',
                    stepFunction: async editor => {
                        await insertLineBreak(editor);
                    },
                    contentAfter: '<p><a href="#">a<br>[]b</a></p>',
                });
            });
        });
        describe('range not collapsed', () => {
            // This succeeds, but why would the cursor stay inside the link
            // if the next text insert should be outside of the link (see next test)
            it('should set the link on two existing characters and loose range', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await convertToLink(editor);
                    },
                    contentAfter: '<p>a<a href="#">bc</a>[]d</p>',
                });
            });
            it('should set the link on two existing characters, lose range and add a character', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]e</p>',
                    stepFunction: async editor => {
                        await convertToLink(editor);
                        await insertText(editor, 'd');
                    },
                    contentAfter: '<p>a<a href="#">bc</a>d[]e</p>',
                });
            });
            // This fails, but why would the cursor stay inside the link
            // if the next text insert should be outside of the link (see previous test)
            it('should replace selection by a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[bc]d</p>',
                    stepFunction: async editor => {
                        await createLink(editor, '#');
                    },
                    contentAfter: '<p>a<a href="#">#</a>[]d</p>',
                });
            });
        });
    });
    describe('remove link', () => {
        describe('range collapsed', () => {
            it('should remove the link if collapsed range at the end of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bcd[]</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>abcd[]e</p>',
                });
            });
            it('should remove the link if collapsed range in the middle a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b[]cd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>ab[]cde</p>',
                });
            });
            it('should remove the link if collapsed range at the start of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">[]bcd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[]bcde</p>',
                });
            });
            it('should remove only the current link if collapsed range in the middle of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore:
                        '<p><a href="exist">a</a>b<a href="exist">c[]d</a>e<a href="exist">f</a></p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p><a href="exist">a</a>bc[]de<a href="exist">f</a></p>',
                });
            });
        });
        describe('range not collapsed', () => {
            it('should remove the link in the selected range at the end of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc[d]</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc[</a>d]e</p>',
                });
            });
            it('should remove the link in the selected range in the middle of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b[c]d</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">b[</a>c]<a href="exist">d</a>e</p>',
                });
            });
            it('should remove the link in the selected range at the start of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">[b]cd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[b]<a href="exist">cd</a>e</p>',
                });
            });
            it('should remove the link in the selected range overlapping the end of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc[d</a>e]f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc[</a>de]f</p>',
                });
            });
            it('should remove the link in the selected range overlapping the start of a link', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<a href="exist">c]de</a>f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[bc]<a href="exist">de</a>f</p>',
                });
            });
        });
    });
    describe('existing link', () => {
        it('should parse correctly a span inside a Link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span>b[]</span></a>c</p>',
                contentAfter: '<p>a<a href="exist"><span>b[]</span></a>c</p>',
            });
        });
        it('should parse correctly an empty span inside a Link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]<span></span></a>c</p>',
                contentAfter: '<p>a<a href="exist">b[]<span></span></a>c</p>',
            });
        });
        it('should parse correctly a span inside a Link 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span>b[]</span>c</a>d</p>',
                contentAfter: '<p>a<a href="exist"><span>b[]</span>c</a>d</p>',
            });
        });
        it('should parse correctly an empty span inside a Link then add a char', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]<span></span></a>c</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist">bc[]<span></span></a>c</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span>b[]</span></a>d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                // JW cAfter: '<p>a<span><a href="exist">b</a>c[]</span>d</p>',
                contentAfter: '<p>a<a href="exist"><span>bc[]</span></a>d</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span>b[]</span>d</a>e</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist"><span>bc[]</span>d</a>e</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char 3', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span>b</span>c[]</a>e</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'd');
                },
                // JW cAfter: '<p>a<a href="exist"><span>b</span>c</a>d[]e</p>',
                contentAfter: '<p>a<a href="exist"><span>b</span>cd[]</a>e</p>',
            });
        });
        it('should add a character after the link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]</a>d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                // JW cAfter: '<p>a<a href="exist">b</a>c[]d</p>',
                contentAfter: '<p>a<a href="exist">bc[]</a>d</p>',
            });
        });
        it('should add a character after the link if range just after link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b</a>[]d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist">b</a>c[]d</p>',
            });
        });
        it('should add a character in the link after a br tag', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b<br>[]</a>d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist">b<br>c[]</a>d</p>',
            });
        });
        it('should not add a character in the link if start of paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b</a></p><p>[]d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist">b</a></p><p>c[]d</p>',
            });
        });
        it('should restrict editing to link when clicked', async () => {
            const initialContent = '<p>a<a href="#/"><span>b</span></a></p>';
            const editFunction = editableLink => async editor => {
                const a = editor.editable.querySelector('a');
                await click(a, { clientX: a.getBoundingClientRect().left + 5 });
                window.chai.expect(a.isContentEditable).to.be.equal(editableLink);
            };
            await testEditor(BasicEditor, {
                contentBefore: initialContent,
                stepFunction: editFunction(true),
                contentAfter: '<p>a<a href="#/" contenteditable="true"><span>b</span></a></p>',
            });
            // The following is a regression test, checking that the link
            // remains non-editable whenever the editable zone is contained by
            // the link.
            await testEditor(BasicEditor, {
                contentBefore: initialContent,
                stepFunction: editFunction(false),
                contentAfter: '<p>a<a href="#/"><span contenteditable="true">b</span></a></p>',
            }, {
                isRootEditable: false,
                getContentEditableAreas: function (editor) {
                    return editor.editable.querySelectorAll('a span');
                }
            });
        });
        // it('should select and replace all text and add the next char in bold', async () => {
        //     await testEditor(BasicEditor, {
        //         contentBefore: '<div><p>[]123</p><p><a href="#">abc</a></p></div>',
        //         stepFunction: async (editor) => {
        //             const p = editor.selection.anchor.parent.nextSibling();
        //             await editor.execCommand('setSelection', {
        //                 vSelection: {
        //                     anchorNode: p.firstLeaf(),
        //                     anchorPosition: RelativePosition.BEFORE,
        //                     focusNode: p.lastLeaf(),
        //                     focusPosition: RelativePosition.AFTER,
        //                     direction: Direction.FORWARD,
        //                 },
        //             });
        //             await editor.execCommand('insertText', { text: 'd' });
        //         },
        //         contentAfter: '<div><p>123</p><p><a href="#">d[]</a></p></div>',
        //     });
        // });
    });
});
