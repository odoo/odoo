odoo.define('account.tax_group_custom_widget_tests', function (require) {
    "use strict";

    const fieldRegistry = require('web.field_registry_owl');
    const FormView = require('web.FormView');
    const testUtils = require('web.test_utils');

    const createView = testUtils.createView;

    QUnit.module('account', {
        beforeEach: function () {
            this.data = {
                'account.move': {
                    fields: {
                        amount_by_group: { string: "amount_by_group data", type: "binary" },
                        move_type: { string: 'Move Type', type: 'char' },
                        state: { string: 'State', type:'char' },
                        currency_id: { string: 'Currency', type: 'many2one', relation: 'res.currency' },
                    },
                    records: [{
                        id: 1,
                        amount_by_group: [['Tax 15%', 72.27, 500.00, '$ 72.27', '$ 500.00', 1, 2]],
                        move_type: 'in_invoice',
                        state: 'draft',
                        currency_id: 1,
                    }]
                },
                'res.currency': {
                    fields: {
                        name: { string: "Name", type: 'char' },
                        digits: { string: 'Digits', type: 'integer' },
                    },
                    records: [{
                        id: 1,
                        name: 'USD',
                        digits: [16, 2],
                    }],
                }
            };
        }
    }, function () {
        QUnit.module('Tax Group');

        QUnit.test('tax group custom field', async function (assert) {
            assert.expect(11);

            const taxGroup = fieldRegistry.get('tax-group-custom-field');
            taxGroup.patch('tax-group-patched', T => class extends T {
                _changeTaxValueByTaxGroup() {
                    assert.step("_changeTaxValueByTaxGroup");
                }
            });

            const form = await createView({
                View: FormView,
                model: 'account.move',
                data: this.data,
                arch: `<form>
                        <field name="move_type" invisible="1"/>
                        <field name="state" invisible="1"/>
                        <field name="currency_id" invisible="1"/>
                        <field name="amount_by_group" widget="tax-group-custom-field"/>
                    </form>`,
                res_id: 1,
                session: {
                    currencies: _.indexBy(this.data['res.currency'].records, 'id'),
                    get_currency: function (currencyId) {
                        return this.currencies[currencyId];
                    },
                },
            });

            assert.strictEqual(form.$('.o_field_widget[name="amount_by_group"]').text().replace(/[\s\n\r]+/g, ' '),
                "Tax 15%$ 72.27",
                "should display tax group information");

            await testUtils.form.clickEdit(form);
            assert.isVisible(form.$('.tax_group_edit'),
                "edit icon should be visible");
            assert.isNotVisible(form.$('.tax_group_edit_input'),
                "edit input should be invisible");

            await testUtils.dom.click(form.$('.o_field_widget[name="amount_by_group"] .tax_group_edit'));
            assert.isNotVisible(form.$('.tax_group_edit'),
                "edit icon should be visible");
            assert.isVisible(form.$('.tax_group_edit_input'),
                "edit input should be invisible");

            // do not change input box and trigger blur
            assert.strictEqual(document.activeElement, form.$('.tax_group_edit_input input')[0],
                "input should have the focus");
            form.$('.o_field_widget[name="amount_by_group"] .tax_group_edit_input input')[0]
                .dispatchEvent(new Event('blur'));
            await testUtils.nextTick();
            assert.isVisible(form.$('.tax_group_edit'),
                "edit icon should be visible");
            assert.isNotVisible(form.$('.tax_group_edit_input'),
                "edit input should be invisible");
            assert.verifySteps([]);

            // change input box and trigger blur
            await testUtils.dom.click(form.$('.o_field_widget[name="amount_by_group"] .tax_group_edit'));
            form.$('.o_field_widget[name="amount_by_group"] .tax_group_edit_input input').val(27.72);
            form.$('.o_field_widget[name="amount_by_group"] .tax_group_edit_input input')[0]
                .dispatchEvent(new Event('blur'));
            assert.verifySteps(['_changeTaxValueByTaxGroup']);

            form.destroy();
        });
    });
});
