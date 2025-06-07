/** @odoo-module */

import { BasicEditor, testEditor, unformat } from '../utils.js';

describe('Odoo fields', () => {
    describe('monetary field', () => {
        it('should make a span inside a monetary field be unremovable', async () => {
            const content = unformat(`
                <p>
                    <span data-oe-model="product.template" data-oe-id="27" data-oe-field="list_price" data-oe-type="monetary" data-oe-expression="product.list_price" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">
                        $&nbsp;
                        <span class="oe_currency_value">[]</span>
                    </span>
                </p>
            `);
            await testEditor(BasicEditor, {
                contentBefore: content,
                stepFunction: (editor) => editor.execCommand('oDeleteBackward'),
                contentAfter: content,
            });
        });
    });
    it('should remove data-oe-zws-empty-inline and zero-width space when emptying an inline field', async () => {
        await testEditor(BasicEditor, {
            contentBefore: `<p><span data-oe-model="product.template" data-oe-id="27" data-oe-field="name" data-oe-type="char" data-oe-expression="product.name" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">a[]</span></p>`,
            contentBeforeEdit: `<p><span data-oe-model="product.template" data-oe-id="27" data-oe-field="name" data-oe-type="char" data-oe-expression="product.name" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">a[]</span></p>`,
            stepFunction: (editor) => editor.execCommand('oDeleteBackward'),
            contentAfterEdit: `<p><span data-oe-model="product.template" data-oe-id="27" data-oe-field="name" data-oe-type="char" data-oe-expression="product.name" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable" data-oe-zws-empty-inline="">[]\u200b</span><br></p>`,
            contentAfter: `<p><span data-oe-model="product.template" data-oe-id="27" data-oe-field="name" data-oe-type="char" data-oe-expression="product.name" data-oe-xpath="/t[1]/div[1]/h3[2]/span[1]" class="o_editable">[]</span><br></p>`,
        });
    });
    it('should keep zero-width breaking space for empty inline editable', async () => {
        testEditor(BasicEditor, {
            contentBefore: '<div><span class="o_editable" data-oe-field="arch">\u200b</span></div>',
            stepFunction: async editor => {
                await editor.cleanForSave();
                const cleanContent = editor.editable.innerHTML;
                window.chai.assert.strictEqual(
                    cleanContent,
                    '<div><span class="o_editable" data-oe-field="arch" contenteditable="true">\u200b</span></div>'
                );
            },
            contentAfter: '<div><span class="o_editable" data-oe-field="arch" contenteditable="true">\u200b</span></div>',
        }, {
            isRootEditable: false,
            getContentEditableAreas: function (editor) {
                return [...editor.editable.querySelectorAll('span')];
            }
        });
    });
});
