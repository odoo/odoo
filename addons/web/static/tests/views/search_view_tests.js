odoo.define('web.search_view_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;
var createControlPanel = testUtils.createControlPanel;
var createView = testUtils.createView;
var patchDate = testUtils.mock.patchDate;

var controlPanelViewParameters = require('web.controlPanelViewParameters');
var PERIOD_OPTIONS_IDS = controlPanelViewParameters.PERIOD_OPTIONS.map(function (option) {return option.optionId;});

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
    QUnit.test('basic rendering', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.doAction(1);

        assert.strictEqual($('.o_searchview input.o_searchview_input')[0], document.activeElement,
            "searchview input should be focused");

        actionManager.destroy();
    });
    QUnit.test('navigation with facets', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.doAction(1);

        // add a facet
        testUtils.dom.click(actionManager.$('.o_dropdown_toggler_btn:contains(Group By)'));
        testUtils.dom.click(actionManager.$('.o_menu_item a'));
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

    QUnit.module('GroupByMenu');

    QUnit.test('click on groupby filter adds a facet', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });
        actionManager.doAction(1);
        testUtils.dom.click($('.o_dropdown_toggler_btn:contains(Group By)'));
        testUtils.dom.click($('.o_menu_item a'));
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
        testUtils.dom.click($('.o_dropdown_toggler_btn:contains(Group By)'));
        testUtils.dom.click($('.o_menu_item a'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').text().trim(), 'candle',
            'should have a facet with candle name');
        testUtils.dom.click($('.o_facet_remove:first'));
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
        testUtils.dom.click($('span.fa-bars'));
        testUtils.dom.click($('.o_submenu_switcher'));
        // Don't forget there is a hidden li.divider element at first place among children
        testUtils.dom.click($('.o_item_option:nth-child(2)'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        testUtils.dom.click($('.o_item_option:nth-child(3)'));
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        testUtils.dom.click($('.o_item_option:nth-child(3)'));
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
        testUtils.dom.click($('span.fa-bars'));
        testUtils.dom.click($('.o_menu_item:first'));
        testUtils.dom.click($('.o_menu_item:first'));
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
        testUtils.dom.click($('.o_graph_controller .o_control_panel .o_cp_buttons button').eq(1));
        testUtils.dom.click($('.o_graph_controller .o_group_by_menu .o_menu_item').eq(1));
        testUtils.dom.click($('.o_graph_controller .o_group_by_menu .o_menu_item .o_item_option > .dropdown-item').first());
        assert.doesNotHaveClass($('.o_graph_controller .o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected',
            'groupby should be unselected');
        testUtils.dom.click($('.o_search_options button span.fa-filter'));
        testUtils.dom.click($('.o_filters_menu .o_menu_item a').first());
        assert.doesNotHaveClass($('.o_graph_controller .o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected',
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
        testUtils.dom.click($('.o_search_options .fa-bars'));
        // Activate the groupby 'Date'
        testUtils.dom.click($('.o_group_by_menu .o_menu_item'));
        // // select option 'day'
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]'));
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Day');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // // select option 'month'
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]'));
        // // data should be grouped by the field 'Date' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 3);
        // // deactivate option 'month'
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="month"]'));
        // // no groupby is applied
        assert.strictEqual($('div.o_facet_values span').length, 0);
        // // open 'Add custom Groupby' menu
        testUtils.dom.click($('.o_group_by_menu .o_add_custom_group'));
        // // click on 'Apply' button
        testUtils.dom.click($('.o_group_by_menu .o_generator_menu button'));
        // // data should be grouped by the field 'Birthday' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // // open submenu with interval options
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_submenu_switcher').eq(1));
        // // select option 'year'
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option').eq(9));
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
        testUtils.dom.click($('span.fa-bars'));
        // open options menu
        testUtils.dom.click($('.o_group_by_menu .o_menu_item a:first'));
        // activate groupby with 'day' option
        testUtils.dom.click($('.o_group_by_menu .o_menu_item .o_item_option[data-option_id="day"]'));
        // activate the second groupby
        testUtils.dom.click($('.o_group_by_menu .o_menu_item > a').eq(1));
        assert.strictEqual($('.o_group_by_menu .o_menu_item').length, 2);
        assert.strictEqual($('.o_group_by_menu .o_menu_item > .dropdown-item.selected').length, 2);
        // deactivate second groupby
        testUtils.dom.click($('.o_group_by_menu .o_menu_item > a').eq(1));
        assert.hasClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0), 'selected');
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected');
        // remove facet
        testUtils.dom.click($('.o_facet_remove'));
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(0), 'selected');
        assert.doesNotHaveClass($('.o_group_by_menu .o_menu_item > .dropdown-item').eq(1), 'selected');
        actionManager.destroy();
    });

    QUnit.module('FilterMenu');

    QUnit.test('Search date and datetime fields. Support of timezones', function (assert) {
        assert.expect(4);

        this.data.partner.fields.birth_datetime = {string: "Birth DateTime", type: "datetime", store: true, sortable: true};
        this.data.partner.records = this.data.partner.records.slice(0,-1); // exclude wrong date record

        function stringToEvent ($element, string) {
            for (var i = 0; i < string.length; i++) {
                var keyAscii = string.charCodeAt(i);
                $element.val($element.val()+string[i]);
                $element.trigger($.Event('keyup', {which: keyAscii, keyCode:keyAscii}));
            }
        }

        var searchReadSequence = 0;
        var actionManager = createActionManager({
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

        actionManager.doAction(11);

        // Date case
        var $autocomplete = $('.o_searchview_input');
        stringToEvent($autocomplete, '07/15/1983');

        $autocomplete.trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));

        assert.equal($('.o_searchview_facet .o_facet_values').text().trim(), '07/15/1983',
            'The format of the date in the facet should be in locale');

        // Close Facet
        $('.o_searchview_facet .o_facet_remove').click();

        // DateTime case
        $autocomplete = $('.o_searchview_input');
        stringToEvent($autocomplete, '07/15/1983 00:00:00');

        $autocomplete.trigger($.Event('keyup', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));

        assert.equal($('.o_searchview_facet .o_facet_values').text().trim(), '07/15/1983 00:00:00',
            'The format of the datetime in the facet should be in locale');

        actionManager.destroy();
    });

    QUnit.test('add a custom filter works', function (assert) {
        assert.expect(1);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);
        testUtils.dom.click($('span.fa-filter'));
        testUtils.dom.click($('.o_add_custom_filter'));
        testUtils.dom.click($('.o_apply_filter'));
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
        testUtils.dom.click($('span.fa-filter'));
        testUtils.dom.click($('.o_add_custom_filter'));
        testUtils.dom.click($('.o_apply_filter'));
        testUtils.dom.click($('.o_menu_item'));
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
        testUtils.dom.click($('.o_search_options .fa-filter'));
        // open menu options
        testUtils.dom.click($('.o_menu_item'));

        var periodOptions = $('.o_menu_item .o_item_option').map(function () {
            return $(this).data('option_id');
        }).toArray();



        assert.deepEqual(periodOptions, PERIOD_OPTIONS_IDS,
            "13 period options should be available:");

        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_7_days"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_30_days"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_365_days"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="today"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_week"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_month"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_quarter"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="this_year"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="yesterday"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_week"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_month"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_quarter"]'));
        testUtils.dom.click($('.o_menu_item .o_item_option[data-option_id="last_year"]'));

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
        testUtils.dom.click($('span.fa-filter'));
        testUtils.dom.click($('.o_filters_menu .o_menu_item a'));
        testUtils.dom.click($('.o_item_option[data-option_id="today"]'));
        testUtils.dom.click($('span.fa-star'));
        testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        testUtils.fields.editInput($('div.o_favorite_name input'), 'name for favorite');
        testUtils.dom.click($('.o_favorites_menu .o_save_favorite button'));
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

        testUtils.form.clickEdit(form);

        testUtils.fields.many2one.clickOpenDropdown('bar');
        testUtils.fields.many2one.clickItem('bar','Search');

        assert.strictEqual($('tr.o_data_row').length, 9, "should display 9 records");

        testUtils.dom.click($('button:contains(Filters)'));
        testUtils.dom.click($('.o_add_custom_filter:visible'));
        assert.strictEqual($('.o_filter_condition select.o_searchview_extended_prop_field').val(), 'date_field',
            "date field should be selected");
        testUtils.dom.click($('.o_apply_filter'));

        assert.strictEqual($('tr.o_data_row').length, 0, "should display 0 records");

        // Save this search
        testUtils.mock.intercept(form, 'create_filter', function (event) {
            assert.strictEqual(event.data.filter.name, "Awesome Test Customer Filter", "filter name should be correct");
        });
        testUtils.dom.click($('button:contains(Favorites)'));
        testUtils.dom.click($('.o_add_favorite'));
        var filterNameInput = $('.o_favorite_name .o_input[type="text"]:visible');
        assert.strictEqual(filterNameInput.length, 1, "should display an input field for the filter name");
        testUtils.fields.editInput(filterNameInput, 'Awesome Test Customer Filter');
        testUtils.dom.click($('.o_save_favorite button'));

        form.destroy();
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

        testUtils.dom.click($('button .fa-star'));
        testUtils.dom.click($('.o_favorites_menu .o_add_favorite'));
        testUtils.fields.editInput($('div.o_favorite_name input'), 'name for favorite');
        testUtils.dom.click($('.o_favorites_menu div.o_save_favorite button'));

        actionManager.destroy();
    });

    QUnit.test('delete an active favorite remove it both in list of favorite and in search bar', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            intercepts: {
                load_filters: function (event) {
                    return $.when([{
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

        actionManager.doAction(6);
        testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options button.o_favorites_menu_button'));
        assert.containsOnce(actionManager, '.o_control_panel .o_searchview_input_container .o_facet_values');
        testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options .o_favorites_menu span.o_trash_button'));
        testUtils.modal.clickButton('Ok');
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
                    return $.when([{
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

    QUnit.module('Search Arch');

    QUnit.test('arch order of groups of filters preserved', function (assert) {
        assert.expect(12);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(8);
        testUtils.dom.click($('span.fa-filter'));
        assert.strictEqual($('.o_filters_menu .o_menu_item').length, 11);
        for (var i = 0;  i < 11; i++) {
            assert.strictEqual($('.o_filters_menu .o_menu_item').eq(i).text().trim(), (i+1).toString());
        }
        actionManager.destroy();
    });

    QUnit.module('Autocompletion');

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

        testUtils.dom.click($('button .fa-filter'));
        testUtils.dom.click($('.o_filters_menu .o_menu_item').eq(0));
        assert.strictEqual($('.o_filters_menu .o_item_option a.selected').text().trim(), "This Month",
            "The item 'This Month' should be selected in the filters menu");

        testUtils.dom.click($('button .fa-bars'));
        testUtils.dom.click($('.o_group_by_menu .o_menu_item').eq(0));
        assert.strictEqual($('.o_group_by_menu .o_item_option a.selected').text().trim(), "Day",
            "The item 'Day' should be selected in the groupby menu");

        actionManager.destroy();
    });

    QUnit.module('TimeRangeMenu');

    QUnit.test('time range menu stays hidden', function (assert) {
        assert.expect(4);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(1);

        // check that there is no time range menu
        assert.containsNone(actionManager, '.o_control_panel .o_search_options .o_time_range_menu');
        // check if search view has no facets
        assert.strictEqual($('.o_facet_values').length, 0);

        // activate groupby
        testUtils.dom.click($('button .fa-bars'));
        testUtils.dom.click($('.o_menu_item a').eq(0));
        // check that there is a facet
        assert.strictEqual($('div.o_facet_values').length, 1);
        // check that there is still no time range menu
        assert.containsNone(actionManager, '.o_control_panel .o_search_options .o_time_range_menu');
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
        assert.deepEqual(periodOptions, PERIOD_OPTIONS_IDS,
            "13 period options should be available:");

        $periodOptions.each(function () {
            periodOptionText = $(this).text().trim();
            periodOptionValue = $(this).val();
            // opens time range menu dropdown
            testUtils.dom.click($('.o_time_range_menu_button'));
            var $timeRangeMenu = $('.o_time_range_menu');
            // comparison is not checked by default
            if (!$timeRangeMenu.find('.o_comparison_checkbox').is(':checked')) {
                testUtils.dom.click($timeRangeMenu.find('.o_comparison_checkbox'));
                assert.strictEqual($('.o_comparison_time_range_selector:visible').length, 1,
                    "Comparison has to be checked (only at the first time)");
            }
            // select one period option to test it
            $timeRangeMenu.find('.o_time_range_selector').val(periodOptionValue);
            // apply
            testUtils.dom.click($timeRangeMenu.find('.o_apply_range'));
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

    QUnit.test('Customizing filter does not close the filter dropdown', function (assert) {
        assert.expect(3);
        var self = this;

        _.each(this.data.partner.records.slice(), function (rec) {
            var copy = _.defaults({}, rec, {id: rec.id + 10 });
            self.data.partner.records.push(copy);
        });

        this.data.partner.fields.date_field.searchable = true;
        var form = createView({
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
        });

        testUtils.fields.many2one.clickOpenDropdown('bar');
        testUtils.fields.many2one.clickItem('bar', 'Search More');

        assert.containsOnce(document.body, '.modal');

        testUtils.dom.click($('.modal .o_filters_menu_button'));

        var $filterDropdown = $('.modal .o_filters_menu');
        testUtils.dom.click($filterDropdown.find('.o_add_custom_filter'));

        assert.containsN($filterDropdown, '.o_input', 3);

        // We really are interested in the click event
        // We do it twice on each input to make sure
        // the parent dropdown doesn't react to any of it
        _.each($filterDropdown.find('input'), function (input) {
            var $input = $(input);
            $input.click();
            $input.click();
        });

        assert.isVisible($filterDropdown);

        form.destroy();
    });
});
});
