odoo.define('web.groupby_menu_generator_tests', function (require) {
    "use strict";

    const { CustomGroupByItem } = require('@web/search/group_by_menu/custom_group_by_item');
    const ActionModel = require('web.ActionModel');
    const testUtils = require('web.test_utils');

    const { createComponent } = testUtils;

    QUnit.module('Components', {}, function () {

        QUnit.module('CustomGroupByItem (legacy)');

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
            assert.hasClass(cgi.el, 'o_add_custom_group_menu');
            assert.strictEqual(cgi.el.children.length, 1);

            await testUtils.dom.click(cgi.el.querySelector('.o_add_custom_group_menu .dropdown-toggle'));

            // Single select node with a single option
            assert.containsOnce(cgi, 'div > select');
            assert.strictEqual(cgi.el.querySelector('div > select option').innerText.trim(),
                "Super Date");

            // Button apply
            assert.containsOnce(cgi, 'div > button.btn.btn-primary');
        });

        QUnit.test('select a field name in Add Custom Group menu properly trigger the corresponding field', async function (assert) {
            assert.expect(4);

            const fields = [
                { sortable: true, name: 'candlelight', string: 'Candlelight', type: 'boolean' },
            ];
            const searchModel = new ActionModel();
            const cgi = await createComponent(CustomGroupByItem, {
                props: {
                    fields,
                    onAddCustomGroup(fieldName) {
                        assert.deepEqual(fieldName, fields[0].name);
                    },
                },
                env: { searchModel },
            });

            await testUtils.dom.click(cgi.el.querySelector('.o_add_custom_group_menu .dropdown-toggle'));
            await testUtils.dom.click(cgi.el.querySelector('div > button.btn.btn-primary'));

            // The only things visible should be the button 'Add Custom Group' and the dropdown menu;
            assert.strictEqual(cgi.el.children.length, 2);
            assert.containsOnce(cgi, '.dropdown-toggle');
            assert.containsOnce(cgi, '.dropdown-menu');
        });
    });
});
