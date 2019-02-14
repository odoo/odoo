odoo.define('web.search_panel_tests', function (require) {
"use strict";

var AbstractStorageService = require('web.AbstractStorageService');
var KanbanView = require('web.KanbanView');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: 'boolean'},
                    company_id: {string: "company", type: 'many2one', relation: 'company'},
                    category_id: { string: "category", type: 'many2one', relation: 'category' },
                    state: { string: "State", type: 'selection', selection: [['abc', "ABC"], ['def', "DEF"], ['ghi', "GHI"]]},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", company_id: 3, state: 'abc', category_id: 6},
                    {id: 2, bar: true, foo: "blip", company_id: 5, state: 'def', category_id: 7},
                    {id: 3, bar: true, foo: "gnap", company_id: 3, state: 'ghi', category_id: 7},
                    {id: 4, bar: false, foo: "blip", company_id: 5, state: 'ghi', category_id: 7},
                ]
            },
            company: {
                fields: {
                    name: {string: "Display Name", type: 'char'},
                    parent_id: {string: 'Parent company', type: 'many2one', relation: 'company'},
                    category_id: {string: 'Category', type: 'many2one', relation: 'category'},
                },
                records: [
                    {id: 3, name: "asustek", category_id: 6},
                    {id: 5, name: "agrolait", category_id: 7},
                ],
            },
            category: {
                fields: {
                    name: {string: "Category Name", type: 'char'},
                },
                records: [
                    {id: 6, name: "gold"},
                    {id: 7, name: "silver"},
                ]
            },
        };

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        this.services = {
            local_storage: RamStorageService,
        };
    },
}, function () {

    QUnit.module('SearchPanel in Kanban views');

    QUnit.test('basic rendering', function (assert) {
        assert.expect(17);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                assert.step((args.method || route) + (args.model ? (' on ' + args.model) : ''));
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                        '<field select="multi" name="category_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.containsOnce(kanban, '.o_content.o_kanban_with_searchpanel > .o_search_panel');
        assert.containsOnce(kanban, '.o_content.o_kanban_with_searchpanel > .o_kanban_view');

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        assert.containsN(kanban, '.o_search_panel_section', 2);

        var $firstSection = kanban.$('.o_search_panel_section:first');
        assert.hasClass($firstSection.find('.o_search_panel_section_header i'), 'fa-folder');
        assert.containsOnce($firstSection, '.o_search_panel_section_header:contains(company)');
        assert.containsN($firstSection, '.o_search_panel_category_value', 3);
        assert.containsOnce($firstSection, '.o_search_panel_category_value:first .active');
        assert.strictEqual($firstSection.find('.o_search_panel_category_value').text().replace(/\s/g, ''),
            'Allasustekagrolait');

        var $secondSection = kanban.$('.o_search_panel_section:nth(1)');
        assert.hasClass($secondSection.find('.o_search_panel_section_header i'), 'fa-filter');
        assert.containsOnce($secondSection, '.o_search_panel_section_header:contains(category)');
        assert.containsN($secondSection, '.o_search_panel_filter_value', 2);
        assert.strictEqual($secondSection.find('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'gold1silver3');

        assert.verifySteps([
            'search_panel_select_range on partner',
            'search_panel_select_multi_range on partner',
            '/web/dataset/search_read on partner',
        ]);

        kanban.destroy();
    });

    QUnit.test('sections with custom icon and color', function (assert) {
        assert.expect(4);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id" icon="fa-car" color="blue"/>' +
                        '<field select="multi" name="state" icon="fa-star" color="#000"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.hasClass(kanban.$('.o_search_panel_section_header:first i'), 'fa-car');
        assert.hasAttrValue(kanban.$('.o_search_panel_section_header:first i'), 'style="{color: blue}"');
        assert.hasClass(kanban.$('.o_search_panel_section_header:nth(1) i'), 'fa-star');
        assert.hasAttrValue(kanban.$('.o_search_panel_section_header:nth(1) i'), 'style="{color: #000}"');

        kanban.destroy();
    });

    QUnit.test('sections with attr invisible="1" are ignored', function (assert) {
        // 'groups' attributes are converted server-side into invisible="1" when the user doesn't
        // belong to the given group
        assert.expect(4);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                        '<field select="multi" invisible="1" name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, '.o_search_panel_section');

        assert.verifySteps([
            'search_panel_select_range',
            '/web/dataset/search_read',
        ]);

        kanban.destroy();
    });

    QUnit.test('categories and filters order is kept', function (assert) {
        assert.expect(4);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                        '<field select="multi" name="category_id"/>' +
                        '<field name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.containsN(kanban, '.o_search_panel_section', 3);
        assert.strictEqual(kanban.$('.o_search_panel_section_header:nth(0)').text().trim(),
            'company');
        assert.strictEqual(kanban.$('.o_search_panel_section_header:nth(1)').text().trim(),
            'category');
        assert.strictEqual(kanban.$('.o_search_panel_section_header:nth(2)').text().trim(),
            'State');

        kanban.destroy();
    });

    QUnit.test('specify active category value in context', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                        '<field name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [["state", "=", "ghi"]]);
                }
                return this._super.apply(this, arguments);
            },
            context: {
                searchpanel_default_company_id: false,
                searchpanel_default_state: 'ghi',
            },
        });

        kanban.destroy();
    });

    QUnit.test('use category (on many2one) to refine search', function (assert) {
        assert.expect(14);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        // select 'asustek'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'agrolait'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","=",3]]',
            '[["bar","=",true],["company_id","=",5]]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('use category (on selection) to refine search', function (assert) {
        assert.expect(14);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // select 'abc'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(3) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'All' again
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        assert.verifySteps([
            '[]',
            '[["state","=","abc"]]',
            '[["state","=","ghi"]]',
            '[]',
        ]);

        kanban.destroy();
    });

    QUnit.test('store and retrieve active category value', function (assert) {
        assert.expect(8);

        var Storage = RamStorage.extend({
            getItem: function (key) {
                assert.step('getItem ' + key);
                return 3; // 'asustek'
            },
            setItem: function (key, value) {
                assert.step('setItem ' + key + ' to ' + value);
            },
        });
        var RamStorageService = AbstractStorageService.extend({
            storage: new Storage(),
        });

        var expectedActiveId = 3;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [['company_id', '=', expectedActiveId]]);
                }
                return this._super.apply(this, arguments);
            },
        });

        // 'asustek' should be selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'agrolait'
        expectedActiveId = 5;
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.verifySteps([
            'getItem searchpanel_partner_company_id',
            'setItem searchpanel_partner_company_id to 5',
        ]);

        kanban.destroy();
    });

    QUnit.test('retrieved category value does not exist', function (assert) {
        assert.expect(5);

        var Storage = RamStorage.extend({
            getItem: function (key) {
                assert.step('getItem ' + key);
                return 343; // this value doesn't exist
            },
        });
        var RamStorageService = AbstractStorageService.extend({
            storage: new Storage(),
        });

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, []);
                }
                return this._super.apply(this, arguments);
            },
        });

        // 'All' should be selected by default as the retrieved value does not exist
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        kanban.destroy();
    });

    QUnit.test('use two categories to refine search', function (assert) {
        assert.expect(14);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                        '<field name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_section', 2);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'asustek'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=3] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'abc'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=abc] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi'
        testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=ghi] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in first category (company_id)
        testUtils.dom.click(kanban.$('.o_search_panel_section:first .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in second category (state)
        testUtils.dom.click(kanban.$('.o_search_panel_section:nth(1) .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","=",3]]',
            '[["bar","=",true],["company_id","=",3],["state","=","abc"]]',
            '[["bar","=",true],["company_id","=",3],["state","=","ghi"]]',
            '[["bar","=",true],["state","=","ghi"]]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('category with parent_field', function (assert) {
        assert.expect(24);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // 'All' is selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_search_panel_category_value .o_toggle_fold');

        // unfold parent category
        testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_toggle_fold'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 5);
        assert.containsN(kanban, '.o_search_panel_category_value .o_search_panel_category_value', 2);

        // click on first child company
        testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value .o_search_panel_category_value:first .active');
        assert.containsOnce(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        // click on parent company
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) > header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // fold category with children
        testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_toggle_fold'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        assert.verifySteps([
            '[]',
            '[["company_id","=",40]]',
            '[["company_id","=",5]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('can (un)fold parent category values', function (assert) {
        assert.expect(7);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.strictEqual(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold').length, 1,
            "'agrolait' should be displayed as a parent category value");
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-left',
            "'agrolait' should be folded");
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        // unfold agrolait
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        // fold agrolait
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-left',
            "'agrolait' should be folded");
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        kanban.destroy();
    });

    QUnit.test('fold status is kept at reload', function (assert) {
        assert.expect(4);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // unfold agrolait
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        kanban.reload({});

        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        kanban.destroy();
    });

    QUnit.test('concurrency: delayed search_reads', function (assert) {
        assert.expect(19);

        var def;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        // 'All' should be selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'asustek' (delay the reload)
        def = $.Deferred();
        var asustekDef = def;
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        // 'asustek' should be selected, but there should still be 3 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'agrolait' (delay the reload)
        def = $.Deferred();
        var agrolaitDef = def;
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        // 'agrolait' should be selected, but there should still be 3 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // unlock asustek search (should be ignored, so there should still be 3 records)
        asustekDef.resolve();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // unlock agrolait search, there should now be 1 record
        agrolaitDef.resolve();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","=",3]]',
            '[["bar","=",true],["company_id","=",5]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('concurrency: misordered get_filters', function (assert) {
        assert.expect(15);

        var def;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="state"/>' +
                        '<field select="multi" name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // 'All' should be selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'abc' (delay the reload)
        def = $.Deferred();
        var abcDef = def;
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        // 'All' should still be selected, and there should still be 4 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'ghi' (delay the reload)
        def = $.Deferred();
        var ghiDef = def;
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(3) header'));

        // 'All' should still be selected, and there should still be 4 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // unlock ghi search
        ghiDef.resolve();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // unlock abc search (should be ignored)
        abcDef.resolve();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        kanban.destroy();
    });

    QUnit.test('concurrency: delayed get_filter', function (assert) {
        assert.expect(3);

        var def;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    return $.when(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        // trigger a reload and delay the get_filter
        def = $.Deferred();
        kanban.reload({domain: [['id', '=', 1]]});

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        def.resolve();

        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');

        kanban.destroy();
    });

    QUnit.test('use filter (on many2one) to refine search', function (assert) {
        assert.expect(32);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    // the following keys should have same value for all calls to this route
                    var keys = ['field_name', 'group_by', 'comodel_domain', 'search_domain', 'category_domain'];
                    assert.deepEqual(_.pick(args.kwargs, keys), {
                        group_by: false,
                        comodel_domain: [],
                        search_domain: [['bar', '=', true]],
                        category_domain: [],
                    });
                    // the filter_domain depends on the filter selection
                    assert.step(JSON.stringify(args.kwargs.filter_domain));
                }
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'asustek'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // check 'agrolait'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // uncheck 'asustek'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustekagrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1);

        // uncheck 'agrolait'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            // nothing checked
            '[]',
            '[["bar","=",true]]',
            // 'asustek' checked
            '[["bar","=",true],["company_id","in",[3]]]',
            '[["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[["bar","=",true],["company_id","in",[3,5]]]',
            '[["company_id","in",[3,5]]]',
            // 'agrolait' checked
            '[["bar","=",true],["company_id","in",[5]]]',
            '[["company_id","in",[5]]]',
            // nothing checked
            '[["bar","=",true]]',
            '[]',
        ]);

        kanban.destroy();
    });

    QUnit.test('use filter (on selection) to refine search', function (assert) {
        assert.expect(32);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    // the following keys should have same value for all calls to this route
                    var keys = ['group_by', 'comodel_domain', 'search_domain', 'category_domain'];
                    assert.deepEqual(_.pick(args.kwargs, keys), {
                        group_by: false,
                        comodel_domain: [],
                        search_domain: [['bar', '=', true]],
                        category_domain: [],
                    });
                    // the filter_domain depends on the filter selection
                    assert.step(JSON.stringify(args.kwargs.filter_domain));
                }
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 3);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'abc'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEFGHI');
        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1);

        // check 'def'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // uncheck 'abc'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABCDEF1GHI');
        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');

        // uncheck 'def'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            // nothing checked
            '[]',
            '[["bar","=",true]]',
            // 'asustek' checked
            '[["bar","=",true],["state","in",["abc"]]]',
            '[["state","in",["abc"]]]',
            // 'asustek' and 'agrolait' checked
            '[["bar","=",true],["state","in",["abc","def"]]]',
            '[["state","in",["abc","def"]]]',
            // 'agrolait' checked
            '[["bar","=",true],["state","in",["def"]]]',
            '[["state","in",["def"]]]',
            // nothing checked
            '[["bar","=",true]]',
            '[]',
        ]);

        kanban.destroy();
    });

    QUnit.test('only reload filters when domains change', function (assert) {
        assert.expect(11);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="state"/>' +
                        '<field select="multi" name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
        ]);

        // go to page 2 (the domain doesn't change, so the filters should not be reloaded)
        testUtils.dom.click(kanban.$('.o_pager_next'));

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        // reload with another domain, so the filters should be reloaded
        kanban.reload({domain: [['id', '<', 5]]});

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'search_panel_select_multi_range',
        ]);

        // change category value, so the filters should be reloaded
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
            'search_panel_select_multi_range',
        ]);

        kanban.destroy();
    });

    QUnit.test('filter with groupby', function (assert) {
        assert.expect(42);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    // the following keys should have same value for all calls to this route
                    var keys = ['group_by', 'comodel_domain', 'search_domain', 'category_domain'];
                    assert.deepEqual(_.pick(args.kwargs, keys), {
                        group_by: 'category_id',
                        comodel_domain: [],
                        search_domain: [['bar', '=', true]],
                        category_domain: [],
                    });
                    // the filter_domain depends on the filter selection
                    assert.step(JSON.stringify(args.kwargs.filter_domain));
                }
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id" groupby="category_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsOnce(kanban, '.o_search_panel_filter_group:first .o_search_panel_filter_value');
        assert.containsN(kanban, '.o_search_panel_filter_group:nth(1) .o_search_panel_filter_value', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_group > div > label').text().replace(/\s/g, ''),
            'goldsilver');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1camptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'asustek'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        var firstGroupCheckbox = kanban.$('.o_search_panel_filter_group:first > div > input').get(0);
        assert.strictEqual(firstGroupCheckbox.checked, true,
            "first group checkbox should be checked");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // check 'agrolait'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.checked, false,
            "second group checkbox should not be checked");
        assert.strictEqual(secondGroupCheckbox.indeterminate, true,
            "second group checkbox should be indeterminate");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustekagrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 0);

        // check 'camptocamp'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(2) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 3);
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.checked, true,
            "second group checkbox should be checked");
        assert.strictEqual(secondGroupCheckbox.indeterminate, false,
            "second group checkbox should not be indeterminate");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustekagrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 0);

        // uncheck second group
        testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) > div > input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.checked, false,
            "second group checkbox should not be checked");
        assert.strictEqual(secondGroupCheckbox.indeterminate, false,
            "second group checkbox should not be indeterminate");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        assert.verifySteps([
            // nothing checked
            '[]',
            '[["bar","=",true]]',
            // 'asustek' checked
            '[["bar","=",true],["company_id","in",[3]]]',
            '[["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[["bar","=",true],["company_id","in",[3]],["company_id","in",[5]]]',
            '[["company_id","in",[3]],["company_id","in",[5]]]',
            // 'asustek', 'agrolait' and 'camptocamp' checked
            '[["bar","=",true],["company_id","in",[3]],["company_id","in",[5,11]]]',
            '[["company_id","in",[3]],["company_id","in",[5,11]]]',
            // 'asustek' checked
            '[["bar","=",true],["company_id","in",[3]]]',
            '[["company_id","in",[3]]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('filter with domain', function (assert) {
        assert.expect(3);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 3});

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    assert.deepEqual(args.kwargs, {
                        group_by: false,
                        category_domain: [],
                        filter_domain: [],
                        search_domain: [],
                        comodel_domain: [['parent_id', '=', false]],
                        disable_counters: false,
                    });
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id" domain="[(\'parent_id\',\'=\',False)]"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait2');

        kanban.destroy();
    });

    QUnit.test('(un)fold filter group', function (assert) {
        assert.expect(13);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id" groupby="category_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // groups are opened by default
        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsN(kanban, '.o_search_panel_filter_value', 3);

        // check 'agrolait'
        testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));
        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);
        assert.hasAttrValue(kanban.$('.o_search_panel_filter_value:nth(1) input'), 'checked', 'checked');

        // fold second group
        testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);

        // fold first group
        testUtils.dom.click(kanban.$('.o_search_panel_filter_group:first .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value');

        // unfold second group
        testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);
        assert.hasAttrValue(kanban.$('.o_search_panel_filter_value:first input'), 'checked', 'checked');

        kanban.destroy();
    });

    QUnit.test('filter with domain depending on category', function (assert) {
        assert.expect(22);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    // the following keys should have same value for all calls to this route
                    var keys = ['group_by', 'search_domain', 'filter_domain'];
                    assert.deepEqual(_.pick(args.kwargs, keys), {
                        group_by: false,
                        filter_domain: [],
                        search_domain: [],
                    });
                    assert.step(JSON.stringify(args.kwargs.category_domain));
                    assert.step(JSON.stringify(args.kwargs.comodel_domain));
                }
                return result;
            },
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field name="category_id"/>' +
                        '<field select="multi" name="company_id" domain="[[\'category_id\', \'=\', category_id]]"/>' +
                    '</searchpanel>' +
                '</kanban>',
        });

        // select 'gold' category
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            "asustek1");

        // select 'silver' category
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            "agrolait2");

        // select All
        testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsNone(kanban, '.o_search_panel_filter_value');

        assert.verifySteps([
            '[]', // category_domain (All)
            '[["category_id","=",false]]', // comodel_domain (All)
            '[["category_id","=",6]]', // category_domain ('gold')
            '[["category_id","=",6]]', // comodel_domain ('gold')
            '[["category_id","=",7]]', // category_domain ('silver')
            '[["category_id","=",7]]', // comodel_domain ('silver')
            '[]', // category_domain (All)
            '[["category_id","=",false]]', // comodel_domain (All)
        ]);

        kanban.destroy();
    });

    QUnit.test('specify active filter values in context', function (assert) {
        assert.expect(4);

        var expectedDomain = [
            ['company_id', 'in', [5]],
            ['state', 'in', ['abc', 'ghi']],
        ];
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id"/>' +
                        '<field select="multi" name="state"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, expectedDomain);
                }
                return this._super.apply(this, arguments);
            },
            context: {
                searchpanel_default_company_id: [5],
                searchpanel_default_state: ['abc', 'ghi'],
            },
        });

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 3);

        // manually untick a default value
        expectedDomain = [['state', 'in', ['abc', 'ghi']]];
        testUtils.dom.click(kanban.$('.o_search_panel_filter:first .o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);

        kanban.destroy();
    });

    QUnit.test('retrieved filter value from context does not exist', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [["company_id", "in", [3]]]);
                }
                return this._super.apply(this, arguments);
            },
            context: {
                searchpanel_default_company_id: [1, 3],
            },
        });

        kanban.destroy();
    });

    QUnit.test('filter with groupby and default values in context', function (assert) {
        assert.expect(2);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                    '<searchpanel>' +
                        '<field select="multi" name="company_id" groupby="category_id"/>' +
                    '</searchpanel>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [['company_id', 'in', [5]]]);
                }
                return this._super.apply(this, arguments);
            },
            context: {
                searchpanel_default_company_id: [5],
            },
        });

        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);

        kanban.destroy();
    });
});

});
