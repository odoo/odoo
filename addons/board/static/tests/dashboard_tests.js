odoo.define('board.dashboard_tests', function (require) {
"use strict";

var BoardView = require('board.BoardView');

var ListController = require('web.ListController');
var testUtils = require('web.test_utils');
var ListRenderer = require('web.ListRenderer');
var pyUtils = require('web.py_utils');

var createActionManager = testUtils.createActionManager;
var createView = testUtils.createView;

QUnit.module('Dashboard', {
    beforeEach: function () {
        this.data = {
            board: {
                fields: {
                },
                records: [
                ]
            },
            partner: {
                fields: {
                    display_name: {string: "Displayed name", type: "char", searchable: true},
                    foo: {string: "Foo", type: "char", default: "My little Foo Value", searchable: true},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "Integer field", type: "integer", group_operator: 'sum'},
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    foo: "yop",
                    int_field: 3,
                }, {
                    id: 2,
                    display_name: "second record",
                    foo: "lalala",
                    int_field: 5,
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                    int_field: 2,
                }],
            },
        };
    },
});

QUnit.test('dashboard basic rendering', async function (assert) {
    assert.expect(4);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
            '</form>',
    });

    assert.doesNotHaveClass(form.renderer.$el, 'o_dashboard',
        "should not have the o_dashboard css class");

    form.destroy();

    form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column></column>' +
                '</board>' +
            '</form>',
    });

    assert.hasClass(form.renderer.$el,'o_dashboard',
        "with a dashboard, the renderer should have the proper css class");
    assert.containsOnce(form, '.o_dashboard .o_view_nocontent',
        "should have a no content helper");
    assert.strictEqual(form.$('.o_control_panel .breadcrumb-item').text(), "My Dashboard",
        "should have the correct title");
    form.destroy();
});

QUnit.test('display the no content helper', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column></column>' +
                '</board>' +
            '</form>',
        viewOptions: {
            action: {
                help: '<p class="hello">click to add a partner</p>'
            }
        },
    });

    assert.containsOnce(form, '.o_dashboard .o_view_nocontent',
        "should have a no content helper with action help");
    form.destroy();
});

