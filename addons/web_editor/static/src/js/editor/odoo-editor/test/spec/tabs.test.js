/** @odoo-module */

import {
    BasicEditor,
    deleteBackward,
    deleteForward,
    insertText,
    triggerEvent,
    testEditor,
} from '../utils.js';

const TAB_WIDTH = 40;

describe('Tabs', () => {
    const oeTab =  (size, contenteditable = true) => (
        `<span class="oe-tabs"` +
            (contenteditable ? '' : ' contenteditable="false"') +
            (size ?` style="width: ${size}px;"` : '') +
        `>\u0009</span>\u200B`
    );
    describe('insert tabulation', () => {
        it('should insert a tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab(32.8906, false)}[]b</p>`,
                contentAfter: `<p>a${oeTab(32.8906)}[]b</p>`,
            });
        });
        it('should keep selection and insert a tab character at the beginning of the paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[xxx]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[xxx]b</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[xxx]b</p>`,
            });
        });
        it('should insert two tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab(32.8906, false)}${oeTab(TAB_WIDTH, false)}[]b</p>`,
                contentAfter: `<p>a${oeTab(32.8906)}${oeTab(TAB_WIDTH)}[]b</p>`,
            });
        });
        it('should insert two tab characters with one char between them', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                    await insertText(editor,'a');
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab'});
                },
                contentAfterEdit: `<p>a${oeTab(32.8906, false)}a${oeTab(32.8906, false)}[]b</p>`,
                contentAfter: `<p>a${oeTab(32.8906)}a${oeTab(32.8906)}[]b</p>`,
            });
        });
        it('should insert tab characters at the beginning of two separate paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[b</p>` +
                               `<p>c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
            });
        });
        it('should insert tab characters at the beginning of two separate indented paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[b</p>` +
                               `<p>${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}c]d</p>`,
            });
        });
        it('should insert tab characters at the beginning of two separate paragraphs (one indented, the other not)', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[b</p>` +
                               `<p>c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[b</p>` +
                               `<p>${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}c]d</p>`,
            });
        });
        it('should insert tab characters at the beginning of two separate paragraphs with tabs in them', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<p>c${oeTab()}]d${oeTab()}</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}c${oeTab(32.8906, false)}]d${oeTab(32, false)}</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<p>${oeTab(TAB_WIDTH)}c${oeTab(32.8906)}]d${oeTab(32)}</p>`,
            });
        });
        it('should insert tab characters at the beginning of three separate blocks', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>a[b</p>` +
                               `<h1>cd</h1>` +
                               `<blockquote>e]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>xxx</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<h1>${oeTab(TAB_WIDTH, false)}cd</h1>` +
                                  `<blockquote>${oeTab(TAB_WIDTH, false)}e]f</blockquote>` +
                                  `<h4>zzz</h4>`,
                contentAfter: `<p>xxx</p>` +
                              `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<h1>${oeTab(TAB_WIDTH)}cd</h1>` +
                              `<blockquote>${oeTab(TAB_WIDTH)}e]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should insert tab characters at the beginning of three separate indented blocks', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}xxx</p>` +
                               `<p>${oeTab()}a[b</p>` +
                               `<h1>${oeTab()}cd</h1>` +
                               `<blockquote>${oeTab()}e]f</blockquote>` +
                               `<h4>${oeTab()}zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}xxx</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<h1>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}cd</h1>` +
                                  `<blockquote>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}e]f</blockquote>` +
                                  `<h4>${oeTab(TAB_WIDTH, false)}zzz</h4>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}xxx</p>` +
                              `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<h1>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}cd</h1>` +
                              `<blockquote>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}e]f</blockquote>` +
                              `<h4>${oeTab(TAB_WIDTH)}zzz</h4>`,
            });
        });
        it('should insert tab characters at the beginning of three separate blocks of mixed indentation', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>${oeTab()}${oeTab()}a[b</p>` +
                               `<h1>${oeTab()}cd</h1>` +
                               `<blockquote>e]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>xxx</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<h1>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}cd</h1>` +
                                  `<blockquote>${oeTab(TAB_WIDTH, false)}e]f</blockquote>` +
                                  `<h4>zzz</h4>`,
                contentAfter: `<p>xxx</p>` +
                              `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<h1>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}cd</h1>` +
                              `<blockquote>${oeTab(TAB_WIDTH)}e]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should insert tab characters at the beginning of three separate blocks with tabs in them', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<h1>c${oeTab()}d${oeTab()}</h1>` +
                               `<blockquote>e${oeTab()}]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>xxx</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<h1>${oeTab(TAB_WIDTH, false)}c${oeTab(25.7969, false)}d${oeTab(22.2031, false)}</h1>` +
                                  `<blockquote>${oeTab(TAB_WIDTH, false)}e${oeTab(32.8906, false)}]f</blockquote>` +
                                  `<h4>zzz</h4>`,
                contentAfter: `<p>xxx</p>` +
                              `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<h1>${oeTab(TAB_WIDTH)}c${oeTab(25.7969)}d${oeTab(22.2031)}</h1>` +
                              `<blockquote>${oeTab(TAB_WIDTH)}e${oeTab(32.8906)}]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should insert tab characters in blocks and indent lists', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<ul>` +
                                    `<li>c${oeTab()}d${oeTab()}</li>` +
                                    `<li class="oe-nested"><ul><li>${oeTab()}e${oeTab()}</li></ul></li>` +
                                `</ul>` +
                               `<blockquote>f${oeTab()}]g</blockquote>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab'}),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}${oeTab(TAB_WIDTH, false)}a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<ul>` +
                                        `<li class="oe-nested"><ul><li>c${oeTab(32.8906, false)}d${oeTab(32, false)}</li>` +
                                        `<li class="oe-nested"><ul><li>${oeTab(TAB_WIDTH, false)}e${oeTab(32.8906, false)}</li></ul></li></ul></li>` +
                                  `</ul>` +
                                  `<blockquote>${oeTab(TAB_WIDTH, false)}f${oeTab(34.6719, false)}]g</blockquote>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}${oeTab(TAB_WIDTH)}a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<ul>` +
                                    `<li class="oe-nested"><ul><li>c${oeTab(32.8906)}d${oeTab(32)}</li>` +
                                    `<li class="oe-nested"><ul><li>${oeTab(TAB_WIDTH)}e${oeTab(32.8906)}</li></ul></li></ul></li>` +
                              `</ul>` +
                              `<blockquote>${oeTab(TAB_WIDTH)}f${oeTab(34.6719)}]g</blockquote>`,
            });
        });
    });
    describe('delete backward tabulation', () => {
        it('should remove one tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]${oeTab(32.8906)}b</p>`,
            });
        });
        it('should remove two tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}${oeTab()}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}${oeTab()}[]${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]${oeTab(32.8906)}b</p>`,
            });
        });
        it('should remove three tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}${oeTab()}${oeTab()}[]b</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
        });
    });
    describe('delete forward tabulation', () => {
        it('should remove one tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab(32.8906)}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a${oeTab(32.8906)}[]b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab(32.8906)}${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]${oeTab(32.8906)}b3</p>`,
            });
        });
        it('should remove two tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab(32.8906)}${oeTab()}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab(32.8906)}${oeTab()}${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]${oeTab(32.8906)}b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a${oeTab(32.8906)}[]b3</p>`,
            });
        });
        it('should remove three tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[]${oeTab(32.8906)}${oeTab()}${oeTab()}b</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteForward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b</p>`,
            });
        });
    });
    describe('delete mixed tabulation', () => {
        it('should remove all tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}b1</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b1</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}b2</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b2</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}${oeTab()}[]${oeTab()}b3</p>`,
                stepFunction: async editor => {
                    await deleteBackward(editor);
                    await deleteForward(editor);
                    await deleteBackward(editor);
                },
                contentAfter: `<p>a[]b3</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab(32.8906)}[]${oeTab()}${oeTab()}b4</p>`,
                stepFunction: async editor => {
                    await deleteForward(editor);
                    await deleteBackward(editor);
                    await deleteForward(editor);
                },
                contentAfter: `<p>a[]b4</p>`,
            });
        });
    });
    describe('remove tabulation with shift+tab', () => {
        it('should not remove a non-leading tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>a${oeTab()}[]b</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>a${oeTab(32.8906, false)}[]b</p>`,
                contentAfter: `<p>a${oeTab(32.8906)}[]b</p>`,
            });
        });
        it('should remove a tab character', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[]b</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p>a[]b</p>`,
            });
        });
        it('should keep selection and remove a tab character from the beginning of the paragraph', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[xxx]b</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p>a[xxx]b</p>`,
            });
        });
        it('should remove two tab characters', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}${oeTab()}a[]b</p>`,
                stepFunction: async editor => {
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true });
                    await triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true });
                },
                contentAfter: `<p>a[]b</p>`,
            });
        });
        it('should remove tab characters from the beginning of two separate paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[b</p>` +
                               `<p>${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p>a[b</p>` +
                              `<p>c]d</p>`,
            });
        });
        it('should remove tab characters from the beginning of two separate double-indented paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}${oeTab()}a[b</p>` +
                               `<p>${oeTab()}${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH, false)}c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>${oeTab(TAB_WIDTH)}c]d</p>`,
            });
        });
        it('should remove tab characters from the beginning of two separate paragraphs of mixed indentations', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}${oeTab()}a[b</p>` +
                               `<p>${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<p>c]d</p>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<p>c]d</p>`,
            });
            await testEditor(BasicEditor, {
                contentBefore: `<p>a[b</p>` +
                               `<p>${oeTab()}c]d</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p>a[b</p>` +
                              `<p>c]d</p>`,
            });
        });
        it('should remove tab characters from the beginning of two separate paragraphs with tabs in them', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<p>c${oeTab()}]d${oeTab()}</p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<p>c${oeTab(32.8906, false)}]d${oeTab(32, false)}</p>`,
                contentAfter: `<p>a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<p>c${oeTab(32.8906)}]d${oeTab(32)}</p>`,
            });
        });
        it('should remove tab characters from the beginning of three separate blocks', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>${oeTab()}a[b</p>` +
                               `<h1>${oeTab()}cd</h1>` +
                               `<blockquote>${oeTab()}e]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p>xxx</p>` +
                              `<p>a[b</p>` +
                              `<h1>cd</h1>` +
                              `<blockquote>e]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should remove tab characters from the beginning of three separate blocks of mixed indentation', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>${oeTab()}${oeTab()}a[b</p>` +
                               `<h1>${oeTab()}cd</h1>` +
                               `<blockquote>e]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>xxx</p>` +
                                  `<p>${oeTab(TAB_WIDTH, false)}a[b</p>` +
                                  `<h1>cd</h1>` +
                                  `<blockquote>e]f</blockquote>` +
                                  `<h4>zzz</h4>`,
                contentAfter: `<p>xxx</p>` +
                              `<p>${oeTab(TAB_WIDTH)}a[b</p>` +
                              `<h1>cd</h1>` +
                              `<blockquote>e]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should remove tab characters from the beginning of three separate blocks with tabs in them', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>xxx</p>` +
                               `<p>${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<h1>${oeTab()}c${oeTab()}d${oeTab()}</h1>` +
                               `<blockquote>${oeTab()}e${oeTab()}]f</blockquote>` +
                               `<h4>zzz</h4>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>xxx</p>` +
                                  `<p>a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<h1>c${oeTab(25.7969, false)}d${oeTab(22.2031, false)}</h1>` +
                                  `<blockquote>e${oeTab(32.8906, false)}]f</blockquote>` +
                                  `<h4>zzz</h4>`,
                contentAfter: `<p>xxx</p>` +
                              `<p>a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<h1>c${oeTab(25.7969)}d${oeTab(22.2031)}</h1>` +
                              `<blockquote>e${oeTab(32.8906)}]f</blockquote>` +
                              `<h4>zzz</h4>`,
            });
        });
        it('should remove tab characters from the beginning of blocks and outdent lists', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}${oeTab()}a[${oeTab()}b${oeTab()}</p>` +
                               `<ul>` +
                                    `<li class="oe-nested"><ul><li>c${oeTab()}d${oeTab()}</li>` +
                                    `<li class="oe-nested"><ul><li>${oeTab()}e${oeTab()}</li></ul></li></ul></li>` +
                               `</ul>` +
                               `<blockquote>${oeTab()}f${oeTab()}]g</blockquote>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfterEdit: `<p>${oeTab(TAB_WIDTH, false)}a[${oeTab(32.8906, false)}b${oeTab(32, false)}</p>` +
                                  `<ul>` +
                                        `<li>c${oeTab(32.8906, false)}d${oeTab(32, false)}</li>` +
                                        `<li class="oe-nested"><ul><li>${oeTab(TAB_WIDTH, false)}e${oeTab(32.8906, false)}</li></ul></li>` +
                                  `</ul>` +
                                  `<blockquote>f${oeTab(34.6719, false)}]g</blockquote>`,
                contentAfter: `<p>${oeTab(TAB_WIDTH)}a[${oeTab(32.8906)}b${oeTab(32)}</p>` +
                              `<ul>` +
                                    `<li>c${oeTab(32.8906)}d${oeTab(32)}</li>` +
                                    `<li class="oe-nested"><ul><li>${oeTab(TAB_WIDTH)}e${oeTab(32.8906)}</li></ul></li>` +
                              `</ul>` +
                              `<blockquote>f${oeTab(34.6719)}]g</blockquote>`,
            });
        });
        it('should remove a tab character from formatted text', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p><strong>${oeTab()}a[]b</strong></p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p><strong>a[]b</strong></p>`,
            });
        });
        it('should remove tab characters from the beginning of two separate formatted paragraphs', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p>${oeTab()}<strong>a[b</strong></p>` +
                               `<p>${oeTab()}<strong>c]d</strong></p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p><strong>a[b</strong></p>` +
                              `<p><strong>c]d</strong></p>`,
            });
        });
        it('should remove a tab character from styled text', async () => {
            await testEditor(BasicEditor, {
                contentBefore: `<p><font style="background-color: rgb(255,255,0);">${oeTab()}a[]b</font></p>`,
                stepFunction: editor => triggerEvent(editor.editable, 'keydown', { key: 'Tab', shiftKey: true }),
                contentAfter: `<p><font style="background-color: rgb(255,255,0);">a[]b</font></p>`,
            });
        });
    });
});
