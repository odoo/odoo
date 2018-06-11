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
                    Birthday: {string: "Birthday", type: "date", store: true, sortable: true},
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "many2one", relation: 'partner'},
                    float_field: {string: "Float", type: "float"},
                },
                records: [
                    {id: 1, display_name: "First record", foo: "yop", bar: 2, date_field: "2017-01-25", Birthday: "1983-07-15", float_field: 1},
                    {id: 2, display_name: "Second record", foo: "blip", bar: 1, date_field: "2017-01-24", Birthday: "1982-06-04",float_field: 2},
                    {id: 3, display_name: "Third record", foo: "gnap", bar: 1, date_field: "2017-01-13", Birthday: "1985-09-13",float_field: 1.618},
                    {id: 4, display_name: "Fourth record", foo: "plop", bar: 2, date_field: "2017-02-25", Birthday: "1983-05-05",float_field: -1},
                    {id: 5, display_name: "Fifth record", foo: "zoup", bar: 2, date_field: "2016-01-25", Birthday: "1800-01-01",float_field: 13},
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
                    '<field name="foo" string="Foo"/>' +
                    '<filter string="candle" name="itsName" context="{\'group_by\': \'foo\'}"/>' +
                '</search>',
            'partner,2,search': '<search>'+
                    '<field name="date_field" string="Date"/>' +
                    '<filter string="Date" name="coolName" context="{\'group_by\': \'date_field\'}"/>' +
                '</search>',
            'partner,3,search': '<search>'+
                    '<field name="date_field" string="Date"/>' +
                    '<filter string="float" name="positive" domain="[(\'float_field\', \'>=\', 0)]"/>' +
                '</search>',
            'partner,4,search': '<search>'+
                    '<field name="date_field" string="Date"/>' +
                    '<filter string="Date" name="coolName" context="{\'group_by\': \'date_field:day\'}"/>' +
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
        $('li.o_menu_item a').click();
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
        $('li.o_menu_item a').click();
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
        $('.o_item_option:first').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        $('.o_item_option:nth-child(2)').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 1,
            'should have a facet');
        $('.o_item_option:nth-child(2)').click();
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
        assert.expect(9);

        var actionManager = createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        actionManager.doAction(5);
        // open menu 'Group By'
        $('.o_search_options .fa-bars').click();
        // Activate the groupby 'Date'
        $('.o_group_by_menu .o_menu_item').click();
        // by default, data should be grouped by the field 'Date' using the interval 'day'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Day');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // open submenu with interval options
        $('.o_group_by_menu .o_menu_item .o_submenu_switcher').click();
        // select option 'month'
        $('.o_group_by_menu .o_menu_item .o_item_option:nth-child(3)').click();
        // data should be grouped by the field 'Date' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Date: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 3);
        // deactivate option 'month'
        $('.o_group_by_menu .o_menu_item .o_item_option:nth-child(3)').click();
        // no groupby is applied
        assert.strictEqual($('div.o_facet_values span').length, 0);
        // open 'Add custom Groupby' menu
        $('.o_group_by_menu .o_add_custom_group a').click();
        // click on 'Apply' button
        $('.o_group_by_menu .o_generator_menu button').click();
        // data should be grouped by the field 'Birthday' using the interval 'month'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Month');
        assert.strictEqual($('.o_content tr.o_group_header').length, 5);
        // open submenu with interval options
        $('.o_group_by_menu .o_menu_item .o_submenu_switcher').eq(1).click();
        // select option 'year'
        $('.o_group_by_menu .o_menu_item .o_item_option').eq(9).click();
        // data should be grouped by the field 'Birthday' using the interval 'year'
        assert.strictEqual($('div.o_facet_values span').text().trim(),'Birthday: Year');
        assert.strictEqual($('.o_content tr.o_group_header').length, 4);
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
        $('li.o_add_custom_filter').click();
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
        $('li.o_add_custom_filter').click();
        $('.o_apply_filter').click();
        $('li.o_menu_item').click();
        assert.strictEqual($('.o_searchview .o_searchview_facet .o_facet_values span').length, 0,
            'no facet should be in the search view');
        actionManager.destroy();
    });
});
});