QUnit.test('basic functionality, with one sub action', async function (assert) {
    assert.expect(26);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{&quot;orderedBy&quot;: [{&quot;name&quot;: &quot;foo&quot;, &quot;asc&quot;: True}]}" view_mode="list" string="ABC" name="51" domain="[[\'foo\', \'!=\', \'False\']]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/web/action/load') {
                assert.step('load action');
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            if (route === '/web/dataset/search_read') {
                assert.deepEqual(args.domain, [['foo', '!=', 'False']], "the domain should be passed");
                assert.deepEqual(args.context.orderedBy, [{
                        'name': 'foo',
                        'asc': true,
                    }],
                    'orderedBy is present in the search read when specified on the custom action'
                );
            }
            if (route === '/web/view/edit_custom') {
                assert.step('edit custom');
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.containsOnce(form, '.oe_dashboard_links',
        "should have rendered a link div");
    assert.containsOnce(form, 'table.oe_dashboard[data-layout="2-1"]',
        "should have rendered a table");
    assert.containsNone(form, 'td.o_list_record_selector',
        "td should not have a list selector");
    assert.strictEqual(form.$('h2 span.oe_header_txt:contains(ABC)').length, 1,
        "should have rendered a header with action string");
    assert.containsN(form, 'tr.o_data_row', 3,
        "should have rendered 3 data rows");

    assert.ok(form.$('.oe_content').is(':visible'), "content is visible");

    await testUtils.dom.click(form.$('.oe_fold'));

    assert.notOk(form.$('.oe_content').is(':visible'), "content is no longer visible");

    await testUtils.dom.click(form.$('.oe_fold'));

    assert.ok(form.$('.oe_content').is(':visible'), "content is visible again");
    assert.verifySteps(['load action', 'edit custom', 'edit custom']);

    assert.strictEqual($('.modal').length, 0, "should have no modal open");

    await testUtils.dom.click(form.$('button.oe_dashboard_link_change_layout'));

    assert.strictEqual($('.modal').length, 1, "should have opened a modal");
    assert.strictEqual($('.modal li[data-layout="2-1"] i.oe_dashboard_selected_layout').length, 1,
        "should mark currently selected layout");

    await testUtils.dom.click($('.modal .oe_dashboard_layout_selector li[data-layout="1-1"]'));

    assert.strictEqual($('.modal').length, 0, "should have no modal open");
    assert.containsOnce(form, 'table.oe_dashboard[data-layout="1-1"]',
        "should have rendered a table with correct layout");


    assert.containsOnce(form, '.oe_action', "should have one displayed action");
    await testUtils.dom.click(form.$('span.oe_close'));

    assert.strictEqual($('.modal').length, 1, "should have opened a modal");

    // confirm the close operation
    await testUtils.dom.click($('.modal button.btn-primary'));

    assert.strictEqual($('.modal').length, 0, "should have no modal open");
    assert.containsNone(form, '.oe_action', "should have no displayed action");

    assert.verifySteps(['edit custom', 'edit custom']);
    form.destroy();
});

QUnit.test('views in the dashboard do not have a control panel', async function (assert) {
    assert.expect(2);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form>' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list'], [5, 'form']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.containsOnce(form, '.o_action .o_list_view');
    assert.containsNone(form, '.o_action .o_control_panel');

    form.destroy();
});

QUnit.test('can render an action without view_mode attribute', async function (assert) {
    // The view_mode attribute is automatically set to the 'action' nodes when
    // the action is added to the dashboard using the 'Add to dashboard' button
    // in the searchview. However, other dashboard views can be written by hand
    // (see openacademy tutorial), and in this case, we don't want hardcode
    // action's params (like context or domain), as the dashboard can directly
    // retrieve them from the action. Same applies for the view_type, as the
    // first view of the action can be used, by default.
    assert.expect(3);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action string="ABC" name="51" context="{\'a\': 1}"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
        mockRPC: function (route, args) {
            if (route === '/board/static/src/img/layout_1-1-1.png') {
                return Promise.resolve();
            }
            if (route === '/web/action/load') {
                return Promise.resolve({
                    context: '{"b": 2}',
                    domain: '[["foo", "=", "yop"]]',
                    res_model: 'partner',
                    views: [[4, 'list'], [false, 'form']],
                });
            }
            if (args.method === 'load_views') {
                assert.deepEqual(args.kwargs.context, {a: 1, b: 2},
                    "should have mixed both contexts");
            }
            if (route === '/web/dataset/search_read') {
                assert.deepEqual(args.domain, [['foo', '=', 'yop']],
                    "should use the domain of the action");
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('.oe_action:contains(ABC) .o_list_view').length, 1,
        "the list view (first view of action) should have been rendered correctly");

    form.destroy();
});

QUnit.test('can sort a sub list', async function (assert) {
    assert.expect(2);

    this.data.partner.fields.foo.sortable = true;

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.strictEqual($('tr.o_data_row').text(), 'yoplalalaabc',
        "should have correct initial data");

    await testUtils.dom.click(form.$('th.o_column_sortable:contains(Foo)'));

    assert.strictEqual($('tr.o_data_row').text(), 'abclalalayop',
        "data should have been sorted");
    form.destroy();
});

QUnit.test('can open a record', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
        intercepts: {
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    res_id: 1,
                    res_model: 'partner',
                    type: 'ir.actions.act_window',
                    views: [[false, 'form']],
                }, "should do a do_action with correct parameters");
            },
        },
    });

    await testUtils.dom.click(form.$('tr.o_data_row td:contains(yop)'));
    form.destroy();
});

QUnit.test('can open record using action form view', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list'], [5, 'form']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
            'partner,5,form':
                '<form string="Partner"><field name="display_name"/></form>',
        },
        intercepts: {
            do_action: function (event) {
                assert.deepEqual(event.data.action, {
                    res_id: 1,
                    res_model: 'partner',
                    type: 'ir.actions.act_window',
                    views: [[5, 'form']],
                }, "should do a do_action with correct parameters");
            },
        },
    });

    await testUtils.dom.click(form.$('tr.o_data_row td:contains(yop)'));
    form.destroy();
});

