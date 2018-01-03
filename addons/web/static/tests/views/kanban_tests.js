odoo.define('web.kanban_tests', function (require) {
"use strict";

var core = require('web.core');
var KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

var createAsyncView = testUtils.createAsyncView;
var createView = testUtils.createView;

QUnit.module('Views', {
    before: function () {
        this._initialKanbanProgressBarAnimate = KanbanColumnProgressBar.prototype.ANIMATE;
        KanbanColumnProgressBar.prototype.ANIMATE = false;
    },
    after: function () {
        KanbanColumnProgressBar.prototype.ANIMATE = this._initialKanbanProgressBarAnimate;
    },
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "my float", type: "float"},
                    product_id: {string: "something_id", type: "many2one", relation: "product"},
                    category_ids: { string: "categories", type: "many2many", relation: 'category'},
                    state: { string: "State", type: "selection", selection: [["abc", "ABC"], ["def", "DEF"], ["ghi", "GHI"]]},
                    date: {string: "Date Field", type: 'date'},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4, product_id: 3, state: "abc", category_ids: []},
                    {id: 2, bar: true, foo: "blip", int_field: 9, qux: 13, product_id: 5, state: "def", category_ids: [6]},
                    {id: 3, bar: true, foo: "gnap", int_field: 17, qux: -3, product_id: 3, state: "ghi", category_ids: [7]},
                    {id: 4, bar: false, foo: "blip", int_field: -4, qux: 9, product_id: 5, state: "ghi", category_ids: []},
                ]
            },
            product: {
                fields: {
                    id: {string: "ID", type: "integer"},
                    name: {string: "Display Name", type: "char"},
                },
                records: [
                    {id: 3, name: "hello"},
                    {id: 5, name: "xmo"},
                ]
            },
            category: {
                fields: {
                    name: {string: "Category Name", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 6, name: "gold", color: 2},
                    {id: 7, name: "silver", color: 5},
                ]
            },
        };
    },
}, function () {

    QUnit.module('KanbanView');

    QUnit.test('basic ungrouped rendering', function (assert) {
        assert.expect(5);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<t t-esc="record.foo.value"/>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_ungrouped'),
                        "should have classname 'o_kanban_ungrouped'");
        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_test'),
                        "should have classname 'o_kanban_test'");

        assert.strictEqual(kanban.$('.o_kanban_record:not(.o_kanban_ghost)').length, 4,
                        "should have 4 records");
        assert.strictEqual(kanban.$('.o_kanban_ghost').length, 6, "should have 6 ghosts");
        assert.strictEqual(kanban.$('.o_kanban_record:contains(gnap)').length, 1,
                        "should contain gnap");
        kanban.destroy();
    });

    QUnit.test('basic grouped rendering', function (assert) {
        assert.expect(13);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    // the lazy option is important, so the server can fill in
                    // the empty groups
                    assert.ok(args.kwargs.lazy, "should use lazy read_group");
                }
                return this._super(route, args);
            },
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'),
                        "should have classname 'o_kanban_grouped'");
        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_test'),
                        "should have classname 'o_kanban_test'");
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have " + 2 + " columns");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain " + 1 + " record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 3,
                        "column should contain " + 3 + " record(s)");
        // check available actions in kanban header's config dropdown
        assert.ok(kanban.$('.o_kanban_header:first .o_kanban_config .o_kanban_toggle_fold').length,
                        "should be able to fold the column");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive').length,
                        "should be not able to archive the records");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive').length,
                        "should be not able to restore the records");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_edit').length,
                        "should not be able to edit the column");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_delete').length,
                        "should not be able to delete the column");

        // the next line makes sure that reload works properly.  It looks useless,
        // but it actually test that a grouped local record can be reloaded without
        // changing its result.
        kanban.reload();
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 3,
                        "column should contain " + 3 + " record(s)");
        kanban.destroy();
    });

    QUnit.test('basic grouped rendering with active field', function (assert) {
        assert.expect(6);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var envIDs = [1, 2, 3, 4]; // the ids that should be in the environment during this test
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="active"/>' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            intercepts: {
                env_updated: function (event) {
                    assert.deepEqual(event.data.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });

        // check available actions in kanban header's config dropdown
        assert.ok(kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive').length,
                        "should be able to archive the records");
        assert.ok(kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive').length,
                        "should be able to restore the records");

        // archive the records of the first column
        assert.strictEqual(kanban.$('.o_kanban_group:last .o_kanban_record').length, 3,
            "last column should contain 3 records");
        envIDs = [4];
        kanban.$('.o_kanban_group:last .o_column_archive').click(); // click on 'Archive'
        assert.strictEqual(kanban.$('.o_kanban_group:last .o_kanban_record').length, 0,
            "last column should contain no record");
        kanban.destroy();
    });

    QUnit.test('pager should be hidden in grouped mode', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });
        kanban.renderPager();

        assert.ok(kanban.pager.$el.hasClass('o_hidden'),
                        "pager should be hidden in grouped kanban");
        kanban.destroy();
    });

    QUnit.test('pager, ungrouped, with default limit', function (assert) {
        assert.expect(3);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.limit, 40, "default limit should be 40 in Kanban");
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(!kanban.pager.$el.hasClass('o_hidden'),
                        "pager should be visible in ungrouped kanban");
        assert.strictEqual(kanban.pager.state.size, 4, "pager's size should be 4");
        kanban.destroy();
    });

    QUnit.test('pager, ungrouped, with limit given in options', function (assert) {
        assert.expect(3);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.limit, 2, "limit should be 2");
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.strictEqual(kanban.pager.state.limit, 2, "pager's limit should be 2");
        assert.strictEqual(kanban.pager.state.size, 4, "pager's size should be 4");
        kanban.destroy();
    });

    QUnit.test('pager, ungrouped, with limit set on arch and given in options', function (assert) {
        assert.expect(3);

        // the limit given in the arch should take the priority over the one given in options
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" limit="3">' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                assert.strictEqual(args.limit, 3, "limit should be 3");
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                limit: 2,
            },
        });

        assert.strictEqual(kanban.pager.state.limit, 3, "pager's limit should be 3");
        assert.strictEqual(kanban.pager.state.size, 4, "pager's size should be 4");
        kanban.destroy();
    });

    QUnit.test('create in grouped on m2o', function (assert) {
        assert.expect(5);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });
        kanban.renderButtons();

        assert.ok(kanban.$('.o_kanban_view').hasClass('ui-sortable'),
            "columns are sortable when grouped by a m2o field");
        assert.ok(kanban.$buttons.find('.o-kanban-button-new').hasClass('btn-primary'),
            "'create' button should be btn-primary for grouped kanban with at least one column");
        assert.ok(kanban.$('.o_kanban_view > div:last').hasClass('o_column_quick_create'),
            "column quick create should be enabled when grouped by a many2one field)");

        kanban.$buttons.find('.o-kanban-button-new').click(); // Click on 'Create'
        assert.ok(kanban.$('.o_kanban_group:first() > div:nth(1)').hasClass('o_kanban_quick_create'),
            "clicking on create should open the quick_create in the first column");

        assert.ok(kanban.$('span.o_column_title:contains(hello)').length,
            "should have a column title with a value from the many2one");
        kanban.destroy();
    });

    QUnit.test('create in grouped on char', function (assert) {
        assert.expect(4);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['foo'],
        });

        assert.ok(!kanban.$('.o_kanban_view').hasClass('ui-sortable'),
            "columns aren't sortable when not grouped by a m2o field");
        assert.strictEqual(kanban.$('.o_kanban_group').length, 3, "should have " + 3 + " columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first() .o_column_title').text(), "yop",
            "'yop' column should be the first column");
        assert.ok(!kanban.$('.o_kanban_view > div:last').hasClass('o_column_quick_create'),
            "column quick create should be disabled when not grouped by a many2one field)");
        kanban.destroy();
    });

    QUnit.test('quick create and change state in grouped mode', function (assert) {
        assert.expect(1);

        this.data.partner.fields.kanban_state = {
            string: "Kanban State",
            type: "selection",
            selection: [["normal", "Grey"], ["done", "Green"], ["blocked", "Red"]],
        };

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                        '<div class="oe_kanban_bottom_right">' +
                        '<field name="kanban_state" widget="state_selection"/>' +
                        '</div>' +
                        '</t></templates>' +
                  '</kanban>',
            groupBy: ['foo'],
        });

        // Quick create kanban record
        kanban.$('.o_kanban_header .o_kanban_quick_add i').first().click();
        var $quickAdd = kanban.$('.o_kanban_quick_create');
        $quickAdd.find('.o_input').val('Test');
        $quickAdd.find('.o_kanban_add').click();

        // Select state in kanban
        kanban.$('.o_status').first().click();
        kanban.$('.o_selection ul:first li:first').click();
        assert.ok(kanban.$('.o_status').first().hasClass('o_status_green'),
            "Kanban state should be done (Green)");
        kanban.destroy();
    });

    QUnit.test('quick create in grouped mode', function (assert) {
        assert.expect(8);

        var nbRecords = 4;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            intercepts: {
                env_updated: function (event) {
                    assert.strictEqual(event.data.ids.length, nbRecords,
                        "should update the env with the records ids");
                },
            }
        });

        // click to add an element and cancel the quick creation
        kanban.$('.o_kanban_header .o_kanban_quick_add i').first().click();

        var $quickCreate = kanban.$('.o_kanban_quick_create');
        assert.strictEqual($quickCreate.length, 1, "should have a quick create element");

        $quickCreate.find('input').trigger($.Event('keydown', {keyCode: $.ui.keyCode.ESCAPE}));
        assert.strictEqual(kanban.$('.o_kanban_quick_create').length, 0,
            "should have destroyed the quick create element");

        //click to add and element and focus out the blank input, should cancel the quick creation
        kanban.$('.o_kanban_header .o_kanban_quick_add i').first().click();
        $quickCreate = kanban.$('.o_kanban_quick_create');
        $quickCreate.find('input').blur();
        assert.strictEqual(kanban.$('.o_kanban_quick_create').length, 0,
            "Blur should have destroyed the quick create element");

        // click to really add an element
        kanban.$('.o_kanban_header .o_kanban_quick_add i').first().click();
        $quickCreate = kanban.$('.o_kanban_quick_create');
        $quickCreate.find('input').val('new partner');
        $quickCreate.find('input').blur();

        // When focus out the input containing value, should not delete the Quick Creation
        assert.strictEqual(kanban.$('.o_kanban_quick_create').length, 1,
            "Blur should not have destroyed the quick create element");
        nbRecords = 5;
        $quickCreate.find('button.o_kanban_add').click();

        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a partner");
        assert.strictEqual(_.last(this.data.partner.records).name, "new partner",
            "should have correct name");

        kanban.destroy();
    });

    QUnit.test('quick create and edit in grouped mode', function (assert) {
        assert.expect(6);

        var newRecordID;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                var def = this._super.apply(this, arguments);
                if (args.method === 'name_create') {
                    def.then(function (result) {
                        newRecordID = result[0];
                    });
                }
                return def;
            },
            groupBy: ['bar'],
            intercepts: {
                switch_view: function (event) {
                    assert.strictEqual(event.data.mode, "edit",
                        "should trigger 'open_record' event in edit mode");
                    assert.strictEqual(event.data.res_id, newRecordID,
                        "should open the correct record");
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:first .o_kanban_record').length, 1,
            "first column should contain one record");

        // click to add and edit an element
        var $quickCreate = kanban.$('.o_kanban_quick_create');
        kanban.$('.o_kanban_header .o_kanban_quick_add i').first().click();
        $quickCreate = kanban.$('.o_kanban_quick_create');
        $quickCreate.find('input').val('new partner');
        $quickCreate.find('button.o_kanban_edit').click();

        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a partner");
        assert.strictEqual(_.last(this.data.partner.records).name, "new partner",
            "should have correct name");
        assert.strictEqual(kanban.$('.o_kanban_group:first .o_kanban_record').length, 2,
            "first column should now contain two records");

        kanban.destroy();
    });

    QUnit.test('quick create fail in grouped', function (assert) {
        assert.expect(7);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            archs: {
                'partner,false,form': '<form string="Partner">' +
                        '<field name="product_id"/>' +
                        '<field name="foo"/>' +
                    '</form>',
            },
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    return $.Deferred().reject({
                        code: 200,
                        data: {},
                        message: "Odoo server error",
                    }, $.Event());
                }
                return this._super.apply(this, arguments);
            },
        });
        kanban.renderButtons();

        assert.strictEqual(kanban.$('.o_kanban_group:first .o_kanban_record').length, 2,
            "there should be 2 records in first column");

        kanban.$buttons.find('.o-kanban-button-new').click(); // Click on 'Create'
        assert.ok(kanban.$('.o_kanban_group:first() > div:nth(1)').hasClass('o_kanban_quick_create'),
            "clicking on create should open the quick_create in the first column");

        kanban.$('.o_kanban_quick_create input')
            .val('test')
            .trigger($.Event('keypress', {keyCode: $.ui.keyCode.ENTER}));

        assert.strictEqual($('.modal .o_form_view.o_form_editable').length, 1,
            "a form view dialog should have been opened (in edit)");
        assert.strictEqual($('.modal .o_field_many2one input').val(), 'hello',
            "the correct product_id should already be set");

        // specify a name and save
        $('.modal input[name=foo]').val('test').trigger('input');
        $('.modal-footer .btn-primary').click();

        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.strictEqual(kanban.$('.o_kanban_group:first .o_kanban_record').length, 3,
            "there should be 3 records in first column");
        var $firstRecord = kanban.$('.o_kanban_group:first .o_kanban_record:first');
        assert.strictEqual($firstRecord.text(), 'test',
            "the first record of the first column should be the new one");

        kanban.destroy();
    });

    QUnit.test('many2many_tags in kanban views', function (assert) {
        assert.expect(12);

        this.data.partner.records[0].category_ids = [6, 7];
        this.data.partner.records[1].category_ids = [7, 8];
        this.data.category.records.push({
            id: 8,
            name: "hello",
            color: 0,
        });

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div class="oe_kanban_global_click">' +
                                '<field name="category_ids" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                                '<field name="foo"/>' +
                                '<field name="state" widget="priority"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.deepEqual(event.data, {
                        mode: 'readonly',
                        model: 'partner',
                        res_id: 1,
                        view_type: 'form',
                    }, "should trigger an event to open the clicked record in a form view");
                },
            },
        });

        var $first_record = kanban.$('.o_kanban_record:first()');
        assert.strictEqual($first_record.find('.o_field_many2manytags .o_tag').length, 2,
            'first record should contain 2 tags');
        assert.ok($first_record.find('.o_tag:first()').hasClass('o_tag_color_2'),
            'first tag should have color 2');
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/category/read'],
            'two RPC should have been done (one search read and one read for the m2m)');

        // Checks that second records has only one tag as one should be hidden (color 0)
        assert.strictEqual(kanban.$('.o_kanban_record').eq(1).find('.o_tag').length, 1,
            'there should be only one tag in second record');

        // Write on the record using the priority widget to trigger a re-render in readonly
        kanban.$('.o_field_widget.o_priority a.o_priority_star.fa-star-o').first().click();
        assert.verifySteps([
            '/web/dataset/search_read',
            '/web/dataset/call_kw/category/read',
            '/web/dataset/call_kw/partner/write',
            '/web/dataset/call_kw/partner/read',
            '/web/dataset/call_kw/category/read'
        ], 'five RPCs should have been done (previous 2, 1 write (triggers a re-render), same 2 at re-render');
        assert.strictEqual(kanban.$('.o_kanban_record:first()').find('.o_field_many2manytags .o_tag').length, 2,
            'first record should still contain only 2 tags');

        // click on a tag (should trigger switch_view)
        kanban.$('.o_tag:contains(gold):first').click();

        kanban.destroy();
    });

    QUnit.test('can drag and drop a record from one column to the next', function (assert) {
        assert.expect(9);

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        this.data.partner.fields.sequence = {type: 'number', string: "Sequence"};
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/>' +
                                '<t t-if="widget.editable"><span class="thisiseditable">edit</span></t>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.ok(true, "should call resequence");
                    return $.when(true);
                }
                return this._super(route, args);
            },
            intercepts: {
                env_updated: function (event) {
                    assert.deepEqual(event.data.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");

        assert.strictEqual(kanban.$('.thisiseditable').length, 4, "all records should be editable");
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        envIDs = [3, 2, 4, 1]; // first record of first column moved to the bottom of second column
        testUtils.dragAndDrop($record, $group);

        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should now contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 3,
                        "column should contain 3 record(s)");
        assert.strictEqual(kanban.$('.thisiseditable').length, 4, "all records should be editable");
        kanban.destroy();
    });

    QUnit.test('drag and drop a record, grouped by selection', function (assert) {
        assert.expect(6);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates>' +
                            '<t t-name="kanban-box">' +
                                '<div><field name="state"/></div>' +
                            '</t>' +
                        '</templates>' +
                    '</kanban>',
            groupBy: ['state'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.ok(true, "should call resequence");
                    return $.when(true);
                }
                if (args.model === 'partner' && args.method === 'write') {
                    assert.deepEqual(args.args[1], {state: 'def'});
                }
                return this._super(route, args);
            },
        });
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");

        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        testUtils.dragAndDrop($record, $group);

        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 0,
                        "column should now contain 0 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");
        kanban.destroy();
    });

    QUnit.test('prevent drag and drop of record if grouped by readonly', function (assert) {
        assert.expect(12);

        this.data.partner.fields.foo.readonly = true;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates>' +
                            '<t t-name="kanban-box"><div>' +
                                '<field name="foo"/>' +
                                '<field name="state" readonly="1"/>' +
                            '</div></t>' +
                        '</templates>' +
                    '</kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    return $.when();
                }
                if (args.model === 'partner' && args.method === 'write') {
                    throw new Error('should not be draggable');
                }
                return this._super(route, args);
            },
        });
        // simulate an update coming from the searchview, with another groupby given
        kanban.update({groupBy: ['state']});
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        // drag&drop a record in another column
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        testUtils.dragAndDrop($record, $group);
        // should not be draggable
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should now contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");

        // simulate an update coming from the searchview, with another groupby given
        kanban.update({groupBy: ['foo']});
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");
        // drag&drop a record in another column
        $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        $group = kanban.$('.o_kanban_group:nth-child(2)');
        testUtils.dragAndDrop($record, $group);
        // should not be draggable
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should now contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");

        // drag&drop a record in the same column
        var $record1 = kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(0)');
        var $record2 = kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(1)');
        assert.strictEqual($record1.text(), "blipDEF", "first record should be DEF");
        assert.strictEqual($record2.text(), "blipGHI", "second record should be GHI");
        testUtils.dragAndDrop($record2, $record1, {position: 'top'});
        // should still be able to resequence
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(0)').text(), "blipGHI",
            "records should have been resequenced");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(1)').text(), "blipDEF",
            "records should have been resequenced");

        kanban.destroy();
    });

    QUnit.test('kanban view with default_group_by', function (assert) {
        assert.expect(7);
        this.data.partner.records.product_id = 1;
        this.data.product.records.push({id: 1, display_name: "third product"});

        var readGroupCount = 0;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" default_group_by="bar">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/read_group') {
                    readGroupCount++;
                    var correctGroupBy;
                    if (readGroupCount === 2) {
                        correctGroupBy = ['product_id'];
                    } else {
                        correctGroupBy = ['bar'];
                    }
                    // this is done three times
                    assert.ok(_.isEqual(args.kwargs.groupby, correctGroupBy),
                        "groupby args should be correct");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'),
                        "should have classname 'o_kanban_grouped'");
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have " + 2 + " columns");

        // simulate an update coming from the searchview, with another groupby given
        kanban.update({groupBy: ['product_id']});
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should now have " + 3 + " columns");

        // simulate an update coming from the searchview, removing the previously set groupby
        kanban.update({groupBy: []});
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have " + 2 + " columns again");
        kanban.destroy();
    });

    QUnit.test('kanban view with create=False', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" create="0">' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
        });

        assert.ok(!kanban.$buttons || !kanban.$buttons.find('.o-kanban-button-new').length,
            "Create button shouldn't be there");
        kanban.destroy();
    });

    QUnit.test('clicking on a link triggers correct event', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div><a type="edit">Edit</a></div>' +
                '</t></templates></kanban>',
        });

        testUtils.intercept(kanban, 'switch_view', function (event) {
            assert.deepEqual(event.data, {
                view_type: 'form',
                res_id: 1,
                mode: 'edit',
                model: 'partner',
            });
        });
        kanban.$('a').first().click();
        kanban.destroy();
    });

    QUnit.test('environment is updated when (un)folding groups', function (assert) {
        assert.expect(3);

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            intercepts: {
                env_updated: function (event) {
                    assert.deepEqual(envIDs, event.data.ids,
                        "should notify the environment with the correct ids");
                },
            },
        });

        // fold the second group and check that the res_ids it contains are no
        // longer in the environment
        envIDs = [1, 3];
        kanban.$('.o_kanban_group:last .o_kanban_toggle_fold').click();

        // re-open the second group and check that the res_ids it contains are
        // back in the environment
        envIDs = [1, 3, 2, 4];
        kanban.$('.o_kanban_group:last .o_kanban_toggle_fold').click();

        kanban.destroy();
    });

    QUnit.test('create a column in grouped on m2o', function (assert) {
        assert.expect(13);

        var nbRPCs = 0;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                nbRPCs++;
                if (args.method === 'name_create') {
                    assert.ok(true, "should call name_create");
                }
                return this._super(route, args);
            },
        });
        assert.strictEqual(kanban.$('.o_column_quick_create').length, 1, "should have a quick create column");
        assert.notOk(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should not be visible");

        kanban.$('.o_column_quick_create').click();

        assert.ok(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should be visible");

        // discard the column creation and click it again
        kanban.$('.o_column_quick_create').click();
        assert.notOk(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should not be visible after discard");

        kanban.$('.o_column_quick_create').click();
        assert.ok(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should be visible");

        kanban.$('.o_column_quick_create input').val('new value');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group:last span:contains(new value)').length, 1,
            "the last column should be the newly created one");
        assert.ok(_.isNumber(kanban.$('.o_kanban_group:last').data('id')),
            'the created column should have the correct id');
        assert.ok(!kanban.$('.o_kanban_group:last').hasClass('o_column_folded'),
            'the created column should not be folded');

        // fold and unfold the created column, and check that no RPC is done (as there is no record)
        nbRPCs = 0;
        kanban.$('.o_kanban_group:last .o_kanban_toggle_fold').click(); // fold the group
        assert.ok(kanban.$('.o_kanban_group:last').hasClass('o_column_folded'),
            'the created column should now be folded');
        kanban.$('.o_kanban_group:last').click();
        assert.ok(!kanban.$('.o_kanban_group:last').hasClass('o_column_folded'),
            'the created column should not be folded');
        assert.strictEqual(nbRPCs, 0, 'no rpc should have been done when folding/unfolding');

        // quick create a record
        kanban.$buttons.find('.o-kanban-button-new').click(); // Click on 'Create'
        assert.ok(kanban.$('.o_kanban_group:first() > div:nth(1)').hasClass('o_kanban_quick_create'),
            "clicking on create should open the quick_create in the first column");
        kanban.destroy();
    });

    QUnit.test('quick create record & column in grouped on m2o', function (assert) {
        assert.expect(2);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });
        kanban.$('.o_kanban_group:first .o_kanban_quick_add').click();
        var $quickCreate = kanban.$('.o_kanban_quick_create');
        $quickCreate.find('input').val('new partner');
        $quickCreate.find('button.o_kanban_add').click();
        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a partner");

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('new column');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group:last span:contains(new column)').length, 1,
            "the last column should be the newly created one");
        kanban.destroy();
    });

    QUnit.test('delete a column in grouped on m2o', function (assert) {
        assert.expect(32);

        testUtils.patch(KanbanRenderer, {
            _renderGrouped: function () {
                this._super.apply(this, arguments);
                // set delay and revert animation time to 0 so dummy drag and drop works
                if (this.$el.sortable('instance')) {
                    this.$el.sortable('option', {delay: 0, revert: 0});
                }
            },
        });

        var resequencedIDs;

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    resequencedIDs = args.ids;
                    assert.strictEqual(_.reject(args.ids, _.isNumber).length, 0,
                        "column resequenced should be existing records with IDs");
                    return $.when(true);
                }
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super(route, args);
            },
        });

        // check the initial rendering
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have two columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 3,
            'first column should be [3, "hello"]');
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 5,
            'second column should be [5, "xmo"]');
        assert.strictEqual(kanban.$('.o_kanban_group:last .o_column_title').text(), 'xmo',
            'second column should have correct title');
        assert.strictEqual(kanban.$('.o_kanban_group:last .o_kanban_record').length, 2,
            "second column should have two records");

        // check available actions in kanban header's config dropdown
        assert.ok(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold').length,
                        "should be able to fold the column");
        assert.ok(kanban.$('.o_kanban_group:first .o_column_edit').length,
                        "should be able to edit the column");
        assert.ok(kanban.$('.o_kanban_group:first .o_column_delete').length,
                        "should be able to delete the column");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive').length,
                        "should not be able to archive the records");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive').length,
                        "should not be able to restore the records");

        // delete second column (first cancel the confirm request, then confirm)
        kanban.$('.o_kanban_group:last .o_column_delete').click(); // click on delete
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-default').click(); // click on cancel
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 5,
            'column [5, "xmo"] should still be there');
        kanban.$('.o_kanban_group:last .o_column_delete').click(); // click on delete
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 3,
            'last column should now be [3, "hello"]');
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should still have two columns");
        assert.ok(!_.isNumber(kanban.$('.o_kanban_group:first').data('id')),
            'first column should have no id (Undefined column)');
        // check available actions on 'Undefined' column
        assert.ok(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold').length,
                        "should be able to fold the column");
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_delete').length,
            'Undefined column could not be deleted');
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_edit').length,
            'Undefined column could not be edited');
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive').length,
                        "should not be able to archive the records");
        assert.ok(!kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive').length,
                        "should not be able to restore the records");
        assert.verifySteps(['read_group', 'unlink', 'read_group']);
        assert.strictEqual(kanban.renderer.widgets.length, 2,
            "the old widgets should have been correctly deleted");

        // test column drag and drop having an 'Undefined' column
        testUtils.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:last'), {position: 'right'}
        );
        assert.strictEqual(resequencedIDs, undefined,
            "resequencing require at least 2 not Undefined columns");
        kanban.$('.o_column_quick_create input').val('once third column');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();
        var newColumnID = kanban.$('.o_kanban_group:last').data('id');
        testUtils.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:last'), {position: 'right'}
        );
        assert.deepEqual([3, newColumnID], resequencedIDs,
            "moving the Undefined column should not affect order of other columns")
        testUtils.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:nth(1)'), {position: 'right'}
        );
        assert.deepEqual([newColumnID, 3], resequencedIDs,
            "moved column should be resequenced accordingly")

        kanban.destroy();
        testUtils.unpatch(KanbanRenderer);
    });

    QUnit.test('create a column, delete it and create another one', function (assert) {
        assert.expect(5);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });

        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have two columns");

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('new column 1');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group').length, 3, "should have two columns");

        kanban.$('.o_kanban_group:last .o_column_delete').click();
        $('.modal .modal-footer .btn-primary').click();

        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have twos columns");

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('new column 2');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group').length, 3, "should have three columns");
        assert.strictEqual(kanban.$('.o_kanban_group:last span:contains(new column 2)').length, 1,
            "the last column should be the newly created one");
        kanban.destroy();
    });

    QUnit.test('edit a column in grouped on m2o', function (assert) {
        assert.expect(12);

        var nbRPCs = 0;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            archs: {
                'product,false,form': '<form string="Product"><field name="display_name"/></form>',
            },
            mockRPC: function (route, args) {
                nbRPCs++;
                return this._super(route, args);
            },
        });
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'xmo',
            'title of the column should be "xmo"');

        // edit the title of column [5, 'xmo'] and close without saving
        kanban.$('.o_kanban_group[data-id=5] .o_column_edit').click(); // click on 'Edit'
        assert.ok($('.modal .o_form_editable').length, 'a form view should be open in a modal');
        assert.strictEqual($('.modal .o_form_editable input').val(), 'xmo',
            'the name should be "xmo"');
        $('.modal .o_form_editable input').val('ged').trigger('input'); // change the value
        nbRPCs = 0;
        $('.modal .modal-header .close').click(); // click on the cross to close the modal
        assert.ok(!$('.modal').length, 'the modal should be closed');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'xmo',
            'title of the column should still be "xmo"');
        assert.strictEqual(nbRPCs, 0, 'no RPC should have been done');

        // edit the title of column [5, 'xmo'] and discard
        kanban.$('.o_kanban_group[data-id=5] .o_column_edit').click(); // click on 'Edit'
        $('.modal .o_form_editable input').val('ged').trigger('input'); // change the value
        nbRPCs = 0;
        $('.modal .modal-footer .btn-default').click(); // click on discard
        assert.ok(!$('.modal').length, 'the modal should be closed');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'xmo',
            'title of the column should still be "xmo"');
        assert.strictEqual(nbRPCs, 0, 'no RPC should have been done');

        // edit the title of column [5, 'xmo'] and save
        kanban.$('.o_kanban_group[data-id=5] .o_column_edit').click(); // click on 'Edit'
        $('.modal .o_form_editable input').val('ged').trigger('input'); // change the value
        nbRPCs = 0;
        $('.modal .modal-footer .btn-primary').click(); // click on save
        assert.ok(!$('.modal').length, 'the modal should be closed');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'ged',
            'title of the column should be "ged"');
        assert.strictEqual(nbRPCs, 4, 'should have done 1 write, 1 read_group and 2 search_read');
        kanban.destroy();
    });

    QUnit.test('if view was grouped at start, it stays grouped', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });
        kanban.update({groupBy: []});

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'));
        kanban.destroy();
    });

    QUnit.test('if view was not grouped at start, it can be grouped and ungrouped', function (assert) {
        assert.expect(3);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
        });
        assert.notOk(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'), "should not be grouped");
        kanban.update({groupBy: ['product_id']});
        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'), "should be grouped");
        kanban.update({groupBy: []});
        assert.notOk(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'), "should not be grouped");
        kanban.destroy();
    });

    QUnit.test('no content helper when no data', function (assert) {
        assert.expect(5);

        var records = this.data.partner.records;

        this.data.partner.records = [];

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<t t-esc="record.foo.value"/>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            viewOptions: {
                action: {
                    help: '<p class="hello">click to add a partner</p>'
                }
            },
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_nocontent'),
            "$el should have correct no content class");

        assert.strictEqual(kanban.$('.oe_view_nocontent').length, 1,
            "should display the no content helper");

        assert.strictEqual(kanban.$('.oe_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.partner.records = records;
        kanban.reload();

        assert.notOk(kanban.$el.hasClass('o_kanban_nocontent'),
            "$el should have removed no content class");

        assert.strictEqual(kanban.$('.oe_view_nocontent').length, 0,
            "should not display the no content helper");
        kanban.destroy();
    });

    QUnit.test('no nocontent helper for grouped kanban with empty groups', function (assert) {
        assert.expect(2);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    return this._super.apply(this, arguments).then(function (result) {
                        _.each(result, function (group) {
                            group[args.kwargs.groupby[0] + '_count'] = 0;
                        });
                        return result;
                    });
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group').length, 2,
            "there should be two columns");
        assert.strictEqual(kanban.$('.o_kanban_record').length, 0,
            "there should be no records");

        kanban.destroy();
    });

    QUnit.test('no nocontent helper for grouped kanban with no records', function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group').length, 0,
            "there should be no columns");
        assert.strictEqual(kanban.$('.o_kanban_record').length, 0,
            "there should be no records");
        assert.strictEqual(kanban.$('.oe_view_nocontent').length, 0,
            "there should be no nocontent helper");
        assert.strictEqual(kanban.$('.o_column_quick_create').length, 1,
            "there should be a column quick create");
        kanban.destroy();
    });

    QUnit.test('nocontent helper for grouped kanban with no records with no group_create', function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban group_create="false">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group').length, 0,
            "there should be no columns");
        assert.strictEqual(kanban.$('.o_kanban_record').length, 0,
            "there should be no records");
        assert.strictEqual(kanban.$('.oe_view_nocontent').length, 1,
            "there should be a nocontent helper");
        assert.strictEqual(kanban.$('.o_column_quick_create').length, 0,
            "there should not be a column quick create");
        kanban.destroy();
    });

    QUnit.test('buttons with modifiers', function (assert) {
        assert.expect(2);

        this.data.partner.records[1].bar = false; // so that test is more complete

        var kanban = createView({
            View: KanbanView,
            model: "partner",
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="state"/>' +
                    '<templates><div t-name="kanban-box">' +
                        '<button class="o_btn_test_1" type="object" name="a1" ' +
                            'attrs="{\'invisible\': [[\'foo\', \'!=\', \'yop\']]}"/>' +
                        '<button class="o_btn_test_2" type="object" name="a2" ' +
                            'attrs="{\'invisible\': [[\'bar\', \'=\', True]]}" ' +
                            'states="abc,def"/>' +
                    '</div></templates>' +
                '</kanban>',
        });

        assert.strictEqual(kanban.$(".o_btn_test_1").length, 1,
            "kanban should have one buttons of type 1");
        assert.strictEqual(kanban.$(".o_btn_test_2").length, 3,
            "kanban should have three buttons of type 2");
        kanban.destroy();
    });

    QUnit.test('button executes action and reloads', function (assert) {
        assert.expect(6);

        var kanban = createView({
            View: KanbanView,
            model: "partner",
            data: this.data,
            arch:
                '<kanban>' +
                    '<templates><div t-name="kanban-box">' +
                        '<field name="foo"/>' +
                        '<button type="object" name="a1" />' +
                    '</div></templates>' +
                '</kanban>',
            mockRPC: function (route) {
                assert.step(route);
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(kanban.$('button[data-name="a1"]').length,
            "kanban should have at least one button a1");

        var count = 0;
        testUtils.intercept(kanban, 'execute_action', function (event) {
            count++;
            event.data.on_closed();
        });
        $('button[data-name="a1"]').first().click();
        assert.strictEqual(count, 1, "should have triggered a execute action");

        $('button[data-name="a1"]').first().click();
        assert.strictEqual(count, 1, "double-click on kanban actions should be debounced");

        assert.verifySteps([
            '/web/dataset/search_read',
            '/web/dataset/call_kw/partner/read'
        ], 'a read should be done after the call button to reload the record');

        kanban.destroy();
    });

    QUnit.test('rendering date and datetime', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].date = "2017-01-25";
        this.data.partner.records[1].datetime= "2016-12-12 10:55:05";

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="date"/>' +
                    '<field name="datetime"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<t t-esc="record.date.raw_value"/>' +
                        '<t t-esc="record.datetime.raw_value"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
        });

        // FIXME: this test is locale dependant. we need to do it right.
        assert.strictEqual(kanban.$('div.o_kanban_record:contains(Wed Jan 25)').length, 1,
            "should have formatted the date");
        assert.strictEqual(kanban.$('div.o_kanban_record:contains(Mon Dec 12)').length, 1,
            "should have formatted the datetime");
        kanban.destroy();
    });

    QUnit.test('evaluate conditions on relational fields', function (assert) {
        assert.expect(3);

        this.data.partner.records[0].product_id = false;

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<field name="product_id"/>' +
                    '<field name="category_ids"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                        '<button t-if="!record.product_id.raw_value" class="btn_a">A</button>' +
                        '<button t-if="!record.category_ids.raw_value.length" class="btn_b">B</button>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
        });

        assert.strictEqual($('.o_kanban_record:not(.o_kanban_ghost)').length, 4,
            "there should be 4 records");
        assert.strictEqual($('.o_kanban_record:not(.o_kanban_ghost) .btn_a').length, 1,
            "only 1 of them should have the 'Action' button");
        assert.strictEqual($('.o_kanban_record:not(.o_kanban_ghost) .btn_b').length, 2,
            "only 2 of them should have the 'Action' button");

        kanban.destroy();
    });

    QUnit.test('resequence columns in grouped by m2o', function (assert) {
        assert.expect(7);

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route) {
                if (route === '/web/dataset/resequence') {
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                env_updated: function (event) {
                    assert.deepEqual(event.data.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('ui-sortable'),
            "columns should be sortable");
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2,
            "should have two columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 3,
            "first column should be id 3 before resequencing");

        // there is a 100ms delay on the d&d feature (jquery sortable) for
        // kanban columns, making it hard to test. So we rather bypass the d&d
        // for this test, and directly call the event handler
        envIDs = [2, 4, 1, 3]; // the columns will be inverted
        kanban._onResequenceColumn({data: {ids: [5, 3]}});
        kanban.update({}, {reload: false}); // re-render without reloading

        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 5,
            "first column should be id 5 before resequencing");

        kanban.destroy();
    });

    QUnit.test('properly evaluate more complex domains', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="category_ids"/>' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="foo"/>' +
                                '<button type="object" attrs="{\'invisible\':[\'|\', (\'bar\',\'=\',True), (\'category_ids\', \'!=\', [])]}" class="btn btn-primary pull-right btn-sm" name="channel_join_and_get_info">Join</button>' +
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
        });

        assert.strictEqual(kanban.$('button.oe_kanban_action_button').length, 1,
            "only one button should be visible");
        kanban.destroy();
    });

    QUnit.test('edit the kanban color with the colorpicker', function (assert) {
        assert.expect(5);

        var writeOnColor;

        this.data.category.records[0].color = 12;

        var kanban = createView({
            View: KanbanView,
            model: 'category',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="color"/>' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div color="color">' +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a class="dropdown-toggle btn" data-toggle="dropdown" href="#">' +
                                            '<span class="fa fa-bars fa-lg"/>' +
                                    '</a>' +
                                    '<ul class="dropdown-menu" role="menu" aria-labelledby="dLabel">' +
                                        '<li>' +
                                            '<ul class="oe_kanban_colorpicker"/>' +
                                        '</li>' +
                                    '</ul>' +
                                '</div>' +
                                '<field name="name"/>' +
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'write' && 'color' in args.args[1]) {
                    writeOnColor = true;
                }
                return this._super.apply(this, arguments);
            },
        });

        var $firstRecord = kanban.$('.o_kanban_record:first()');

        assert.strictEqual(kanban.$('.o_kanban_record.oe_kanban_color_12').length, 0,
            "no record should have the color 12");
        assert.strictEqual($firstRecord.find('.oe_kanban_colorpicker').length, 1,
            "there should be a color picker");
        assert.strictEqual($firstRecord.find('.oe_kanban_colorpicker').children().length, 12,
            "the color picker should have 12 children (the colors)");

        // Set a color
        $firstRecord.find('.oe_kanban_colorpicker a.oe_kanban_color_9').click();
        assert.ok(writeOnColor, "should write on the color field");
        $firstRecord = kanban.$('.o_kanban_record:first()'); // First record is reloaded here
        assert.ok($firstRecord.is('.oe_kanban_color_9'),
            "the first record should have the color 9");

        kanban.destroy();
    });

    QUnit.test('archive kanban column, when active field is not in the view', function (assert) {
        assert.expect(3);

        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var writeOnActive;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                '<field name="product_id"/>' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
            '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'write' && 'active' in args.args[1]) {
                    writeOnActive = true;
                }
                return this._super.apply(this, arguments);
            },
        });

        var $first_column = kanban.$('.o_kanban_group:first()');
        assert.strictEqual($first_column.find('.o_kanban_record').length, 2,
            "there should be 2 partners in first column");
        $first_column.find('.o_column_archive').click();
        assert.ok(writeOnActive, "should write on the active field");
        assert.strictEqual($first_column.find('.o_kanban_record').length, 0,
            "there should not be partners anymore");

        kanban.destroy();
    });

    QUnit.test('load more records in column', function (assert) {
        assert.expect(12);

        var envIDs = [1, 2, 4]; // the ids that should be in the environment during this test
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates>' +
            '</kanban>',
            groupBy: ['bar'],
            viewOptions: {
                limit: 2,
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    assert.step([args.limit, args.offset]);
                }
                return this._super.apply(this, arguments);
            },
            intercepts:{
                env_updated: function (event) {
                    assert.deepEqual(event.data.ids, envIDs,
                        "should notify the environment with the correct ids");
                },
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 2,
            "there should be 2 records in the column");

        // load more
        envIDs = [1, 2, 3, 4]; // id 3 will be loaded
        kanban.$('.o_kanban_group:eq(1)').find('.o_kanban_load_more').click();

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 3,
            "there should now be 3 records in the column");

        assert.verifySteps([[2, undefined], [2, undefined], [2, 2]],
            "the records should be correctly fetched");

        // reload
        envIDs = [1, 2, 4]; // first group is limited again to 2 records
        kanban.reload();
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 2,
            "there should be 2 records in the column after reload");

        kanban.destroy();
    });

    QUnit.test('load more records in column with x2many', function (assert) {
        assert.expect(10);

        this.data.partner.records[0].category_ids = [7];
        this.data.partner.records[1].category_ids = [];
        this.data.partner.records[2].category_ids = [6];
        this.data.partner.records[3].category_ids = [];

        // record [2] will be loaded after

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                '<templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="category_ids"/>' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</t></templates>' +
            '</kanban>',
            groupBy: ['bar'],
            viewOptions: {
                limit: 2,
            },
            mockRPC: function (route, args) {
                if (args.model === 'category' && args.method === 'read') {
                    assert.step(args.args[0]);
                }
                if (route === '/web/dataset/search_read') {
                    if (args.limit) {
                        assert.strictEqual(args.limit, 2,
                            "the limit should be correctly set");
                    }
                    if (args.offset) {
                        assert.strictEqual(args.offset, 2,
                            "the offset should be correctly set at load more");
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 2,
            "there should be 2 records in the column");

        assert.verifySteps([[7]], "only the appearing category should be fetched");

        // load more
        kanban.$('.o_kanban_group:eq(1)').find('.o_kanban_load_more').click();

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 3,
            "there should now be 3 records in the column");

        assert.verifySteps([[7], [6]], "the other categories should not be fetched");

        kanban.destroy();
    });

    QUnit.test('update buttons after column creation', function (assert) {
        assert.expect(2);

        this.data.partner.records = [];

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['product_id'],
        });

        assert.ok(kanban.$buttons.find('.o-kanban-button-new').hasClass('btn-default'),
            "Create button shouldn't be highlighted");

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('new column');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        assert.ok(kanban.$buttons.find('.o-kanban-button-new').hasClass('btn-primary'),
            "Create button should now be highlighted");
        kanban.destroy();
    });

    QUnit.test('group_by_tooltip option when grouping on a many2one', function (assert) {
        assert.expect(12);
        delete this.data.partner.records[3].product_id;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban default_group_by="bar">' +
                    '<field name="bar"/>' +
                    '<field name="product_id" '+
                        'options=\'{"group_by_tooltip": {"name": "Kikou"}}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/read') {
                    assert.strictEqual(args.args[0].length, 2,
                        "read on two groups");
                    assert.deepEqual(args.args[1], ['display_name', 'name'],
                        "should read on specified fields on the group by relation");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(kanban.$('.o_kanban_view').hasClass('o_kanban_grouped'),
                        "should have classname 'o_kanban_grouped'");
        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have " + 2 + " columns");

        // simulate an update coming from the searchview, with another groupby given
        kanban.update({groupBy: ['product_id']});
        assert.strictEqual(kanban.$('.o_kanban_group').length, 3, "should have " + 3 + " columns");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(3) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.ok(kanban.$('.o_kanban_group:first span.o_column_title:contains(Undefined)').length,
            "first column should have a default title for when no value is provided");
        assert.strictEqual(kanban.$('.o_kanban_group:first .o_kanban_header_title').data('original-title'),
            "<p>1 records</p>",
            "first column should have a tooltip with the number of records, but not" +
            "the group_by_tooltip title and the many2one field value since it has no value");
        assert.ok(kanban.$('.o_kanban_group:eq(1) span.o_column_title:contains(hello)').length,
            "second column should have a title with a value from the many2one");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_header_title').data('original-title'),
            "<p>2 records</p><div>Kikou<br>hello</div>",
            "second column should have a tooltip with the number of records, the group_by_tooltip title and many2one field value");

        kanban.destroy();
    });

    QUnit.test('move a record then put it again in the same column', function (assert) {
        assert.expect(6);

        this.data.partner.records = [];

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                '</t></templates></kanban>',
            groupBy: ['product_id'],
        });

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('column1');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('column2');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        kanban.$('.o_kanban_group:eq(1) .o_kanban_quick_add i').click();
        var $quickCreate = kanban.$('.o_kanban_group:eq(1) .o_kanban_quick_create');
        $quickCreate.find('input').val('new partner');
        $quickCreate.find('button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 0,
                        "column should contain 0 record");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 1,
                        "column should contain 1 records");

        var $record = kanban.$('.o_kanban_group:eq(1) .o_kanban_record:eq(0)');
        var $group = kanban.$('.o_kanban_group:eq(0)');
        testUtils.dragAndDrop($record, $group);

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 1,
                        "column should contain 1 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 0,
                        "column should contain 0 records");

        $record = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)');
        $group = kanban.$('.o_kanban_group:eq(1)');

        testUtils.dragAndDrop($record, $group);

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 0,
                        "column should contain 0 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 1,
                        "column should contain 1 records");
        kanban.destroy();
    });

    QUnit.test('resequence a record twice', function (assert) {
        assert.expect(10);

        this.data.partner.records = [];

        var nbResequence = 0;
        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="product_id"/>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                '</t></templates></kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route) {
                if (route === '/web/dataset/resequence') {
                    nbResequence++;
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        });

        kanban.$('.o_column_quick_create').click();
        kanban.$('.o_column_quick_create input').val('column1');
        kanban.$('.o_column_quick_create button.o_kanban_add').click();

        kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_add i').click();
        var $quickCreate = kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_create');
        $quickCreate.find('input').val('record1');
        $quickCreate.find('button.o_kanban_add').click();

        kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_add i').click();
        $quickCreate = kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_create');
        $quickCreate.find('input').val('record2');
        $quickCreate.find('button.o_kanban_add').click();

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record2",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record1",
                        "records should be correctly ordered");

        var $record1 = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)');
        var $record2 = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)');
        testUtils.dragAndDrop($record1, $record2, {position: 'top'});

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record1",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record2",
                        "records should be correctly ordered");

        testUtils.dragAndDrop($record2, $record1, {position: 'top'});

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record2",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record1",
                        "records should be correctly ordered");
        assert.strictEqual(nbResequence, 2, "should have resequenced twice");
        kanban.destroy();
    });

    QUnit.test('don\'t fold column quick create after creation', function (assert) {
        assert.expect(2);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });

        // add a new column
        kanban.$('.o_kanban_group:first .o_kanban_quick_add').click();
        var $quickCreate = kanban.$('.o_kanban_quick_create');
        $quickCreate.find('input').val('new partner');
        $quickCreate.find('button.o_kanban_add').click();
        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a 'new partner' column");

        assert.strictEqual(kanban.$('.o_kanban_add:visible').length, 1,
            "the add button should still be visible");
        kanban.destroy();
    });

    QUnit.test('basic support for widgets', function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
            },
            start: function () {
                this.$el.text(JSON.stringify(this.data));
            },
        });
        widgetRegistry.add('test', MyWidget);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<t t-esc="record.foo.value"/>' +
                    '<field name="foo" blip="1"/>' +
                    '<widget name="test"/>' +
                    '</div>' +
                '</t></templates></kanban>',
        });

        assert.strictEqual(kanban.$('.o_widget:eq(2)').text(), '{"foo":"gnap","id":3}',
            "widget should have been instantiated");

        kanban.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('column progressbars properly work', function (assert) {
        assert.expect(2);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="bar"/>' +
                    '<field name="int_field"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        assert.strictEqual(kanban.$('.o_kanban_counter').length, this.data.product.records.length,
            "kanban counters should have been created");

        assert.strictEqual(parseInt(kanban.$('.o_kanban_counter_side').last().text()), 36,
            "counter should display the sum of int_field values");
        kanban.destroy();
    });

    QUnit.test('column progressbars: creating a new column should create a new progressbar', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="product_id"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['product_id'],
        });

        var nbProgressBars = kanban.$('.o_kanban_counter').length;

        // Create a new column: this should create an empty progressbar
        var $columnQuickCreate = kanban.$('.o_column_quick_create');
        $columnQuickCreate.click();
        $columnQuickCreate.find('input').val('test');
        $columnQuickCreate.find('.btn-primary').click();

        assert.strictEqual(kanban.$('.o_kanban_counter').length, nbProgressBars + 1,
            "a new column with a new column progressbar should have been created");

        kanban.destroy();
    });

    QUnit.test('column progressbars on quick create properly update counter', function (assert) {
        assert.expect(1);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        var initialCount = parseInt(kanban.$('.o_kanban_counter_side').eq(1).text());
        kanban.$('.o_kanban_quick_add').eq(1).click();
        kanban.$('.o_input').val('Test');
        kanban.$('.o_kanban_add').click();
        var lastCount = parseInt(kanban.$('.o_kanban_counter_side').eq(1).text());
        assert.strictEqual(lastCount, initialCount + 1,
            "kanban counters should have updated on quick create");

        kanban.destroy();
    });

    QUnit.test('keep adding quickcreate in first column after a record from this column was moved', function (assert) {
        assert.expect(2);

        var kanban = createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban on_create="quick_create">' +
                    '<field name="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['int_field'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    return $.when(true);
                }
                return this._super(route, args);
            },
        });

        var $quickCreateGroup;
        var $groups;
        _quickCreateAndTest();
        testUtils.dragAndDrop($groups.first().find('.o_kanban_record:first'), $groups.eq(1));
        _quickCreateAndTest();
        kanban.destroy();

        function _quickCreateAndTest() {
            kanban.$buttons.find('.o-kanban-button-new').click();
            $quickCreateGroup = kanban.$('.o_kanban_quick_create').closest('.o_kanban_group');
            $groups = kanban.$('.o_kanban_group');
            assert.strictEqual($quickCreateGroup[0], $groups[0],
                "quick create should have been added in the first column");
        }
    });
});

});
