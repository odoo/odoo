odoo.define('web.filter_menu_generator_tests', function (require) {
    "use strict";

    const Domain = require('web.Domain');
    const CustomFilterItem = require('web.CustomFilterItem');
    const ActionModel = require('web.ActionModel');
    const pyUtils = require('web.py_utils');
    const testUtils = require('web.test_utils');

    const cpHelpers = require('@web/../tests/search/helpers');
    const { createComponent } = testUtils;

    const toggleAddCustomFilterStandalone = async (el) => {
        await cpHelpers.toggleMenu(el, "Add Custom Filter");
    };

    QUnit.module('Components', {
        beforeEach: function () {
            this.fields = {
                date_field: { name: 'date_field', string: "A date", type: 'date', searchable: true },
                date_time_field: { name: 'date_time_field', string: "DateTime", type: 'datetime', searchable: true },
                boolean_field: { name: 'boolean_field', string: "Boolean Field", type: 'boolean', default: true, searchable: true },
                binary_field: { name: 'binary_field', string: "Binary Field", type: 'binary', searchable: true },
                char_field: { name: 'char_field', string: "Char Field", type: 'char', default: "foo", trim: true, searchable: true },
                float_field: { name: 'float_field', string: "Floaty McFloatface", type: 'float', searchable: true },
                color: { name: 'color', string: "Color", type: 'selection', selection: [['black', "Black"], ['white', "White"]], searchable: true },
            };
        },
    }, function () {

        QUnit.module('CustomFilterItem (legacy)');

        QUnit.test('basic rendering', async function (assert) {
            assert.expect(16);

            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: {
                    searchModel: new ActionModel(),
                },
            });

            assert.strictEqual(cfi.el.innerText.trim(), "Add Custom Filter");
            assert.hasClass(cfi.el, 'o_add_custom_filter_menu');
            assert.strictEqual(cfi.el.children.length, 1);

            await toggleAddCustomFilterStandalone(cfi);

            // Single condition
            assert.containsOnce(cfi, '.o_filter_condition');
            assert.containsOnce(cfi, '.o_filter_condition select.o_generator_menu_field');
            assert.containsOnce(cfi, '.o_filter_condition select.o_generator_menu_operator');
            assert.containsOnce(cfi, '.o_filter_condition span.o_generator_menu_value');
            assert.containsNone(cfi, '.o_filter_condition .o_or_filter');
            assert.containsNone(cfi, '.o_filter_condition .o_generator_menu_delete');

            // no deletion allowed on single condition
            assert.containsNone(cfi, '.o_filter_condition > i.o_generator_menu_delete');

            // Buttons
            assert.containsOnce(cfi, 'button.o_apply_filter');
            assert.containsOnce(cfi, 'button.o_add_condition');

            assert.containsOnce(cfi, '.o_filter_condition');

            await cpHelpers.addCondition(cfi);

            assert.containsN(cfi, '.o_filter_condition', 2);
            assert.containsOnce(cfi, '.o_filter_condition .o_or_filter');
            assert.containsN(cfi, '.o_filter_condition .o_generator_menu_delete', 2);

            cfi.destroy();
        });

        QUnit.test('custom OR filter presets new condition from preceding', async function (assert) {
            assert.expect(4);

            const searchModel = new ActionModel();
            const cfi = await createComponent(CustomFilterItem, {
                props: {
                    fields: this.fields,
                },
                env: { searchModel },
            });

            // Open custom filter form
            await toggleAddCustomFilterStandalone(cfi);

            // Retrieve second selectable values for field and operator dropdowns
            const fieldSecondValue = cfi.el.querySelector('.o_generator_menu_field option:nth-of-type(2)').value;
            const operatorSecondValue = cfi.el.querySelector('.o_generator_menu_operator option:nth-of-type(2)').value;

            // Check if they really exist…
            assert.ok(!!fieldSecondValue);
            assert.ok(!!operatorSecondValue);

            // Add first filter condition
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), fieldSecondValue);
            await cpHelpers.editConditionOperator(cfi, 0, operatorSecondValue);

            // Add a second conditon on the filter being created
            await cpHelpers.addCondition(cfi);

            // Check the defaults for field and operator dropdowns
            assert.strictEqual(
                cfi.el.querySelector('.o_filter_condition:nth-of-type(2) .o_generator_menu_field').value,
                fieldSecondValue
            );
            assert.strictEqual(
                cfi.el.querySelector('.o_filter_condition:nth-of-type(2) .o_generator_menu_operator').value,
                operatorSecondValue
            );

            cfi.destroy();
        });

        QUnit.test('binary field: basic search', async function (assert) {
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
                description: 'Binary Field is set',
                domain: '[["binary_field","!=",False]]',
                type: 'filter',
            }];
            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'binary_field');
            await cpHelpers.applyFilter(cfi);

            // Updated value
            expectedFilters = [{
                description: 'Binary Field is not set',
                domain: '[["binary_field","=",False]]',
                type: 'filter',
            }];
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'binary_field');
            await cpHelpers.editConditionOperator(cfi, 0, '=');
            await cpHelpers.applyFilter(cfi);

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
                description: 'Color is "Black"',
                domain: '[["color","=","black"]]',
                type: 'filter',
            }];
            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'color');
            await cpHelpers.applyFilter(cfi);

            // Updated value
            expectedFilters = [{
                description: 'Color is "White"',
                domain: '[["color","=","white"]]',
                type: 'filter',
            }];
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'color');
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_value select'), 'white');
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });
        QUnit.test('selection field: no value', async function (assert) {
            assert.expect(2);

            this.fields.color.selection = [];
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
                description: 'Color is ""',
                domain: '[["color","=",""]]',
                type: 'filter',
            }];
            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'color');
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        })

        QUnit.test('adding a simple filter works', async function (assert) {
            assert.expect(7);

            delete this.fields.date_field;

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const preFilters = args[0];
                    const preFilter = preFilters[0];
                    assert.strictEqual(preFilter.type, 'filter');
                    assert.strictEqual(preFilter.description, 'Boolean Field is Yes');
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

            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'boolean_field');
            await cpHelpers.applyFilter(cfi);

            // The only things visible should be the button 'Add Custom Filter' and the menu;
            assert.strictEqual(cfi.el.children.length, 2);
            assert.containsOnce(cfi, 'button.dropdown-toggle');
            assert.containsOnce(cfi, '.dropdown-menu');

            cfi.destroy();
        });

        QUnit.test('filtering by ID interval works', async function (assert) {
            assert.expect(4);
            this.fields.id_field = { name: 'id_field', string: "ID", type: "id", searchable: true };

            const expectedDomains = [
                [['id_field','>', 10]],
                [['id_field','<=', 20]],
            ];

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

            async function testValue(operator, value) {
                // open filter menu generator, select ID field, switch operator, type value, then click apply
                await cpHelpers.editConditionField(cfi, 0, 'id_field');
                await cpHelpers.editConditionOperator(cfi, 0, operator);
                await cpHelpers.editConditionValue(cfi, 0,
                    value
                );
                await cpHelpers.applyFilter(cfi);
            }

            await toggleAddCustomFilterStandalone(cfi);
            for (const domain of [...expectedDomains]) {
                await testValue(domain[0][1], domain[0][2]);
            }

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
                await cpHelpers.editConditionField(cfi, 0, 'many2one_field');
                await cpHelpers.editConditionValue(cfi, 0,
                    value
                );
                await cpHelpers.applyFilter(cfi);
            }

            await toggleAddCustomFilterStandalone(cfi);
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

            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'date_time_field');

            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_field').value, 'date_time_field');
            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_operator').value, 'between');

            await cpHelpers.editConditionOperator(cfi, 0, '=');
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_filter_condition span.o_generator_menu_value input'), '02/22/2017 11:00:00'); // in TZ
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

            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'date_time_field');

            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_field').value, 'date_time_field');
            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_operator').value, 'between');

            const valueInputs = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');
            await testUtils.fields.editSelect(valueInputs[0], '02/22/2017 11:00:00'); // in TZ
            await testUtils.fields.editSelect(valueInputs[1], '02-22-2017 17:00:00'); // in TZ
            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });

        QUnit.test('default custom filter datetime', async function (assert) {
            assert.expect(5);

            class MockedSearchModel extends ActionModel {
                dispatch(method, ...args) {
                    assert.strictEqual(method, 'createNewFilters');
                    const domain = JSON.parse(args[0][0].domain);
                    assert.strictEqual(domain[0][2].split(' ')[1],
                        '04:00:00',
                        "domain should be in UTC format");
                    assert.strictEqual(domain[1][2].split(' ')[1],
                        '03:59:59',
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

            await toggleAddCustomFilterStandalone(cfi);
            await testUtils.fields.editSelect(cfi.el.querySelector('.o_generator_menu_field'), 'date_time_field');

            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_field').value, 'date_time_field');
            assert.strictEqual(cfi.el.querySelector('.o_generator_menu_operator').value, 'between');

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

            await toggleAddCustomFilterStandalone(cfi);
            await cpHelpers.addCondition(cfi);

            await cpHelpers.editConditionField(cfi, 0, "float_field");
            await cpHelpers.editConditionField(cfi, 1, "id");

            const [floatInput, idInput] = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');

            // Default values
            assert.strictEqual(floatInput.value, "0.0");
            assert.strictEqual(idInput.value, "0");

            // Float parsing
            await cpHelpers.editConditionValue(cfi, 0, "4.2");
            assert.strictEqual(floatInput.value, "4.2");
            await cpHelpers.editConditionValue(cfi, 0, "DefinitelyValidFloat");
            // String input in a number input gives "", which is parsed as 0
            assert.strictEqual(floatInput.value, "0.0");

            // Number parsing
            await cpHelpers.editConditionValue(cfi, 1, "4");
            assert.strictEqual(idInput.value, "4");
            await cpHelpers.editConditionValue(cfi, 1, "4.2");
            assert.strictEqual(idInput.value, "4");
            await cpHelpers.editConditionValue(cfi, 1, "DefinitelyValidID");
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

            await toggleAddCustomFilterStandalone(cfi);
            await cpHelpers.addCondition(cfi);

            await cpHelpers.editConditionField(cfi, 0, "float_field");

            const [floatInput] = cfi.el.querySelectorAll('.o_generator_menu_value .o_input');

            // Default values
            assert.strictEqual(floatInput.value, "0,0");

            // Float parsing
            await cpHelpers.editConditionValue(cfi, 0, '4,');
            assert.strictEqual(floatInput.value, "4,");
            await cpHelpers.editConditionValue(cfi, 0, '4,2');
            assert.strictEqual(floatInput.value, "4,2");
            await cpHelpers.editConditionValue(cfi, 0, '4,2,');
            assert.strictEqual(floatInput.value, "4,2");
            await cpHelpers.editConditionValue(cfi, 0, "DefinitelyValidFloat");
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
                            description: 'Boolean Field is No',
                            domain: '[["boolean_field","!=",True]]',
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

            await toggleAddCustomFilterStandalone(cfi);
            await cpHelpers.addCondition(cfi);
            await cpHelpers.addCondition(cfi);
            await cpHelpers.addCondition(cfi);
            await cpHelpers.addCondition(cfi);

            await cpHelpers.editConditionField(cfi, 0, 'date_field');
            await cpHelpers.editConditionValue(cfi, 0, '01/09/1997');

            await cpHelpers.editConditionField(cfi, 1, 'boolean_field');
            await cpHelpers.editConditionOperator(cfi, 1, '!=');

            await cpHelpers.editConditionField(cfi, 2, 'char_field');
            await cpHelpers.editConditionValue(cfi, 2, "I will be deleted anyway");

            await cpHelpers.editConditionField(cfi, 3, 'float_field');
            await cpHelpers.editConditionValue(cfi, 3, 7.2);

            await cpHelpers.editConditionField(cfi, 4, 'id');
            await cpHelpers.editConditionValue(cfi, 4, 9);

            await cpHelpers.removeCondition(cfi, 2);

            await cpHelpers.applyFilter(cfi);

            cfi.destroy();
        });
    });
});