QUnit.test('can drag and drop a view', async function (assert) {
    assert.expect(5);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            if (route === '/web/view/edit_custom') {
                assert.step('edit custom');
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.containsOnce(form, 'td.index_0 .oe_action',
        "initial action is in column 0");

    await testUtils.dom.dragAndDrop(form.$('.oe_dashboard_column.index_0 .oe_header'),
        form.$('.oe_dashboard_column.index_1'));
    assert.containsNone(form, 'td.index_0 .oe_action',
        "initial action is not in column 0");
    assert.containsOnce(form, 'td.index_1 .oe_action',
        "initial action is in in column 1");
    assert.verifySteps(['edit custom']);

    form.destroy();
});

QUnit.test('twice the same action in a dashboard', async function (assert) {
    assert.expect(2);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                        '<action context="{}" view_mode="kanban" string="DEF" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list'],[5, 'kanban']],
                });
            }
            if (route === '/web/view/edit_custom') {
                assert.step('edit custom');
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
            'partner,5,kanban':
                '<kanban><templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates></kanban>',
        },
    });

    var $firstAction = form.$('.oe_action:contains(ABC)');
    assert.strictEqual($firstAction.find('.o_list_view').length, 1,
        "list view should be displayed in 'ABC' block");
    var $secondAction = form.$('.oe_action:contains(DEF)');
    assert.strictEqual($secondAction.find('.o_kanban_view').length, 1,
        "kanban view should be displayed in 'DEF' block");

    form.destroy();
});

QUnit.test('non-existing action in a dashboard', async function (assert) {
    assert.expect(1);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="kanban" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        intercepts: {
            load_views: function () {
                throw new Error('load_views should not be called');
            }
        },
        mockRPC: function (route) {
            if (route === '/board/static/src/img/layout_1-1-1.png') {
                return Promise.resolve();
            }
            if (route === '/web/action/load') {
                // server answer if the action doesn't exist anymore
                return Promise.resolve(false);
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('.oe_action:contains(ABC)').length, 1,
        "there should be a box for the non-existing action");

    form.destroy();
});

QUnit.test('clicking on a kanban\'s button should trigger the action', async function (assert) {
    assert.expect(2);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action name="149" string="Partner" view_mode="kanban" id="action_0_1"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        archs: {
            'partner,false,kanban':
                '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="foo"/>' +
                    '</div>' +
                    '<div><button name="sitting_on_a_park_bench" type="object">Eying little girls with bad intent</button>' +
                    '</div>' +
                '</t></templates></kanban>',
        },
        intercepts: {
            execute_action: function (event) {
                var data = event.data;
                assert.strictEqual(data.env.model, 'partner', "should have correct model");
                assert.strictEqual(data.action_data.name, 'sitting_on_a_park_bench',
                    "should call correct method");
            }
        },

        mockRPC: function (route) {
            if (route === '/board/static/src/img/layout_1-1-1.png') {
                return Promise.resolve();
            }
            if (route === '/web/action/load') {
                return Promise.resolve({res_model: 'partner', view_mode: 'kanban', views: [[false, 'kanban']]});
            }
            if (route === '/web/dataset/search_read') {
                return Promise.resolve({records: [{foo: 'aqualung'}]});
            }
            return this._super.apply(this, arguments);
        }
    });

    await testUtils.dom.click(form.$('.o_kanban_test').find('button:first'));

    form.destroy();
});

QUnit.test('subviews are aware of attach in or detach from the DOM', async function (assert) {
    assert.expect(2);

    // patch list renderer `on_attach_callback` for the test only
    testUtils.mock.patch(ListRenderer, {
        on_attach_callback: function () {
            assert.step('subview on_attach_callback');
        }
    });

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<list string="Partner"><field name="foo"/></list>',
        },
    });

    assert.verifySteps(['subview on_attach_callback']);

    // restore on_attach_callback of ListRenderer
    testUtils.mock.unpatch(ListRenderer);

    form.destroy();
});

QUnit.test('dashboard intercepts custom events triggered by sub controllers', async function (assert) {
    assert.expect(1);

    // we patch the ListController to force it to trigger the custom events that
    // we want the dashboard to intercept (to stop them or to tweak their data)
    testUtils.mock.patch(ListController, {
        start: function () {
            this.trigger_up('update_filters');
            return this._super.apply(this, arguments);
        },
    });

    var board = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({res_model: 'partner', views: [[false, 'list']]});
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,false,list': '<tree string="Partner"/>',
        },
        intercepts: {
            update_filters: assert.step.bind(assert, 'update_filters'),
        },
    });

    assert.verifySteps([]);

    testUtils.mock.unpatch(ListController);
    board.destroy();
});

