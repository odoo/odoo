odoo.define('web.custom_checkbox_tests', function (require) {
    "use strict";

    const CustomCheckbox = require('web.CustomCheckbox');
    const testUtils = require('web.test_utils');

    const { createComponent, dom: testUtilsDom } = testUtils;

    QUnit.module('Components', {}, function () {

        QUnit.module('CustomCheckbox');

        QUnit.test('test checkbox: default values', async function(assert) {
            assert.expect(6);

            const checkbox = await createComponent(CustomCheckbox, {});

            assert.containsOnce(checkbox.el, 'input');
            assert.containsNone(checkbox.el, 'input:disabled');
            assert.containsOnce(checkbox.el, 'label');

            const input = checkbox.el.querySelector('input');
            assert.notOk(input.checked, 'checkbox should be unchecked');
            assert.ok(input.id.startsWith('checkbox-comp-'));

            await testUtilsDom.click(checkbox.el.querySelector('label'));
            assert.ok(input.checked, 'checkbox should be checked');
        });

        QUnit.test('test checkbox: custom values', async function(assert) {
            assert.expect(6);

            const checkbox = await createComponent(CustomCheckbox, {
                props: {
                    id: 'my-form-check',
                    disabled: true,
                    value: true,
                    text: 'checkbox',
                }
            });

            assert.containsOnce(checkbox.el, 'input');
            assert.containsOnce(checkbox.el, 'input:disabled');
            assert.containsOnce(checkbox.el, 'label');

            const input = checkbox.el.querySelector('input');
            assert.ok(input.checked, 'checkbox should be checked');
            assert.strictEqual(input.id, 'my-form-check');
            assert.ok(input.checked, 'checkbox should be checked');
        });
    });
});
