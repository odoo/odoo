odoo.define('web.search_view_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');
var createActionManager = testUtils.createActionManager;
var patchDate = testUtils.patchDate;
var createView = testUtils.createView;

QUnit.module('Search View', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    date_field: {string: "Date", type: "date", store: true, sortable: true},
                    birthday: {string: "Birthday", type: "date", store: true, sortable: true},
                    foo: {string: "Foo", type: "char", store: true, sortable: true},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                    float_field: {string: "Float", type: "float"},
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
                    '<field name="bar"/>' +
                    '<field name="float_field"/>' +
                    '<filter string="Date Field Filter" name="positive" date="date_field"/>' +
                    '<filter string="Date Field Groupby" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
                '</search>',
        };

        this.periodOptions = [
          'last_7_days',
          'last_30_days',
          'last_365_days',
          'today',
          'this_week',
          'this_month',
          'this_quarter',
          'this_year',
          'yesterday',
          'last_week',
          'last_month',
          'last_quarter',
          'last_year',
        ];

        // assuming that the current time is: 2017-03-22:01:00:00
        this.periodDomains = [
            // last 7 days (whole days)
            ['&', ["date_field", ">=", "2017-03-15"],["date_field", "<", "2017-03-22"]],
            // last 30 days
            ['&', ["date_field", ">=", "2017-02-20"],["date_field", "<", "2017-03-22"]],
            // last 365 days
            ['&', ["date_field", ">=", "2016-03-22"],["date_field", "<", "2017-03-22"]],
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

        // assuming that the current time is: 2017-03-22:01:00:00
        this.previousPeriodDomains = [
            // last 7 days (whole days) - 1 week
            ['&', ["date_field", ">=", "2017-03-08"],["date_field", "<", "2017-03-15"]],
            // last 30 days - 30 days
            ['&', ["date_field", ">=", "2017-01-21"],["date_field", "<", "2017-02-20"]],
            // last 365 days
            ['&', ["date_field", ">=", "2015-03-23"],["date_field", "<", "2016-03-22"]],
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
    QUnit.module('Groupby Menu');

    QUnit.test('click on groupby filter adds a facet', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);
        $('span.fa-bars').prev().click();
        $('.o_menu_item a').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'candle',
            'should have a facet with candle name');
        actionManager.destroy();
    });

    QUnit.test('remove a "Group By" facet properly unchecks groupbys in groupby menu', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);
        $('span.fa-bars').prev().click();
        $('.o_menu_item a').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'candle',
            'should have a facet with candle name');
        $('.o_facet_remove:first').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'there should be no facet');
        actionManager.destroy();
    });

    QUnit.test('change option of a "Group By" does not remove groupy in facet "Group By"', function (assert) {
        assert.expect(3);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(2);
        $('span.fa-bars').click();
        $('.o_submenu_switcher').click();
        // Don't forget there is a hidden li.divider element at first place among children
        $('.o_item_option:nth-child(2)').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        $('.o_item_option:nth-child(3)').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        $('.o_item_option:nth-child(3)').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'should have no facet');
        actionManager.destroy();
    });

    QUnit.test('select and unselect quickly groupby does not crash', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(3);
        $('span.fa-bars').click();
        $('.o_menu_item:first').click();
        $('.o_menu_item:first').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'should have a facet');
        actionManager.destroy();
    });

    QUnit.test('groupby selected within graph subview are not deleted when modifying search view content', function (assert) {
        assert.expect(2);

        this.actions[3].flags = {isEmbedded: true};

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(4);
        $('.o_graph_buttons div.o_graph_groupbys_menu > button').click();
        $('.o_graph_buttons div.o_graph_groupbys_menu .o_menu_item').click();
        assert.ok(!$('.o_graph_buttons div.o_graph_groupbys_menu .o_menu_item > .dropdown-item').hasClass('selected'),
            'groupby should be unselected');
        $('.o_search_options button span.fa-filter').click();
        $('.o_filters_menu .o_menu_item a').click();
        assert.ok(!$('.o_graph_buttons div.o_graph_groupbys_menu .o_menu_item > .dropdown-item').hasClass('selected'),
            'groupby should be still unselected');
        actionManager.destroy();
    });

    QUnit.test('group by a date field using interval works', function (assert) {
            assert.expect(13);


        var groupbys = [
            ["date_field:day"],
            ["date_field:month"],
            ["birthday:month"],
            ["birthday:year"],
        ];

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/read_group') {
                    assert.deepEqual(args.kwargs.groupby, groupbys.shift());
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction(5);
        // open menu 'Group By'
        $('.o_search_options .fa-bars').click();
        // Activate the groupby 'Date'
        $('.o_group_by_menu .o_menu_item').click();
        // // select option 'day'
        $('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]').click();
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Day');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // // select option 'month'
        $('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]').click();
        // // data should be grouped by the field 'Date' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 3);
        // // deactivate option 'month'
        $('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]').click();
        // // no groupby is applied
        assert.strictEqual($('div.o_facet_values span').length, 0);
        // // open 'Add custom Groupby' menu
        $('.o_group_by_menu .o_add_custom_group').click();
        // // click on 'Apply' button
        $('.o_group_by_menu .o_generator_menu button').click();
        // // data should be grouped by the field 'Birthday' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // // open submenu with interval options
        $('.o_group_by_menu .o_menu_item .o_submenu_switcher').eq(1).click();
        // // select option 'year'
        $('.o_group_by_menu .o_menu_item .o_item_option').eq(9).click();
        // // data should be grouped by the field 'Birthday' using the interval 'year'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Year');
        assert.strictEqual($('.o_content tr.o_group_header').length, 4);
        actionManager.destroy();
    });

    QUnit.test('a separator in groupbys does not cause problems', function (assert) {
        assert.expect(6);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(7);
        // open menu 'Group By'
        $('span.fa-bars').click();
        // open options menu
        $('.o_group_by_menu .o_menu_item a:first').click();
        // activate groupby with 'day' option
        $('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]').click();
        // activate the second groupby
        $('.o_group_by_menu .o_menu_item > a').eq(1).click();
        assert.strictEqual($('.o_group_by_menu .o_menu_item').length, 2);
        assert.ok($('.o_group_by_menu .o_menu_item > .dropdown-item').hasClass('selected'));
        // deactivate second groupby
        $('.o_group_by_menu .o_menu_item > a').eq(1).click();
        assert.ok($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0).hasClass('selected'));
        assert.ok(!$('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1).hasClass('selected'));
        // remove facet
        $('.o_facet_remove').click();
        assert.ok(!$('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0).hasClass('selected'));
        assert.ok(!$('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1).hasClass('selected'));
        actionManager.destroy();
    });

    QUnit.module('Filters Menu');

    QUnit.test('add a custom filter works', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);
        $('span.fa-filter').click();
        $('.o_add_custom_filter').click();
        $('.o_apply_filter').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'ID is \"0\"',
            'should have a facet with candle name');
        actionManager.destroy();
    });

    QUnit.test('deactivate a new custom filter works', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);
        $('span.fa-filter').click();
        $('.o_add_custom_filter').click();
        $('.o_apply_filter').click();
        $('.o_menu_item').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'no facet should be in the search view');
        actionManager.destroy();
    });

    QUnit.test('filter by a date field using period works', function (assert) {
        assert.expect(14);

        var self = this;

        this.archs['partner,4,search'] = '<search>'+
            '<filter string="AAA" name="some_filter" date="date_field" default_period="this_week"></filter>' +
        '</search>';

        var RealDate = window.Date;

        window.Date = function TestDate() {
            // month are indexed from 0!
            return new RealDate(2017,2,22);
        };
        window.Date.now = function Test() {
            return new Date(2017,2,22);
        };

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read' && args.domain.length) {
                    assert.deepEqual(args.domain, self.periodDomains.shift());
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction(5);

        // open menu 'Filter'
        $('.o_search_options .fa-filter').click();
        // open menu options
        $('.o_menu_item').click();

        var periodOptions = $('.o_menu_item .o_item_option').map(function () {
            return $(this).data('option_id');
        }).toArray();
        assert.deepEqual(periodOptions, this.periodOptions,
            "13 period options should be available:");

        $('.o_menu_item .o_item_option[data-option_id="last_7_days"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_30_days"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_365_days"]').click();
        $('.o_menu_item .o_item_option[data-option_id="today"]').click();
        $('.o_menu_item .o_item_option[data-option_id="this_week"]').click();
        $('.o_menu_item .o_item_option[data-option_id="this_month"]').click();
        $('.o_menu_item .o_item_option[data-option_id="this_quarter"]').click();
        $('.o_menu_item .o_item_option[data-option_id="this_year"]').click();
        $('.o_menu_item .o_item_option[data-option_id="yesterday"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_week"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_month"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_quarter"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_year"]').click();

        actionManager.destroy();
        window.Date = RealDate;
    });

    QUnit.module('Favorites Menu');

    QUnit.test('dynamic filters are saved dynamic', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                create_filter: function (ev) {
                    console.log(ev.data);
                    assert.equal(
                        ev.data.filter.domain,
                        "['&', " +
                        "('date_field', '>=', (context_today() + relativedelta()).strftime('%Y-%m-%d')), " +
                        "('date_field', '<', (context_today() + relativedelta(days = 1)).strftime('%Y-%m-%d'))"+
                        "]");
                },
            },
        });

        actionManager.doAction(6);
        $('span.fa-filter').click();
        $('.o_filters_menu .o_menu_item a').click();
        $('.o_item_option[data-option_id="today"]').click();
        $('span.fa-star').click();
        $('.o_favorites_menu .o_save_search a').click();
        $('.o_favorites_menu .o_save_name button').click();
        actionManager.destroy();
    });

    QUnit.test('arch order of groups of filters preserved', function (assert) {
        assert.expect(12);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(8);
        $('span.fa-filter').click();
        assert.strictEqual($('.o_filters_menu .o_menu_item').length, 11);
        for (var i = 0;  i < 11; i++) {
            assert.strictEqual($('.o_filters_menu .o_menu_item').eq(i).text().trim(), (i+1).toString());
        }
        actionManager.destroy();
    });

    QUnit.test('selection via autocompletion modifies appropriately submenus', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(9);

        $('.o_searchview_input').trigger($.Event('keypress', {
            which: 97,
        }));

        $('.o_searchview_input').trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));

        $('.o_searchview_input').trigger($.Event('keypress', {
            which: 103,
        }));

        $('.o_searchview_input').trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));

        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(0).text().trim(),
            "Date Field Filter: This Month",
            "There should be a filter facet with label 'Date Field Filter: This Month'");
        assert.strictEqual($('.o_searchview_input_container .o_facet_values').eq(1).text().trim(),
            "Date Field Groupby: Day",
            "There should be a filter facet with label 'Date Field Groupby: Day'");

        $('button .fa-filter').click();
        $('.o_filters_menu .o_menu_item').eq(0).click();
        assert.strictEqual($('.o_filters_menu .o_item_option a.selected').text().trim(), "This Month",
            "The item 'This Month' should be selected in the filters menu");

        $('button .fa-bars').click();
        $('.o_group_by_menu .o_menu_item').eq(0).click();
        assert.strictEqual($('.o_group_by_menu .o_item_option a.selected').text().trim(), "Day",
            "The item 'Day' should be selected in the groupby menu");

        actionManager.destroy();
    });

    QUnit.test('save filters created via autocompletion works', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                create_filter: function (ev) {
                    assert.ok(ev.data.filter.domain === "[['foo', 'ilike', 'a']]");
                },
            },
        });

        actionManager.doAction(10);

        $('.o_searchview_input').trigger($.Event('keypress', {
            which: 97,
        }));

        $('.o_searchview_input').trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));

        assert.strictEqual($('.o_searchview_input_container .o_facet_values span').text().trim(), "a");

        $('button .fa-star').click();
        $('.o_favorites_menu a.o_save_search').click();
        $('.o_favorites_menu div.o_save_name button').click();

        actionManager.destroy();
    });

    QUnit.test('time range menu stays hidden', function (assert) {
        assert.expect(6);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);

        // check that the fifth dropdown is the time range menu and is hidden
        assert.ok($('.btn-group.o_dropdown').eq(4).hasClass('o_hidden'));
        assert.ok($('.btn-group.o_dropdown').eq(4).children().eq(1).hasClass('o_time_range_menu'));
        // check if search view has no facets
        assert.strictEqual($('.o_facet_values').length, 0);

        // activate groupby
        $('button .fa-bars').click();
        $('.o_menu_item a').eq(0).click();
        // check that there is a facet
        assert.strictEqual($('div.o_facet_values').length, 1);
        // check that the fifth dropdown is the time range menu and is still hidden
        assert.ok($('.btn-group.o_dropdown').eq(4).hasClass('o_hidden'));
        assert.ok($('.btn-group.o_dropdown').eq(4).children().eq(1).hasClass('o_time_range_menu'));
        actionManager.destroy();
    });

    QUnit.test('time range menu in comparison mode', function (assert) {
        assert.expect(43);

        var self = this;
        var nbrReadGroup = 0;

        var periodOptionText, periodOptionValue;
        var unpatchDate = patchDate(2017, 2, 22, 1, 0, 0);

        var actionManager = createActionManager({
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
        actionManager.doAction(4);

        var $timeRangeMenu = $('.o_time_range_menu');
        assert.strictEqual($timeRangeMenu.not('.o_hidden').length, 1,
            "Time range menu should be visible");
        assert.strictEqual($('.o_facet_values').length, 0,
            "Search view has no facet");

        var $periodOptions = $timeRangeMenu.find('.o_time_range_selector option');
        var periodOptions = $periodOptions.map(function () {
            return $(this).val();
        }).toArray();
        assert.deepEqual(periodOptions, this.periodOptions,
            "13 period options should be available:");

        $periodOptions.each(function () {
            periodOptionText = $(this).text().trim();
            periodOptionValue = $(this).val();
            // opens time range menu dropdown
            $('.o_time_range_menu_button').click();
            var $timeRangeMenu = $('.o_time_range_menu');
            // comparison is not checked by default
            if (!$timeRangeMenu.find('.o_comparison_checkbox').is(':checked')) {
                $timeRangeMenu.find('.o_comparison_checkbox').click();
                assert.strictEqual($('.o_comparison_time_range_selector:visible').length, 1,
                    "Comparison has to be checked (only at the first time)");
            }
            // select one period option to test it
            $timeRangeMenu.find('.o_time_range_selector').val(periodOptionValue);
            // apply
            $timeRangeMenu.find('.o_apply_range').click();
            assert.strictEqual($('.o_facet_values').text().trim(),
                "Date: " + periodOptionText + " / Previous Period",
                "Facet should be updated with this period: " + periodOptionValue);
        });

        unpatchDate();
        actionManager.destroy();
    });

    QUnit.test('a default time range only in context is taken into account', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            mockRPC: function (route, args) {
                // there are two read_group calls (for the groupby lists [] and ["date_field:day"])
                if (route === '/web/dataset/call_kw/partner/read_group') {
                    var timeRangeMenuData = args.kwargs.context.timeRangeMenuData;
                    assert.ok(timeRangeMenuData.timeRange.length > 0, "time range should be non empty");
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction({
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'pivot']],
            context: {time_ranges: {range: 'today', field: 'date_field'}}
        });

        actionManager.destroy();
    });

    QUnit.test('save search filter in modal', function (assert) {
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
        var form = createView({
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

        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('.o_m2o_dropdown_option:contains(Search)').mouseenter().click();  // Open Search More

        assert.strictEqual($('tr.o_data_row').length, 9, "should display 9 records");

        $('button:contains(Filters)').click();
        $('.o_add_custom_filter:visible').click();  // Add a custom filter, datetime field is selected
        assert.strictEqual($('.o_filter_condition select.o_searchview_extended_prop_field').val(), 'date_field',
            "date field should be selected");
        $('.o_apply_filter').click();

        assert.strictEqual($('tr.o_data_row').length, 0, "should display 0 records");

        // Save this search
        testUtils.intercept(form, 'create_filter', function (event) {
            assert.strictEqual(event.data.filter.name, "Awesome Test Customer Filter", "filter name should be correct");
        });
        $('button:contains(Favorites)').click();
        $('.o_save_search').click();
        var filterNameInput = $('.o_save_name .o_input[type="text"]:visible');
        assert.strictEqual(filterNameInput.length, 1, "should display an input field for the filter name");
        filterNameInput.val('Awesome Test Customer Filter').trigger('input');
        $('.o_save_name button').click();

        form.destroy();
    });

});
});