QUnit.test('save actions to dashboard', async function (assert) {
    assert.expect(6);

    testUtils.patch(ListController, {
        getOwnedQueryParams: function () {
            var result = this._super.apply(this, arguments);
            result.context = {
                'fire': 'on the bayou',
            }
            return result;
        }
    });

    this.data['partner'].fields.foo.sortable = true;

    var actionManager = await createActionManager({
        data: this.data,
        archs: {
            'partner,false,list': '<list><field name="foo"/></list>',
            'partner,false,search': '<search></search>',
        },
        mockRPC: function (route, args) {
            if (route === '/board/add_to_dashboard') {
                assert.deepEqual(args.context_to_save.group_by, ['foo'],
                    'The group_by should have been saved');
                assert.deepEqual(args.context_to_save.orderedBy,
                    [{
                        name: 'foo',
                        asc: true,
                    }],
                    'The orderedBy should have been saved');
                assert.strictEqual(args.context_to_save.fire, 'on the bayou',
                    'The context of a controller should be passed and flattened');
                assert.strictEqual(args.action_id, 1,
                    "should save the correct action");
                assert.strictEqual(args.view_mode, 'list',
                    "should save the correct view type");
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
    });

    await actionManager.doAction({
        id: 1,
        res_model: 'partner',
        type: 'ir.actions.act_window',
        views: [[false, 'list']],
    });

    assert.containsOnce(actionManager, '.o_list_view',
        "should display the list view");

    // Sort the list
    await testUtils.dom.click($('.o_column_sortable'));

    // Group It
    await testUtils.dom.click($('.o_search_options .o_dropdown button:contains(Group By)'));
    await testUtils.dom.click($('.o_search_options .o_group_by_menu button'));
    await testUtils.dom.click($('.o_search_options .o_group_by_menu button.o_apply_group'));

    // add this action to dashboard
    await testUtils.dom.click($('.o_search_options .o_dropdown button:contains(Favorites)'));
    await testUtils.dom.click($('.o_add_to_board.o_menu_header'));
    testUtils.fields.editInput($('input.o_add_to_board_input'), 'a name');
    await testUtils.dom.click($('.o_add_to_board_confirm_button'));

    testUtils.unpatch(ListController);

    actionManager.destroy();
});

QUnit.test('save two searches to dashboard', async function (assert) {
    // the second search saved should not be influenced by the first
    assert.expect(2);

    var actionManager = await createActionManager({
        data: this.data,
        archs: {
            'partner,false,list': '<list><field name="foo"/></list>',
            'partner,false,search': '<search></search>',
        },
        mockRPC: function (route, args) {
            if (route === '/board/add_to_dashboard') {
                if (filter_count === 0) {
                    assert.deepEqual(args.domain, [["display_name", "ilike", "a"]],
                        "the correct domain should be sent");
                }
                if (filter_count === 1) {
                    assert.deepEqual(args.domain, [["display_name", "ilike", "b"]],
                        "the correct domain should be sent");
                }

                filter_count += 1;
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
    });

    await actionManager.doAction({
        id: 1,
        res_model: 'partner',
        type: 'ir.actions.act_window',
        views: [[false, 'list']],
    });

    var filter_count = 0;
    // Add a first filter
    await testUtils.dom.click(actionManager.$('.o_filters_menu_button'));
    await testUtils.dom.click(actionManager.$('.o_add_custom_filter'));
    actionManager.$('.o_searchview_extended_prop_value .o_input').val('a');
    await testUtils.dom.click(actionManager.$('.o_apply_filter'));
    // Add it to dashboard
    await testUtils.dom.click(actionManager.$('.o_favorites_menu_button'));
    $('.o_search_options .dropdown-menu.o_favorites_menu').one('click', function (ev) {
        // This handler is on the webClient
        // But since the test suite doesn't have one
        // We manually set it here
        ev.stopPropagation();
    });
    await testUtils.dom.click(actionManager.$('.o_add_to_board'));
    await testUtils.dom.click(actionManager.$('.o_add_to_board_confirm_button'));
    // Remove it
    await testUtils.dom.click(actionManager.$('.o_facet_remove'));

    // Add the second filter
    await testUtils.dom.click(actionManager.$('.o_filters_menu_button'));
    await testUtils.dom.click(actionManager.$('.o_add_custom_filter'));
    actionManager.$('.o_searchview_extended_prop_value .o_input').val('b');
    await testUtils.dom.click(actionManager.$('.o_apply_filter'));
    // Add it to dashboard
    await testUtils.dom.click(actionManager.$('.o_favorites_menu_button'));
    $('.o_search_options .dropdown-menu.o_favorites_menu').one('click', function (ev) {
        // This handler is on the webClient
        // But since the test suite doesn't have one
        // We manually set it here
        ev.stopPropagation();
    });
    await testUtils.dom.click(actionManager.$('.o_add_to_board'));
    await testUtils.dom.click(actionManager.$('.o_add_to_board_confirm_button'));

    actionManager.destroy();
});

QUnit.test('save a action domain to dashboard', async function (assert) {
    // View domains are to be added to the dashboard domain
    assert.expect(1);

    var view_domain = ["display_name", "ilike", "a"];
    var filter_domain = ["display_name", "ilike", "b"];

    // The filter domain already contains the view domain, but is always added by dashboard..,
    var expected_domain = ['&', '&', view_domain, view_domain, filter_domain]

    var actionManager = await createActionManager({
        data: this.data,
        archs: {
            'partner,false,list': '<list><field name="foo"/></list>',
            'partner,false,search': '<search></search>',
        },
        mockRPC: function (route, args) {
            if (route === '/board/add_to_dashboard') {
                assert.deepEqual(args.domain, expected_domain,
                    "the correct domain should be sent");
                return Promise.resolve(true);
            }
            return this._super.apply(this, arguments);
        },
    });

    await actionManager.doAction({
        id: 1,
        res_model: 'partner',
        type: 'ir.actions.act_window',
        views: [[false, 'list']],
        domain: [view_domain],
    });

    // Add a filter
    await testUtils.dom.click(actionManager.$('.o_filters_menu_button'));
    await testUtils.dom.click(actionManager.$('.o_add_custom_filter'));
    actionManager.$('.o_searchview_extended_prop_value .o_input').val('b');
    await testUtils.dom.click(actionManager.$('.o_apply_filter'));
    // Add it to dashboard
    await testUtils.dom.click(actionManager.$('.o_favorites_menu_button'));
    await testUtils.dom.click(actionManager.$('.o_add_to_board'));
    await testUtils.dom.click(actionManager.$('.o_add_to_board_confirm_button'));

    actionManager.destroy();
});

QUnit.test("Views should be loaded in the user's language", async function (assert) {
    assert.expect(2);
    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        session: {user_context: {lang: 'fr_FR'}},
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{\'lang\': \'en_US\'}" view_mode="list" string="ABC" name="51" domain="[]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'load_views') {
                assert.deepEqual(pyUtils.eval('context', args.kwargs.context), {lang: 'fr_FR'},
                    'The views should be loaded with the correct context');
            }
            if (route === "/web/dataset/search_read") {
                assert.equal(args.context.lang, 'fr_FR',
                    'The data should be loaded with the correct context');
            }
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<list string="Partner"><field name="foo"/></list>',
        },
    });

    form.destroy();
});

QUnit.test("Dashboard should use correct groupby", async function (assert) {
    assert.expect(1);
    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{\'group_by\': [\'bar\']}" string="ABC" name="51"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'web_read_group') {
                assert.deepEqual(args.kwargs.groupby, ['bar'],
                    'user defined groupby should have precedence on action groupby');
            }
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    context: {
                        group_by: 'some_field',
                    },
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<list string="Partner"><field name="foo"/></list>',
        },
    });

    form.destroy();
});

