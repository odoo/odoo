odoo.define('web.control_panel_tests', function (require) {
"use strict";

const AbstractAction = require('web.AbstractAction');
const ControlPanelView = require('web.ControlPanelView');
const core = require('web.core');
const testUtils = require('web.test_utils');

const createActionManager = testUtils.createActionManager;
const createControlPanel = testUtils.createControlPanel;

function createControlPanelFactory(arch, fields) {
    arch = arch || "<search></search>";
    fields = fields || {};
    var viewInfo = {arch: arch, fields: fields};
    var controlPanelFactory = new ControlPanelView({viewInfo: viewInfo, context: {}});
    return controlPanelFactory;
}

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: 'char' },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", store: true, sortable: true},
                    date_field: {string: "Date", type: "date", store: true, sortable: true},
                    float_field: {string: "Float", type: "float"},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                },
                records: [],
                onchanges: {},
            },
        };
    }
}, function () {
    QUnit.module('ControlPanelView');

    QUnit.module('Control Panel Arch Parsing');

    QUnit.test('empty arch', function (assert) {
        assert.expect(1);

        var controlPanelFactory = createControlPanelFactory();
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [],
            "there should be no group at all"
        );
    });

    QUnit.test('parse one field tag', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<field name=\"bar\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [[{
                attrs: {
                    name: "bar",
                    string: "Bar"
                },
                autoCompleteValues: [],
                description: "bar",
                isDefault: false,
                type: "field"
            }]],
            "there should be one group with one field"
        );
    });

    QUnit.test('parse one separator tag', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<separator/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [],
            "there should be no group at all");
    });

    QUnit.test('parse one separator tag and one field tag', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<separator/>" +
                        "<field name=\"bar\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [[
                {
                  attrs: {
                    name: "bar",
                    string: "Bar"
                  },
                  autoCompleteValues: [],
                  description: "bar",
                  isDefault: false,
                  type: "field"
                }
            ]],
            "there should be one group with one field"
        );
    });

    QUnit.test('parse one filter tag', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<filter name=\"filter\" string=\"Hello\" " +
                        "domain=\"[]\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [[{
                context: {},
                description: "Hello",
                groupNumber: 2,
                domain: "[]",
                isDefault: false,
                type: "filter"
            }]],
            "there should be one group with one filter"
        );
    });

    QUnit.test('parse one groupBy tag', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<groupBy name=\"groupby\" string=\"Hi\" " +
                        "context=\"{\'group_by\': \'date_field:day\'}\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [[
                {
                    currentOptionIds: new Set(),
                    defaultOptionId: "day",
                    description: "Hi",
                    fieldName: "date_field",
                    fieldType: "date",
                    groupNumber: 2,
                    hasOptions: true,
                    isDefault: false,
                    options: [
                        {
                          description: "Year",
                          groupId: 1,
                          optionId: "year"
                        },
                        {
                          description: "Quarter",
                          groupId: 1,
                          optionId: "quarter"
                        },
                        {
                          description: "Month",
                          groupId: 1,
                          optionId: "month"
                        },
                        {
                          description: "Week",
                          groupId: 1,
                          optionId: "week"
                        },
                        {
                          description: "Day",
                          groupId: 1,
                          optionId: "day"
                        }
                      ],
                    type: "groupBy"
                }
            ]],
            "there should be one group with one groupBy with options"
        );
    });

    QUnit.test('parse two filter tags', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<filter name=\"filter_1\" string=\"Hello One\" " +
                        "domain=\"[]\"/>" +
                        "<filter name=\"filter_2\" string=\"Hello Two\" " +
                        "domain=\"[(\'bar\', \'=\', 3)]\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [[
                {
                  "context": {},
                  "description": "Hello One",
                  "domain": "[]",
                  "groupNumber": 2,
                  "isDefault": false,
                  "type": "filter"
                },
                {
                  "context": {},
                  "description": "Hello Two",
                  "domain": "[('bar', '=', 3)]",
                  "groupNumber": 2,
                  "isDefault": false,
                  "type": "filter"
                }
            ]],
            'there should be one group of two filters'
        );
    });

    QUnit.test('parse two filter tags separated by a separator', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<filter name=\"filter_1\" string=\"Hello One\" " +
                        "domain=\"[]\"/>" +
                        "<separator/>" +
                        "<filter name=\"filter_2\" string=\"Hello Two\" " +
                        "domain=\"[(\'bar\', \'=\', 3)]\"/>" +
                    "</search>";

        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [
                [
                    {
                      context: {},
                      description: "Hello One",
                      domain: "[]",
                      groupNumber: 2,
                      isDefault: false,
                      type: "filter"
                    }
                ],
                [
                    {
                      context: {},
                      description: "Hello Two",
                      domain: "[('bar', '=', 3)]",
                      groupNumber: 4,
                      isDefault: false,
                      type: "filter"
                    }
                ]
            ],
            "there should be two groups of one filter"
        );
    });

    QUnit.test('parse one filter tag and one field', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<filter name=\"filter\" string=\"Hello\" domain=\"[]\"/>" +
                        "<field name=\"bar\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [
                [
                    {
                        context: {},
                        description: "Hello",
                        domain: "[]",
                        groupNumber: 2,
                        isDefault: false,
                        type: "filter"
                    }
                ],
                [
                    {
                        attrs: {
                            name: "bar",
                            string: "Bar"
                        },
                        autoCompleteValues: [],
                        description: "bar",
                        isDefault: false,
                        type: "field"
                    }
                ]
            ],
            "there should be one group with a filter and one group with a field"
        );
    });

    QUnit.test('parse two field tags', function (assert) {
        assert.expect(1);
        var arch = "<search>" +
                        "<field name=\"foo\"/>" +
                        "<field name=\"bar\"/>" +
                    "</search>";
        var fields = this.data.partner.fields;
        var controlPanelFactory = createControlPanelFactory(arch, fields);
        assert.deepEqual(
            controlPanelFactory.loadParams.groups,
            [
                [
                    {
                        attrs: {
                            name: "foo",
                            string: "Foo"
                        },
                        autoCompleteValues: [],
                        description: "foo",
                        isDefault: false,
                        type: "field"
                    }
                ],
                [
                    {
                        attrs: {
                            name: "bar",
                            string: "Bar"
                        },
                        autoCompleteValues: [],
                        description: "bar",
                        isDefault: false,
                        type: "field"
                    }
                ]
            ],
            "there should be two groups of a single field"
        );
    });

    QUnit.module('Control Panel behaviour');

    QUnit.test('remove a facet with backspace', async function (assert) {
        assert.expect(2);

        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search><filter name=\"filterA\" string=\"A\" domain=\"[]\"/></search>",
            data: this.data,
            searchMenuTypes: ['filter'],
        });
        await testUtils.dom.click(controlPanel.$('.o_filters_menu_button'));
        await testUtils.dom.click($('.o_menu_item a'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'A',
            'should have a facet with A');

        // delete a facet
        controlPanel.$('input.o_searchview_input').trigger($.Event('keydown', {
            which: $.ui.keyCode.BACKSPACE,
            keyCode: $.ui.keyCode.BACKSPACE,
        }));
        await testUtils.nextTick();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
        'there should be no facet');

        // delete nothing (should not crash)
        controlPanel.$('input.o_searchview_input').trigger($.Event('keydown', {
            which: $.ui.keyCode.BACKSPACE,
            keyCode: $.ui.keyCode.BACKSPACE,
        }));
        await testUtils.nextTick();

        controlPanel.destroy();
    });

    QUnit.module('Control Panel Rendering');

    QUnit.test('default breadcrumb in abstract action', async function (assert) {
        assert.expect(1);

        const ConcreteAction = AbstractAction.extend({
            hasControlPanel: true,
        });
        core.action_registry.add('ConcreteAction', ConcreteAction);

        const actionManager = await createActionManager();
        await actionManager.doAction({id: 1,
            name: 'A Concrete Action',
            tag: 'ConcreteAction',
            type: 'ir.actions.client',
        });

        assert.strictEqual(actionManager.$('.breadcrumb').text(), 'A Concrete Action');

        actionManager.destroy();
    });

    QUnit.test('fields and filters with groups/invisible attribute are not always rendered but activable as search default', async function (assert) {
        assert.expect(15);
        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search>" +
                        "<field name=\"display_name\" string=\"Foo B\" invisible=\"1\"/>" +
                        "<field name=\"foo\" string=\"Foo A\"/>" +
                        "<filter name=\"filterA\" string=\"FA\" domain=\"[]\"/>" +
                        "<filter name=\"filterB\" string=\"FB\" invisible=\"1\" domain=\"[]\"/>" +
                        "<filter name=\"filterC\" string=\"FC\" invisible=\"not context.get('show_filterC')\"/>" +
                        "<filter name=\"groupByA\" string=\"GA\" context=\"{'group_by': 'date_field:day'}\"/>" +
                        "<filter name=\"groupByB\" string=\"GB\" context=\"{'group_by': 'date_field:day'}\" invisible=\"1\"/>" +
                    "</search>",
            data: this.data,
            searchMenuTypes: ['filter', 'groupBy'],
            viewOptions: {
                context: {
                    show_filterC: true,
                    search_default_display_name: 'value',
                    search_default_filterB: true,
                    search_default_groupByB: true,
                },
            },
        });

        // default filters/fields should be activated even if invisible
        assert.containsN(controlPanel, '.o_searchview_facet', 3);


        await testUtils.dom.click(controlPanel.$('.o_filters_menu_button'));
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("FA")');
        assert.containsNone(controlPanel, '.o_menu_item a:contains("FB")');
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("FC")');
        // default filter should be activated even if invisible
        assert.containsOnce(controlPanel, '.o_searchview_facet .o_facet_values:contains(FB)');

        await testUtils.dom.click(controlPanel.$('button span.fa-bars'));
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("GA")');
        assert.containsNone(controlPanel, '.o_menu_item a:contains("GB")');
        // default filter should be activated even if invisible
        assert.containsOnce(controlPanel, '.o_searchview_facet .o_facet_values:contains(GB)');

        assert.strictEqual(controlPanel.$('.o_searchview_facet').eq(0).text().replace(/[\s\t]+/g, ""), "FooBvalue");


        // 'a' key to filter nothing on bar
        controlPanel.$('.o_searchview_input').val('a');
        controlPanel.$('.o_searchview_input').trigger($.Event('keypress', { which: 65, keyCode: 65 }));
        await testUtils.nextTick();
        // the only item in autocomplete menu should be FooA: a
        assert.strictEqual(controlPanel.$('div.o_searchview_autocomplete').text().replace(/[\s\t]+/g, ""), "SearchFooAfor:A");
        controlPanel.$('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();


        // The items in the Filters menu and the Group By menu should be the same as before
        await testUtils.dom.click(controlPanel.$('.o_filters_menu_button'));
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("FA")');
        assert.containsNone(controlPanel, '.o_menu_item a:contains("FB")');
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("FC")');

        await testUtils.dom.click(controlPanel.$('button span.fa-bars'));
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("GA")');
        assert.containsNone(controlPanel, '.o_menu_item a:contains("GB")');


        controlPanel.destroy();
    });

    QUnit.test('invisible fields and filters with unknown related fields should not be rendered', async function (assert) {
        assert.expect(2);

        // This test case considers that the current user is not a member of
        // the "base.group_system" group and both "bar" and "date_field" fields
        // have field-level access control that limit access to them only from
        // that group.
        //
        // As MockServer currently does not support "groups" access control, we:
        //
        // - emulate field-level access control of fields_get() by removing
        //   "bar" and "date_field" from the model fields
        // - set filters with groups="base.group_system" as `invisible=1` in
        //   view to emulate the behavior of fields_view_get()
        //   [see ir.ui.view `_apply_group()`]

        delete this.data['partner'].fields['bar'];
        delete this.data['partner'].fields['date_field'];

        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search>" +
                        "<field name=\"foo\"/>" +
                        "<filter name=\"filterDate\" string=\"Date\" date=\"date_field\" default_period=\"last_365_days\" invisible=\"1\" groups=\"base.group_system\"/>" +
                        "<filter name=\"groupByBar\" string=\"Bar\" context=\"{'group_by': 'bar'}\" invisible=\"1\" groups=\"base.group_system\"/>" +
                    "</search>",
            data: this.data,
        });

        assert.containsNone(controlPanel, '.o_search_options .o_dropdown:contains("Filters")',
            "there should not be filter dropdown");
        assert.containsNone(controlPanel, '.o_search_options .o_dropdown:contains("Group By")',
            "there should not be groupby dropdown");

        controlPanel.destroy();
    });

    QUnit.test('Favorites Use by Default and Share are exclusive', async function (assert) {
        assert.expect(11);
        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search></search>",
            data: this.data,
            searchMenuTypes: ['favorite'],
        });
        testUtils.dom.click(controlPanel.$('.o_favorites_menu_button'));
        testUtils.dom.click(controlPanel.$('button.o_add_favorite'));
        var $checkboxes = controlPanel.$('input[type="checkbox"]');

        assert.strictEqual($checkboxes.length, 2,
            '2 checkboxes are present')

        assert.notOk($checkboxes[0].checked, 'Start: None of the checkboxes are checked (1)');
        assert.notOk($checkboxes[1].checked, 'Start: None of the checkboxes are checked (2)');

        testUtils.dom.click($checkboxes.eq(0));
        assert.ok($checkboxes[0].checked, 'The first checkbox is checked');
        assert.notOk($checkboxes[1].checked, 'The second checkbox is not checked');

        testUtils.dom.click($checkboxes.eq(1));
        assert.notOk($checkboxes[0].checked,
            'Clicking on the second checkbox checks it, and unchecks the first (1)');
        assert.ok($checkboxes[1].checked,
            'Clicking on the second checkbox checks it, and unchecks the first (2)');

        testUtils.dom.click($checkboxes.eq(0));
        assert.ok($checkboxes[0].checked,
            'Clicking on the first checkbox checks it, and unchecks the second (1)');
        assert.notOk($checkboxes[1].checked,
            'Clicking on the first checkbox checks it, and unchecks the second (2)');

        testUtils.dom.click($checkboxes.eq(0));
        assert.notOk($checkboxes[0].checked, 'End: None of the checkboxes are checked (1)');
        assert.notOk($checkboxes[1].checked, 'End: None of the checkboxes are checked (2)');

        controlPanel.destroy();
    });

    QUnit.test('load filter', async function (assert) {
        assert.expect(1);

        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search></search>",
            data: this.data,
            searchMenuTypes: ['filter'],
            intercepts: {
                load_filters: function (ev) {
                    ev.data.on_success([
                        {
                            user_id: [2,"Mitchell Admin"],
                            name: 'sorted filter',
                            id: 5,
                            context: {},
                            sort: "[\"foo\", \"-bar\"]",
                            domain: "[('user_id', '=', uid)]",
                        }
                    ]);
                }
            }
        });

         _.each(controlPanel.exportState().filters, function (filter) {
            if (filter.type === 'favorite') {
                assert.deepEqual(filter.orderedBy, 
                    [{
                        name: 'foo',
                        asc: true,
                    }, {
                        name: 'bar',
                        asc: false,
                    }],
                    'the filter should have the right orderedBy values');
            }
        });

        controlPanel.destroy();
    });

    QUnit.test('save filter', async function (assert) {
        assert.expect(1);

        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search></search>",
            data: this.data,
            searchMenuTypes: ['filter'],
            intercepts: {
                create_filter: function (ev) {
                    assert.strictEqual(ev.data.filter.sort, "[\"foo\",\"bar desc\"]",
                        'The right format for the string "sort" should be sent to the server');
                },
                get_controller_query_params: function (ev) {
                    ev.data.callback({
                        orderedBy: [
                            {
                                name: 'foo',
                                asc: true,
                            }, {
                                name: 'bar',
                                asc: false,
                            }
                        ]
                    });
                }
            }
        });

        controlPanel._onNewFavorite({
            data: {
                description: 'Morbier',
                type: 'favorite',
            },
            stopPropagation: function () {return;}
        });

        controlPanel.destroy();
    });

    QUnit.test('groupby menu is not rendered if searchMenuTypes does not have groupBy', async function (assert) {
        assert.expect(2);

        const controlPanel = await createControlPanel({
            model: 'partner',
            arch: `<search>
                <filter name="filterA" string="A" domain="[]"/>
                <groupBy name="groupby" string="Hi"
                    "context="{'group_by': 'bar'}"/>
                </search>`,
            data: this.data,
            searchMenuTypes: ['filter'],
        });

        assert.containsN(controlPanel, '.o_search_options .o_dropdown', 1,
            "there should be 1 dropdown for filter only");
        assert.containsNone(controlPanel, '.o_search_options .o_dropdown:contains("Group By")',
            "there should not be groupby dropdown");

        controlPanel.destroy();
    });
});
});
