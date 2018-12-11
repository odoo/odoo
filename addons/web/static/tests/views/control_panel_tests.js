odoo.define('web.control_panel_tests', function (require) {
"use strict";

var ControlPanelView = require('web.ControlPanelView');
var testUtils = require('web.test_utils');

var createControlPanel = testUtils.createControlPanel;

function createControlPanelFactory(arch, fields, params) {
    params = params || {};
    arch = arch || "<search></search>";
    fields = fields || {};
    var viewInfo = {arch:  arch, fields: fields};
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
                    currentOptionId: false,
                    defaultOptionId: "day",
                    description: "Hi",
                    fieldName: "date_field",
                    fieldType: "date",
                    groupNumber: 2,
                    hasOptions: true,
                    isDefault: false,
                    options: [
                        {
                          description: "Day",
                          groupId: 1,
                          optionId: "day"
                        },
                        {
                          description: "Week",
                          groupId: 1,
                          optionId: "week"
                        },
                        {
                          description: "Month",
                          groupId: 1,
                          optionId: "month"
                        },
                        {
                          description: "Quarter",
                          groupId: 1,
                          optionId: "quarter"
                        },
                        {
                          description: "Year",
                          groupId: 1,
                          optionId: "year"
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
                  "description": "Hello One",
                  "domain": "[]",
                  "groupNumber": 2,
                  "isDefault": false,
                  "type": "filter"
                },
                {
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
                      description: "Hello One",
                      domain: "[]",
                      groupNumber: 2,
                      isDefault: false,
                      type: "filter"
                    }
                ],
                [
                    {
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

    QUnit.module('Control Panel Rendering');

    QUnit.test('invisible filters are not rendered', async function (assert) {
        assert.expect(2);
        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: "<search>" +
                        "<filter name=\"filterA\" string=\"A\" domain=\"[]\"/>" +
                        "<filter name=\"filterB\" string=\"B\" invisible=\"1\" domain=\"[]\"/>" +
                    "</search>",
            data: this.data,
            searchMenuTypes: ['filter'],
            context: {
                search_disable_custom_filters: true,
            },
        });
        testUtils.dom.click(controlPanel.$('.o_filters_menu_button'));
        assert.containsOnce(controlPanel, '.o_menu_item a:contains("A")');
        assert.containsNone(controlPanel, '.o_menu_item a:contains("B")');

        controlPanel.destroy();
    });
});
});
