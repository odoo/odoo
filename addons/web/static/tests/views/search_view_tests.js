odoo.define('web.search_view_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;
var createControlPanel = testUtils.createControlPanel;
var createView = testUtils.createView;
var patchDate = testUtils.mock.patchDate;
var session = require('web.session');

var controlPanelViewParameters = require('web.controlPanelViewParameters');
const PERIOD_OPTIONS_IDS = controlPanelViewParameters.PERIOD_OPTIONS.map(o => o.optionId);
const OPTION_GENERATOR_IDS = controlPanelViewParameters.OPTION_GENERATORS.map(o => o.optionId);

QUnit.module('Search View', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    date_field: {string: "Date", type: "date", store: true, sortable: true},
                    birthday: {string: "Birthday", type: "date", store: true, sortable: true},
                    foo: {string: "Foo", type: "char", store: true, sortable: true},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                    float_field: {string: "Float", type: "float", group_operator: 'sum'},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop", bar: 2, date_field: "2017-01-25", birthday: "1983-07-15", float_field: 1},
                    {id: 2, display_name: "Second record", foo: "blip", bar: 1, date_field: "2017-01-24", birthday: "1982-06-04",float_field: 2},
                    {id: 3, display_name: "Third record", foo: "gnap", bar: 1, date_field: "2017-01-13", birthday: "1985-09-13",float_field: 1.618},
                    {id: 4, display_name: "Fourth record", foo: "plop", bar: 2, date_field: "2017-02-25", birthday: "1983-05-05",float_field: -1},
                    {id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, date_field: "2016-01-25", birthday: "1800-01-01",float_field: 13},
                ],
            },
            pony: {
                fields: {
                    name: {string: 'Name', type: 'char'},
                },
                records: [
                    {id: 4, name: 'Twilight Sparkle'},
                    {id: 6, name: 'Applejack'},
                    {id: 9, name: 'Fluttershy'}
                ],
            },
        };

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
        }, {
            id: 2,
            name: 'Partners Action 2',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
            search_view_id: [2, 'search'],
        }, {
            id: 3,
            name: 'Partners Action 3',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'kanban']],
            search_view_id: [2, 'search'],
        }, {
            id: 4,
            name: 'Partners Action 4',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'graph']],
            search_view_id: [3, 'search'],
        }, {
            id: 5,
            name: 'Partners Action 5',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [4, 'search'],
        }, {
            id: 6,
            name: 'Partners Action 6',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [5, 'search'],
        }, {
            id: 7,
            name: 'Partners Action 7',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [6, 'search'],
        }, {
            id: 8,
            name: 'Partners Action 8',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [7, 'search'],
        }, {
            id: 9,
            name: 'Partners Action 9',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'pivot']],
            search_view_id: [5, 'search'],
        }, {
            id: 10,
            name: 'Partners Action 10',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'pivot']],
            search_view_id: [8, 'search'],
        }, {
            id: 11,
            name: 'Partners Action 11',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [8, 'search'],
        }, {
            id: 12,
            name: 'Partners Action 12',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[2, 'list']],
            search_view_id: [9, 'search'],
        }
        ];

        this.archs = {
            // list views
            'partner,false,list': '<tree><field name="foo"/></tree>',
            'partner,2,list': '<tree><field name="foo"/></tree>',

            // kanban views
            'partner,false,kanban': '<kanban><templates><t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click"><field name="foo"/></div>' +
                '</t></templates></kanban>',

            // graph views
            'partner,false,graph': '<graph>' +
                        '<field name="date_field" type="row" interval="day"/>' +
                        '<field name="float_field" type="measure"/>' +
                    '</graph>',

            // pivot views
            'partner,false,pivot': '<pivot>' +
                        '<field name="date_field" type="row" interval="day"/>' +
                        '<field name="float_field" type="measure"/>' +
                '</pivot>',

            // search views
            'partner,false,search': '<search>'+
                    '<filter string="candle" name="itsName" context="{\'group_by\': \'foo\'}"/>' +
                '</search>',
            'partner,2,search': '<search>'+
                    '<filter string="Date" name="coolName" context="{\'group_by\': \'date_field\'}"/>' +
                '</search>',
            'partner,3,search': '<search>'+
                    '<filter string="float" name="positive" domain="[(\'float_field\', \'>=\', 0)]"/>' +
                '</search>',
            'partner,4,search': '<search>'+
                    '<filter string="Date" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                '</search>',
            'partner,5,search': '<search>'+
                    '<filter string="Date Field Filter" name="positive" date="date_field"/>' +
                    '<filter string="Date Field Groupby" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                '</search>',
            'partner,6,search': '<search>'+
                    '<filter string="Date" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                    '<separator/>' +
                    '<filter string="Bar" name="superName" context="{\'group_by\': \'bar\'}"/>' +
                '</search>',
            'partner,7,search': '<search>'+
                    '<filter string="1" name="coolName1" date="date_field"/>' +
                    '<separator/>' +
                    '<filter string="2" name="coolName2" date="birthday"/>' +
                    '<separator/>' +
                    '<filter string="3" name="coolName3" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="4" name="coolName4" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="5" name="coolName5" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="6" name="coolName6" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="7" name="coolName7" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="8" name="coolName8" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="9" name="coolName9" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="10" name="coolName10" domain="[]"/>' +
                    '<separator/>' +
                    '<filter string="11" name="coolName11" domain="[]"/>' +
                '</search>',
            'partner,8,search': '<search>'+
                    '<field name="foo"/>' +
                    '<field name="date_field"/>' +
                    '<field name="birthday"/>' +
                    '<field name="bar" context="{\'bar\': self}"/>' +
                    '<field name="float_field"/>' +
                    '<filter string="Date Field Filter" name="positive" date="date_field"/>' +
                    '<filter string="Date Field Groupby" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                '</search>',
            'partner,9,search': '<search>'+
                '<filter string="float" name="positive" domain="[(\'date_field\', \'>=\', (context_today() + relativedelta()).strftime(\'%Y-%m-%d\'))]"/>' +
            '</search>',
            'partner,10,search': '<search>'+
                    '<field string="Foo" name="foo"/>' +
                    '<filter string="Date Field Filter" name="positive" date="date_field"/>' +
                    '<filter string="Date Field Groupby" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                '</search>',
        };


        // assuming that the current time is: 2017-03-22:01:00:00
        this.periodDomains = [
            // last 7 days (whole days)
            ['&', ["date_field", ">=", "2017-03-15"],["date_field", "<", "2017-03-22"]],
            // last 30 days
            ['&', ["date_field", ">=", "2017-02-20"],["date_field", "<", "2017-03-22"]],
            // last 365 days
            ['&', ["date_field", ">=", "2016-03-22"],["date_field", "<", "2017-03-22"]],
            // last 5 years
            ['&', ["date_field", ">=", "2012-03-22"],["date_field", "<", "2017-03-22"]],
            // today
            ['&', ["date_field", ">=", "2017-03-22"],["date_field", "<", "2017-03-23"]],
            // this week
            ['&', ["date_field", ">=", "2017-03-20"],["date_field", "<", "2017-03-27"]],
            // this month
            ['&', ["date_field", ">=", "2017-03-01"],["date_field", "<", "2017-04-01"]],
            // this quarter
            ['&', ["date_field", ">=", "2017-01-01"],["date_field", "<", "2017-04-01"]],
            // this year
            ['&', ["date_field", ">=", "2017-01-01"],["date_field", "<", "2018-01-01"]],
            // yesterday
            ['&', ["date_field", ">=", "2017-03-21"],["date_field", "<", "2017-03-22"]],
            // last week
            ['&', ["date_field", ">=", "2017-03-13"],["date_field", "<", "2017-03-20"]],
            // last month
            ['&', ["date_field", ">=", "2017-02-01"],["date_field", "<", "2017-03-01"]],
            // last quarter
            ['&', ["date_field", ">=", "2016-10-01"],["date_field", "<", "2017-01-01"]],
            // last year
            ['&', ["date_field", ">=", "2016-01-01"],["date_field", "<", "2017-01-01"]],
        ];

        this.basicDomains = [
            ["&",["date_field",">=","2017-03-01"],["date_field","<=","2017-03-31"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"]],
            ["&",["date_field",">=","2017-02-01"],["date_field","<=","2017-02-28"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-01-31"]],
            ["|",
                "&",["date_field",">=","2017-01-01"],["date_field","<=","2017-01-31"],
                "&",["date_field",">=","2017-10-01"],["date_field","<=","2017-12-31"]
            ],
            ["&",["date_field",">=","2017-10-01"],["date_field","<=","2017-12-31"]],
  	        ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-03-31"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"]],
            ["&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"]],
            ["|",
                "&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"],
                "&",["date_field",">=","2016-01-01"],["date_field","<=","2016-12-31"]
            ],
            ["|",
                "|",
                    "&",["date_field",">=","2017-01-01"],["date_field","<=","2017-12-31"],
                    "&",["date_field",">=","2016-01-01"],["date_field","<=","2016-12-31"],
                "&",["date_field",">=","2015-01-01"],["date_field","<=","2015-12-31"]
            ],
            ["|",
                "|",
                    "&", ["date_field",">=","2017-03-01"],["date_field","<=","2017-03-31"],
                    "&",["date_field",">=","2016-03-01"],["date_field","<=","2016-03-31"],
                "&",["date_field",">=","2015-03-01"],["date_field","<=","2015-03-31"]
            ]
        ];

        // assuming that the current time is: 2017-03-22:01:00:00
        this.previousPeriodDomains = [
            // last 7 days (whole days) - 1 week
            ['&', ["date_field", ">=", "2017-03-08"],["date_field", "<", "2017-03-15"]],
            // last 30 days - 30 days
            ['&', ["date_field", ">=", "2017-01-21"],["date_field", "<", "2017-02-20"]],
            // last 365 days
            ['&', ["date_field", ">=", "2015-03-23"],["date_field", "<", "2016-03-22"]],
            // last 5 years
            ['&', ["date_field", ">=", "2007-03-22"],["date_field", "<", "2012-03-22"]],
            // today - 1 day
            ['&', ["date_field", ">=", "2017-03-21"],["date_field", "<", "2017-03-22"]],
            // this week - 1 week
            ['&', ["date_field", ">=", "2017-03-13"],["date_field", "<", "2017-03-20"]],
            // this month - 1 month
            ['&', ["date_field", ">=", "2017-02-01"],["date_field", "<", "2017-03-01"]],
            // this quarter - 3 months
            ['&', ["date_field", ">=", "2016-10-01"],["date_field", "<", "2017-01-01"]],
            // this year - 1 year
            ['&', ["date_field", ">=", "2016-01-01"],["date_field", "<", "2017-01-01"]],
            // yesterday - 1 day
            ['&', ["date_field", ">=", "2017-03-20"],["date_field", "<", "2017-03-21"]],
            // last week - 1 week
            ['&', ["date_field", ">=", "2017-03-06"],["date_field", "<", "2017-03-13"]],
            // last month - 1 month
            ['&', ["date_field", ">=", "2017-01-01"],["date_field", "<", "2017-02-01"]],
            // last quarter - 3 months
            ['&', ["date_field", ">=", "2016-07-01"],["date_field", "<", "2016-10-01"]],
            // last year - 1 year
            ['&', ["date_field", ">=", "2015-01-01"],["date_field", "<", "2016-01-01"]],
        ];
    },
}, function () {
    QUnit.test('basic rendering', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        await actionManager.doAction(1);

        assert.strictEqual($('.o_searchview input.o_searchview_input')[0], document.activeElement,
            "searchview input should be focused");

        actionManager.destroy();
    });
    QUnit.test('navigation with facets', async function (assert) {
        assert.expect(4);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        await actionManager.doAction(1);

        // add a facet
        await testUtils.dom.click(actionManager.$('.o_dropdown_toggler_btn:contains(Group By)'));
        await testUtils.dom.click(actionManager.$('.o_menu_item a'));
        assert.strictEqual(actionManager.$('.o_searchview .o_searchview_facet').length, 1,
            "there should be one facet");
        assert.strictEqual(actionManager.$('.o_searchview input.o_searchview_input')[0], document.activeElement,
            "searchview input should be focused");

        // press left to focus the facet
        actionManager.$('.o_searchview_input_container').trigger($.Event('keydown', {
            which: $.ui.keyCode.LEFT,
            keyCode: $.ui.keyCode.LEFT,
        }));
        assert.strictEqual(actionManager.$('.o_searchview .o_searchview_facet')[0], document.activeElement,
            "the facet should be focused");

        // press right to focus the facet
        actionManager.$('.o_searchview_input_container').trigger($.Event('keydown', {
            which: $.ui.keyCode.RIGHT,
            keyCode: $.ui.keyCode.RIGHT,
        }));
        assert.strictEqual(actionManager.$('.o_searchview input.o_searchview_input')[0], document.activeElement,
            "searchview input should be focused");

        actionManager.destroy();
    });

    QUnit.test('default groupbys can be ordered', async function (assert) {
        assert.expect(7);

        const unpatchDate = patchDate(2019,6,31,13,43,0);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        this.archs['partner,5,search'] =
            '<search>'+
                '<field name="bar"/>' +
                '<filter string="Foo" name="foo" domain="[]" />' +
                '<filter string="Foo 2" name="foo_2" domain="[]" />' +
                '<filter string="Filter Date Field" name="date" date="date_field"/>' +
                '<filter string="Groupby Date Field Day" name="gb_day" context="{\'group_by\': \'date_field:day\'}"/>' +
                '<filter string="Groupby Foo" name="gb_foo" context="{\'group_by\': \'foo\'}"/>' +
                '<filter string="Groupby Bar" name="gb_bar" context="{\'group_by\': \'bar\'}"/>' +
            '</search>';
        this.actions[0].views = [[false, 'graph']],
        this.actions[0].search_view_id = [5, 'search'];
        this.actions[0].context = {
            search_default_foo: true,
            search_default_date: true,
            search_default_bar: 3,
            search_default_gb_foo: 1,
            search_default_gb_day: 5,
            search_default_gb_bar: true,
            time_ranges: {field: 'date_field', range: 'this_week'},
        };
        await actionManager.doAction(1);

        const $facetValues = $('.o_searchview .o_searchview_facet .o_facet_values span:not(.o_facet_values_sep)');
        const expectedLabels = [
            "Third record",
            "Foo",
            "Filter Date Field: July 2019",
            "Groupby Foo",
            "Groupby Date Field Day: Day",
            "Groupby Bar",
            "Date: This Week"
        ];

        for (let i = 0; i < expectedLabels.length; i++) {
            assert.strictEqual($facetValues.eq(i).text(), expectedLabels[i],
            `first facet value should be ${expectedLabels[i]}`);
        }
        actionManager.destroy();
        unpatchDate();
    });

    QUnit.module('GroupByMenu');

    QUnit.test('click on groupby filter adds a facet', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        await testUtils.dom.click($('.o_dropdown_toggler_btn:contains(Group By)'));
        await testUtils.dom.click($('.o_menu_item a'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'candle',
            'should have a facet with candle name');

        actionManager.destroy();
    });

    QUnit.test('remove a "Group By" facet properly unchecks groupbys in groupby menu', async function (assert) {
        assert.expect(2);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        await testUtils.dom.click($('.o_dropdown_toggler_btn:contains(Group By)'));
        await testUtils.dom.click($('.o_menu_item a'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'candle',
            'should have a facet with candle name');
        await testUtils.dom.click($('.o_facet_remove:first'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'there should be no facet');
        actionManager.destroy();
    });

    QUnit.test('change option of a "Group By" does not remove groupy in facet "Group By"', async function (assert) {
        assert.expect(3);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(2);
        await testUtils.dom.click($('span.fa-bars'));
        await testUtils.dom.click($('.o_submenu_switcher'));
        // Don't forget there is a hidden li.divider element at first place among children
        await testUtils.dom.click($('.o_item_option:nth-child(2)'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
        'should have a facet');
        await testUtils.dom.click($('.o_item_option:nth-child(3)'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 3,
            'should have three facet spans (two options and a separator between them)');
        await testUtils.dom.click($('.o_item_option:nth-child(2)'));
        await testUtils.dom.click($('.o_item_option:nth-child(3)'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'should have no facet');
        actionManager.destroy();
    });

    QUnit.test('select and unselect quickly groupby does not crash', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(3);
        await testUtils.dom.click($('span.fa-bars'));
        await testUtils.dom.click($('.o_menu_item:first'));
        await testUtils.dom.click($('.o_menu_item:first'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'should have a facet');
        actionManager.destroy();
    });

    QUnit.test('groupby selected within graph subview are not deleted when modifying search view content', async function (assert) {
        assert.expect(2);

        this.actions[3].flags = {isEmbedded: true};

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        await actionManager.doAction(4);
        await testUtils.dom.click($('.o_graph_controller .o_control_panel .o_cp_buttons button').eq(1));
        await testUtils.dom.click($('.o_graph_controller .o_group_by_menu .o_menu_item').eq(1));
        await testUtils.dom.click($('.o_graph_controller .o_group_by_menu .o_menu_item .o_item_option > .dropdown-item').eq(4));
        assert.doesNotHaveClass($('.o_graph_controller .o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');
        await testUtils.dom.click($('.o_search_options button span.fa-filter'));
        await testUtils.dom.click($('.o_filters_menu .o_menu_item a').first());
        await testUtils.dom.click($('.o_graph_controller .o_control_panel .o_cp_buttons button').eq(1));
        await testUtils.dom.click($('.o_graph_controller .o_group_by_menu .o_menu_item').eq(1));
        assert.doesNotHaveClass($('.o_graph_controller .o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected',
            'groupby should be still unselected');
        actionManager.destroy();
    });

    QUnit.test('group by a date field using interval works', async function (assert) {
            assert.expect(13);


        var groupbys = [
            ["date_field:day"],
            ["date_field:month"],
            ["birthday:month"],
            ["birthday:year"],
        ];

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/web_read_group') {
                    assert.deepEqual(args.kwargs.groupby, groupbys.shift());
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(5);
        // open menu 'Group By'
        await testUtils.dom.click($('.o_search_options .fa-bars'));
        // Open the groupby 'Date'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item'));
        // select option 'day'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]'));
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Day');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // select option 'month'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]'));
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]'));
        // data should be grouped by the field 'Date' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 3);
        // deactivate option 'month'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]'));
        // no groupby is applied
        assert.strictEqual($('div.o_facet_values span').length, 0);
        // open 'Add custom Groupby' menu
        await testUtils.dom.click($('.o_group_by_menu .o_add_custom_group'));
        // click on 'Apply' button
        await testUtils.dom.click($('.o_group_by_menu .o_generator_menu button'));
        // data should be grouped by the field 'Birthday' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // close first submenu
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_submenu_switcher').eq(0));
        // open submenu with interval options
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_submenu_switcher').eq(1));
        // deselect option 'month'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]'));
        // select option 'year'
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option').eq(0));
        // data should be grouped by the field 'Birthday' using the interval 'year'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Year');
        assert.strictEqual($('.o_content tr.o_group_header').length, 4);
        actionManager.destroy();
    });

    QUnit.test('a separator in groupbys does not cause problems', async function (assert) {
        assert.expect(6);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(7);
        // open menu 'Group By'
        await testUtils.dom.click($('span.fa-bars'));
        // open options menu
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item a:first'));
        // activate groupby with 'day' option
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]'));
        // activate the second groupby
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item > a').eq(1));
        assert.strictEqual($('.o_group_by_menu .o_menu_item').length, 2);
        assert.strictEqual($('.o_group_by_menu .o_menu_item > .dropdown-item.selected').length, 2);
        // deactivate second groupby
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item > a').eq(1));
        assert.hasClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0), 'selected');
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected');
        // remove facet
        await testUtils.dom.click($('.o_facet_remove'));
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0), 'selected');
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected');
        actionManager.destroy();
    });

    QUnit.module('FilterMenu');

    QUnit.test('Search date and datetime fields. Support of timezones', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.birth_datetime = {string: "Birth DateTime", type: "datetime", store: true, sortable: true};
        this.data.partner.records = this.data.partner.records.slice(0,-1); // exclude wrong date record

        async function stringToEvent ($element, string) {
            for (var i = 0; i < string.length; i++) {
                var keyAscii = string.charCodeAt(i);
                $element.val($element.val()+string[i]);
                await testUtils.nextTick();
                $element.trigger($.Event('keyup', {which: keyAscii, keyCode:keyAscii}));
                await testUtils.nextTick();
            }
        }

        var searchReadSequence = 0;
        var actionManager = await createActionManager({
            actions: [{
                id: 11,
                name: 'Partners Action 11',
                res_model: 'partner',
                type: 'ir.actions.act_window',
                views: [[3, 'list']],
                search_view_id: [9, 'search'],
            }],
            archs:  {
                'partner,3,list': '<tree>' +
                                      '<field name="foo"/>' +
                                      '<field name="birthday" />' +
                                      '<field name="birth_datetime" />' +
                                '</tree>',

                'partner,9,search': '<search>'+
                                        '<field name="birthday"/>' +
                                        '<field name="birth_datetime" />' +
                                    '</search>',
            },
            data: this.data,
            session: {
                getTZOffset: function() {
                    return 360;
                }
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReadSequence === 1) { // The 0th time is at loading
                        assert.deepEqual(args.domain, [["birthday", "=", "1983-07-15"]],
                            'A date should stay what the user has input, but transmitted in server\'s format');
                    } else if (searchReadSequence === 3) { // the 2nd time is at closing the first facet
                        assert.deepEqual(args.domain, [["birth_datetime", "=", "1983-07-14 18:00:00"]],
                            'A datetime should be transformed in UTC and transmitted in server\'s format');
                    }
                    searchReadSequence+=1;
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(11);

        // Date case
        var $autocomplete = $('.o_searchview_input');
        await stringToEvent($autocomplete, '07/15/1983');
        await testUtils.fields.triggerKey('up', $autocomplete, 'enter');

        assert.equal($('.o_searchview_facet .o_facet_values').text().trim(), '07/15/1983',
            'The format of the date in the facet should be in locale');

        // Close Facet
        await testUtils.dom.click($('.o_searchview_facet .o_facet_remove'));

        // DateTime case
        $autocomplete = $('.o_searchview_input');
        await stringToEvent($autocomplete, '07/15/1983 00:00:00');
        await testUtils.fields.triggerKey('down', $autocomplete, 'down');
        await testUtils.fields.triggerKey('up', $autocomplete, 'enter');

        assert.equal($('.o_searchview_facet .o_facet_values').text().trim(), '07/15/1983 00:00:00',
            'The format of the datetime in the facet should be in locale');

        actionManager.destroy();
    });

    QUnit.test('add a custom filter works', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        await testUtils.dom.click($('span.fa-filter'));
        await testUtils.dom.click($('.o_add_custom_filter'));
        await testUtils.dom.click($('.o_apply_filter'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'ID is \"0\"',
            'should have a facet with candle name');
        actionManager.destroy();
    });

    QUnit.test('deactivate a new custom filter works', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        await testUtils.dom.click($('span.fa-filter'));
        await testUtils.dom.click($('.o_add_custom_filter'));
        await testUtils.dom.click($('.o_apply_filter'));
        await testUtils.dom.click($('.o_menu_item'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'no facet should be in the search view');
        actionManager.destroy();
    });

    QUnit.test('filter by a date field using period works', async function (assert) {
        assert.expect(15);

        var self = this;

        this.archs['partner,4,search'] = '<search>'+
            '<filter string="AAA" name="some_filter" date="date_field" default_period="this_week"></filter>' +
        '</search>';

        var unpatchDate = patchDate(2017,2,22,1,0,0);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function(route, args) {
                if (route === '/web/dataset/search_read' && args.domain.length) {
                    assert.deepEqual(args.domain, self.basicDomains.shift());
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(5);

        // open menu 'Filter'
        await testUtils.dom.click($('.o_search_options .fa-filter'));
        // open menu options
        await testUtils.dom.click($('.o_menu_item'));

        var generatorIds = $('.o_menu_item .o_item_option')
                                .map(function() {return $(this).data('option_id');})
                                .toArray();

        assert.deepEqual(generatorIds, OPTION_GENERATOR_IDS,
            "10 basic period options should be available:");

        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="antepenultimate_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="fourth_quarter"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="antepenultimate_month"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="fourth_quarter"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="first_quarter"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="first_quarter"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_year"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_year"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_year"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="antepenultimate_year"]'));
        await testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_month"]'));
        actionManager.destroy();
        unpatchDate();
    });

    QUnit.test('`context` key in <filter> is used', async function (assert) {
        assert.expect(3);

        this.archs['partner,4,search'] = '<search>'+
            '<filter string="AAA" name="some_filter" context="{\'coucou_1\': 1}"></filter>' +
        '</search>';

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.context));
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(5);

        // select filter
        await testUtils.dom.click($('.o_search_options .fa-filter'));
        await testUtils.dom.click($('.o_menu_item:contains(AAA)'));

        assert.verifySteps([
            "{\"bin_size\":true}",
            "{\"coucou_1\":1,\"bin_size\":true}",
        ]);

        actionManager.destroy();
    });

    QUnit.test('Filter with JSON-parsable domain works', async function (assert) {
        assert.expect(1);

        var domain = [['foo' ,'=', 'Gently Weeps']];
        var xml_domain = JSON.stringify(domain);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, domain,
                        'A JSON parsable xml domain should be handled just like any other');
                }
                return this._super.apply(this, arguments);
            }
        });

        this.archs['partner,5,search'] =
            '<search>'+
                '<filter string="Foo" name="gently_weeps" domain="' + _.escape(xml_domain) + '" />' +
            '</search>';
        this.actions[0].search_view_id = [5, 'search'];
        this.actions[0].context = {search_default_gently_weeps: true};

        await actionManager.doAction(1);

        actionManager.destroy();
    });

    QUnit.test('filter with date attribute set as search_default', async function (assert) {
        assert.expect(1);

        const unpatchDate = patchDate(2019,6,31,13,43,0);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        this.archs['partner,5,search'] =
            '<search>'+
                '<filter string="Date" name="date_field" date="date_field" />' +
            '</search>';
        this.actions[0].search_view_id = [5, 'search'];
        this.actions[0].context = {search_default_date_field: true};

        await actionManager.doAction(1);

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(),
            "Date: July 2019",
            "There should be a filter facet with label 'Date: July 2019'");

        actionManager.destroy();
        unpatchDate();
    });

    QUnit.test('Custom Filter datetime with equal operator', async function (assert) {
        assert.expect(5);

        this.data.partner.fields.date_time_field = {string: "DateTime", type: "datetime", store: true, searchable: true};

        var searchReadCount = 0;
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
            mockRPC: async function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReadCount === 1) {
                        assert.deepEqual(args.domain,
                            [['date_time_field', '=', '2017-02-22 15:00:00']], // In UTC
                            'domain is correct'
                        );
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        // List view
        await actionManager.doAction(2);

        await testUtils.dom.click($('button:contains(Filters)'));
        await testUtils.dom.click($('.o_dropdown_menu .o_add_custom_filter'));
        assert.strictEqual($('.o_dropdown_menu select.o_searchview_extended_prop_field').val(), 'date_time_field',
            'the date_time_field should be selected in the custom filter');

        assert.strictEqual($('.o_dropdown_menu select.o_searchview_extended_prop_op').val(), 'between',
            'The between operator is selected');

        await testUtils.fields.editSelect($('.o_dropdown_menu select.o_searchview_extended_prop_op'), '=');

        assert.strictEqual($('.o_dropdown_menu select.o_searchview_extended_prop_op').val(), '=',
            'The equal operator is selected');

        await testUtils.fields.editAndTrigger($('.o_searchview_extended_prop_value input:first'), '02/22/2017 11:00:00', ['change']); // in TZ

        searchReadCount = 1;
        await testUtils.dom.click($('.o_dropdown_menu .o_apply_filter'));

        assert.strictEqual($('.o_dropdown_menu .dropdown-item.selected').text().trim(), 'DateTime is equal to "02/22/2017 11:00:00"',
            'Label of Filter is correct');

        actionManager.destroy();
    });

    QUnit.test('Custom Filter datetime between operator', async function (assert) {
        assert.expect(4);

        this.data.partner.fields.date_time_field = {string: "DateTime", type: "datetime", store: true, searchable: true};

        var searchReadCount = 0;
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            session: {
                getTZOffset: function () {
                    return -240;
                },
            },
            mockRPC: async function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchReadCount === 1) {
                        assert.deepEqual(args.domain,
                            [
                                '&', ['date_time_field', '>=', '2017-02-22 15:00:00'], ['date_time_field', '<=', '2017-02-22 21:00:00']  // In UTC
                            ],
                            'domain is correct'
                        );
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        // List view
        await actionManager.doAction(2);

        await testUtils.dom.click($('button:contains(Filters)'));
        await testUtils.dom.click($('.o_dropdown_menu .o_add_custom_filter'));
        assert.strictEqual($('.o_dropdown_menu select.o_searchview_extended_prop_field').val(), 'date_time_field',
            'the date_time_field should be selected in the custom filter');

        assert.strictEqual($('.o_dropdown_menu select.o_searchview_extended_prop_op').val(), 'between',
            'The between operator is selected');

        await testUtils.fields.editAndTrigger($('.o_searchview_extended_prop_value input:first'), '02/22/2017 11:00:00', ['change']); // in TZ
        await testUtils.fields.editAndTrigger($('.o_searchview_extended_prop_value input:last'), '02/22/2017 17:00:00', ['change']); // in TZ

        searchReadCount = 1;
        await testUtils.dom.click($('.o_dropdown_menu .o_apply_filter'));

        assert.strictEqual($('.o_dropdown_menu .dropdown-item.selected').text().trim(), 'DateTime is between "02/22/2017 11:00:00 and 02/22/2017 17:00:00"',
            'Label of Filter is correct');

        actionManager.destroy();
    });

    QUnit.module('Favorites Menu');

    QUnit.test('dynamic filters are saved dynamic', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                create_filter: function (ev) {
                    assert.equal(
                        ev.data.filter.domain,
                        `[("date_field", ">=", (context_today() + relativedelta()).strftime("%Y-%m-%d"))]`);
                },
            },
        });

        await actionManager.doAction(12);
        await testUtils.dom.click($('span.fa-filter'));
        await testUtils.dom.click($('.o_filters_menu .o_menu_item a'));
        await testUtils.dom.click($('span.fa-star'));
        await testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        await testUtils.fields.editInput($('div.o_favorite_name input'), 'name for favorite');
        await testUtils.dom.click($('.o_favorites_menu .o_save_favorite button'));
        actionManager.destroy();
    });

    QUnit.test('save search filter in modal', async function (assert) {
        assert.expect(5);
        this.data.partner.records.push({
            id: 7,
            display_name: "Partner 6",
        }, {
            id: 8,
            display_name: "Partner 7",
        }, {
            id: 9,
            display_name: "Partner 8",
        }, {
            id: 10,
            display_name: "Partner 9",
        });
        this.data.partner.fields.date_field.searchable = true;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                '<sheet>' +
                '<group>' +
                '<field name="bar"/>' +
                '</group>' +
                '</sheet>' +
                '</form>',
            archs: {
                'partner,false,list': '<tree><field name="display_name"/></tree>',
                'partner,false,search': '<search><field name="date_field"/></search>',
            },
            res_id: 1,
        });

        await testUtils.form.clickEdit(form);

        await testUtils.fields.many2one.clickOpenDropdown('bar');
        await testUtils.fields.many2one.clickItem('bar','Search');

        assert.strictEqual($('tr.o_data_row').length, 9, "should display 9 records");

        await testUtils.dom.click($('button:contains(Filters)'));
        await testUtils.dom.click($('.o_add_custom_filter:visible'));
        assert.strictEqual($('.o_filter_condition select.o_searchview_extended_prop_field').val(), 'date_field',
            "date field should be selected");
        await testUtils.dom.click($('.o_apply_filter'));

        assert.strictEqual($('tr.o_data_row').length, 0, "should display 0 records");

        // Save this search
        await testUtils.mock.intercept(form, 'create_filter', function (event) {
            assert.strictEqual(event.data.filter.name, "Awesome Test Customer Filter", "filter name should be correct");
        });
        await testUtils.dom.click($('button:contains(Favorites)'));
        await testUtils.dom.click($('.o_add_favorite'));
        var filterNameInput = $('.o_favorite_name .o_input[type="text"]:visible');
        assert.strictEqual(filterNameInput.length, 1, "should display an input field for the filter name");
        await testUtils.fields.editInput(filterNameInput, 'Awesome Test Customer Filter');
        await testUtils.dom.click($('.o_save_favorite button'));

        form.destroy();
    });

    QUnit.test('save filters created via autocompletion works', async function (assert) {
        assert.expect(2);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                create_filter: function (ev) {
                    assert.ok(ev.data.filter.domain === `[["foo", "ilike", "a"]]`);
                },
            },
        });

        await actionManager.doAction(10);

        $('.o_searchview_input').trigger($.Event('keypress', {
            which: 97,
        }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();

        await testUtils.nextTick();

        assert.strictEqual($('.o_searchview_input_container .o_facet_values span').text().trim(), "a");

        await testUtils.dom.click($('button .fa-star'));
        await testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        await testUtils.fields.editInput($('div.o_favorite_name input'), 'name for favorite');
        await testUtils.dom.click($('.o_favorites_menu div.o_save_favorite button'));

        actionManager.destroy();
    });

    QUnit.test('delete an active favorite remove it both in list of favorite and in search bar', async function (assert) {
        assert.expect(2);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                load_filters: function (event) {
                    return Promise.resolve([{
                        context: "{}",
                        domain: "[]",
                        id: 7,
                        is_default: true,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    }]).then(event.data.on_success);
                },
                delete_filter: function (event) {
                    event.data.on_success();
                }
            },
        });

        await actionManager.doAction(6);
        await testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options button.o_favorites_menu_button'));
        assert.containsOnce(actionManager, '.o_control_panel .o_searchview_input_container .o_facet_values');
        await testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options .o_favorites_menu span.o_trash_button'));
        await testUtils.modal.clickButton('Ok');
        assert.containsNone(actionManager, '.o_control_panel .o_searchview_input_container .o_facet_values');
        actionManager.destroy();
    });

    QUnit.test('default favorite is not activated if key search_disable_custom_filters is set to true', async function (assert) {
        assert.expect(1);

        var controlPanel = await createControlPanel({
            model: 'partner',
            arch: '<controlpanel/>',
            data: this.data,
            intercepts: {
                load_filters: function (event) {
                    return Promise.resolve([{
                        context: "{}",
                        domain: "[]",
                        id: 7,
                        is_default: true,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    }]).then(event.data.on_success);
                },
            },
            context: {
                search_disable_custom_filters: true,
            },
        });

        assert.containsNone(controlPanel, '.o_facet_values');
        controlPanel.destroy();
    });

    QUnit.test('toggle favorite correctly clears filter, groupbys and field "options"', async function (assert) {
        assert.expect(8);

        const unpatchDate = patchDate(2019,6,31,13,43,0);

        const actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                load_filters: function (event) {
                    return Promise.resolve([{
                        context: "{}",
                        domain: "[]",
                        id: 7,
                        is_default: false,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    }]).then(event.data.on_success);
                },
            },
        });

        this.actions[11].search_view_id = [10, 'search'];
        await actionManager.doAction(12);

        // activate Foo a
        await testUtils.fields.triggerKey('press', $('.o_searchview_input'), 97);
        await testUtils.fields.triggerKey('up', $('.o_searchview_input'), 'enter');

        // activate Date Filter with This Month
        await testUtils.dom.click($('button .fa-filter'));
        await testUtils.dom.click($('.o_filters_menu .o_menu_item a'));
        await testUtils.dom.click($('.o_item_option[data-option_id="this_month"]'));

        // activate Date Groupby with Year
        await testUtils.dom.click($('button .fa-bars'));
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item a'));
        await testUtils.dom.click($('.o_item_option[data-option_id="year"]'));

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(),
            "a",
            "There should be a filter Foo a");

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(1).text().trim(),
            "Date Field Filter: July 2019",
            "There should be a filter facet with label 'Date Field Filter: July 2019'");

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(2).text().trim(),
            "Date Field Groupby: Year",
            "There should be a groupby facet with label 'Date Field Groupby: Year'");

        // activate the favorite
        await testUtils.dom.click($('button .fa-star'));
        await testUtils.dom.click($('.o_favorites_menu .o_menu_item a'));

        assert.containsOnce(actionManager, '.o_searchview_input_container .o_facet_values',
            "There should be a unique facet in the search bar");
        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(),
            "My favorite",
            "There should be a facet with label 'My favorite''");

        await testUtils.dom.click($('button .fa-filter'));
        await testUtils.dom.click($('.o_filters_menu .o_menu_item a'));
        assert.doesNotHaveClass($('.o_item_option[data-option_id="this_month"]'), 'selected',
            "The Date Filter option 'This Month' should be deactivated");

        await testUtils.dom.click($('button .fa-bars'));
        await testUtils.dom.click($('.o_group_by_menu .o_menu_item a'));
        assert.doesNotHaveClass($('.o_item_option[data-option_id="year"]'), 'selected',
        "The Date Groupby option 'Year' should be deactivated");

        await testUtils.fields.triggerKey('press', $('.o_searchview_input'), 98);
        await testUtils.fields.triggerKey('up', $('.o_searchview_input'), 'enter');
        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(1).text().trim(),
            "b",
            "There should be a filter Foo b");

        actionManager.destroy();
        unpatchDate();
    });

    QUnit.test('favorites have unique descriptions (the submenus of the favorite menu are correctly updated)', async function (assert) {
        assert.expect(7);

        const UID = session.uid;

        const actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                load_filters: function (event) {
                    return Promise.resolve([{
                        context: "{}",
                        domain: "[]",
                        id: 7,
                        is_default: false,
                        name: "My favorite",
                        sort: "[]",
                        user_id: [2, "Mitchell Admin"],
                    }]).then(event.data.on_success);
                },
                create_filter: function (event) {
                    assert.step('create_filter');
                    assert.deepEqual(event.data.filter, {
                        "action_id": 1,
                        "context": {},
                        "domain": "[]",
                        "is_default": false,
                        "model_id": "partner",
                        "name": "My favorite 2",
                        "sort": "[]",
                        "user_id": UID,
                      });
                    return Promise.resolve(1).then(event.data.on_success);
                }
            },
        });
        testUtils.mock.intercept(actionManager, 'call_service', function (ev) {
            if (ev.data.service === 'notification') {
                // A notification alerting that another favorite with same name exists
                // should be triggered
                assert.step('notification');
                assert.deepEqual(ev.data.args[0], {
                    "className": undefined,
                    "message": "Filter with same name already exists.",
                    "sticky": undefined,
                    "title": "Error",
                    "type": "danger"
                  });
            }
        }, true);

        await actionManager.doAction(1);
        await testUtils.dom.click($('button .fa-star'));
        await testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        await testUtils.fields.editInput($('div.o_favorite_name input'), 'My favorite');
        await testUtils.dom.click($('.o_favorites_menu div.o_save_favorite button'));

        await testUtils.fields.editInput($('div.o_favorite_name input'), 'My favorite 2');
        await testUtils.dom.click($('.o_favorites_menu div.o_save_favorite button'));

        await testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        await testUtils.fields.editInput($('div.o_favorite_name input'), 'My favorite 2');
        await testUtils.dom.click($('.o_favorites_menu div.o_save_favorite button'));

        assert.verifySteps([
            'notification',
            'create_filter',
            'notification'
        ])

        actionManager.destroy();
    });

    QUnit.module('Search Arch');

    QUnit.test('arch order of groups of filters preserved', async function (assert) {
        assert.expect(12);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(8);
        await testUtils.dom.click($('span.fa-filter'));
        assert.strictEqual($('.o_filters_menu .o_menu_item').length, 11);
        for (var i = 0;  i < 11; i++) {
            assert.strictEqual($('.o_filters_menu .o_menu_item').eq(i).text().trim(), (i+1).toString());
        }
        actionManager.destroy();
    });

    QUnit.module('Autocompletion');

    QUnit.test('select an autocomplete field', async function (assert) {
        assert.expect(3);

        var searchRead = 0;
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchRead === 1) {
                        assert.deepEqual(args.domain, [["foo", "ilike", "a"]]);
                    }
                    searchRead++;
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(11);

        await testUtils.fields.triggerKey('press', $('.o_searchview_input'), 97);
        assert.strictEqual(actionManager.$('.o_searchview_autocomplete li').length, 2,
            "there should be 2 result for 'a' in search bar autocomplete");

        await testUtils.fields.triggerKey('up', $('.o_searchview_input'), 'enter');
        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(),
            "a", "There should be a field facet with label 'a'");

        actionManager.destroy();
    });

    QUnit.test('select an autocomplete field with `context` key', async function (assert) {
        assert.expect(9);

        var searchRead = 0;
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    if (searchRead === 1) {
                        assert.deepEqual(args.domain, [["bar", "=", 1]]);
                        assert.deepEqual(args.context.bar, [1]);
                    } else if (searchRead === 2) {
                        assert.deepEqual(args.domain, ["|", ["bar", "=", 1], ["bar", "=", 2]]);
                        assert.deepEqual(args.context.bar, [1, 2]);
                    }
                    searchRead++;
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(11);
        await testUtils.nextTick();
        assert.strictEqual(searchRead, 1, "there should be 1 search_read");

        // 'r' key to filter on bar "First Record"
        $('.o_searchview_input').val('r');
        $('.o_searchview_input').trigger($.Event('keypress', { which: 82, keyCode: 82 }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();

        await testUtils.nextTick();
        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(), "First record",
            "the autocompletion facet should be correct");
        assert.strictEqual(searchRead, 2, "there should be 2 search_read");

        // 'r' key to filter on bar "Second Record"
        $('.o_searchview_input').val('r');
        $('.o_searchview_input').trigger($.Event('keypress', { which: 82, keyCode: 82 }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        $('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(), "First record or Second record",
            "the autocompletion facet should be correct");
        assert.strictEqual(searchRead, 3, "there should be 3 search_read");

        actionManager.destroy();
    });

    QUnit.test('no search text triggers a reload', async function (assert) {
        assert.expect(2);
        var rpcs = 0;
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function () {
                rpcs++;
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(10);
        rpcs = 0;
        $('.o_searchview_input').trigger($.Event('keydown', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();

        $('.o_searchview_input').trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();

        assert.containsNone(actionManager, '.o_searchview_facet_label');
        assert.strictEqual(rpcs, 2, "should have reloaded");

        actionManager.destroy();
    });

    QUnit.test('selecting (no result) triggers a re-render', async function (assert) {
        assert.expect(3);
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(10);
        await testUtils.nextTick();

        // 'a' key to filter nothing on bar
        actionManager.$('.o_searchview_input').val('a');
        actionManager.$('.o_searchview_input').trigger($.Event('keypress', { which: 65, keyCode: 65 }));
        await testUtils.nextTick();
        actionManager.$('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();
        actionManager.$('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT }));
        await testUtils.nextTick();
        actionManager.$('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN }));
        await testUtils.nextTick();

        assert.strictEqual(actionManager.$('.o_searchview_autocomplete .o-selection-focus').text(), "(no result)",
            "there should be no result for 'a' in bar");

        actionManager.$('.o_searchview_input').trigger($.Event('keydown', { which: $.ui.keyCode.ENTER, keyCode: $.ui.keyCode.ENTER }));
        await testUtils.nextTick();

        assert.containsNone(actionManager, '.o_searchview_facet_label');
        assert.strictEqual(actionManager.$('.o_searchview_input').val(), "",
            "the search input should be re-rendered");

        actionManager.destroy();
    });

    QUnit.module('TimeRangeMenu');

    QUnit.test('time range menu stays hidden', async function (assert) {
        assert.expect(4);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);

        // check that there is no time range menu
        assert.containsNone(actionManager, '.o_control_panel .o_search_options .o_time_range_menu');
        // check if search view has no facets
        assert.strictEqual($('.o_facet_values').length, 0);

        // activate groupby
        await testUtils.dom.click($('button .fa-bars'));
        await testUtils.dom.click($('.o_menu_item a').eq(0));
        // check that there is a facet
        assert.strictEqual($('div.o_facet_values').length, 1);
        // check that there is still no time range menu
        assert.containsNone(actionManager, '.o_control_panel .o_search_options .o_time_range_menu');
        actionManager.destroy();
    });

    QUnit.test('time range menu in comparison mode', async function (assert) {
        assert.expect(46);

        var self = this;
        var nbrReadGroup = 0;

        var periodOptionText, periodOptionValue;
        var unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/read_group') {
                    nbrReadGroup++;
                    var timeRangeMenuData = args.kwargs.context.timeRangeMenuData;
                    if (timeRangeMenuData) {
                        // nbrReadGroup % 2 === 0 is true when the read group is for data, false
                        // for comparison data
                        if (nbrReadGroup % 2 === 0) {
                            assert.deepEqual(timeRangeMenuData.timeRange,
                                self.periodDomains.shift(),
                                "time range domain for " + periodOptionText);
                        } else {
                            assert.deepEqual(timeRangeMenuData.comparisonTimeRange,
                                self.previousPeriodDomains.shift(),
                                "comparaison time range domain for " + periodOptionText);
                        }
                    }
                }
                return this._super.apply(this, arguments);
            },
        });
        // time range menu should be available in graph view
        await actionManager.doAction(4);

        var $timeRangeMenu = $('.o_time_range_menu');
        assert.strictEqual($timeRangeMenu.not('.o_hidden').length, 1,
            "Time range menu should be visible");
        assert.strictEqual($('.o_facet_values').length, 0,
            "Search view has no facet");

        var $periodOptions = $timeRangeMenu.find('.o_time_range_selector option');
        var periodOptions = $periodOptions.map(function () {
            return $(this).val();
        }).toArray();
        assert.deepEqual(periodOptions, PERIOD_OPTIONS_IDS,
            "13 period options should be available:");

        for (var option of $periodOptions) {
            periodOptionText = $(option).text().trim();
            periodOptionValue = $(option).val();
            // opens time range menu dropdown
            await testUtils.dom.click($('.o_time_range_menu_button'));
            var $timeRangeMenu = $('.o_time_range_menu');
            // comparison is not checked by default
            if (!$timeRangeMenu.find('.o_comparison_checkbox').is(':checked')) {
                await testUtils.dom.click($timeRangeMenu.find('.o_comparison_checkbox'));
                assert.strictEqual($('.o_comparison_time_range_selector:visible').length, 1,
                    "Comparison has to be checked (only at the first time)");
            }
            // select one period option to test it
            $timeRangeMenu.find('.o_time_range_selector').val(periodOptionValue);
            // apply
            await testUtils.dom.click($timeRangeMenu.find('.o_apply_range'));
            assert.strictEqual($('.o_facet_values').text().trim(),
                "Date: " + periodOptionText + " / Previous Period",
                "Facet should be updated with this period: " + periodOptionValue);
        }
        unpatchDate();
        actionManager.destroy();
    });

    QUnit.test('a default time range only in context is taken into account', async function (assert) {
        assert.expect(1);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                // there are only one read_group call (for the groupby lists [])
                // the read group for the list ["date_field:day"] is not done since no data is available for today)
                if (route === '/web/dataset/call_kw/partner/read_group') {
                    var timeRangeMenuData = args.kwargs.context.timeRangeMenuData;
                    assert.ok(timeRangeMenuData.timeRange.length > 0, "time range should be non empty");
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction({
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'pivot']],
            context: {time_ranges: {range: 'today', field: 'date_field'}}
        });
        actionManager.destroy();
    });

    QUnit.test('Customizing filter does not close the filter dropdown', async function (assert) {
        assert.expect(5);
        var self = this;

        _.each(this.data.partner.records.slice(), function (rec) {
            var copy = _.defaults({}, rec, {id: rec.id + 10 });
            self.data.partner.records.push(copy);
        });

        this.data.partner.fields.date_field.searchable = true;
        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="bar"/>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            archs: {
                'partner,false,list': '<tree><field name="display_name"/></tree>',
                'partner,false,search': '<search><field name="date_field"/></search>',
            },
            res_id: 1,
            intercepts: {
                create_filter: function (ev) {
                    var data = ev.data;
                    assert.strictEqual(data.filter.name, 'Fire on the bayou');
                    assert.strictEqual(data.filter.is_default, true);
                },
            },
        });

        await testUtils.fields.many2one.clickOpenDropdown('bar');
        await testUtils.fields.many2one.clickItem('bar', 'Search More');

        assert.containsOnce(document.body, '.modal');

        await testUtils.dom.click($('.modal .o_filters_menu_button'));

        var $filterDropdown = $('.modal .o_filters_menu');
        await testUtils.dom.click($filterDropdown.find('.o_add_custom_filter'));

        assert.containsN($filterDropdown, '.o_input', 4);

        // We really are interested in the click event
        // We do it twice on each input to make sure
        // the parent dropdown doesn't react to any of it
        _.each($filterDropdown.find('input'), async function (input) {
            var $input = $(input);
            $input.click();
            $input.click();
            await testUtils.nextTick();
        });
        assert.isVisible($filterDropdown);

        // Favorites Menu
        var $modal = $('.modal');
        await testUtils.dom.click($modal.find('.o_favorites_menu_button'));
        await testUtils.dom.click($modal.find('.o_add_favorite'));
        $modal.find('.o_search_options .dropdown-menu').one('click', function (ev) {
            // This handler is on the webClient
            // But since the test suite doesn't have one
            // We manually set it here
            ev.stopPropagation();
        });
        await testUtils.fields.editInput($modal.find('div.o_favorite_name input'), 'Fire on the bayou');
        await testUtils.dom.click($modal.find('.o_add_favorite ~ div label:contains(Use by default)'));
        await testUtils.dom.click($modal.find('.o_save_favorite button'));

        form.destroy();
    });
});
});
