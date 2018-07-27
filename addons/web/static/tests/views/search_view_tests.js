odoo.define('web.search_view_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var createActionManager = testUtils.createActionManager;

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
        };
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
        assert.ok(!$('.o_graph_buttons div.o_graph_groupbys_menu .o_menu_item').hasClass('selected'),
            'groupby should be unselected');
        $('.o_search_options button span.fa-filter').click();
        $('.o_filters_menu .o_menu_item a').click();
        assert.ok(!$('.o_graph_buttons div.o_graph_groupbys_menu .o_menu_item').hasClass('selected'),
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
        assert.ok($('.o_group_by_menu .o_menu_item').hasClass('selected'));
        // deactivate second groupby
        $('.o_group_by_menu .o_menu_item > a').eq(1).click();
        assert.ok($('.o_group_by_menu .o_menu_item').eq(0).hasClass('selected'));
        assert.ok(!$('.o_group_by_menu .o_menu_item').eq(1).hasClass('selected'));
        // remove facet
        $('.o_facet_remove').click();
        assert.ok(!$('.o_group_by_menu .o_menu_item').eq(0).hasClass('selected'));
        assert.ok(!$('.o_group_by_menu .o_menu_item').eq(1).hasClass('selected'));
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

        this.archs['partner,4,search'] = '<search>'+
            '<filter string="AAA" name="some_filter" date="date_field" default_period="this_week"></filter>' +
        '</search>';

        var domains = [
            [],
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
            // last 7 days (whole days)
            ['&', ["date_field", ">=", "2017-03-15"],["date_field", "<", "2017-03-22"]],
            // last 30 days
            ['&', ["date_field", ">=", "2017-02-20"],["date_field", "<", "2017-03-22"]],
            // last 365 days
            ['&', ["date_field", ">=", "2016-03-22"],["date_field", "<", "2017-03-22"]],
        ];

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
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, domains.shift());
                }
                return this._super.apply(this, arguments);
            },
        });

        actionManager.doAction(5);

        // open menu 'Filter'
        $('.o_search_options .fa-filter').click();
        // open menu options
        $('.o_menu_item').click();
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
        $('.o_menu_item .o_item_option[data-option_id="last_7_days"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_30_days"]').click();
        $('.o_menu_item .o_item_option[data-option_id="last_365_days"]').click();

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
        $('.o_item_option:first').click();
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
});
});
