odoo.define('web.filter_menu_generator_tests', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const CustomFilterItem = require('web.CustomFilterItem');
    const ActionModel = require('web/static/src/js/views/action_model.js');
    const pyUtils = require('web.py_utils');
    const testUtils = require('web.test_utils');

    const cpHelpers = testUtils.controlPanel;
    const { createComponent } = testUtils;

    QUnit.module('Components', {
        beforeEach: function () {
            this.fields = {
                date_field: { name: 'date_field', string: "A date", type: 'date', searchable: true },
                date_time_field: { name: 'date_time_field', string: "DateTime", type: 'datetime', searchable: true },
                boolean_field: { name: 'boolean_field', string: "Boolean Field", type: 'boolean', default: true, searchable: true },
                char_field: { name: 'char_field', string: "Char Field", type: 'char', default: "foo", trim: true, searchable: true },
                float_field: { name: 'float_field', string: "Floaty McFloatface", type: 'float', searchable: true },
                color: { name: 'color', string: "Color", type: 'selection', selection: [['black', "Black"], ['white', "White"]], searchable: true },
            };
        },
    }, function () {

        QUnit.module('CustomFilterItem');

        QUnit.test('basic rendering', async function (assert) {
            assert.expect(17);

            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: {
                    searchModel: new ActionModel(),
                },
            });

            assert.strictEqual(cfi.el.innerText.trim(), "Add Custom Filter");
            assert.hasClass(cfi.el, 'o_generator_menu');
            assert.strictEqual(cfi.el.children.length, 1);

            await cpHelpers.toggleAddCustomFilter(cfi);

            // Single condition
            assert.containsOnce(cfi, 'div.o_filter_condition');
            assert.containsOnce(cfi, 'div.o_filter_condition > select.o_generator_menu_field');
            assert.containsOnce(cfi, 'div.o_filter_condition > select.o_generator_menu_operator');
            assert.containsOnce(cfi, 'div.o_filter_condition > span.o_generator_menu_value');
            assert.containsNone(cfi, 'div.o_filter_condition .o_or_filter');
            assert.containsNone(cfi, 'div.o_filter_condition .o_generator_menu_delete');

            // no deletion allowed on single condition
            assert.containsNone(cfi, 'div.o_filter_condition > i.o_generator_menu_delete');

            // Buttons
            assert.containsOnce(cfi, 'div.o_add_filter_menu');
            assert.containsOnce(cfi, 'div.o_add_filter_menu > button.o_apply_filter');
            assert.containsOnce(cfi, 'div.o_add_filter_menu > button.o_add_condition');

            assert.containsOnce(cfi, 'div.o_filter_condition');

            await testUtils.dom.click('button.o_add_condition');

            assert.containsN(cfi, 'div.o_filter_condition', 2);
            assert.containsOnce(cfi, 'div.o_filter_condition .o_or_filter');
            assert.containsN(cfi, 'div.o_filter_condition .o_generator_menu_delete', 2);

            cfi.destroy();
        });

        QUnit.test('selection field: default and updated value', async function (assert) {
            assert.expect(4);

            let expectedFilters;
            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    assert.deepEqual(preFilters, expectedFilters);
                }
            }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: { searchModel },
            });

            // Default value
            expectedFilters = [{
                description: 'Color is "black"',
                domain: '[["color","=","black"]]',
                type: 'filter',
            }];
            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'color');
            await cpHelpers.applyFilter(cfi);

            // Updated value
            expectedFilters = [{
                description: 'Color is "white"',
                domain: '[["color","=","white"]]',
                type: 'filter',
            }];
            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'color');
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_value select'), 'white');
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });

        QUnit.test('adding a simple filter works', async function (assert) {
            assert.expect(6);

            delete this.fields.date_field;

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const preFilter = preFilters[0];
                    assert.strictEqual(preFilter.type, 'filter');
                    assert.strictEqual(preFilter.description, 'Boolean Field is true');
                    assert.strictEqual(preFilter.domain, '[["boolean_field","=",True]]');
                }
            }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: { searchModel },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await cpHelpers.applyFilter(cfi);

            // The only thing visible should be the button 'Add Custome Filter';
            assert.strictEqual(cfi.el.children.length, 1);
            assert.containsOnce(cfi, 'button.o_add_custom_filter');

            cfi.destroy();
        });

        QUnit.test('commit search with an extended proposition with field char does not cause a crash', async function (assert) {
            assert.expect(12);

            this.fields.many2one_field = { name: 'many2one_field', string: "Trululu", type: "many2one", searchable: true };
            const expectedDomains = [
                [['many2one_field', 'ilike', `a`]],
                [['many2one_field', 'ilike', `"a"`]],
                [['many2one_field', 'ilike', `'a'`]],
                [['many2one_field', 'ilike', `'`]],
                [['many2one_field', 'ilike', `"`]],
                [['many2one_field', 'ilike', `\\`]],
            ];
            const testedValues = [`a`, `"a"`, `'a'`, `'`, `"`, `\\`];

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const preFilter = preFilters[0];
                    // this step combine a tokenization/parsing followed by a string formatting
                    let domain = pyUtils.assembleDomains([preFilter.domain]);
                    domain = Domain.prototype.stringToArray(domain);
                    assert.deepEqual(domain, expectedDomains.shift());
                }
            }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: { searchModel },
            });

            async function testValue(value) {
                // open filter menu generator, select trululu field and enter string `a`, then click apply
                await cpHelpers.toggleAddCustomFilter(cfi);
                await testUtils.fields.editSelect(cfi.el.querySelector('select.o_generator_menu_field'), 'many2one_field');
                await testUtils.fields.editInput(cfi.el.querySelector(
                    'div.o_filter_condition > span.o_generator_menu_value input'),
                    value
                );
                await cpHelpers.applyFilter(cfi);
            }

            for (const value of testedValues) {
                await testValue(value);
            }

            delete ActionModel.registry.map.testExtension;
            cfi.destroy();
        });

        QUnit.test('custom filter datetime with equal operator', async function (assert) {
            assert.expect(5);

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const preFilter = preFilters[0];
                    assert.strictEqual(preFilter.description,
                        'DateTime is equal to "02/22/2017 11:00:00"',
                        "description should be in localized format");
                    assert.deepEqual(preFilter.domain,
                        '[["date_time_field","=","2017-02-22 15:00:00"]]',
                        "domain should be in UTC format");
                    }
                }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                session: {
                    getTZOffset() {
                        return -240;
                    },
                },
                env: { searchModel },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'date_time_field');

            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_field').value, 'date_time_field');
            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_operator').value, 'between');

            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_operator'), '=');
            await testUtils.fields.editSelect(cfi.el.querySelector('div.o_filter_condition > span.o_generator_menu_value input'), '02/22/2017 11:00:00'); // in TZ
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });

        QUnit.test('custom filter datetime between operator', async function (assert) {
            assert.expect(5);

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const preFilter = preFilters[0];
                    assert.strictEqual(preFilter.description,
                        'DateTime is between "02/22/2017 11:00:00 and 02/22/2017 17:00:00"',
                        "description should be in localized format");
                    assert.deepEqual(preFilter.domain,
                        '[["date_time_field",">=","2017-02-22 15:00:00"]' +
                        ',["date_time_field","<=","2017-02-22 21:00:00"]]',
                        "domain should be in UTC format");
                }
            }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                session: {
                    getTZOffset() {
                        return -240;
                    },
                },
                env: { searchModel },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'date_time_field');

            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_field').value, 'date_time_field');
            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_operator').value, 'between');

            const valueInputs = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');
            await testUtils.fields.editSelect(valueInputs[0], '02/22/2017 11:00:00'); // in TZ
            await testUtils.fields.editSelect(valueInputs[1], '02-22-2017 17:00:00'); // in TZ
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });

        QUnit.test('input value parsing', async function (assert) {
            assert.expect(7);

            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: {
                    searchModel: new ActionModel(),
                },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.dom.click('button.o_add_condition');

            const [floatSelect, idSelect] = cfi.el.querySelectorAll('.o_generator_menu_field');
            await testUtils.fields.editSelect(floatSelect, 'float_field');
            await testUtils.fields.editSelect(idSelect, 'id');

            const [floatInput, idInput] = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');

            // Default values
            assert.strictEqual(floatInput.value, "0.0");
            assert.strictEqual(idInput.value, "0");

            // Float parsing
            await testUtils.fields.editInput(floatInput, "4.2");
            assert.strictEqual(floatInput.value, "4.2");
            await testUtils.fields.editInput(floatInput, "DefinitelyValidFloat");
            // String input in a number input gives "", which is parsed as 0
            assert.strictEqual(floatInput.value, "0.0");

            // Number parsing
            await testUtils.fields.editInput(idInput, "4");
            assert.strictEqual(idInput.value, "4");
            await testUtils.fields.editInput(idInput, "4.2");
            assert.strictEqual(idInput.value, "4");
            await testUtils.fields.editInput(idInput, "DefinitelyValidID");
            // String input in a number input gives "", which is parsed as 0
            assert.strictEqual(idInput.value, "0");

            cfi.destroy();
        });

        QUnit.test('input value parsing with language', async function (assert) {
            assert.expect(5);

            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: {
                    searchModel: new ActionModel(),
                    _t: Object.assign(s => s, { database: { parameters: { decimal_point: "," } }}),
                },
                translateParameters: {
                    decimal_point: ",",
                    thousands_sep: "",
                    grouping: [3, 0],
                },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.dom.click('button.o_add_condition');

            const [floatSelect] = cfi.el.querySelectorAll('.o_generator_menu_field');
            await testUtils.fields.editSelect(floatSelect, 'float_field');

            const [floatInput] = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');

            // Default values
            assert.strictEqual(floatInput.value, "0,0");

            // Float parsing
            await testUtils.fields.editInput(floatInput, '4,');
            assert.strictEqual(floatInput.value, "4,");
            await testUtils.fields.editInput(floatInput, '4,2');
            assert.strictEqual(floatInput.value, "4,2");
            await testUtils.fields.editInput(floatInput, '4,2,');
            assert.strictEqual(floatInput.value, "4,2");
            await testUtils.fields.editInput(floatInput, "DefinitelyValidFloat");
            // The input here is a string, resulting in a parsing error instead of 0
            assert.strictEqual(floatInput.value, "4,2");

            cfi.destroy();
        });

        QUnit.test('add custom filter with multiple values', async function (assert) {
            assert.expect(2);

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const expected = [
                        {
                            description: 'A date is equal to "01/09/1997"',
                            domain: '[["date_field","=","1997-01-09"]]',
                            type: "filter",
                        },
                        {
                            description: 'Boolean Field is true',
                            domain: '[["boolean_field","=",True]]',
                            type: "filter",
                        },
                        {
                            description: 'Floaty McFloatface is equal to "7.2"',
                            domain: '[["float_field","=",7.2]]',
                            type: "filter",
                        },
                        {
                            description: 'ID is "9"',
                            domain: '[["id","=",9]]',
                            type: "filter",
                        },
                    ];
                    assert.deepEqual(preFilters, expected,
                        "Conditions should be in the correct order witht the right values.");
                }
            }
            const searchModel = new MockedSearchModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: { searchModel },
            });

            await cpHelpers.toggleAddCustomFilter(cfi);
            await testUtils.dom.click('button.o_add_condition');
            await testUtils.dom.click('button.o_add_condition');
            await testUtils.dom.click('button.o_add_condition');
            await testUtils.dom.click('button.o_add_condition');

            function getCondition(index, selector) {
                const condition = cfi.el.querySelectorAll('.o_filter_condition')[index];
                return condition.querySelector(selector);
            }

            await testUtils.fields.editSelect(getCondition(0, '.o_generator_menu_field'), 'date_field');
            await testUtils.fields.editSelect(getCondition(0, '.o_generator_menu_value .o_input'), '01/09/1997');

            await testUtils.fields.editSelect(getCondition(1, '.o_generator_menu_field'), 'boolean_field');
            await testUtils.fields.editInput(getCondition(1, '.o_generator_menu_operator'), '!=');

            await testUtils.fields.editSelect(getCondition(2, '.o_generator_menu_field'), 'char_field');
            await testUtils.fields.editInput(getCondition(2, '.o_generator_menu_value .o_input'), "I will be deleted anyway");

            await testUtils.fields.editSelect(getCondition(3, '.o_generator_menu_field'), 'float_field');
            await testUtils.fields.editInput(getCondition(3, '.o_generator_menu_value .o_input'), 7.2);

            await testUtils.fields.editSelect(getCondition(4, '.o_generator_menu_field'), 'id');
            await testUtils.fields.editInput(getCondition(4, '.o_generator_menu_value .o_input'), 9);

            await testUtils.dom.click(getCondition(2, '.o_generator_menu_delete'));

            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });
    });
});
