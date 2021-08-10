odoo.define("web/static/tests/control_panel/control_panel_model_extension_tests.js", function (require) {
    "use strict";

    const ActionModel = require("web/static/src/js/views/action_model.js");
    const makeTestEnvironment = require('web.test_env');

    function createModel(params = {}) {
        const archs = (params.arch && { search: params.arch, }) || {};
        const { ControlPanel: controlPanelInfo, } = ActionModel.extractArchInfo(archs);
        const extensions = {
            ControlPanel: {
                context: params.context,
                archNodes: controlPanelInfo.children,
                dynamicFilters: params.dynamicFilters,
                favoriteFilters: params.favoriteFilters,
                env: makeTestEnvironment(),
                fields: params.fields,
            },
        };
        const model = new ActionModel(extensions);
        return model;
    }
    function sanitizeFilters(model) {
        const cpme = model.extensions[0].find(
            (ext) => ext.constructor.name === "ControlPanelModelExtension"
        );
        const filters = Object.values(cpme.state.filters);
        return filters.map(filter => {
            const copy = Object.assign({}, filter);
            delete copy.groupId;
            delete copy.groupNumber;
            delete copy.id;
            return copy;
        });
    }

    QUnit.module('ControlPanelModelExtension', {
        beforeEach() {
            this.fields = {
                display_name: { string: "Displayed name", type: 'char' },
                foo: { string: "Foo", type: "char", default: "My little Foo Value", store: true, sortable: true },
                date_field: { string: "Date", type: "date", store: true, sortable: true },
                float_field: { string: "Float", type: "float" },
                bar: { string: "Bar", type: "many2one", relation: 'partner' },
            };
        }
    }, function () {
        QUnit.module('Arch parsing');

        QUnit.test('empty arch', async function (assert) {
            assert.expect(1);
            const model = createModel();
            assert.deepEqual(sanitizeFilters(model), []);
        });

        QUnit.test('one field tag', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field"
                },
            ]);
        });

        QUnit.test('one separator tag', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <separator/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), []);
        });

        QUnit.test('one separator tag and one field tag', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <separator/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field"
                },
            ]);
        });

        QUnit.test('one filter tag', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter" string="Hello" domain="[]"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Hello",
                    domain: "[]",
                    type: "filter",
                },
            ]);
        });

        QUnit.test('one filter tag with date attribute', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="date_filter" string="Date" date="date_field"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            const dateFilterId = Object.values(model.get('filters'))[0].id;
            assert.deepEqual(sanitizeFilters(model), [
                {
                    defaultOptionId: "this_month",
                    description: "Date",
                    fieldName: "date_field",
                    fieldType: "date",
                    isDateFilter: true,
                    hasOptions: true,
                    type: "filter"
                  },
                  {
                    comparisonOptionId: "previous_period",
                    dateFilterId,
                    description: "Date: Previous Period",
                    type: "comparison"
                  },
                  {
                    comparisonOptionId: "previous_year",
                    dateFilterId,
                    description: "Date: Previous Year",
                    type: "comparison"
                  }
            ]);
        });

        QUnit.test('one groupBy tag', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="groupby" string="Hi" context="{ 'group_by': 'date_field:day'}"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    defaultOptionId: "day",
                    description: "Hi",
                    fieldName: "date_field",
                    fieldType: "date",
                    hasOptions: true,
                    type: "groupBy",
                },
            ]);
        });

        QUnit.test('two filter tags', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter_1" string="Hello One" domain="[]"/>
                    <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Hello One",
                    domain: "[]",
                    type: "filter",
                },
                {
                    description: "Hello Two",
                    domain: "[('bar', '=', 3)]",
                    type: "filter",
                },
            ]);
        });

        QUnit.test('two filter tags separated by a separator', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter_1" string="Hello One" domain="[]"/>
                    <separator/>
                    <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Hello One",
                    domain: "[]",
                    type: "filter",
                },
                {
                    description: "Hello Two",
                    domain: "[('bar', '=', 3)]",
                    type: "filter",
                },
            ]);
        });

        QUnit.test('one filter tag and one field', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter" string="Hello" domain="[]"/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Hello",
                    domain: "[]",
                    type: "filter",
                },
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field",
                },
            ]);
        });

        QUnit.test('two field tags', async function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <field name="foo"/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Foo",
                    fieldName: "foo",
                    fieldType: "char",
                    type: "field"
                },
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field"
                },
            ]);
        });

        QUnit.module('Preparing initial state');

        QUnit.test('process favorite filters', async function (assert) {
            assert.expect(1);
            const favoriteFilters = [{
                user_id: [2, "Mitchell Admin"],
                name: 'Sorted filter',
                id: 5,
                context: {
                    group_by: ['foo', 'bar']
                },
                sort: '["foo", "-bar"]',
                domain: "[('user_id', '=', uid)]",
            }];

            const model = createModel({ favoriteFilters });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    context: {},
                    description: "Sorted filter",
                    domain: "[('user_id', '=', uid)]",
                    groupBys: ['foo', 'bar'],
                    orderedBy: [
                        {
                            asc: true,
                            name: "foo"
                        },
                        {
                            asc: false,
                            name: "bar"
                        }
                    ],
                    removable: true,
                    serverSideId: 5,
                    type: "favorite",
                    userId: 2
                },
            ]);

        });

        QUnit.test('process dynamic filters', async function (assert) {
            assert.expect(1);
            const dynamicFilters = [{
                description: 'Quick search',
                domain: [['id', 'in', [1, 3, 4]]]
            }];

            const model = createModel({ dynamicFilters });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: 'Quick search',
                    domain: "[[\"id\",\"in\",[1,3,4]]]",
                    isDefault: true,
                    type: 'filter'
                },
            ]);

        });

        QUnit.test('falsy search defaults are not activated', async function (assert) {
            assert.expect(1);

            const context = {
                search_default_filter: false,
                search_default_bar: 0,
                search_default_groupby: 2,
            };
            const arch = `
                <search>
                    <filter name="filter" string="Hello" domain="[]"/>
                    <filter name="groupby" string="Goodbye" context="{'group_by': 'foo'}"/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createModel({ arch, fields, context });
            // only the truthy filter 'groupby' has isDefault true
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: 'Hello',
                    domain: "[]",
                    type: 'filter',
                },
                {
                    description: 'Bar',
                    fieldName: 'bar',
                    fieldType: 'many2one',
                    type: 'field',
                },
                {
                    defaultRank: 2,
                    description: 'Goodbye',
                    fieldName: 'foo',
                    fieldType: 'char',
                    isDefault: true,
                    type: 'groupBy',
                },
            ]);

        });

        QUnit.test('search defaults on X2M fields', async function (assert) {
            assert.expect(1);

            const context = {
                search_default_otom: [1, 2],
                search_default_mtom: [1, 2]
            };
            const fields = this.fields;
            fields.otom = { string: "O2M", type: "one2many", relation: 'partner' };
            fields.mtom = { string: "M2M", type: "many2many", relation: 'partner' };
            const arch = `
                <search>
                    <field name="otom"/>
                    <field name="mtom"/>
                </search>`;
            const model = createModel({ arch, fields, context });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    "defaultAutocompleteValue": {
                      "label": [1, 2],
                      "operator": "ilike",
                      "value": [1, 2]
                    },
                    "defaultRank": -10,
                    "description": "O2M",
                    "fieldName": "otom",
                    "fieldType": "one2many",
                    "isDefault": true,
                    "type": "field"
                },
                {
                    "defaultAutocompleteValue": {
                      "label": [1, 2],
                      "operator": "ilike",
                      "value": [1, 2]
                    },
                    "defaultRank": -10,
                    "description": "M2M",
                    "fieldName": "mtom",
                    "fieldType": "many2many",
                    "isDefault": true,
                    "type": "field"
                }
            ]);

        });

    });
});
