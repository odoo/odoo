odoo.define('web.control_panel_model_tests', function (require) {
    "use strict";

    const ControlPanelModel = require('web.ControlPanelModel');
    const makeTestEnvironment = require('web.test_env');

    function createControlPanelModel(config = {}) {
        return new ControlPanelModel(Object.assign(
            { env: makeTestEnvironment() },
            config
        ));
    }
    function sanitizeFilters(model) {
        return Object.values(model.state.filters).map(filter => {
            const copy = Object.assign({}, filter);
            delete copy.groupId;
            delete copy.groupNumber;
            delete copy.id;
            return copy;
        });
    }

    QUnit.module('ControlPanelModel', {
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

        QUnit.test('empty arch', function (assert) {
            assert.expect(1);

            const model = createControlPanelModel();
            assert.deepEqual(sanitizeFilters(model), [{ type: 'timeRange' }]);
        });

        QUnit.test('one field tag', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field"
                },
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('one separator tag', function (assert) {
            assert.expect(1);
            const arch = `
            <search>
                <separator/>
            </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
            assert.deepEqual(sanitizeFilters(model), [{ type: 'timeRange' }]);
        });

        QUnit.test('one separator tag and one field tag', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <separator/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Bar",
                    fieldName: "bar",
                    fieldType: "many2one",
                    type: "field"
                },
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('one filter tag', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter" string="Hello" domain="[]"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: "Hello",
                    domain: "[]",
                    type: "filter",
                },
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('one groupBy tag', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="groupby" string="Hi" context="{ 'group_by': 'date_field:day'}"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    defaultOptionId: "day",
                    description: "Hi",
                    fieldName: "date_field",
                    fieldType: "date",
                    hasOptions: true,
                    type: "groupBy",
                },
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('two filter tags', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter_1" string="Hello One" domain="[]"/>
                    <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
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
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('two filter tags separated by a separator', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter_1" string="Hello One" domain="[]"/>
                    <separator/>
                    <filter name="filter_2" string="Hello Two" domain="[('bar', '=', 3)]"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
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
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('one filter tag and one field', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <filter name="filter" string="Hello" domain="[]"/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
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
                { type: 'timeRange' },
            ]);
        });

        QUnit.test('two field tags', function (assert) {
            assert.expect(1);
            const arch = `
                <search>
                    <field name="foo"/>
                    <field name="bar"/>
                </search>`;
            const fields = this.fields;
            const model = createControlPanelModel({ viewInfo: { arch, fields } });
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
                { type: 'timeRange' },
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

            const model = createControlPanelModel({ viewInfo: { favoriteFilters } });
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
                { type: 'timeRange' }
            ]);

        });

        QUnit.test('process dynamic filters', async function (assert) {
            assert.expect(1);
            const dynamicFilters = [{
                description: 'Quick search',
                domain: [['id', 'in', [1, 3, 4]]]
            }];

            const model = createControlPanelModel({ dynamicFilters });
            assert.deepEqual(sanitizeFilters(model), [
                {
                    description: 'Quick search',
                    domain: "[[\"id\",\"in\",[1,3,4]]]",
                    isDefault: true,
                    type: 'filter'
                },
                { type: 'timeRange' },
            ]);

        });

        QUnit.test('falsy search defaults are not activated', async function (assert) {
            assert.expect(1);

            const actionContext = {
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
            const model = createControlPanelModel({ viewInfo: { arch, fields }, actionContext });
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
                { type: 'timeRange' },
            ]);

        });

    });
});
