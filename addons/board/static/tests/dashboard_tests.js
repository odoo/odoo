odoo.define('board.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var FormView = require('web.FormView');

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
                },
                records: [{
                    id: 1,
                    display_name: "first record",
                    foo: "yop",
                }, {
                    id: 2,
                    display_name: "second record",
                    foo: "lalala",
                }, {
                    id: 4,
                    display_name: "aaa",
                    foo: "abc",
                }],
            },
        };
    }
});

QUnit.test('dashboard basic rendering', function (assert) {
    assert.expect(4);

    var form = createView({
        View: FormView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
            '</form>',
    });

    assert.notOk(form.renderer.$el.hasClass('o_dashboard'),
        "should not have the o_dashboard css class");

    form.destroy();

    form = createView({
        View: FormView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column></column>' +
                '</board>' +
            '</form>',
    });

    assert.ok(form.renderer.$el.hasClass('o_dashboard'),
        "with a dashboard, the renderer should have the proper css class");
    assert.strictEqual(form.$('.o_dashboard .oe_view_nocontent').length, 1,
        "should have a no content helper");
    assert.strictEqual(form.get('title'), "My Dashboard",
        "should have the correct title");
    form.destroy();
});

QUnit.test('display the no content helper', function (assert) {
    assert.expect(1);

    var form = createView({
        View: FormView,
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

    assert.strictEqual(form.$('.o_dashboard .oe_view_nocontent p:contains(click to add a partner)').length, 1,
        "should have a no content helper with action help");
    form.destroy();
});

QUnit.test('basic functionality, with one sub action', function (assert) {
    assert.expect(25);

    var form = createView({
        View: FormView,
        model: 'board',
        data: this.data,
        arch: '<form string="My Dashboard">' +
                '<board style="2-1">' +
                    '<column>' +
                        '<action context="{}" view_mode="list" string="ABC" name="51" domain="[[\'foo\', \'!=\', \'False\']]"></action>' +
                    '</column>' +
                '</board>' +
            '</form>',
        mockRPC: function (route, args) {
            if (route === '/web/action/load') {
                assert.step('load action');
                return $.when({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            if (route === '/web/dataset/search_read') {
                assert.deepEqual(args.domain, [['foo', '!=', 'False']], "the domain should be passed");
            }
            if (route === '/web/view/add_custom') {
                assert.step('add custom');
                return $.when(true);
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.strictEqual(form.$('.oe_dashboard_links').length, 1,
        "should have rendered a link div");
    assert.strictEqual(form.$('table.oe_dashboard[data-layout="2-1"]').length, 1,
        "should have rendered a table");
    assert.strictEqual(form.$('td.o_list_record_selector').length, 0,
        "td should not have a list selector");
    assert.strictEqual(form.$('h2 span.oe_header_txt:contains(ABC)').length, 1,
        "should have rendered a header with action string");
    assert.strictEqual(form.$('tr.o_data_row').length, 3,
        "should have rendered 3 data rows");

    assert.ok(form.$('.oe_content').is(':visible'), "content is visible");

    form.$('.oe_fold').click();

    assert.notOk(form.$('.oe_content').is(':visible'), "content is no longer visible");

    form.$('.oe_fold').click();

    assert.ok(form.$('.oe_content').is(':visible'), "content is visible again");
    assert.verifySteps(['load action', 'add custom', 'add custom']);

    assert.strictEqual($('.modal').length, 0, "should have no modal open");

    form.$('button.oe_dashboard_link_change_layout').click();

    assert.strictEqual($('.modal').length, 1, "should have opened a modal");
    assert.strictEqual($('.modal li[data-layout="2-1"] i.oe_dashboard_selected_layout').length, 1,
        "should mark currently selected layout");

    $('.modal .oe_dashboard_layout_selector li[data-layout="1-1"]').click();

    assert.strictEqual($('.modal').length, 0, "should have no modal open");
    assert.strictEqual(form.$('table.oe_dashboard[data-layout="1-1"]').length, 1,
        "should have rendered a table with correct layout");


    assert.strictEqual(form.$('.oe_action').length, 1, "should have one displayed action");
    form.$('span.oe_close').click();

    assert.strictEqual($('.modal').length, 1, "should have opened a modal");

    // confirm the close operation
    $('.modal button.btn-primary').click();

    assert.strictEqual($('.modal').length, 0, "should have no modal open");
    assert.strictEqual(form.$('.oe_action').length, 0, "should have no displayed action");

    assert.verifySteps(['load action', 'add custom', 'add custom', 'add custom', 'add custom']);
    form.destroy();
});

QUnit.test('can sort a sub list', function (assert) {
    assert.expect(2);

    this.data.partner.fields.foo.sortable = true;

    var form = createView({
        View: FormView,
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
                return $.when({
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

    form.$('th.o_column_sortable:contains(Foo)').click();

    assert.strictEqual($('tr.o_data_row').text(), 'abclalalayop',
        "data should have been sorted");
    form.destroy();
});

QUnit.test('can open a record', function (assert) {
    assert.expect(1);

    var form = createView({
        View: FormView,
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
                return $.when({
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

    form.$('tr.o_data_row td:contains(yop)').click();
    form.destroy();
});

QUnit.test('can drag and drop a view', function (assert) {
    assert.expect(4);

    var form = createView({
        View: FormView,
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
                return $.when({
                    res_model: 'partner',
                    views: [[4, 'list']],
                });
            }
            if (route === '/web/view/add_custom') {
                assert.step('add custom');
                return $.when(true);
            }
            return this._super.apply(this, arguments);
        },
        archs: {
            'partner,4,list':
                '<tree string="Partner"><field name="foo"/></tree>',
        },
    });

    assert.strictEqual(form.$('td.index_0 .oe_action').length, 1,
        "initial action is in column 0");

    testUtils.dragAndDrop(form.$('.oe_dashboard_column.index_0 .oe_header'),
        form.$('.oe_dashboard_column.index_1'));
    assert.strictEqual(form.$('td.index_0 .oe_action').length, 0,
        "initial action is not in column 0");
    assert.strictEqual(form.$('td.index_1 .oe_action').length, 1,
        "initial action is in in column 1");

    form.destroy();
});

QUnit.test('twice the same action in a dashboard', function (assert) {
    assert.expect(2);

    var form = createView({
        View: FormView,
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
                return $.when({
                    res_model: 'partner',
                    views: [[4, 'list'],[5, 'kanban']],
                });
            }
            if (route === '/web/view/add_custom') {
                assert.step('add custom');
                return $.when(true);
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

QUnit.test('non-existing action in a dashboard', function (assert) {
    assert.expect(1);

    var form = createView({
        View: FormView,
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
                return $.when();
            }
            if (route === '/web/action/load') {
                // server answer if the action doesn't exist anymore
                return $.when(false);
            }
            return this._super.apply(this, arguments);
        },
    });

    assert.strictEqual(form.$('.oe_action:contains(ABC)').length, 1,
        "there should be a box for the non-existing action");

    form.destroy();
});


});
