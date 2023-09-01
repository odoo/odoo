/** @odoo-module */

import { URL_REGEX } from '../../src/OdooEditor.js';
import {
    BasicEditor,
    click,
    deleteBackward,
    insertText,
    insertParagraphBreak,
    insertLineBreak,
    testEditor,
    createLink,
    undo
} from '../utils.js';

const convertToLink = createLink;
const unlink = async function (editor) {
    editor.execCommand('unlink');
};
const testUrlRegex = (content, {expectedUrl} = {}) => {
    const message = expectedUrl ?
        `should have the text be "${content}" with one link ${expectedUrl}` :
        `should be a link: ${content}`;
    it(message, () => {
        const match = content.match(URL_REGEX);
        if (expectedUrl) {
            window.chai.assert.equal(expectedUrl, match && match[0]);
        }
        window.chai.assert.exists(content.match(URL_REGEX));
    });
}
const testNotUrlRegex = (url) => {
    it(`should NOT be a link: ${url}`, () => {
        window.chai.assert.notExists(url.match(URL_REGEX));
    });
}

describe('Link', () => {
    describe('regex', () => {
        testUrlRegex('google.com');
        testUrlRegex('a google.com b', {expectedUrl: 'google.com'});

        // Url separator
        testUrlRegex('google.com/', {expectedUrl: 'google.com/'});
        testUrlRegex('google.com?', {expectedUrl: 'google.com?'});
        testUrlRegex('google.com#', {expectedUrl: 'google.com#'});

        testUrlRegex('google.com!', {expectedUrl: 'google.com'});
        testUrlRegex('google.com)', {expectedUrl: 'google.com'});
        testUrlRegex('google.com(', {expectedUrl: 'google.com'});
        testUrlRegex('google.com. a', {expectedUrl: 'google.com'});
        testUrlRegex('google.com, a', {expectedUrl: 'google.com'});

        // Some special characters should not be included if at the end.
        testUrlRegex('google.com/.', {expectedUrl: 'google.com/'});
        testUrlRegex('google.com/,', {expectedUrl: 'google.com/'});
        testUrlRegex('google.com/)', {expectedUrl: 'google.com/'});
        testUrlRegex('google.com/]', {expectedUrl: 'google.com/'});
        testUrlRegex('google.com/}', {expectedUrl: 'google.com/'});
        testUrlRegex("google.com/'", {expectedUrl: 'google.com/'});
        testUrlRegex('google.com/"', {expectedUrl: 'google.com/'});

        // The previous special character should be included when they are nt at the end.
        testUrlRegex('google.com/.a', {expectedUrl: 'google.com/.a'});
        testUrlRegex('google.com/,a', {expectedUrl: 'google.com/,a'});
        testUrlRegex('google.com/)a', {expectedUrl: 'google.com/)a'});
        testUrlRegex('google.com/]a', {expectedUrl: 'google.com/]a'});
        testUrlRegex('google.com/}a', {expectedUrl: 'google.com/}a'});
        testUrlRegex("google.com/'a", {expectedUrl: "google.com/'a"});
        testUrlRegex('google.com/"a', {expectedUrl: 'google.com/"a'});

        // Other special character can be included at the end.
        testUrlRegex('google.com/(', {expectedUrl: 'google.com/('});
        testUrlRegex('google.com/[', {expectedUrl: 'google.com/['});
        testUrlRegex('google.com/{', {expectedUrl: 'google.com/{'});

        testUrlRegex('google.co.uk');
        testUrlRegex('http://google.com');
        testUrlRegex('https://google.com');
        testUrlRegex('https://www.google.com');
        testUrlRegex('https://google.shop');
        testNotUrlRegex('google.shop');
        testUrlRegex('google.com/');
        testUrlRegex('http://google.com/');
        testUrlRegex('https://google.com/');
        testUrlRegex('https://google.co.uk/');
        testUrlRegex('https://www.google.com/');
        testNotUrlRegex('google.shop/');
        testUrlRegex('http://google.com/foo#test');
        testUrlRegex('a.bcd.ef');
        testUrlRegex('a.bc.de');
        testNotUrlRegex('a.bc.d');
        testNotUrlRegex('a.b.bc');
        testNotUrlRegex('20.08.2022');
        testNotUrlRegex('31.12');

        // Url data and anchors count as part of the url.
        testUrlRegex('google.com?data=hello', { expectedUrl: 'google.com?data=hello' });
        testUrlRegex('google.com/?data=hello', { expectedUrl: 'google.com/?data=hello' });
        testUrlRegex('google.com/foo/?data=hello', { expectedUrl: 'google.com/foo/?data=hello' });
        testUrlRegex('google.com/.?data=hello', { expectedUrl: 'google.com/.?data=hello' });
        testUrlRegex('google.com?data=hello#anchor', { expectedUrl: 'google.com?data=hello#anchor' });
        testUrlRegex('google.com/?data=hello#anchor', { expectedUrl: 'google.com/?data=hello#anchor' });
        testUrlRegex('google.com/.?data=hello#anchor', { expectedUrl: 'google.com/.?data=hello#anchor' });
        testUrlRegex('google.com/foo/?data=hello&data2=foo#anchor', { expectedUrl: 'google.com/foo/?data=hello&data2=foo#anchor' });
    });
    describe('insert Link', () => {
        describe('range collapsed', () => {
            it('should insert a link and preserve spacing', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a [] c</p>',
                    stepFunction: createLink,
                    // Two consecutive spaces like one so `a [] c` is
                    // effectively the same as `a []c`.
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
    describe('edit link label', () => {
        describe('range collapsed', () => {
            it('should not change the url when a link is not edited', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.co">google.com</a>b</p>',
                    contentAfter: '<p>a<a href="https://google.co">google.com</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cd[]</a></p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'e');
                    },
                    contentAfter: '<p>a<a href="https://google.xx">google.com</a>b<a href="https://google.co">cde[]</a></p>',
                });
            });
            it('should change the url when the label change', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'm');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://gogle.com">go[]gle.com</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'o');
                    },
                    contentAfter: '<p>a<a href="https://google.com">goo[]gle.com</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://else.com">go[]gle.com</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'o');
                    },
                    contentAfter: '<p>a<a href="https://google.com">goo[]gle.com</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://else.com">http://go[]gle.com</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'o');
                    },
                    contentAfter: '<p>a<a href="http://google.com">http://goo[]gle.com</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@moto[].com</a></p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'r');
                    },
                    contentAfter: '<p>a<a href="mailto:hello@motor.com">hello@motor[].com</a></p>',
                });
            });
            it('should change the url when the label change, without changing the protocol', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://google.co">google.co[]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'm');
                    },
                    contentAfter: '<p>a<a href="http://google.com">google.com[]</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'm');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
                });
            });
            it('should change the url when the label change, changing to the suitable protocol', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="http://hellomoto.com">hello[]moto.com</a></p>',
                    stepFunction: async editor => {
                        await insertText(editor, '@');
                    },
                    contentAfter: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="mailto:hello@moto.com">hello@[]moto.com</a></p>',
                    stepFunction: async editor => {
                        await deleteBackward(editor);
                    },
                    contentAfter: '<p>a<a href="http://hellomoto.com">hello[]moto.com</a></p>',
                });
            });
            it('should change the url in one step', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'm');
                        await undo(editor);
                    },
                    contentAfter: '<p>a<a href="https://google.co">google.co[]</a>b</p>',
                });
            });
            it('should not change the url when the label change', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.com">google.com[]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'u');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google.comu[]</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.com">google.com[]</a></p>',
                    stepFunction: async editor => {
                        await insertLineBreak(editor);
                        await insertText(editor, 'odoo.com')
                    },
                    contentAfter: '<p>a<a href="https://google.com">google.com<br>odoo.com[]</a></p>',
                });
            });
        });
        describe('range not collapsed', () => {
            it('should change the url when the label change', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'be');
                    },
                    contentAfter: '<p>a<a href="https://google.be">google.be[]</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://gogle.com">[yahoo].com</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'google');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google[].com</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://else.com">go[gle.c]om</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, '.c');
                    },
                    contentAfter: '<p>a<a href="https://go.com">go.c[]om</a>b</p>',
                });
            });
            it('should not change the url when the label change', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.com">googl[e.com]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'e');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google[]</a>b</p>',
                });
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="https://google.com">google.[com]</a>b</p>',
                    stepFunction: async editor => {
                        await insertText(editor, 'vvv');
                    },
                    contentAfter: '<p>a<a href="https://google.com">google.vvv[]</a>b</p>',
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
                // With fontawesome at the start of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>bcd[]</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<span class="fa fa-music" contenteditable="false"></span>bcd[]e</p>',
                });
                // With fontawesome at the middle of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc<span class="fa fa-music" contenteditable="false">\u200B</span>d[]</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>abc<span class="fa fa-music" contenteditable="false"></span>d[]e</p>',
                });
                // With fontawesome at the end of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bcd[]<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>abcd[]<span class="fa fa-music" contenteditable="false"></span>e</p>',
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
                // With fontawesome at the start of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>b[]cd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<span class="fa fa-music" contenteditable="false"></span>b[]cde</p>',
                });
                // With fontawesome at the middle of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b[]c<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>ab[]c<span class="fa fa-music" contenteditable="false"></span>de</p>',
                });
                // With fontawesome at the end of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b[]cd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>ab[]cd<span class="fa fa-music" contenteditable="false"></span>e</p>',
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
                // With fontawesome at the start of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>[]bcd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<span class="fa fa-music" contenteditable="false"></span>[]bcde</p>',
                });
                // With fontawesome at the middle of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">[]bc<span class="fa fa-music" contenteditable="false">\u200B</span>d</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[]bc<span class="fa fa-music" contenteditable="false"></span>de</p>',
                });
                // With fontawesome at the end of the link.
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">[]bcd<span class="fa fa-music" contenteditable="false">\u200B</span></a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[]bcd<span class="fa fa-music" contenteditable="false"></span>e</p>',
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
                // With fontawesome at the start of the link.
                await testEditor(BasicEditor, {
                    contentBefore:
                        '<p><a href="exist">a</a>b<a href="exist"><span class="fa fa-music" contenteditable="false">\u200B</span>c[]d</a>e<a href="exist">f</a></p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p><a href="exist">a</a>b<span class="fa fa-music" contenteditable="false"></span>c[]de<a href="exist">f</a></p>',
                });
                // With fontawesome at the middle of the link.
                await testEditor(BasicEditor, {
                    contentBefore:
                        '<p><a href="exist">a</a>b<a href="exist">c<span class="fa fa-music" contenteditable="false">\u200B</span>d[]e</a>f<a href="exist">g</a></p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p><a href="exist">a</a>bc<span class="fa fa-music" contenteditable="false"></span>d[]ef<a href="exist">g</a></p>',
                });
                // With fontawesome at the end of the link.
                await testEditor(BasicEditor, {
                    contentBefore:
                        '<p><a href="exist">a</a>b<a href="exist">c[]d<span class="fa fa-music" contenteditable="false">\u200B</span></a>e<a href="exist">f</a></p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p><a href="exist">a</a>bc[]d<span class="fa fa-music" contenteditable="false"></span>e<a href="exist">f</a></p>',
                });
            });
        });
        describe('range not collapsed', () => {
            it('should remove the link in the selected range at the end of a link', async () => {
                // FORWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc[d]</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc</a>[d]e</p>',
                });
                // BACKWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc]d[</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc</a>]d[e</p>',
                });
            });
            it('should remove the link in the selected range in the middle of a link', async () => {
                // FORWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b[c]d</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">b</a>[c]<a href="exist">d</a>e</p>',
                });
                // BACKWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">b]c[d</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">b</a>]c[<a href="exist">d</a>e</p>',
                });
            });
            it('should remove the link in the selected range at the start of a link', async () => {
                // FORWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">[b]cd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[b]<a href="exist">cd</a>e</p>',
                });
                // BACKWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">]b[cd</a>e</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a]b[<a href="exist">cd</a>e</p>',
                });
            });
            it('should remove the link in the selected range overlapping the end of a link', async () => {
                // FORWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc[d</a>e]f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc</a>[de]f</p>',
                });
                // BACKWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a<a href="exist">bc]d</a>e[f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a<a href="exist">bc</a>]de[f</p>',
                });
            });
            it('should remove the link in the selected range overlapping the start of a link', async () => {
                // FORWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a[b<a href="exist">c]de</a>f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a[bc]<a href="exist">de</a>f</p>',
                });
                // BACKWARD
                await testEditor(BasicEditor, {
                    contentBefore: '<p>a]b<a href="exist">c[de</a>f</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>a]bc[<a href="exist">de</a>f</p>',
                });
            });
            it('should not unlink selected non-editable links', async () => {
                await testEditor(BasicEditor, {
                    contentBefore: '<p><a href="exist">[ab</a><a contenteditable="false" href="exist">cd</a>ef]</p>',
                    stepFunction: async editor => {
                        await unlink(editor);
                    },
                    contentAfter: '<p>[ab<a contenteditable="false" href="exist">cd</a>ef]</p>',
                });
            });
        });
    });
    describe('isolated link', () => {
        const clickOnLink = async editor => {
            const a = editor.editable.querySelector('a');
            await click(a, { clientX: a.getBoundingClientRect().left + 5 });
            return a;
        };
        it('should restrict editing to link when clicked', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="#/"><span class="a">b</span></a></p>',
                stepFunction: async editor => {
                    const a = await clickOnLink(editor);
                    window.chai.expect(a.isContentEditable).to.be.equal(true);
                },
                contentAfter: '<p>a<a href="#/"><span class="a">b</span></a></p>',
            });
            // The following is a regression test, checking that the link
            // remains non-editable whenever the editable zone is contained by
            // the link.
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="#/"><span class="a">b</span></a></p>',
                stepFunction: async editor => {
                    const a = await clickOnLink(editor);
                    window.chai.expect(a.isContentEditable).to.be.equal(false);
                },
                contentAfter: '<p>a<a href="#/"><span class="a" contenteditable="true">b</span></a></p>',
            }, {
                isRootEditable: false,
                getContentEditableAreas: function (editor) {
                    return [...editor.editable.querySelectorAll('a span')];
                }
            });
        });
        it('should keep isolated link after a delete', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
                stepFunction: async editor => {
                    await clickOnLink(editor);
                    await deleteBackward(editor);
                },
                contentAfterEdit: '<p>a<a href="#/" data-oe-zws-empty-inline="" class="o_link_in_selection">' +
                        '<span data-o-link-zws="start" contenteditable="false">\u200B</span>' + // start zws
                        '[]\u200B' + // content: empty inline zws
                        '<span data-o-link-zws="end">\u200B</span>' + // end zws
                    '</a>' +
                    '<span data-o-link-zws="after" contenteditable="false">\u200B</span>' + // after zws
                    'c</p>',
                contentAfter: '<p>a[]c</p>',
            });
        });
        it('should keep isolated link after a delete and typing', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="#/">b[]</a>c</p>',
                stepFunction: async editor => {
                    await clickOnLink(editor);
                    await deleteBackward(editor);
                    await insertText(editor, 'a');
                    await insertText(editor, 'b');
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="#/">abc[]</a>c</p>',
            });
        });
        it('should delete the content from the link when popover is active', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p><a href="#/">abc[]abc</a></p>',
                stepFunction: async editor => {
                    await clickOnLink(editor);
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: '<p><a href="#/">[]abc</a></p>',
            });
        });
    });
    describe('existing link', () => {
        it('should parse correctly a span inside a Link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span class="a">b[]</span></a>c</p>',
                contentAfter: '<p>a<a href="exist"><span class="a">b[]</span></a>c</p>',
            });
        });
        it('should parse correctly an empty span inside a Link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
                contentAfter: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
            });
        });
        it('should parse correctly a span inside a Link 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span class="a">b[]</span>c</a>d</p>',
                contentAfter: '<p>a<a href="exist"><span class="a">b[]</span>c</a>d</p>',
            });
        });
        it('should parse correctly an empty span inside a Link then add a char', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]<span class="a"></span></a>c</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist">bc[]<span class="a"></span></a>c</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span class="a">b[]</span></a>d</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                // JW cAfter: '<p>a<span><a href="exist">b</a>c[]</span>d</p>',
                contentAfter: '<p>a<a href="exist"><span class="a">bc[]</span></a>d</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char 2', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span class="a">b[]</span>d</a>e</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'c');
                },
                contentAfter: '<p>a<a href="exist"><span class="a">bc[]</span>d</a>e</p>',
            });
        });
        it('should parse correctly a span inside a Link then add a char 3', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist"><span class="a">b</span>c[]</a>e</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'd');
                },
                // JW cAfter: '<p>a<a href="exist"><span class="a">b</span>c</a>d[]e</p>',
                contentAfter: '<p>a<a href="exist"><span class="a">b</span>cd[]</a>e</p>',
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
        it('should add two character after the link', async () => {
            await testEditor(BasicEditor, {
                contentBefore: '<p>a<a href="exist">b[]</a>e</p>',
                stepFunction: async editor => {
                    await insertText(editor, 'cd');
                },
                contentAfter: '<p>a<a href="exist">bcd[]</a>e</p>',
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
        //             await editor.execCommand('insert', 'd');
        //         },
        //         contentAfter: '<div><p>123</p><p><a href="#">d[]</a></p></div>',
        //     });
        // });
    });
});
