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
});
