odoo.define('web.groupby_menu_generator_tests', function (require) {
    "use strict";

    const CustomGroupByItem = require('web.CustomGroupByItem');
    const ActionModel = require('web/static/src/js/views/action_model.js');
    const testUtils = require('web.test_utils');

    const { createComponent } = testUtils;

    QUnit.module('Components', {}, function () {

        QUnit.module('CustomGroupByItem');

        QUnit.test('click on add custom group toggle group selector', async function (assert) {
            assert.expect(6);

            const cgi = await createComponent(CustomGroupByItem, {
                props: {
                    fields: [
                        { sortable: true, name: "date", string: 'Super Date', type: 'date' },
                    ],
                },
                env: {
                    searchModel: new ActionModel(),
                },
            });

            assert.strictEqual(cgi.el.innerText.trim(), "Add Custom Group");
            assert.hasClass(cgi.el, 'o_generator_menu');
            assert.strictEqual(cgi.el.children.length, 1);

            await testUtils.dom.click(cgi.el.querySelector('.o_generator_menu button.o_add_custom_group_by'));

            // Single select node with a single option
            assert.containsOnce(cgi, 'div > select.o_group_by_selector');
            assert.strictEqual(cgi.el.querySelector('div > select.o_group_by_selector option').innerText.trim(),
                "Super Date");

            // Button apply
            assert.containsOnce(cgi, 'button.o_apply_group_by');

            cgi.destroy();
        });

        QUnit.test('select a field name in Add Custom Group menu properly trigger the corresponding field', async function (assert) {
            assert.expect(4);

            const fields = [
                { sortable: true, name: 'candlelight', string: 'Candlelight', type: 'boolean' },
            ];
            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewGroupBy');
                    const field = args[0];
                    assert.deepEqual(field, fields[0]);
                }
            }
            const searchModel = new MockedSearchModel();
            const cgi = await createComponent(CustomGroupByItem, {
                props: { fields },
                env: { searchModel },
            });

            await testUtils.dom.click(cgi.el.querySelector('.o_generator_menu button.o_add_custom_group_by'));
            await testUtils.dom.click(cgi.el.querySelector('.o_generator_menu button.o_apply_group_by'));

            // The only thing visible should be the button 'Add Custome Group';
            assert.strictEqual(cgi.el.children.length, 1);
            assert.containsOnce(cgi, 'button.o_add_custom_group_by');

            cgi.destroy();
        });
    });
});