QUnit.test("Dashboard should use correct groupby when defined as a string of one field", async function (assert) {
    assert.expect(1);
    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{\'group_by\': \'bar\'}" string="ABC" name="51"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'web_read_group') {
                assert.deepEqual(args.kwargs.groupby, ['bar'],
                    'user defined groupby should have precedence on action groupby');
            }
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    context: {
                        group_by: 'some_field',
                    },
                    views: [[4, 'list']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<list string="Partner"><field name="foo"/></list>',
        },
    });

    form.destroy();
});

QUnit.test('click on a cell of pivot view inside dashboard', async function (assert) {
    assert.expect(3);

    var form = await createView({
        View: BoardView,
        model: 'board',
        data: this.data,
        arch: '<form>' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action view_mode="pivot" string="ABC" name="51"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route) {
            if (route === '/web/action/load') {
                return Promise.resolve({
                    res_model: 'partner',
                    views: [[4, 'pivot']],
                });
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,pivot': '<pivot><field name="int_field" type="measure"/></pivot>',
        },
        intercepts: {
            do_action: function () {
                assert.step('do action');
            },
        },
    });

    assert.verifySteps([]);

    await testUtils.dom.click(form.$('.o_pivot .o_pivot_cell_value'));

    assert.verifySteps(['do action']);

    form.destroy();
});

});
