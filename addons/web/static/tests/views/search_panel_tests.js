odoo.define('web.search_panel_tests', function (require) {
"use strict";

var AbstractStorageService = require('web.AbstractStorageService');
var FormView = require('web.FormView');
var KanbanView = require('web.KanbanView');
var RamStorage = require('web.RamStorage');
var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: 'boolean'},
                    int_field: {string: "Int Field", type: 'integer', group_operator: 'sum'},
                    company_id: {string: "company", type: 'many2one', relation: 'company'},
                    category_id: { string: "category", type: 'many2one', relation: 'category' },
                    state: { string: "State", type: 'selection', selection: [['abc', "ABC"], ['def', "DEF"], ['ghi', "GHI"]]},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 1, company_id: 3, state: 'abc', category_id: 6},
                    {id: 2, bar: true, foo: "blip", int_field: 2, company_id: 5, state: 'def', category_id: 7},
                    {id: 3, bar: true, foo: "gnap", int_field: 4, company_id: 3, state: 'ghi', category_id: 7},
                    {id: 4, bar: false, foo: "blip", int_field: 8, company_id: 5, state: 'ghi', category_id: 7},
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

        this.actions = [{
            id: 1,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'kanban'], [false, 'list'], [false, 'pivot'], [false, 'form']],
        }, {
            id: 2,
            name: 'Partners',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }];

        this.archs = {
            'partner,false,list': '<tree><field name="foo"/></tree>',
            'partner,false,kanban':
                `<kanban>
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            'partner,false,form':
                `<form>
                    <button name="1" type="action" string="multi view"/>
                    <field name="foo"/>
                </form>`,
            'partner,false,pivot': '<pivot><field name="int_field" type="measure"/></pivot>',
            'partner,false,search':
                `<search>
                    <searchpanel>
                        <field name="company_id"/>
                        <field select="multi" name="category_id"/>
                    </searchpanel>
                </search>`,
        };

        var RamStorageService = AbstractStorageService.extend({
            storage: new RamStorage(),
        });
        this.services = {
            local_storage: RamStorageService,
        };
    },
}, function () {

    QUnit.module('SearchPanel');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(17);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                assert.step((args.method || route) + (args.model ? (' on ' + args.model) : ''));
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field select="multi" name="category_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsOnce(kanban, '.o_content.o_controller_with_searchpanel > .o_search_panel');
        assert.containsOnce(kanban, '.o_content.o_controller_with_searchpanel > .o_kanban_view');

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

    QUnit.test('sections with custom icon and color', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" icon="fa-car" color="blue"/>
                            <field select="multi" name="state" icon="fa-star" color="#000"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.hasClass(kanban.$('.o_search_panel_section_header:first i'), 'fa-car');
        assert.hasAttrValue(kanban.$('.o_search_panel_section_header:first i'), 'style="{color: blue}"');
        assert.hasClass(kanban.$('.o_search_panel_section_header:nth(1) i'), 'fa-star');
        assert.hasAttrValue(kanban.$('.o_search_panel_section_header:nth(1) i'), 'style="{color: #000}"');

        kanban.destroy();
    });

    QUnit.test('sections with attr invisible="1" are ignored', async function (assert) {
        // 'groups' attributes are converted server-side into invisible="1" when the user doesn't
        // belong to the given group
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `<kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field select="multi" invisible="1" name="state"/>
                        </searchpanel>
                    </search>`,
            },
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

    QUnit.test('categories and filters order is kept', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field select="multi" name="category_id"/>
                            <field name="state"/>
                        </searchpanel>
                    </search>`,
            }
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

    QUnit.test('specify active category value in context', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field name="state"/>
                        </searchpanel>
                    </search>`,
            },
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

    QUnit.test('use category (on many2one) to refine search', async function (assert) {
        assert.expect(14);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        // select 'asustek'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","child_of",3]]',
            '[["bar","=",true],["company_id","child_of",5]]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('use category (on selection) to refine search', async function (assert) {
        assert.expect(14);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="state"/></searchpanel></search>`,
            },
        });

        // select 'abc'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(3) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'All' again
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

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

    QUnit.test('store and retrieve active category value', async function (assert) {
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
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <seasrch>
                        <searchpanel>
                            <field name="company_id"/>
                        </searchpanel>
                    </seasrch>`,
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.deepEqual(args.domain, [['company_id', 'child_of', expectedActiveId]]);
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
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.verifySteps([
            'getItem searchpanel_partner_company_id',
            'setItem searchpanel_partner_company_id to 5',
        ]);

        kanban.destroy();
    });

    QUnit.test('retrieved category value does not exist', async function (assert) {
        assert.expect(6);

        var Storage = RamStorage.extend({
            getItem: function (key) {
                assert.step('getItem ' + key);
                return 343; // this value doesn't exist
            },
        });
        var RamStorageService = AbstractStorageService.extend({
            storage: new Storage(),
        });

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
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

        assert.verifySteps(['getItem searchpanel_partner_company_id']);

        kanban.destroy();
    });

    QUnit.test('category has been archived', async function (assert) {
        assert.expect(2);

        this.data.company.fields.active = {type: 'boolean', string: 'Archived'};
        this.data.company.records = [
            {
                name: 'Company 5',
                id: 5,
                active: true,
            }, {
                name: 'child of 5 archived',
                parent_id: 5,
                id: 666,
                active: false,
            }, {
                name: 'child of 666',
                parent_id: 666,
                id: 777,
                active: true,
            }
        ];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `
                <kanban>
                  <templates>
                    <t t-name="kanban-box">
                      <div>
                        <field name="foo"/>
                      </div>
                    </t>
                  </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
            mockRPC: async function (route, args) {
                if (route === '/web/dataset/call_kw/partner/search_panel_select_range') {
                    var results = await this._super.apply(this, arguments);
                    results.values = results.values.filter(rec => rec.active !== false);
                    return Promise.resolve(results);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_search_panel_category_value', 2,
            'The number of categories should be 2: All and Company 5');

        assert.containsNone(kanban, '.o_toggle_fold',
            'None of the categories should have children');

        kanban.destroy();
    });

    QUnit.test('use two categories to refine search', async function (assert) {
        assert.expect(14);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field name="state"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_section', 2);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'asustek'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=3] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'abc'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=abc] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi'
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value[data-id=ghi] header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in first category (company_id)
        await testUtils.dom.click(kanban.$('.o_search_panel_section:first .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in second category (state)
        await testUtils.dom.click(kanban.$('.o_search_panel_section:nth(1) .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","child_of",3]]',
            '[["bar","=",true],["company_id","child_of",3],["state","=","abc"]]',
            '[["bar","=",true],["company_id","child_of",3],["state","=","ghi"]]',
            '[["bar","=",true],["state","=","ghi"]]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('category with parent_field', async function (assert) {
        assert.expect(28);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
        });

        // 'All' is selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_search_panel_category_value .o_toggle_fold');

        // unfold parent category
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_toggle_fold'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 5);
        assert.containsN(kanban, '.o_search_panel_category_value .o_search_panel_category_value', 2);

        // click on first child company
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_search_panel_category_value:first header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value .o_search_panel_category_value:first .active');
        assert.containsOnce(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        // click on parent company
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) > header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // parent company should be folded
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // fold category with children
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_toggle_fold'));
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value .o_toggle_fold'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        assert.verifySteps([
            '[]',
            '[["company_id","child_of",40]]',
            '[["company_id","child_of",5]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('category with no parent_field', async function (assert) {
        assert.expect(10);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="category_id"/></searchpanel></search>`,
            },
        });

        // 'All' is selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        // click on 'gold' category
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsOnce(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        assert.verifySteps([
            '[]',
            '[["category_id","=",6]]', // must use '=' operator (instead of 'child_of')
        ]);

        kanban.destroy();
    });

    QUnit.test('can (un)fold parent category values', async function (assert) {
        assert.expect(7);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
        });

        assert.strictEqual(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold').length, 1,
            "'agrolait' should be displayed as a parent category value");
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-left',
            "'agrolait' should be folded");
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        // unfold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        // fold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-left',
            "'agrolait' should be folded");
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        kanban.destroy();
    });

    QUnit.test('fold status is kept at reload', async function (assert) {
        assert.expect(4);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 5});
        this.data.company.records.push({id: 41, name: 'child company 2', parent_id: 5});
        this.data.partner.records[1].company_id = 40;

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
        });

        // unfold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        await kanban.reload({});

        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        kanban.destroy();
    });

    QUnit.test('concurrency: delayed search_reads', async function (assert) {
        assert.expect(19);

        var def;
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `<search><searchpanel><field name="company_id"/></searchpanel></search>`,
            },
            domain: [['bar', '=', true]],
        });

        // 'All' should be selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'asustek' (delay the reload)
        def = testUtils.makeTestPromise();
        var asustekDef = def;
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        // 'asustek' should be selected, but there should still be 3 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'agrolait' (delay the reload)
        def = testUtils.makeTestPromise();
        var agrolaitDef = def;
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        // 'agrolait' should be selected, but there should still be 3 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // unlock asustek search (should be ignored, so there should still be 3 records)
        asustekDef.resolve();
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // unlock agrolait search, there should now be 1 record
        agrolaitDef.resolve();
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        assert.verifySteps([
            '[["bar","=",true]]',
            '[["bar","=",true],["company_id","child_of",3]]',
            '[["bar","=",true],["company_id","child_of",5]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('concurrency: misordered get_filters', async function (assert) {
        assert.expect(15);

        var def;
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="state"/>
                            <field select="multi" name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        // 'All' should be selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'abc' (delay the reload)
        def = testUtils.makeTestPromise();
        var abcDef = def;
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        // 'All' should still be selected, and there should still be 4 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'ghi' (delay the reload)
        def = testUtils.makeTestPromise();
        var ghiDef = def;
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(3) header'));

        // 'All' should still be selected, and there should still be 4 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // unlock ghi search
        ghiDef.resolve();
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // unlock abc search (should be ignored)
        abcDef.resolve();
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        kanban.destroy();
    });

    QUnit.test('concurrency: delayed get_filter', async function (assert) {
        assert.expect(3);

        var def;
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'search_panel_select_multi_range') {
                    return Promise.resolve(def).then(_.constant(result));
                }
                return result;
            },
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        // trigger a reload and delay the get_filter
        def = testUtils.makeTestPromise();
        kanban.reload({domain: [['id', '=', 1]]});
        await testUtils.nextTick();

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        def.resolve();
        await testUtils.nextTick();

        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');

        kanban.destroy();
    });

    QUnit.test('use filter (on many2one) to refine search', async function (assert) {
        assert.expect(32);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'asustek'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // check 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // uncheck 'asustek'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustekagrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1);

        // uncheck 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            // nothing checked
            '[]',
            '[["bar","=",true]]',
            // 'asustek' checked
            '[["company_id","in",[3]]]',
            '[["bar","=",true],["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[["company_id","in",[3,5]]]',
            '[["bar","=",true],["company_id","in",[3,5]]]',
            // 'agrolait' checked
            '[["company_id","in",[5]]]',
            '[["bar","=",true],["company_id","in",[5]]]',
            // nothing checked
            '[]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('use filter (on selection) to refine search', async function (assert) {
        assert.expect(32);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="state"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 3);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'abc'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEFGHI');
        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1);

        // check 'def'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // uncheck 'abc'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABCDEF1GHI');
        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)');

        // uncheck 'def'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            // nothing checked
            '[]',
            '[["bar","=",true]]',
            // 'asustek' checked
            '[["state","in",["abc"]]]',
            '[["bar","=",true],["state","in",["abc"]]]',
            // 'asustek' and 'agrolait' checked
            '[["state","in",["abc","def"]]]',
            '[["bar","=",true],["state","in",["abc","def"]]]',
            // 'agrolait' checked
            '[["state","in",["def"]]]',
            '[["bar","=",true],["state","in",["def"]]]',
            // nothing checked
            '[]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('only reload filters when domains change', async function (assert) {
        assert.expect(11);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="state"/>
                            <field select="multi" name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
        ]);

        // go to page 2 (the domain doesn't change, so the filters should not be reloaded)
        await testUtils.dom.click(kanban.$('.o_pager_next'));

        assert.verifySteps([
            '/web/dataset/search_read',
        ]);

        // reload with another domain, so the filters should be reloaded
        await kanban.reload({domain: [['id', '<', 5]]});

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
        ]);

        // change category value, so the filters should be reloaded
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([
            'search_panel_select_multi_range',
            '/web/dataset/search_read',
        ]);

        kanban.destroy();
    });

    QUnit.test('filter with groupby', async function (assert) {
        assert.expect(42);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id" groupby="category_id"/>
                        </searchpanel>
                    </search>`,
            },
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
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        var firstGroupCheckbox = kanban.$('.o_search_panel_filter_group:first > div > input').get(0);
        assert.strictEqual(firstGroupCheckbox.checked, true,
            "first group checkbox should be checked");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // check 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

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
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(2) input'));

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
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) > div > input'));

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
            '[["company_id","in",[3]]]',
            '[["bar","=",true],["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[["company_id","in",[3]],["company_id","in",[5]]]',
            '[["bar","=",true],["company_id","in",[3]],["company_id","in",[5]]]',
            // 'asustek', 'agrolait' and 'camptocamp' checked
            '[["company_id","in",[3]],["company_id","in",[5,11]]]',
            '[["bar","=",true],["company_id","in",[3]],["company_id","in",[5,11]]]',
            // 'asustek' checked
            '[["company_id","in",[3]]]',
            '[["bar","=",true],["company_id","in",[3]]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('filter with domain', async function (assert) {
        assert.expect(3);

        this.data.company.records.push({id: 40, name: 'child company 1', parent_id: 3});

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id" domain="[('parent_id','=',False)]"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait2');

        kanban.destroy();
    });

    QUnit.test('(un)fold filter group', async function (assert) {
        assert.expect(13);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id" groupby="category_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        // groups are opened by default
        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsN(kanban, '.o_search_panel_filter_value', 3);

        // check 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));
        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);
        assert.hasAttrValue(kanban.$('.o_search_panel_filter_value:nth(1) input'), 'checked', 'checked');

        // fold second group
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);

        // fold first group
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_group:first .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value');

        // unfold second group
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) .o_toggle_fold'));

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);
        assert.hasAttrValue(kanban.$('.o_search_panel_filter_value:first input'), 'checked', 'checked');

        kanban.destroy();
    });

    QUnit.test('filter with domain depending on category', async function (assert) {
        assert.expect(22);

        var kanban = await createView({
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
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="category_id"/>
                            <field select="multi" name="company_id" domain="[['category_id', '=', category_id]]"/>
                        </searchpanel>
                    </search>`,
            },
        });

        // select 'gold' category
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            "asustek1");

        // select 'silver' category
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsOnce(kanban, '.o_search_panel_filter_value');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            "agrolait2");

        // select All
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:first header'));

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

    QUnit.test('specify active filter values in context', async function (assert) {
        assert.expect(4);

        var expectedDomain = [
            ['company_id', 'in', [5]],
            ['state', 'in', ['abc', 'ghi']],
        ];
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id"/>
                            <field select="multi" name="state"/>
                        </searchpanel>
                    </search>`,
            },
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
        await testUtils.dom.click(kanban.$('.o_search_panel_filter:first .o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);

        kanban.destroy();
    });

    QUnit.test('retrieved filter value from context does not exist', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id"/>
                        </searchpanel>
                    </search>`,
            },
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

    QUnit.test('filter with groupby and default values in context', async function (assert) {
        assert.expect(2);

        this.data.company.records.push({id: 11, name: 'camptocamp', category_id: 7});

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field select="multi" name="company_id" groupby="category_id"/>
                        </searchpanel>
                    </search>`,
            },
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

    QUnit.test('tests conservation of category record order', async function (assert) {
        assert.expect(1);

        this.data.company.records.push({id: 56, name: 'highID', category_id: 6});
        this.data.company.records.push({id: 2, name: 'lowID', category_id: 6});

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            services: this.services,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="foo"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id"/>
                            <field select="multi" name="category_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        var $firstSection = kanban.$('.o_search_panel_section:first');
        assert.strictEqual($firstSection.find('.o_search_panel_category_value').text().replace(/\s/g, ''),
            'AllasustekagrolaithighIDlowID');
        kanban.destroy();
    });

    QUnit.test('search panel is available on list and kanban by default', async function (assert) {
        assert.expect(8);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await testUtils.dom.click(actionManager.$('.o_cp_switch_pivot'));
        assert.containsOnce(actionManager, '.o_content .o_pivot');
        assert.containsNone(actionManager, '.o_content .o_search_panel');

        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_list_view');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await testUtils.dom.click(actionManager.$('.o_data_row .o_data_cell:first'));
        assert.containsOnce(actionManager, '.o_content .o_form_view');
        assert.containsNone(actionManager, '.o_content .o_search_panel');

        actionManager.destroy();
    });

    QUnit.test('search panel with view_types attribute', async function (assert) {
        assert.expect(6);

        this.archs['partner,false,search'] =
            `<search>
                <searchpanel view_types="kanban,pivot">
                    <field name="company_id"/>
                    <field select="multi" name="category_id"/>
                </searchpanel>
            </search>`;


        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.containsOnce(actionManager, '.o_content .o_list_view');
        assert.containsNone(actionManager, '.o_content .o_search_panel');

        await testUtils.dom.click(actionManager.$('.o_cp_switch_pivot'));
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_pivot');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');

        actionManager.destroy();
    });

    QUnit.test('search panel state is shared between views', async function (assert) {
        assert.expect(16);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);
        assert.hasClass(actionManager.$('.o_search_panel_category_value:first header'), 'active');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'asustek' company
        await testUtils.dom.click(actionManager.$('.o_search_panel_category_value:nth(1) header'));
        assert.hasClass(actionManager.$('.o_search_panel_category_value:nth(1) header'), 'active');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.hasClass(actionManager.$('.o_search_panel_category_value:nth(1) header'), 'active');
        assert.containsN(actionManager, '.o_data_row', 2);

        // select 'agrolait' company
        await testUtils.dom.click(actionManager.$('.o_search_panel_category_value:nth(2) header'));
        assert.hasClass(actionManager.$('.o_search_panel_category_value:nth(2) header'), 'active');
        assert.containsN(actionManager, '.o_data_row', 2);

        await testUtils.dom.click(actionManager.$('.o_cp_switch_kanban'));
        assert.hasClass(actionManager.$('.o_search_panel_category_value:nth(2) header'), 'active');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        assert.verifySteps([
            '[]', // initial search_read
            '[["company_id","child_of",3]]', // kanban, after selecting the first company
            '[["company_id","child_of",3]]', // list
            '[["company_id","child_of",5]]', // list, after selecting the other company
            '[["company_id","child_of",5]]', // kanban
        ]);

        actionManager.destroy();
    });

    QUnit.test('search panel filters are kept between switch views', async function (assert) {
        assert.expect(16);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);
        assert.containsNone(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select gold filter
        await testUtils.dom.click(actionManager.$('.o_search_panel_filter input[type="checkbox"]:nth(0)'));
        assert.containsOnce(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.containsOnce(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_data_row', 1);

        // select silver filter
        await testUtils.dom.click(actionManager.$('.o_search_panel_filter input[type="checkbox"]:nth(1)'));
        assert.containsN(actionManager, '.o_search_panel_filter_value input:checked', 2);
        assert.containsN(actionManager, '.o_data_row', 4);

        await testUtils.dom.click(actionManager.$('.o_cp_switch_kanban'));
        assert.containsN(actionManager, '.o_search_panel_filter_value input:checked', 2);
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        assert.verifySteps([
            '[]', // initial search_read
            '[["category_id","in",[6]]]', // kanban, after selecting the gold filter
            '[["category_id","in",[6]]]', // list
            '[["category_id","in",[6,7]]]', // list, after selecting the silver filter
            '[["category_id","in",[6,7]]]', // kanban
        ]);

        actionManager.destroy();
    });

    QUnit.test('search panel filters are kept when switching to a view with no search panel', async function (assert) {
        assert.expect(13);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
        });

        await actionManager.doAction(1);
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');
        assert.containsNone(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select gold filter
        await testUtils.dom.click(actionManager.$('.o_search_panel_filter input[type="checkbox"]:nth(0)'));
        assert.containsOnce(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // switch to pivot
        await testUtils.dom.click(actionManager.$('.o_cp_switch_pivot'));
        assert.containsOnce(actionManager, '.o_content .o_pivot');
        assert.containsNone(actionManager, '.o_content .o_search_panel');
        assert.strictEqual(actionManager.$('.o_pivot_cell_value').text(), '15');

        // switch to list
        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_list_view');
        assert.containsOnce(actionManager, '.o_content.o_controller_with_searchpanel .o_search_panel');
        assert.containsOnce(actionManager, '.o_search_panel_filter_value input:checked');
        assert.containsN(actionManager, '.o_data_row', 1);

        actionManager.destroy();
    });

    QUnit.test('after onExecuteAction, selects "All" as default category value', async function (assert) {
        assert.expect(4);

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

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: {
                local_storage: RamStorageService,
            },
        });

        await actionManager.doAction(2);
        await testUtils.dom.click(actionManager.$('.o_form_view button:contains("multi view")'));

        assert.containsOnce(actionManager, '.o_kanban_view');
        assert.containsOnce(actionManager, '.o_search_panel');
        assert.containsOnce(actionManager, '.o_search_panel_category_value:first .active');

        assert.verifySteps([]); // should not communicate with localStorage

        actionManager.destroy();
    });

    QUnit.test('search panel is not instantiated if stated in context', async function (assert) {
        assert.expect(2);

        this.actions[0].context = {search_panel: false};
        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: this.services,
        });

        await actionManager.doAction(2);
        await testUtils.dom.click(actionManager.$('.o_form_view button:contains("multi view")'));

        assert.containsOnce(actionManager, '.o_kanban_view');
        assert.containsNone(actionManager, '.o_search_panel');

        actionManager.destroy();
    });

    QUnit.test('categories and filters are not reloaded when switching between views', async function (assert) {
        assert.expect(8);

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: this.services,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(1);
        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        await testUtils.dom.click(actionManager.$('.o_cp_switch_kanban'));

        assert.verifySteps([
            '/web/action/load',
            'load_views',
            'search_panel_select_range', // kanban: categories
            'search_panel_select_multi_range', // kanban: filters
            '/web/dataset/search_read', // kanban: records
            '/web/dataset/search_read', // list: records
            '/web/dataset/search_read', // kanban: records
        ]);

        actionManager.destroy();
    });

    QUnit.test('scroll position is kept when switching between controllers', async function (assert) {
        assert.expect(6);

        for (var i = 10; i < 20; i++) {
            this.data.category.records.push({id: i, name: "Cat " + i});
        }

        var actionManager = await createActionManager({
            actions: this.actions,
            archs: this.archs,
            data: this.data,
            services: this.services,
        });
        actionManager.$el.css('max-height', 300);

        await actionManager.doAction(1);
        assert.containsOnce(actionManager, '.o_content .o_kanban_view');
        assert.strictEqual(actionManager.$('.o_search_panel').scrollTop(), 0);

        // simulate a scroll in the search panel and switch into list
        actionManager.$('.o_search_panel').scrollTop(50);
        await testUtils.dom.click(actionManager.$('.o_cp_switch_list'));
        assert.containsOnce(actionManager, '.o_content .o_list_view');
        assert.strictEqual(actionManager.$('.o_search_panel').scrollTop(), 50);

        // simulate another scroll and switch back to kanban
        actionManager.$('.o_search_panel').scrollTop(30);
        await testUtils.dom.click(actionManager.$('.o_cp_switch_kanban'));
        assert.containsOnce(actionManager, '.o_content .o_kanban_view');
        assert.strictEqual(actionManager.$('.o_search_panel').scrollTop(), 30);

        actionManager.destroy();
    });

    QUnit.test('search panel is not instantiated in dialogs', async function (assert) {
        assert.expect(2);

        this.data.company.records = [
            {id: 1, name: 'Company1'},
            {id: 2, name: 'Company2'},
            {id: 3, name: 'Company3'},
            {id: 4, name: 'Company4'},
            {id: 5, name: 'Company5'},
            {id: 6, name: 'Company6'},
            {id: 7, name: 'Company7'},
            {id: 8, name: 'Company8'},
        ];

        var form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="company_id"/></form>',
            archs: {
                'company,false,list': '<tree><field name="name"/></tree>',
                'company,false,search':
                    `<search>
                        <field name="name"/>
                        <searchpanel>
                            <field name="category_id"/>
                        </searchpanel>
                    </search>`,
            },
        });

        await testUtils.fields.many2one.clickOpenDropdown('company_id');
        await testUtils.fields.many2one.clickItem('company_id', 'Search More');

        assert.containsOnce(document.body, '.modal .o_list_view');
        assert.containsNone(document.body, '.modal .o_search_panel');

        form.destroy();
    });
});
});
