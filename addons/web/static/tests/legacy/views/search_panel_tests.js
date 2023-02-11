odoo.define("web/static/tests/views/search_panel_tests.js", function (require) {
"use strict";

const FormView = require('web.FormView');
const KanbanView = require('web.KanbanView');
const ListView = require('web.ListView');
const testUtils = require('web.test_utils');
const SearchPanel = require("web.searchPanel");

const createView = testUtils.createView;

const { makeFakeUserService } = require("@web/../tests/helpers/mock_services");
const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');
const { legacyExtraNextTick } = require("@web/../tests/helpers/utils");
const { registry } = require("@web/core/registry");
const { PivotView } = require("@web/views/pivot/pivot_view");

const {
    switchView,
    toggleFilterMenu,
    toggleMenuItem,
} = require("@web/../tests/search/helpers");

/**
 * Return the list of counters displayed in the search panel (if any).
 * @param {Widget} view, view controller
 * @returns {number[]}
 */
function getCounters(view) {
    return [...view.el.querySelectorAll('.o_search_panel_counter')].map(
        counter => Number(counter.innerText.trim())
    );
}

/**
 * Fold/unfold the category value (with children)
 * @param {Widget} widget
 * @param {string} text
 * @returns {Promise}
 */
function toggleFold(widget, text) {
    const headers = [...widget.el.querySelectorAll(".o_search_panel_category_value header")];
    const target = headers.find(
        (header) => header.innerText.trim().startsWith(text)
    );
    return testUtils.dom.click(target);
}

let serverData;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: 'char'},
                    bar: {string: "Bar", type: 'boolean'},
                    int_field: {string: "Int Field", type: 'integer', group_operator: 'sum'},
                    company_id: {string: "company", type: 'many2one', relation: 'company'},
                    company_ids: { string: "Companies", type: 'many2many', relation: 'company' },
                    category_id: { string: "category", type: 'many2one', relation: 'category' },
                    state: { string: "State", type: 'selection', selection: [['abc', "ABC"], ['def', "DEF"], ['ghi', "GHI"]]},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 1, company_ids: [3], company_id: 3, state: 'abc', category_id: 6},
                    {id: 2, bar: true, foo: "blip", int_field: 2, company_ids: [3], company_id: 5, state: 'def', category_id: 7},
                    {id: 3, bar: true, foo: "gnap", int_field: 4, company_ids: [], company_id: 3, state: 'ghi', category_id: 7},
                    {id: 4, bar: false, foo: "blip", int_field: 8, company_ids: [5], company_id: 5, state: 'ghi', category_id: 7},
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
                    <templates>
                        <div t-name="kanban-box" class="oe_kanban_global_click">
                            <field name="foo"/>
                        </div>
                    </templates>
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
                        <field name="company_id" enable_counters="1" expand="1"/>
                        <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                    </searchpanel>
                </search>`,
        };

        // map legacy test data
        const actions = {};
        this.actions.forEach((act) => {
          actions[act.xmlId || act.id] = act;
        });
        serverData = {
            actions,
            models: this.data,
            views: this.archs,
        };
    },
}, function () {

    QUnit.module('SearchPanel');

    QUnit.test('basic rendering', async function (assert) {
        assert.expect(16);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method + ' on ' + args.model);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <searchpanel>
                            <field name="company_id" enable_counters="1"/>
                            <field name="category_id" select="multi" enable_counters="1"/>
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
            'Allasustek2agrolait2');

        var $secondSection = kanban.$('.o_search_panel_section:nth(1)');
        assert.hasClass($secondSection.find('.o_search_panel_section_header i'), 'fa-filter');
        assert.containsOnce($secondSection, '.o_search_panel_section_header:contains(category)');
        assert.containsN($secondSection, '.o_search_panel_filter_value', 2);
        assert.strictEqual($secondSection.find('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'gold1silver3');

        assert.verifySteps([
            'search_panel_select_range on partner',
            'search_panel_select_multi_range on partner',
        ]);

        kanban.destroy();
    });

    QUnit.test('sections with custom icon and color', async function (assert) {
        assert.expect(4);

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
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" icon="fa-car" color="blue" enable_counters="1"/>
                            <field name="state" select="multi" icon="fa-star" color="#000" enable_counters="1"/>
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
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
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
                            <field name="company_id" enable_counters="1"/>
                            <field name="state" select="multi" invisible="1" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method || route);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, '.o_search_panel_section');

        assert.verifySteps([
            'search_panel_select_range',
        ]);

        kanban.destroy();
    });

    QUnit.test('categories and filters order is kept', async function (assert) {
        assert.expect(4);

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
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" enable_counters="1"/>
                            <field name="category_id" select="multi" enable_counters="1"/>
                            <field name="state" enable_counters="1"/>
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

    QUnit.test('specify active category value in context and manually change category', async function (assert) {
        assert.expect(5);

        const kanban = await createView({
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
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" enable_counters="1"/>
                            <field name="state" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step(JSON.stringify(args.domain));
                }
                return this._super.apply(this, arguments);
            },
            context: {
                searchpanel_default_company_id: false,
                searchpanel_default_state: 'ghi',
            },
        });

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value header.active label')].map(
                el => el.innerText
            ),
            ['All', 'GHI']
        );

        // select 'ABC' in the category 'state'
        await testUtils.dom.click(kanban.el.querySelectorAll('.o_search_panel_category_value header')[4]);
        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value header.active label')].map(
                el => el.innerText
            ),
            ['All', 'ABC']
        );

        assert.verifySteps([
            '[["state","=","ghi"]]',
            '[["state","=","abc"]]'
        ]);
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
                            <field name="company_id" enable_counters="1"/>
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
            '["&",["bar","=",true],["company_id","child_of",3]]',
            '["&",["bar","=",true],["company_id","child_of",5]]',
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
                            <field name="state" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
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
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
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

        assert.containsNone(kanban, '.o_toggle_fold > i',
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
                            <field name="company_id" enable_counters="1"/>
                            <field name="state" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_section', 2);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        // select 'asustek'
        await testUtils.dom.click(
            [
                ...kanban.el.querySelectorAll('.o_search_panel_category_value header .o_search_panel_label_title')
            ]
            .filter(el => el.innerText === 'asustek')
        );
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        // select 'abc'
        await testUtils.dom.click(
            [
                ...kanban.el.querySelectorAll('.o_search_panel_category_value header .o_search_panel_label_title')
            ]
            .filter(el => el.innerText === 'ABC')
        );
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi'
        await testUtils.dom.click(
            [
                ...kanban.el.querySelectorAll('.o_search_panel_category_value header .o_search_panel_label_title')
            ]
            .filter(el => el.innerText === 'GHI')
        );
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in first category (company_id)
        await testUtils.dom.click(kanban.$('.o_search_panel_section:first .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'All' in second category (state)
        await testUtils.dom.click(kanban.$('.o_search_panel_section:nth(1) .o_search_panel_category_value:first header'));
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 3);

        assert.verifySteps([
            '[["bar","=",true]]',
            '["&",["bar","=",true],["company_id","child_of",3]]',
            '["&",["bar","=",true],"&",["company_id","child_of",3],["state","=","abc"]]',
            '["&",["bar","=",true],"&",["company_id","child_of",3],["state","=","ghi"]]',
            '["&",["bar","=",true],["state","=","ghi"]]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test('category with parent_field', async function (assert) {
        assert.expect(33);

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
                            <field name="company_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        // 'All' is selected by default
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:first .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_search_panel_category_value .o_toggle_fold > i');

        // unfold parent category and select 'All' again
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) > header'));
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:first > header'));

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
        assert.containsOnce(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        // fold parent company by clicking on it
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
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) > header'));
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(2) > header'));

        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(2) .active');
        assert.containsN(kanban, '.o_search_panel_category_value', 3);
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        assert.verifySteps([
            '[]',
            '[["company_id","child_of",5]]',
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
                            <field name="category_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
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
                            <field name="company_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.strictEqual(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i').length, 1,
            "'agrolait' should be displayed as a parent category value");
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'), 'fa-caret-right',
            "'agrolait' should be folded");
        assert.containsN(kanban, '.o_search_panel_category_value', 3);

        // unfold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        // fold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'), 'fa-caret-right',
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
                            <field name="company_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        // unfold agrolait
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:contains(agrolait) > header'));
        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'), 'fa-caret-down',
            "'agrolait' should be open");
        assert.containsN(kanban, '.o_search_panel_category_value', 5);

        await kanban.reload({});

        assert.hasClass(kanban.$('.o_search_panel_category_value:contains(agrolait) .o_toggle_fold > i'), 'fa-caret-down',
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
                            <field name="company_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
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
            '["&",["bar","=",true],["company_id","child_of",3]]',
            '["&",["bar","=",true],["company_id","child_of",5]]',
        ]);

        kanban.destroy();
    });

    QUnit.test("concurrency: single category", async function (assert) {
        assert.expect(12);

        let prom = testUtils.makeTestPromise();
        const kanbanPromise = createView({
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            archs: {
                "partner,false,search": `
                    <search>
                        <filter name="Filter" domain="[('id', '=', 1)]"/>
                        <searchpanel>
                            <field name="company_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            context: {
                searchpanel_default_company_id: [5],
            },
            data: this.data,
            async mockRPC(route, args) {
                const _super = this._super.bind(this);
                if (route !== "/web/dataset/search_read") {
                    await prom;
                }
                assert.step(args.method || route);
                return _super(...arguments);
            },
            model: 'partner',
            View: KanbanView,
        });

        // Case 1: search panel is awaited to build the query with search defaults
        await testUtils.nextTick();
        assert.verifySteps([]);

        prom.resolve();
        const kanban = await kanbanPromise;

        assert.verifySteps([
            "search_panel_select_range",
            "/web/dataset/search_read",
        ]);

        // Case 2: search domain changed so we wait for the search panel once again
        prom = testUtils.makeTestPromise();

        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);

        assert.verifySteps([]);

        prom.resolve();
        await testUtils.nextTick();

        assert.verifySteps([
            "search_panel_select_range",
            "/web/dataset/search_read",
        ]);

        // Case 3: search domain is the same and default values do not matter anymore
        prom = testUtils.makeTestPromise();

        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        // The search read is executed right away in this case
        assert.verifySteps(["/web/dataset/search_read"]);

        prom.resolve();
        await testUtils.nextTick();

        assert.verifySteps(["search_panel_select_range"]);

        kanban.destroy();
    });

    QUnit.test("concurrency: category and filter", async function (assert) {
        assert.expect(5);

        let prom = testUtils.makeTestPromise();
        const kanbanPromise = createView({
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            archs: {
                "partner,false,search": `
                    <search>
                        <searchpanel>
                            <field name="category_id" enable_counters="1"/>
                            <field name="company_id" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            async mockRPC(route, args) {
                const _super = this._super.bind(this);
                if (route !== "/web/dataset/search_read") {
                    await prom;
                }
                assert.step(args.method || route);
                return _super(...arguments);
            },
            model: 'partner',
            View: KanbanView,
        });

        await testUtils.nextTick();
        assert.verifySteps(["/web/dataset/search_read"]);

        prom.resolve();
        const kanban = await kanbanPromise;

        assert.verifySteps([
            "search_panel_select_range",
            "search_panel_select_multi_range",
        ]);

        kanban.destroy();
    });

    QUnit.test("concurrency: category and filter with a domain", async function (assert) {
        assert.expect(5);

        let prom = testUtils.makeTestPromise();
        const kanbanPromise = createView({
            arch: `
                <kanban>
                    <templates>
                        <div t-name="kanban-box">
                            <field name="foo"/>
                        </div>
                    </templates>
                </kanban>`,
            archs: {
                "partner,false,search": `
                    <search>
                        <searchpanel>
                            <field name="category_id"/>
                            <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            async mockRPC(route, args) {
                const _super = this._super.bind(this);
                if (route !== "/web/dataset/search_read") {
                    await prom;
                }
                assert.step(args.method || route);
                return _super(...arguments);
            },
            model: 'partner',
            View: KanbanView,
        });

        await testUtils.nextTick();
        assert.verifySteps([]);

        prom.resolve();
        const kanban = await kanbanPromise;

        assert.verifySteps([
            "search_panel_select_range",
            "search_panel_select_multi_range",
            "/web/dataset/search_read",
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
                            <field name="state" enable_counters="1"/>
                            <field name="company_id" select="multi" enable_counters="1"/>
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
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(1) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // select 'ghi' (delay the reload)
        def = testUtils.makeTestPromise();
        var ghiDef = def;
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(3) header'));

        // 'All' should still be selected, and there should still be 4 records
        assert.containsOnce(kanban, '.o_search_panel_category_value .active');
        assert.containsOnce(kanban, '.o_search_panel_category_value:nth(3) .active');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 2);

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
                        <filter name="Filter" domain="[('id', '=', 1)]"/>
                        <searchpanel>
                            <field name="company_id" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 4);

        // trigger a reload and delay the get_filter
        def = testUtils.makeTestPromise();
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);
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
                            <field name="company_id" select="multi" enable_counters="1"/>
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
            'asustek2agrolait1');
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
            'asustek2agrolait1');
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
            '[]',
            '["&",["bar","=",true],["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[]',
            '["&",["bar","=",true],["company_id","in",[3,5]]]',
            // 'agrolait' checked
            '[]',
            '["&",["bar","=",true],["company_id","in",[5]]]',
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
                            <field name="state" select="multi" enable_counters="1" expand="1"/>
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
            'ABC1DEF1GHI1');
        assert.containsOnce(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 1);

        // check 'def'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // uncheck 'abc'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'ABC1DEF1GHI1');
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
            '[]',
            '["&",["bar","=",true],["state","in",["abc"]]]',
            // 'asustek' and 'agrolait' checked
            '[]',
            '["&",["bar","=",true],["state","in",["abc","def"]]]',
            // 'agrolait' checked
            '[]',
            '["&",["bar","=",true],["state","in",["def"]]]',
            // nothing checked
            '[]',
            '[["bar","=",true]]',
        ]);

        kanban.destroy();
    });

    QUnit.test("only reload categories and filters when domains change (counters disabled, selection)", async function (assert) {
        assert.expect(8);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="Filter" domain="[('id', '&lt;', 5)]"/>
                        <searchpanel>
                            <field name="state" expand="1"/>
                            <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
            'search_panel_select_multi_range',
        ]);

        // go to page 2 (the domain doesn't change, so the filters should not be reloaded)
        await testUtils.controlPanel.pagerNext(kanban);

        assert.verifySteps([]);

        // reload with another domain, so the filters should be reloaded
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);

        assert.verifySteps([
            'search_panel_select_multi_range',
        ]);

        // change category value, so the filters should be reloaded
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([
            'search_panel_select_multi_range',
        ]);

        kanban.destroy();
    });

    QUnit.test("only reload categories and filters when domains change (counters disabled, many2one)", async function (assert) {
        assert.expect(8);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="domain" domain="[('id', '&lt;', 5)]"/>
                        <searchpanel>
                            <field name="category_id" expand="1"/>
                            <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
            'search_panel_select_multi_range',
        ]);

        // go to page 2 (the domain doesn't change, so the filters should not be reloaded)
        await testUtils.controlPanel.pagerNext(kanban);

        assert.verifySteps([]);

        // reload with another domain, so the filters should be reloaded
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);

        assert.verifySteps([
            'search_panel_select_multi_range',
        ]);

        // change category value, so the filters should be reloaded
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([
            'search_panel_select_multi_range',
        ]);

        kanban.destroy();
    });

    QUnit.test('category counters', async function (assert) {
        assert.expect(16);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                if (route === "/web/dataset/call_kw/partner/search_panel_select_range") {
                    assert.step(args.args[0]);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                        <searchpanel>
                            <field name="state" enable_counters="1" expand="1"/>
                            <field name="company_id" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
            'state',
            'search_panel_select_range',
            'company_id',
        ]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC1", "DEF1", "GHI2", "All", "asustek", "agrolait"]
        );

        // go to page 2 (the domain doesn't change, so the categories should not be reloaded)
        await testUtils.controlPanel.pagerNext(kanban);

        assert.verifySteps([]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC1", "DEF1", "GHI2", "All", "asustek", "agrolait"]
        );

        // reload with another domain, so the categories 'state' and 'company_id' should be reloaded
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);

        assert.verifySteps([
            'search_panel_select_range',
            'state',
        ]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC1", "DEF1", "GHI", "All", "asustek", "agrolait"]
        );

        // change category value, so the category 'state' should be reloaded
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC1", "DEF1", "GHI", "All", "asustek", "agrolait"]
        );

        assert.verifySteps([
            'search_panel_select_range',
            'state',
        ]);

        kanban.destroy();
    });

    QUnit.test('category selection without counters', async function (assert) {
        assert.expect(10);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                if (route === "/web/dataset/call_kw/partner/search_panel_select_range") {
                    assert.step(args.args[0]);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="Filter" domain="[('id', '&lt;', 3)]"/>
                        <searchpanel>
                            <field name="state" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
            'state',
        ]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC", "DEF", "GHI"]
        );

        // go to page 2 (the domain doesn't change, so the categories should not be reloaded)
        await testUtils.controlPanel.pagerNext(kanban);

        assert.verifySteps([]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC", "DEF", "GHI"]
        );

        // reload with another domain, so the category 'state' should be reloaded
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 0);

        assert.verifySteps([]);

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC", "DEF", "GHI"]
        );

        // change category value, so the category 'state' should be reloaded
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value')].map(
                e => e.innerText.replace(/\s/g, '')
            ),
            [  "All", "ABC", "DEF", "GHI"]
        );

        assert.verifySteps([]);

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
                            <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            domain: [['bar', '=', true]],
        });

        assert.containsN(kanban, '.o_search_panel_filter_group', 2);
        assert.containsOnce(kanban, '.o_search_panel_filter_group:first .o_search_panel_filter_value');
        assert.containsN(kanban, '.o_search_panel_filter_group:nth(1) .o_search_panel_filter_value', 2);
        assert.containsNone(kanban, '.o_search_panel_filter_value input:checked');
        assert.strictEqual(kanban.$('.o_search_panel_filter_group > header > div > label').text().replace(/\s/g, ''),
            'goldsilver');
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait1camptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 3);

        // check 'asustek'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:first input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        var firstGroupCheckbox = kanban.$('.o_search_panel_filter_group:first > header > div > input').get(0);
        assert.strictEqual(firstGroupCheckbox.checked, true,
            "first group checkbox should be checked");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 2);

        // check 'agrolait'
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_value:nth(1) input'));

        assert.containsN(kanban, '.o_search_panel_filter_value input:checked', 2);
        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > header > div > input').get(0);
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
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > header > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.checked, true,
            "second group checkbox should be checked");
        assert.strictEqual(secondGroupCheckbox.indeterminate, false,
            "second group checkbox should not be indeterminate");
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustekagrolaitcamptocamp');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_record:not(.o_kanban_ghost)', 0);

        // uncheck second group
        await testUtils.dom.click(kanban.$('.o_search_panel_filter_group:nth(1) > header > div > input'));

        assert.containsOnce(kanban, '.o_search_panel_filter_value input:checked');
        secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > header > div > input').get(0);
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
            '[]',
            '["&",["bar","=",true],["company_id","in",[3]]]',
            // 'asustek' and 'agrolait' checked
            '[]',
            '["&",["bar","=",true],"&",["company_id","in",[3]],["company_id","in",[5]]]',
            // 'asustek', 'agrolait' and 'camptocamp' checked
            '[]',
            '["&",["bar","=",true],"&",["company_id","in",[3]],["company_id","in",[5,11]]]',
            // 'asustek' checked
            '[]',
            '["&",["bar","=",true],["company_id","in",[3]]]',
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
                        expand: true,
                        filter_domain: [],
                        search_domain: [],
                        comodel_domain: [['parent_id', '=', false]],
                        group_domain: [],
                        context: {},
                        enable_counters: true,
                        limit: 200,
                    });
                }
                return result;
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
                    <search>
                        <searchpanel>
                            <field name="company_id" select="multi" domain="[('parent_id','=',False)]" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsN(kanban, '.o_search_panel_filter_value', 2);
        assert.strictEqual(kanban.$('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'asustek2agrolait2');

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
                            <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]" enable_counters="1"/>
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
            "&",
            ['company_id', 'in', [5]],
            ['state', 'in', ['abc', 'ghi']],
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
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" select="multi" enable_counters="1"/>
                            <field name="state" select="multi" enable_counters="1"/>
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
                            <field name="company_id" select="multi" enable_counters="1"/>
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
                            <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
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

        var secondGroupCheckbox = kanban.$('.o_search_panel_filter_group:nth(1) > header > div > input').get(0);
        assert.strictEqual(secondGroupCheckbox.indeterminate, true);

        kanban.destroy();
    });

    QUnit.test('Does not confuse false and "false" groupby values', async function (assert) {
        assert.expect(6);

        this.data.company.fields.char_field = {string: "Char Field", type: 'char'};

        this.data.company.records = [
            {id: 3, name: 'A', char_field: false, },
            {id: 5, name: 'B', char_field: 'false', }
        ];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `<kanban>
                    <templates><t t-name="kanban-box">
                        <div>
                            <field name="foo"/>
                        </div>
                    </t></templates>
                </kanban>`,
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="company_id" select="multi" groupby="char_field"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.containsOnce(kanban, '.o_search_panel_section');
        var $firstSection = kanban.$('.o_search_panel_section');

        // There should be a group 'false' displayed with only value B inside it.
        assert.containsOnce($firstSection, '.o_search_panel_filter_group');
        assert.strictEqual($firstSection.find('.o_search_panel_filter_group').text().replace(/\s/g, ''),
            'falseB');
        assert.containsOnce($firstSection.find('.o_search_panel_filter_group'), '.o_search_panel_filter_value');

        // Globally, there should be two values, one displayed in the group 'false', and one at the end of the section
        // (the group false is not displayed and its values are displayed at the first level)
        assert.containsN($firstSection, '.o_search_panel_filter_value', 2);
        assert.strictEqual($firstSection.find('.o_search_panel_filter_value').text().replace(/\s/g, ''),
            'BA');

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
                            <field name="company_id" enable_counters="1" expand="1"/>
                            <field name="category_id" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        var $firstSection = kanban.$('.o_search_panel_section:first');
        assert.strictEqual($firstSection.find('.o_search_panel_category_value').text().replace(/\s/g, ''),
            'Allasustek2agrolait2highIDlowID');
        kanban.destroy();
    });

    QUnit.test('search panel is available on list and kanban by default', async function (assert) {
        assert.expect(8);

        registry.category("services").add("user", makeFakeUserService());
        const webClient = await createWebClient({ serverData });

        await doAction(webClient, 1);

        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await switchView(webClient, 'pivot');
        await testUtils.nextTick();
        assert.containsOnce(webClient, '.o_content .o_pivot');
        assert.containsNone(webClient, '.o_content .o_search_panel');

        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_list_view');
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await testUtils.dom.click($(webClient.el).find('.o_data_row .o_data_cell:first'));
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content .o_form_view');
        assert.containsNone(webClient, '.o_content .o_search_panel');
    });

    QUnit.skip('search panel with view_types attribute', async function (assert) {
        assert.expect(6);

        serverData.views['partner,false,search'] =
            `<search>
                <searchpanel view_types="kanban,pivot">
                    <field name="company_id" enable_counters="1"/>
                    <field name="category_id" select="multi" enable_counters="1"/>
                </searchpanel>
            </search>`;


        registry.category("views").add("pivot", PivotView, { force: true });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_search_panel');

        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content .o_list_view');
        assert.containsNone(webClient, '.o_content .o_search_panel');

        await switchView(webClient, 'pivot');
        assert.containsOnce(webClient, '.o_content.o_component_with_search_panel .o_legacy_pivot');
        assert.containsOnce(webClient, '.o_content.o_component_with_search_panel .o_search_panel');
    });

    QUnit.test('search panel state is shared between views', async function (assert) {
        assert.expect(16);

        const mockRPC = (route, args) => {
            if (route === '/web/dataset/search_read') {
                assert.step(JSON.stringify(args.domain));
            }
        };

        const webClient = await createWebClient({ serverData , mockRPC });

        await doAction(webClient, 1);

        assert.hasClass($(webClient.el).find('.o_search_panel_category_value:first header'), 'active');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select 'asustek' company
        await testUtils.dom.click($(webClient.el).find('.o_search_panel_category_value:nth(1) header'));
        await legacyExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_search_panel_category_value:nth(1) header'), 'active');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_search_panel_category_value:nth(1) header'), 'active');
        assert.containsN(webClient, '.o_data_row', 2);

        // select 'agrolait' company
        await testUtils.dom.click($(webClient.el).find('.o_search_panel_category_value:nth(2) header'));
        await legacyExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_search_panel_category_value:nth(2) header'), 'active');
        assert.containsN(webClient, '.o_data_row', 2);

        await switchView(webClient, 'kanban');
        await legacyExtraNextTick();
        assert.hasClass($(webClient.el).find('.o_search_panel_category_value:nth(2) header'), 'active');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 2);

        assert.verifySteps([
            '[]', // initial search_read
            '[["company_id","child_of",3]]', // kanban, after selecting the first company
            '[["company_id","child_of",3]]', // list
            '[["company_id","child_of",5]]', // list, after selecting the other company
            '[["company_id","child_of",5]]', // kanban
        ]);
    });

    QUnit.test('search panel filters are kept between switch views', async function (assert) {
        assert.expect(17);

        const mockRPC = (route, args) => {
            if (route === '/web/dataset/search_read') {
                assert.step(JSON.stringify(args.domain));
            }
        };

        const webClient = await createWebClient({ serverData , mockRPC });
        await doAction(webClient, 1);

        assert.containsNone(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select gold filter
        await testUtils.dom.click($(webClient.el).find('.o_search_panel_filter input[type="checkbox"]:nth(0)'));
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_data_row', 1);

        // select silver filter
        await testUtils.dom.click($(webClient.el).find('.o_search_panel_filter input[type="checkbox"]:nth(1)'));
        await legacyExtraNextTick();
        assert.containsN(webClient, '.o_search_panel_filter_value input:checked', 2);
        assert.containsN(webClient, '.o_data_row', 4);

        await switchView(webClient, 'kanban');
        await legacyExtraNextTick();
        assert.containsN(webClient, '.o_search_panel_filter_value input:checked', 2);
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        await testUtils.dom.click($(webClient.el).find(".o_kanban_record:nth(0)"));
        await legacyExtraNextTick();
        await testUtils.dom.click($(webClient.el).find(".breadcrumb-item:nth(0)"));
        await legacyExtraNextTick();

        assert.verifySteps([
            '[]', // initial search_read
            '[["category_id","in",[6]]]', // kanban, after selecting the gold filter
            '[["category_id","in",[6]]]', // list
            '[["category_id","in",[6,7]]]', // list, after selecting the silver filter
            '[["category_id","in",[6,7]]]', // kanban
            '[["category_id","in",[6,7]]]', // kanban, after switching back from form view
        ]);
    });

    QUnit.skip('search panel filters are kept when switching to a view with no search panel', async function (assert) {
        assert.expect(13);

        registry.category("views").add("pivot", PivotView, { force: true });
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 1);

        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_kanban_view');
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_search_panel');
        assert.containsNone(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        // select gold filter
        await testUtils.dom.click($(webClient.el).find('.o_search_panel_filter input[type="checkbox"]:nth(0)'));
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_kanban_record:not(.o_kanban_ghost)', 1);

        // switch to pivot
        await switchView(webClient, 'pivot');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content .o_legacy_pivot');
        assert.containsNone(webClient, '.o_content .o_search_panel');
        assert.strictEqual($(webClient.el).find('.o_pivot_cell_value').text(), '15');

        // switch to list
        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_list_view');
        assert.containsOnce(webClient, '.o_content.o_controller_with_searchpanel .o_search_panel');
        assert.containsOnce(webClient, '.o_search_panel_filter_value input:checked');
        assert.containsN(webClient, '.o_data_row', 1);
    });

    QUnit.test('after onExecuteAction, selects "All" as default category value', async function (assert) {
        assert.expect(4);

        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 2);

        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains("multi view")'));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsOnce(webClient, '.o_search_panel');
        assert.containsOnce(webClient, '.o_search_panel_category_value:first .active');

        assert.verifySteps([]); // should not communicate with localStorage
    });

    QUnit.test('search panel is not instantiated if stated in context', async function (assert) {
        assert.expect(2);

        serverData.actions[2].context = {search_panel: false};
        const webClient = await createWebClient({ serverData });
        await doAction(webClient, 2);

        await testUtils.dom.click($(webClient.el).find('.o_form_view button:contains("multi view")'));
        await legacyExtraNextTick();

        assert.containsOnce(webClient, '.o_kanban_view');
        assert.containsNone(webClient, '.o_search_panel');
    });

    QUnit.test('categories and filters are not reloaded when switching between views', async function (assert) {
        assert.expect(3);

        const mockRPC = (route, args) => {
            if (args.method && args.method.includes('search_panel_')) {
                assert.step(args.method);
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, 1);

        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        await switchView(webClient, 'kanban');
        await legacyExtraNextTick();

        assert.verifySteps([
            'search_panel_select_range', // kanban: categories
            'search_panel_select_multi_range', // kanban: filters
        ]);
    });

    QUnit.test('scroll position is kept when switching between controllers', async function (assert) {
        assert.expect(6);

        const originalDebounce = SearchPanel.scrollDebounce;
        SearchPanel.scrollDebounce = 0;

        for (var i = 10; i < 20; i++) {
            serverData.models.category.records.push({id: i, name: "Cat " + i});
        }

        const webClient = await createWebClient({ serverData });
        webClient.el.querySelector('.o_action_manager').style.maxHeight = "300px";

        await doAction(webClient, 1);

        async function scroll(top) {
            webClient.el.querySelector(".o_search_panel").scrollTop = top;
            await testUtils.nextTick();
        }

        assert.containsOnce(webClient, '.o_content .o_kanban_view');
        assert.strictEqual($(webClient.el).find('.o_search_panel').scrollTop(), 0);

        // simulate a scroll in the search panel and switch into list
        await scroll(50);
        await switchView(webClient, 'list');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content .o_list_view');
        assert.strictEqual($(webClient.el).find('.o_search_panel').scrollTop(), 50);

        // simulate another scroll and switch back to kanban
        await scroll(30);
        await switchView(webClient, 'kanban');
        await legacyExtraNextTick();
        assert.containsOnce(webClient, '.o_content .o_kanban_view');
        assert.strictEqual($(webClient.el).find('.o_search_panel').scrollTop(), 30);
        SearchPanel.scrollDebounce = originalDebounce;
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
                            <field name="category_id" enable_counters="1"/>
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


    QUnit.test("Reload categories with counters when filter values are selected", async function (assert) {
        assert.expect(8);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <searchpanel>
                            <field name="category_id" enable_counters="1"/>
                            <field name="state" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
            "search_panel_select_multi_range",
        ]);

        assert.deepEqual(getCounters(kanban), [
            1, 3, // category counts (in order)
            1, 1, 2 // filter counts
        ]);

        await testUtils.dom.click(kanban.el.querySelector('.o_search_panel_filter_value input'));

        assert.deepEqual(getCounters(kanban), [
            1, // category counts (for silver: 0 is not displayed)
            1, 1, 2 // filter counts
        ]);

        assert.verifySteps([
            'search_panel_select_range',
            "search_panel_select_multi_range",
        ]);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, expand, hierarchize, counters", async function (assert) {
        assert.expect(5);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2 ,1]);

        await toggleFold(kanban, "agrolait");

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 5);
        assert.deepEqual(getCounters(kanban), [2, 1, 1]);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, no expand, hierarchize, counters", async function (assert) {
        assert.expect(5);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1]);

        await toggleFold(kanban, "agrolait");

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.deepEqual(getCounters(kanban), [2, 1, 1]);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, expand, no hierarchize, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" hierarchize="0" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1, 1]);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, no expand, no hierarchize, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" hierarchize="0" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1, 1]);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, expand, hierarchize, no counters", async function (assert) {
        assert.expect(5);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        await toggleFold(kanban, "agrolait");

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 5);
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, no expand, hierarchize, no counters", async function (assert) {
        assert.expect(5);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsOnce(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        await toggleFold(kanban, "agrolait");

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, expand, no hierarchize, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" hierarchize="0" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select one, no expand, no hierarchize, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 50, name: 'agrobeurre', parent_id: 5 });
        this.data.company.records.push({ id: 51, name: 'agrocrèmefraiche', parent_id: 5 });
        this.data.partner.records[1].company_id = 50;
        const kanban = await createView({
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
                            <field name="company_id" hierarchize="0"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, expand, groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 2]);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, no expand, groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" groupby="category_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 2]);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, expand, no groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 2]);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, no expand, no groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 2]);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, expand, groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" groupby="category_id" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, no expand, groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" groupby="category_id"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, expand, no groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2one: select multi, no expand, no groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_id" select="multi"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, expand, groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" groupby="category_id" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1]);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, no expand, groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" groupby="category_id" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1]);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, expand, no groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1]);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, no expand, no groupby, counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [2, 1]);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, expand, groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" groupby="category_id" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, no expand, groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" groupby="category_id"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, expand, no groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("many2many: select multi, no expand, no groupby, no counters", async function (assert) {
        assert.expect(3);

        this.data.company.records.push({ id: 666, name: "Mordor Inc.", category_id: 6 });
        const kanban = await createView({
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
                            <field name="company_ids" select="multi"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("selection: select one, expand, counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [1, 2]);

        kanban.destroy();
    });

    QUnit.test("selection: select one, no expand, counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [1, 2]);

        kanban.destroy();
    });

    QUnit.test("selection: select one, expand, no counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 4);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("selection: select one, no expand, no counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_field .o_search_panel_category_value', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("selection: select multi, expand, counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" select="multi" enable_counters="1" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [1, 2]);

        kanban.destroy();
    });

    QUnit.test("selection: select multi, no expand, counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [1, 2]);

        kanban.destroy();
    });

    QUnit.test("selection: select multi, expand, no counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" select="multi" expand="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 3);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    QUnit.test("selection: select multi, no expand, no counters", async function (assert) {
        assert.expect(3);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" select="multi"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 2);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), []);

        kanban.destroy();
    });

    //-------------------------------------------------------------------------
    // Model domain and count domain distinction
    //-------------------------------------------------------------------------

    QUnit.test("selection: select multi, no expand, counters, extra_domain", async function (assert) {
        assert.expect(5);

        this.data.partner.records.shift();
        const kanban = await createView({
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
                            <field name="state" select="multi" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.containsNone(kanban, '.o_toggle_fold > i');
        assert.deepEqual(getCounters(kanban), [1, 2]);

        await toggleFold(kanban, "asustek");

        assert.containsN(kanban, '.o_search_panel_label', 5);
        assert.deepEqual(getCounters(kanban), [1]);

        kanban.destroy();
    });

    //-------------------------------------------------------------------------
    // Limit
    //-------------------------------------------------------------------------

    QUnit.test("reached limit for a category", async function (assert) {
        assert.expect(6);

        const kanban = await createView({
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
                            <field name="company_id" limit="2"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsOnce(kanban, '.o_search_panel_section');
        assert.containsOnce(kanban, '.o_search_panel_section_header');
        assert.strictEqual(kanban.el.querySelector('.o_search_panel_section_header').innerText, "COMPANY");
        assert.containsOnce(kanban, 'section div.alert.alert-warning');
        assert.strictEqual(kanban.el.querySelector('section div.alert.alert-warning').innerText, "Too many items to display.");
        assert.containsNone(kanban, '.o_search_panel_category_value');

        kanban.destroy();
    });

    QUnit.test("reached limit for a filter", async function (assert) {
        assert.expect(6);

        const kanban = await createView({
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
                            <field name="company_id" select="multi" limit="2"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: 'partner',
            View: KanbanView,
        });

        assert.containsOnce(kanban, '.o_search_panel_section');
        assert.containsOnce(kanban, '.o_search_panel_section_header');
        assert.strictEqual(kanban.el.querySelector('.o_search_panel_section_header').innerText, "COMPANY");
        assert.containsOnce(kanban, 'section div.alert.alert-warning');
        assert.strictEqual(kanban.el.querySelector('section div.alert.alert-warning').innerText, "Too many items to display.");
        assert.containsNone(kanban, '.o_search_panel_filter_value');

        kanban.destroy();
    });

    QUnit.test("a selected value becomming invalid should no more impact the view", async function (assert) {
        assert.expect(13);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                        <searchpanel>
                            <field name="state" enable_counters="1"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
        ]);

        assert.containsN(kanban, '.o_kanban_record span', 4);

        // select 'ABC' in search panel
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([
            'search_panel_select_range',
        ]);

        assert.containsOnce(kanban, '.o_kanban_record span');
        assert.strictEqual(kanban.el.querySelector('.o_kanban_record span').innerText, 'yop' );

        // select DEF in filter menu
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 'DEF');

        assert.verifySteps([
            'search_panel_select_range',
        ]);

        const firstCategoryValue = kanban.el.querySelector('.o_search_panel_category_value header');
        assert.strictEqual(firstCategoryValue.innerText, 'All');
        assert.hasClass(
            firstCategoryValue, 'active',
            "the value 'All' should be selected since ABC is no longer a valid value with respect to search domain"
        );
        assert.containsOnce(kanban, '.o_kanban_record span');
        assert.strictEqual(kanban.el.querySelector('.o_kanban_record span').innerText, 'blip' );

        kanban.destroy();
    });

    QUnit.test("Categories with default attributes should be udpated when external domain changes", async function (assert) {
        assert.expect(8);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method && args.method.includes('search_panel_')) {
                    assert.step(args.method);
                }
                return this._super.apply(this, arguments);
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
                    <search>
                        <filter name="filter_on_def" string="DEF" domain="[('state', '=', 'def')]"/>
                        <searchpanel>
                            <field name="state"/>
                        </searchpanel>
                    </search>`,
            },
        });

        assert.verifySteps([
            'search_panel_select_range',
        ]);
        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value header label')].map(el => el.innerText),
            ['All', 'ABC', 'DEF', 'GHI']
        );

        // select 'ABC' in search panel --> no need to update the category value
        await testUtils.dom.click(kanban.$('.o_search_panel_category_value:nth(1) header'));

        assert.verifySteps([]);
        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value header label')].map(el => el.innerText),
            ['All', 'ABC', 'DEF', 'GHI']
        );

        // select DEF in filter menu --> the external domain changes --> the values should be updated
        await toggleFilterMenu(kanban.$el[0]);
        await toggleMenuItem(kanban.$el[0], 'DEF');

        assert.verifySteps([
            'search_panel_select_range',
        ]);
        assert.deepEqual(
            [...kanban.el.querySelectorAll('.o_search_panel_category_value header label')].map(el => el.innerText),
            ['All', 'DEF']
        );

        kanban.destroy();
    });

    QUnit.test("Category with counters and filter with domain", async function (assert) {
        assert.expect(2);

        const list = await createView({
            arch: '<tree><field name="foo"/></tree>',
            archs: {
                'partner,false,search': `
                    <search>
                        <searchpanel>
                            <field name="category_id"/>
                            <field name="company_id" select="multi" domain="[['category_id', '=', category_id]]"/>
                        </searchpanel>
                    </search>`,
            },
            data: this.data,
            model: "partner",
            services: this.services,
            View: ListView,
        });

        assert.containsN(list, ".o_data_row", 4);
        assert.strictEqual(
            list.$(".o_search_panel_category_value").text().replace(/\s/g, ""),
            "Allgoldsilver",
            "Category counters should be empty if a filter has a domain attribute"
        );

        list.destroy();
    });
});
});
