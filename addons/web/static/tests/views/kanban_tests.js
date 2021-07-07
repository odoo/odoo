odoo.define('web.kanban_tests', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');
var KanbanColumnProgressBar = require('web.KanbanColumnProgressBar');
var kanbanExamplesRegistry = require('web.kanban_examples_registry');
var KanbanRenderer = require('web.KanbanRenderer');
var KanbanView = require('web.KanbanView');
var mixins = require('web.mixins');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var widgetRegistry = require('web.widget_registry');

var createActionManager = testUtils.createActionManager;
var makeTestPromise = testUtils.makeTestPromise;
var nextTick = testUtils.nextTick;
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
                    image: {string: "Image", type: "binary"},
                    displayed_image_id: {string: "cover", type: "many2one", relation: "ir.attachment"},
                },
                records: [
                    {id: 1, bar: true, foo: "yop", int_field: 10, qux: 0.4, product_id: 3, state: "abc", category_ids: [], 'image': 'R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA=='},
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
            'ir.attachment': {
                fields: {
                    mimetype: {type: "char"},
                    name: {type: "char"},
                    res_model: {type: "char"},
                    res_id: {type: "integer"},
                },
                records: [
                    {id: 1, name: "1.png", mimetype: 'image/png', res_model: 'partner', res_id: 1},
                    {id: 2, name: "2.png", mimetype: 'image/png', res_model: 'partner', res_id: 2},
                ]
            },
        };
    },
}, function () {

    QUnit.module('KanbanView');

    QUnit.test('basic ungrouped rendering', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<t t-esc="record.foo.value"/>' +
                    '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                assert.ok(args.context.bin_size,
                    "should not request direct binary payload");
                return this._super(route, args);
            },
        });

        assert.hasClass(kanban.$('.o_kanban_view'), 'o_kanban_ungrouped');
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_kanban_test');
        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);
        assert.containsN(kanban,'.o_kanban_ghost', 6);
        assert.containsOnce(kanban, '.o_kanban_record:contains(gnap)');
        kanban.destroy();
    });

    QUnit.test('basic grouped rendering', async function (assert) {
        assert.expect(13);

        var kanban = await createView({
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
                if (args.method === 'web_read_group') {
                    // the lazy option is important, so the server can fill in
                    // the empty groups
                    assert.ok(args.kwargs.lazy, "should use lazy read_group");
                }
                return this._super(route, args);
            },
        });

        assert.hasClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped');
        assert.hasClass(kanban.$('.o_kanban_view'), 'o_kanban_test');
        assert.containsN(kanban, '.o_kanban_group', 2);
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 3);

        // check available actions in kanban header's config dropdown
        assert.containsOnce(kanban, '.o_kanban_header:first .o_kanban_config .o_kanban_toggle_fold');
        assert.containsNone(kanban, '.o_kanban_header:first .o_kanban_config .o_column_edit');
        assert.containsNone(kanban, '.o_kanban_header:first .o_kanban_config .o_column_delete');
        assert.containsNone(kanban, '.o_kanban_header:first .o_kanban_config .o_column_archive_records');
        assert.containsNone(kanban, '.o_kanban_header:first .o_kanban_config .o_column_unarchive_records');

        // the next line makes sure that reload works properly.  It looks useless,
        // but it actually test that a grouped local record can be reloaded without
        // changing its result.
        await kanban.reload(kanban);
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 3);

        kanban.destroy();
    });

    QUnit.test('basic grouped rendering with active field (archivable by default)', async function (assert) {
        // var done = assert.async();
        assert.expect(10);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var action = { action_id: 1 }
        var envIDs = [1, 2, 3, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
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
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/action_archive') {
                    var partnerIDS = args.args[0];
                    var records = this.data.partner.records
                    _.each(partnerIDS, function(partnerID) {
                        _.find(records, function (record) {
                            return record.id === partnerID; 
                        }).active = false;
                    })

                    // Returning an action should not cause a traceback (opw-2259540)
                    return Promise.resolve(action);
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, action, "should trigger a do_action");
                    // Mocking the JS framework behavior
                    kanban.reload();
                    event.data.on_success(event.data.action);
                },
            }
        });

        // check archive/restore all actions in kanban header's config dropdown
        assert.containsOnce(kanban, '.o_kanban_header:first .o_kanban_config .o_column_archive_records');
        assert.containsOnce(kanban, '.o_kanban_header:first .o_kanban_config .o_column_unarchive_records');
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // archive the records of the first column
        assert.containsN(kanban, '.o_kanban_group:last .o_kanban_record', 3);

        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_archive_records'));
        assert.containsOnce(document.body, '.modal', "a confirm modal should be displayed");
        await testUtils.modal.clickButton('Cancel');
        assert.containsN(kanban, '.o_kanban_group:last .o_kanban_record', 3, "still last column should contain 3 records");
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_archive_records'));
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        await testUtils.modal.clickButton('Ok');
        assert.containsN(kanban, '.o_kanban_view .o_kanban_group', 1, "there should be one remaining column");
        envIDs = [4];
        assert.deepEqual(kanban.exportState().resIds, envIDs);
        kanban.destroy();
    });

    QUnit.test('basic grouped rendering with active field and archive enabled (archivable true)', async function (assert) {
        assert.expect(7);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var envIDs = [1, 2, 3, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" archivable="true">' +
                        '<field name="active"/>' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/action_archive') {
                    var partnerIDS = args.args[0];
                    var records = this.data.partner.records
                    _.each(partnerIDS, function(partnerID) {
                        _.find(records, function (record) {
                            return record.id === partnerID; 
                        }).active = false;
                    })
                    this.data.partner.records[0].active;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        // check archive/restore all actions in kanban header's config dropdown
        assert.ok(kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive_records').length, "should be able to archive all the records");
        assert.ok(kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive_records').length, "should be able to restore all the records");

        // archive the records of the first column
        assert.containsN(kanban, '.o_kanban_group:last .o_kanban_record', 3,
            "last column should contain 3 records");
        envIDs = [4];
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_archive_records'));
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        await testUtils.modal.clickButton('Cancel'); // Click on 'Cancel'
        assert.containsN(kanban, '.o_kanban_group:last .o_kanban_record', 3, "still last column should contain 3 records");
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_archive_records'));
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        await testUtils.modal.clickButton('Ok'); // Click on 'Ok'
        assert.containsNone(kanban, '.o_kanban_group:last .o_kanban_record', "last column should not contain any records");
        kanban.destroy();
    });

    QUnit.test('basic grouped rendering with active field and hidden archive buttons (archivable false)', async function (assert) {
        assert.expect(2);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var envIDs = [1, 2, 3, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" archivable="false">' +
                        '<field name="active"/>' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        // check archive/restore all actions in kanban header's config dropdown
        assert.strictEqual(
            kanban.$('.o_kanban_header:first .o_kanban_config .o_column_archive_records').length, 0,
            "should not be able to archive all the records");
        assert.strictEqual(
            kanban.$('.o_kanban_header:first .o_kanban_config .o_column_unarchive_records').length, 0,
            "should not be able to restore all the records");
        kanban.destroy();
    });

    QUnit.test('context can be used in kanban template', async function (assert) {
        assert.expect(2);

        var form = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div>' +
                                '<t t-if="context.some_key">' +
                                    '<field name="foo"/>' +
                                '</t>' +
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
            context: {some_key: 1},
            domain: [['id', '=', 1]],
        });

        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
            "there should be one record");
        assert.strictEqual(form.$('.o_kanban_record span:contains(yop)').length, 1,
            "condition in the kanban template should have been correctly evaluated");

        form.destroy();
    });

    QUnit.test('pager should be hidden in grouped mode', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
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
        await kanban.renderPager();

        assert.isNotVisible(kanban.pager.$el,
                        "pager should be hidden in grouped kanban");
        kanban.destroy();
    });

    QUnit.test('pager, ungrouped, with default limit', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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

        assert.isVisible(kanban.pager.$el,
                        "pager should be visible in ungrouped kanban");
        assert.strictEqual(kanban.pager.state.size, 4, "pager's size should be 4");
        kanban.destroy();
    });

    QUnit.test('pager, ungrouped, with limit given in options', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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

    QUnit.test('pager, ungrouped, with limit set on arch and given in options', async function (assert) {
        assert.expect(3);

        // the limit given in the arch should take the priority over the one given in options
        var kanban = await createView({
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

    QUnit.test('pager, ungrouped, deleting all records from last page should move to previous page', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" limit="3">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<div><a role="menuitem" type="delete" class="dropdown-item">Delete</a></div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates></kanban>',
        });

        assert.strictEqual(kanban.pager.$('.o_pager_counter').text().trim(), '1-3 / 4',
            "should have 2 pages and current page should be first page");
        // move to next page
        await testUtils.dom.click(kanban.pager.$('.o_pager_next'));
        assert.strictEqual(kanban.pager.$('.o_pager_counter').text().trim(), '4-4 / 4',
            "should be on second page");

        // delete a record
        await testUtils.dom.click(kanban.$('.o_kanban_record:first a:first'));
        await testUtils.dom.click($('.modal-footer button:first'));
        assert.strictEqual(kanban.pager.$('.o_pager_counter').text().trim(), '1-3 / 3',
            "should have 1 page only");

        kanban.destroy();
    });

    QUnit.test('create in grouped on m2o', async function (assert) {
        assert.expect(5);

        var kanban = await createView({
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

        assert.hasClass(kanban.$('.o_kanban_view'),'ui-sortable',
            "columns are sortable when grouped by a m2o field");
        assert.hasClass(kanban.$buttons.find('.o-kanban-button-new'),'btn-primary',
            "'create' button should be btn-primary for grouped kanban with at least one column");
        assert.hasClass(kanban.$('.o_kanban_view > div:last'),'o_column_quick_create',
            "column quick create should be enabled when grouped by a many2one field)");

        await testUtils.kanban.clickCreate(kanban); // Click on 'Create'
        assert.hasClass(kanban.$('.o_kanban_group:first() > div:nth(1)'),'o_kanban_quick_create',
            "clicking on create should open the quick_create in the first column");

        assert.ok(kanban.$('span.o_column_title:contains(hello)').length,
            "should have a column title with a value from the many2one");
        kanban.destroy();
    });

    QUnit.test('create in grouped on char', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
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

        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'ui-sortable',
            "columns aren't sortable when not grouped by a m2o field");
        assert.containsN(kanban, '.o_kanban_group', 3, "should have " + 3 + " columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first() .o_column_title').text(), "yop",
            "'yop' column should be the first column");
        assert.doesNotHaveClass(kanban.$('.o_kanban_view > div:last'), 'o_column_quick_create',
            "column quick create should be disabled when not grouped by a many2one field)");
        kanban.destroy();
    });

    QUnit.test('quick create record without quick_create_view', async function (assert) {
        assert.expect(16);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'name_create') {
                    assert.strictEqual(args.args[0], 'new partner',
                        "should send the correct value");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click on 'Create' -> should open the quick create in the first column
        await testUtils.kanban.clickCreate(kanban);
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');

        assert.strictEqual($quickCreate.length, 1,
            "should have a quick create element in the first column");
        assert.strictEqual($quickCreate.find('.o_form_view.o_xxs_form_view').length, 1,
            "should have rendered an XXS form view");
        assert.strictEqual($quickCreate.find('input').length, 1,
            "should have only one input");
        assert.hasClass($quickCreate.find('input'), 'o_required_modifier',
            "the field should be required");
        assert.strictEqual($quickCreate.find('input[placeholder=Title]').length, 1,
            "input placeholder should be 'Title'");

        // fill the quick create and validate
        await testUtils.fields.editInput($quickCreate.find('input'), 'new partner');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should contain two records");

        assert.verifySteps([
            'web_read_group', // initial read_group
            '/web/dataset/search_read', // initial search_read (first column)
            '/web/dataset/search_read', // initial search_read (second column)
            'default_get', // quick create
            'name_create', // should perform a name_create to create the record
            'read', // read the created record
            'default_get', // reopen the quick create automatically
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record with quick_create_view', async function (assert) {
        assert.expect(19);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    '<field name="state" widget="priority"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {
                        foo: 'new partner',
                        int_field: 4,
                        state: 'def',
                    }, "should send the correct values");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsOnce(kanban, '.o_cp_controller', 'should have one control panel');
        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click on 'Create' -> should open the quick create in the first column
        await testUtils.kanban.clickCreate(kanban);
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');

        assert.strictEqual($quickCreate.length, 1,
            "should have a quick create element in the first column");
        assert.strictEqual($quickCreate.find('.o_form_view.o_xxs_form_view').length, 1,
            "should have rendered an XXS form view");
        assert.containsOnce(kanban, '.o_cp_controller', 'should not have instantiated an extra control panel');
        assert.strictEqual($quickCreate.find('input').length, 2,
            "should have two inputs");
        assert.strictEqual($quickCreate.find('.o_field_widget').length, 3,
            "should have rendered three widgets");

        // fill the quick create and validate
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=foo]'), 'new partner');
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=int_field]'), '4');
        await testUtils.dom.click($quickCreate.find('.o_field_widget[name=state] .o_priority_star:first'));
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should contain two records");

        assert.verifySteps([
            'web_read_group', // initial read_group
            '/web/dataset/search_read', // initial search_read (first column)
            '/web/dataset/search_read', // initial search_read (second column)
            'load_views', // form view in quick create
            'default_get', // quick create
            'create', // should perform a create to create the record
            'read', // read the created record
            'load_views', // form view in quick create (is actually in cache)
            'default_get', // reopen the quick create automatically
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped on m2o (no quick_create_view)', async function (assert) {
        assert.expect(12);

        var kanban = await createView({
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
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'name_create') {
                    assert.strictEqual(args.args[0], 'new partner',
                        "should send the correct value");
                    assert.deepEqual(args.kwargs.context, {
                        default_product_id: 3,
                        default_qux: 2.5,
                    }, "should send the correct context");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                context: {default_qux: 2.5},
            },
        });

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should contain two records");

        // click on 'Create', fill the quick create and validate
        await testUtils.kanban.clickCreate(kanban);
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'new partner');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 3,
            "first column should contain three records");

        assert.verifySteps([
            'web_read_group', // initial read_group
            '/web/dataset/search_read', // initial search_read (first column)
            '/web/dataset/search_read', // initial search_read (second column)
            'default_get', // quick create
            'name_create', // should perform a name_create to create the record
            'read', // read the created record
            'default_get', // reopen the quick create automatically
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped on m2o (with quick_create_view)', async function (assert) {
        assert.expect(14);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    '<field name="state" widget="priority"/>' +
                '</form>',
            },
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {
                        foo: 'new partner',
                        int_field: 4,
                        state: 'def',
                    }, "should send the correct values");
                    assert.deepEqual(args.kwargs.context, {
                        default_product_id: 3,
                        default_qux: 2.5,
                    }, "should send the correct context");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                context: {default_qux: 2.5},
            },
        });

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should contain two records");

        // click on 'Create', fill the quick create and validate
        await testUtils.kanban.clickCreate(kanban);
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=foo]'), 'new partner');
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=int_field]'), '4');
        await testUtils.dom.click($quickCreate.find('.o_field_widget[name=state] .o_priority_star:first'));
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 3,
            "first column should contain three records");

        assert.verifySteps([
            'web_read_group', // initial read_group
            '/web/dataset/search_read', // initial search_read (first column)
            '/web/dataset/search_read', // initial search_read (second column)
            'load_views', // form view in quick create
            'default_get', // quick create
            'create', // should perform a create to create the record
            'read', // read the created record
            'load_views', // form view in quick create (is actually in cache)
            'default_get', // reopen the quick create automatically
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record with default values and onchanges', async function (assert) {
        assert.expect(11);

        this.data.partner.fields.int_field.default = 4;
        this.data.partner.onchanges = {
            foo: function (obj) {
                if (obj.foo) {
                    obj.int_field = 8;
                }
            },
        };

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        // click on 'Create' -> should open the quick create in the first column
        await testUtils.kanban.clickCreate(kanban);
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');

        assert.strictEqual($quickCreate.length, 1,
            "should have a quick create element in the first column");
        assert.strictEqual($quickCreate.find('.o_field_widget[name=int_field]').val(), '4',
            "default value should be set");

        // fill the 'foo' field -> should trigger the onchange
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=foo]'), 'new partner');

        assert.strictEqual($quickCreate.find('.o_field_widget[name=int_field]').val(), '8',
            "onchange should have been triggered");

        assert.verifySteps([
            'web_read_group', // initial read_group
            '/web/dataset/search_read', // initial search_read (first column)
            '/web/dataset/search_read', // initial search_read (second column)
            'load_views', // form view in quick create
            'default_get', // quick create
            'onchange', // default_get's onchange
            'onchange', // onchange due to 'foo' field change
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record with quick_create_view: modifiers', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo" required="1"/>' +
                    '<field name="int_field" attrs=\'{"invisible": [["foo", "=", false]]}\'/>' +
                '</form>',
            },
            groupBy: ['bar'],
        });

        // create a new record
        await testUtils.dom.click(kanban.$('.o_kanban_group:first .o_kanban_quick_add'));
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');

        assert.hasClass($quickCreate.find('.o_field_widget[name=foo]'),'o_required_modifier',
            "foo field should be required");
        assert.hasClass($quickCreate.find('.o_field_widget[name=int_field]'),'o_invisible_modifier',
            "int_field should be invisible");

        // fill 'foo' field
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=foo]'), 'new partner');

        assert.doesNotHaveClass($quickCreate.find('.o_field_widget[name=int_field]'), 'o_invisible_modifier',
            "int_field should now be visible");

        kanban.destroy();
    });

    QUnit.test('quick create record and change state in grouped mode', async function (assert) {
        assert.expect(1);

        this.data.partner.fields.kanban_state = {
            string: "Kanban State",
            type: "selection",
            selection: [["normal", "Grey"], ["done", "Green"], ["blocked", "Red"]],
        };

        var kanban = await createView({
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
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        var $quickAdd = kanban.$('.o_kanban_quick_create');
        $quickAdd.find('.o_input').val('Test');
        await testUtils.dom.click($quickAdd.find('.o_kanban_add'));

        // Select state in kanban
        await testUtils.dom.click(kanban.$('.o_status').first());
        await testUtils.dom.click(kanban.$('.o_selection .dropdown-item:first'));
        assert.hasClass(kanban.$('.o_status').first(),'o_status_green',
            "Kanban state should be done (Green)");
        kanban.destroy();
    });

    QUnit.test('quick create record: cancel and validate without using the buttons', async function (assert) {
        assert.expect(9);

        var nbRecords = 4;
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        assert.strictEqual(kanban.exportState().resIds.length, nbRecords);

        // click to add an element and cancel the quick creation by pressing ESC
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());

        var $quickCreate = kanban.$('.o_kanban_quick_create');
        assert.strictEqual($quickCreate.length, 1, "should have a quick create element");

        $quickCreate.find('input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ESCAPE,
            which: $.ui.keyCode.ESCAPE,
        }));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "should have destroyed the quick create element");

        // click to add and element and click outside, should cancel the quick creation
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "the quick create should be destroyed when the user clicks outside");

        // click to input and drag the mouse outside, should not cancel the quick creation
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.dom.triggerMouseEvent($quickCreate.find('input'), 'mousedown');
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed after clicking outside");

        // click to really add an element
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'new partner');

        // clicking outside should no longer destroy the quick create as it is dirty
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed");

        // confirm by pressing ENTER
        nbRecords = 5;
        $quickCreate.find('input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));

        await nextTick();
        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a partner");
        assert.strictEqual(_.last(this.data.partner.records).name, "new partner",
            "should have correct name");
        assert.strictEqual(kanban.exportState().resIds.length, nbRecords);

        kanban.destroy();
    });

    QUnit.test('quick create record: validate with ENTER', async function (assert) {
        // in this test, we accurately mock the behavior of the webclient by specifying a
        // fieldDebounce > 0, meaning that the changes in an InputField aren't notified to the model
        // on 'input' events, but they wait for the 'change' event (or a call to 'commitChanges',
        // e.g. triggered by a navigation event)
        // in this scenario, the call to 'commitChanges' actually does something (i.e. it notifies
        // the new value of the char field), whereas it does nothing if the changes are notified
        // directly
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            fieldDebounce: 5000,
        });

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should have 4 records at the beginning");

        // add an element and confirm by pressing ENTER
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        await testUtils.kanban.quickCreate(kanban, 'new partner', 'foo');
        // triggers a navigation event, leading to the 'commitChanges' and record creation

        assert.containsN(kanban, '.o_kanban_record', 5,
            "should have created a new record");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), '',
            "quick create should now be empty");

        kanban.destroy();
    });

    QUnit.test('quick create record: prevent multiple adds with ENTER', async function (assert) {
        assert.expect(9);

        var prom = makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            // add a fieldDebounce to accurately simulate what happens in the webclient: the field
            // doesn't notify the BasicModel that it has changed directly, as it waits for the user
            // to focusout or navigate (e.g. by pressing ENTER)
            fieldDebounce: 5000,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'create') {
                    assert.step('create');
                    return prom.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should have 4 records at the beginning");

        // add an element and press ENTER twice
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        var enterEvent = {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        };
        await testUtils.fields.editAndTrigger(
            kanban.$('.o_kanban_quick_create').find('input[name=foo]'),
            'new partner',
            ['input', $.Event('keydown', enterEvent), $.Event('keydown', enterEvent)]
        );

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should not have created the record yet");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), 'new partner',
            "quick create should not be empty yet");
        assert.hasClass(kanban.$('.o_kanban_quick_create'), 'o_disabled',
            "quick create should be disabled");

        prom.resolve();
        await nextTick();

        assert.containsN(kanban, '.o_kanban_record', 5,
            "should have created a new record");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), '',
            "quick create should now be empty");
        assert.doesNotHaveClass(kanban.$('.o_kanban_quick_create'), 'o_disabled',
            "quick create should be enabled");

        assert.verifySteps(['create']);

        kanban.destroy();
    });

    QUnit.test('quick create record: prevent multiple adds with Add clicked', async function (assert) {
        assert.expect(9);

        var prom = makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'create') {
                    assert.step('create');
                    return prom.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should have 4 records at the beginning");

        // add an element and click 'Add' twice
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create').find('input[name=foo]'), 'new partner');
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create').find('.o_kanban_add'));
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create').find('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should not have created the record yet");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), 'new partner',
            "quick create should not be empty yet");
        assert.hasClass(kanban.$('.o_kanban_quick_create'),'o_disabled',
            "quick create should be disabled");

        prom.resolve();

        await nextTick();
        assert.containsN(kanban, '.o_kanban_record', 5,
            "should have created a new record");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), '',
            "quick create should now be empty");
        assert.doesNotHaveClass(kanban.$('.o_kanban_quick_create'), 'o_disabled',
            "quick create should be enabled");

        assert.verifySteps(['create']);

        kanban.destroy();
    });

    QUnit.test('quick create record: prevent multiple adds with ENTER, with onchange', async function (assert) {
        assert.expect(13);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.int_field += (obj.foo ? 3 : 0);
            },
        };
        var shouldDelayOnchange = false;
        var prom = makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    assert.step('onchange');
                    if (shouldDelayOnchange) {
                        return Promise.resolve(prom).then(function () {
                            return result
                        });
                    }
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.deepEqual(_.pick(args.args[0], 'foo', 'int_field'), {
                        foo: 'new partner',
                        int_field: 3,
                    });
                }
                return result;
            },
            // add a fieldDebounce to accurately simulate what happens in the webclient: the field
            // doesn't notify the BasicModel that it has changed directly, as it waits for the user
            // to focusout or navigate (e.g. by pressing ENTER)
            fieldDebounce: 5000,
        });

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should have 4 records at the beginning");

        // add an element and press ENTER twice
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        shouldDelayOnchange = true;
        var enterEvent = {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        };

        await testUtils.fields.editAndTrigger(
            kanban.$('.o_kanban_quick_create').find('input[name=foo]'),
            'new partner',
            ['input', $.Event('keydown', enterEvent), $.Event('keydown', enterEvent)]
        );

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should not have created the record yet");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), 'new partner',
            "quick create should not be empty yet");
        assert.hasClass(kanban.$('.o_kanban_quick_create'),'o_disabled',
            "quick create should be disabled");

        prom.resolve();

        await nextTick();
        assert.containsN(kanban, '.o_kanban_record', 5,
            "should have created a new record");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), '',
            "quick create should now be empty");
        assert.doesNotHaveClass(kanban.$('.o_kanban_quick_create'), 'o_disabled',
            "quick create should be enabled");

        assert.verifySteps([
            'onchange', // default_get
            'onchange', // new partner
            'create',
            'onchange', // default_get
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create record: click Add to create, with delayed onchange', async function (assert) {
        assert.expect(13);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.int_field += (obj.foo ? 3 : 0);
            },
        };
        var shouldDelayOnchange = false;
        var prom = makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/><field name="int_field"/></div>' +
                    '</t></templates></kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    assert.step('onchange');
                    if (shouldDelayOnchange) {
                        return Promise.resolve(prom).then(function () {
                            return result
                        });
                    }
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.deepEqual(_.pick(args.args[0], 'foo', 'int_field'), {
                        foo: 'new partner',
                        int_field: 3,
                    });
                }
                return result;
            },
        });

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should have 4 records at the beginning");

        // add an element and click 'add'
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        shouldDelayOnchange = true;
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create').find('input[name=foo]'), 'new partner');
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create').find('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_record', 4,
            "should not have created the record yet");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), 'new partner',
            "quick create should not be empty yet");
        assert.hasClass(kanban.$('.o_kanban_quick_create'),'o_disabled',
            "quick create should be disabled");

        prom.resolve(); // the onchange returns

        await nextTick();
        assert.containsN(kanban, '.o_kanban_record', 5,
            "should have created a new record");
        assert.strictEqual(kanban.$('.o_kanban_quick_create input[name=foo]').val(), '',
            "quick create should now be empty");
        assert.doesNotHaveClass(kanban.$('.o_kanban_quick_create'), 'o_disabled',
            "quick create should be enabled");

        assert.verifySteps([
            'onchange', // default_get
            'onchange', // new partner
            'create',
            'onchange', // default_get
        ]);

        kanban.destroy();
    });

    QUnit.test('quick create when first column is folded', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        assert.doesNotHaveClass(kanban.$('.o_kanban_group:first'), 'o_column_folded',
            "first column should not be folded");

        // fold the first column
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold'));

        assert.hasClass(kanban.$('.o_kanban_group:first'),'o_column_folded',
            "first column should be folded");

        // click on 'Create' to open the quick create in the first column
        await testUtils.kanban.clickCreate(kanban);

        assert.doesNotHaveClass(kanban.$('.o_kanban_group:first'), 'o_column_folded',
            "first column should no longer be folded");
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');
        assert.strictEqual($quickCreate.length, 1,
            "should have added a quick create element in first column");

        // fold again the first column
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold'));

        assert.hasClass(kanban.$('.o_kanban_group:first'),'o_column_folded',
            "first column should be folded");
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "there should be no more quick create");

        kanban.destroy();
    });

    QUnit.test('quick create record: cancel when not dirty', async function (assert) {
        assert.expect(11);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click to add an element
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        // click again to add an element -> should have kept the quick create open
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have kept the quick create open");

        // click outside: should remove the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed");

        // click to reopen the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        // press ESC: should remove the quick create
        kanban.$('.o_kanban_quick_create input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ESCAPE,
            which: $.ui.keyCode.ESCAPE,
        }));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "quick create widget should have been removed");

        // click to reopen the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        // click on 'Discard': should remove the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "the quick create should be destroyed when the user clicks outside");

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should still contain one record");

        // click to reopen the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        // clicking on the quick create itself should keep it open
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create'));
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed when clicked on itself");


        kanban.destroy();
    });

    QUnit.test('quick create record: cancel when modal is opened', async function (assert) {
        assert.expect(3);

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<templates><t t-name="kanban-box">' +
                    '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                  '</kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="product_id"/>' +
                '</form>',
            },
            groupBy: ['bar'],
        });

        // click to add an element
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        kanban.$('.o_kanban_quick_create input')
            .val('test')
            .trigger('keyup')
            .trigger('focusout');
        await nextTick();

        // When focusing out of the many2one, a modal to add a 'product' will appear.
        // The following assertions ensures that a click on the body element that has 'modal-open'
        // will NOT close the quick create.
        // This can happen when the user clicks out of the input because of a race condition between
        // the focusout of the m2o and the global 'click' handler of the quick create.
        // Check odoo/odoo#61981 for more details.
        const $body = kanban.$el.closest('body');
        assert.hasClass($body, 'modal-open',
            "modal should be opening after m2o focusout");
        await testUtils.dom.click($body);
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "quick create should stay open while modal is opening");

        kanban.destroy();
    });

    QUnit.test('quick create record: cancel when dirty', async function (assert) {
        assert.expect(7);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click to add an element and edit it
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        var $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'some value');

        // click outside: should not remove the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_group .o_kanban_record:first'));
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should not have been destroyed");

        // press ESC: should remove the quick create
        $quickCreate.find('input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ESCAPE,
            which: $.ui.keyCode.ESCAPE,
        }));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "quick create widget should have been removed");

        // click to reopen quick create and edit it
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have open the quick create widget");

        $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'some value');

        // click on 'Discard': should remove the quick create
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create .o_kanban_cancel'));
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "the quick create should be destroyed when the user clicks outside");

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should still contain one record");

        kanban.destroy();
    });

    QUnit.test('quick create record and edit in grouped mode', async function (assert) {
        assert.expect(6);

        var newRecordID;
        var kanban = await createView({
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

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click to add and edit an element
        var $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());
        $quickCreate = kanban.$('.o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'new partner');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_edit'));

        assert.strictEqual(this.data.partner.records.length, 5,
            "should have created a partner");
        assert.strictEqual(_.last(this.data.partner.records).name, "new partner",
            "should have correct name");
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should now contain two records");

        kanban.destroy();
    });

    QUnit.test('quick create several records in a row', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click to add an element, fill the input and press ENTER
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());

        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should be open");

        await testUtils.kanban.quickCreate(kanban, 'new partner 1');

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should now contain two records");
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should still be open");

        // create a second element in a row
        await testUtils.kanban.quickCreate(kanban, 'new partner 2');

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 3,
            "first column should now contain three records");
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should still be open");

        kanban.destroy();
    });

    QUnit.test('quick create is disabled until record is created and read', async function (assert) {
        assert.expect(6);

        var prom = makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'read') {
                    return prom.then(_.constant(result));
                }
                return result;
            },
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain one record");

        // click to add a record, and add two in a row (first one will be delayed)
        await testUtils.dom.click(kanban.$('.o_kanban_header .o_kanban_quick_add i').first());

        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "the quick create should be open");

        await testUtils.kanban.quickCreate(kanban, 'new partner 1');

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should still contain one record");
        assert.containsOnce(kanban, '.o_kanban_quick_create.o_disabled',
            "quick create should be disabled");

        prom.resolve();

        await nextTick();
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should now contain two records");
        assert.strictEqual(kanban.$('.o_kanban_quick_create:not(.o_disabled)').length, 1,
            "quick create should be enabled");

        kanban.destroy();
    });

    QUnit.test('quick create record fail in grouped by many2one', async function (assert) {
        assert.expect(8);

        var kanban = await createView({
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
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event()
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "there should be 2 records in first column");

        await testUtils.kanban.clickCreate(kanban); // Click on 'Create'
        assert.hasClass(kanban.$('.o_kanban_group:first() > div:nth(1)'),'o_kanban_quick_create',
            "clicking on create should open the quick_create in the first column");

        await testUtils.kanban.quickCreate(kanban, 'test');

        assert.strictEqual($('.modal .o_form_view.o_form_editable').length, 1,
            "a form view dialog should have been opened (in edit)");
        assert.strictEqual($('.modal .o_field_many2one input').val(), 'hello',
            "the correct product_id should already be set");

        // specify a name and save
        await testUtils.fields.editInput($('.modal input[name=foo]'), 'test');
        await testUtils.modal.clickButton('Save');

        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 3,
            "there should be 3 records in first column");
        var $firstRecord = kanban.$('.o_kanban_group:first .o_kanban_record:first');
        assert.strictEqual($firstRecord.text(), 'test',
            "the first record of the first column should be the new one");
        assert.strictEqual(kanban.$('.o_kanban_quick_create:not(.o_disabled)').length, 1,
            "quick create should be enabled");

        kanban.destroy();
    });

    QUnit.test('quick create record is re-enabled after discard on failure', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
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
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event()
                    });
                }
                return this._super.apply(this, arguments);
            }
        });

        await testUtils.kanban.clickCreate(kanban);
        assert.containsOnce(kanban, '.o_kanban_quick_create',
            "should have a quick create widget");

        await testUtils.kanban.quickCreate(kanban, 'test');

        assert.strictEqual($('.modal .o_form_view.o_form_editable').length, 1,
            "a form view dialog should have been opened (in edit)");

        await testUtils.modal.clickButton('Discard');

        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.strictEqual(kanban.$('.o_kanban_quick_create:not(.o_disabled)').length, 1,
            "quick create widget should have been re-enabled");

        kanban.destroy();
    });

    QUnit.test('quick create record fails in grouped by char', async function (assert) {
        assert.expect(7);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            archs: {
                'partner,false,form': '<form>' +
                        '<field name="foo"/>' +
                    '</form>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event()
                    });
                }
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {foo: 'yop'},
                        "should write the correct value for foo");
                    assert.deepEqual(args.kwargs.context, {default_foo: 'yop', default_name: 'test'},
                        "should send the correct default value for foo");
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['foo'],
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "there should be 1 record in first column");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'test');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.strictEqual($('.modal .o_form_view.o_form_editable').length, 1,
            "a form view dialog should have been opened (in edit)");
        assert.strictEqual($('.modal .o_field_widget[name=foo]').val(), 'yop',
            "the correct default value for foo should already be set");
        await testUtils.modal.clickButton('Save');

        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "there should be 2 records in first column");

        kanban.destroy();
    });

    QUnit.test('quick create record fails in grouped by selection', async function (assert) {
        assert.expect(7);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="state"/></div>' +
                    '</t></templates>' +
                '</kanban>',
            archs: {
                'partner,false,form': '<form>' +
                        '<field name="state"/>' +
                    '</form>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    return Promise.reject({
                        message: {
                            code: 200,
                            data: {},
                            message: "Odoo server error",
                        },
                        event: $.Event()
                    });
                }
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {state: 'abc'},
                        "should write the correct value for state");
                    assert.deepEqual(args.kwargs.context, {default_state: 'abc', default_name: 'test'},
                        "should send the correct default value for state");
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['state'],
        });

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "there should be 1 record in first column");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'test');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.strictEqual($('.modal .o_form_view.o_form_editable').length, 1,
            "a form view dialog should have been opened (in edit)");
        assert.strictEqual($('.modal .o_field_widget[name=state]').val(), '"abc"',
            "the correct default value for state should already be set");

        await testUtils.modal.clickButton('Save');

        assert.strictEqual($('.modal').length, 0, "the modal should be closed");
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "there should be 2 records in first column");

        kanban.destroy();
    });

    QUnit.test('quick create record in empty grouped kanban', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    var result = {
                        groups: [
                            {__domain: [['product_id', '=', 3]], product_id_count: 0},
                            {__domain: [['product_id', '=', 5]], product_id_count: 0},
                        ],
                        length: 2,
                    };
                    return Promise.resolve(result);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_group', 2,
            "there should be 2 columns");
        assert.containsNone(kanban, '.o_kanban_record',
            "both columns should be empty");

        await testUtils.kanban.clickCreate(kanban);

        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_quick_create',
            "should have opened the quick create in the first column");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped on date(time) field', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['date'],
            intercepts: {
                switch_view: function (ev) {
                    assert.deepEqual(_.pick(ev.data, 'res_id', 'view_type'), {
                        res_id: undefined,
                        view_type: 'form',
                    }, "should trigger an event to open the form view (twice)");
                },
            },
        });

        assert.containsNone(kanban, '.o_kanban_header .o_kanban_quick_add i',
            "quick create should be disabled when grouped on a date field");

        // clicking on CREATE in control panel should not open a quick create
        await testUtils.kanban.clickCreate(kanban);
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "should not have opened the quick create widget");

        await kanban.reload({groupBy: ['datetime']});

        assert.containsNone(kanban, '.o_kanban_header .o_kanban_quick_add i',
            "quick create should be disabled when grouped on a datetime field");

        // clicking on CREATE in control panel should not open a quick create
        await testUtils.kanban.clickCreate(kanban);
        assert.containsNone(kanban, '.o_kanban_quick_create',
            "should not have opened the quick create widget");

        kanban.destroy();
    });

    QUnit.test('quick create record feature is properly enabled/disabled at reload', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['foo'],
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 3,
            "quick create should be enabled when grouped on a char field");

        await kanban.reload({groupBy: ['date']});

        assert.containsNone(kanban, '.o_kanban_header .o_kanban_quick_add i',
            "quick create should now be disabled (grouped on date field)");

        await kanban.reload({groupBy: ['bar']});

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 2,
            "quick create should be enabled again (grouped on boolean field)");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped by char field', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['foo'],
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    assert.deepEqual(args.kwargs.context, {default_foo: 'yop'},
                        "should send the correct default value for foo");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 3,
            "quick create should be enabled when grouped on a char field");
        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain 1 record");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'new record');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should now contain 2 records");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped by boolean field', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    assert.deepEqual(args.kwargs.context, {default_bar: true},
                        "should send the correct default value for bar");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 2,
            "quick create should be enabled when grouped on a boolean field");
        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) .o_kanban_record').length, 3,
            "second column (true) should contain 3 records");

        await testUtils.dom.click(kanban.$('.o_kanban_header:nth(1) .o_kanban_quick_add i'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'new record');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) .o_kanban_record').length, 4,
            "second column (true) should now contain 4 records");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped on selection field', async function (assert) {
        assert.expect(4);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="display_name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    assert.deepEqual(args.kwargs.context, {default_state: 'abc'},
                        "should send the correct default value for bar");
                }
                return this._super.apply(this, arguments);
            },
            groupBy: ['state'],
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 3,
            "quick create should be enabled when grouped on a selection field");
        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column (abc) should contain 1 record");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'new record');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column (abc) should contain 2 records");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped by char field (within quick_create_view)', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="foo"/>' +
                '</form>',
            },
            groupBy: ['foo'],
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {foo: 'yop'},
                        "should write the correct value for foo");
                    assert.deepEqual(args.kwargs.context, {default_foo: 'yop'},
                        "should send the correct default value for foo");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 3,
            "quick create should be enabled when grouped on a char field");
        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column should contain 1 record");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        assert.strictEqual(kanban.$('.o_kanban_quick_create input').val(), 'yop',
            "should have set the correct foo value by default");
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column should now contain 2 records");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped by boolean field (within quick_create_view)', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="bar"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="bar"/>' +
                '</form>',
            },
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {bar: true},
                        "should write the correct value for bar");
                    assert.deepEqual(args.kwargs.context, {default_bar: true},
                        "should send the correct default value for bar");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 2,
            "quick create should be enabled when grouped on a boolean field");
        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) .o_kanban_record').length, 3,
            "second column (true) should contain 3 records");

        await testUtils.dom.click(kanban.$('.o_kanban_header:nth(1) .o_kanban_quick_add i'));
        assert.ok(kanban.$('.o_kanban_quick_create .o_field_boolean input').is(':checked'),
            "should have set the correct bar value by default");
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.strictEqual(kanban.$('.o_kanban_group:nth(1) .o_kanban_record').length, 4,
            "second column (true) should now contain 4 records");

        kanban.destroy();
    });

    QUnit.test('quick create record in grouped by selection field (within quick_create_view)', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="state"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="state"/>' +
                '</form>',
            },
            groupBy: ['state'],
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {state: 'abc'},
                        "should write the correct value for state");
                    assert.deepEqual(args.kwargs.context, {default_state: 'abc'},
                        "should send the correct default value for state");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.containsN(kanban, '.o_kanban_header .o_kanban_quick_add i', 3,
            "quick create should be enabled when grouped on a selection field");
        assert.containsOnce(kanban, '.o_kanban_group:first .o_kanban_record',
            "first column (abc) should contain 1 record");

        await testUtils.dom.click(kanban.$('.o_kanban_header:first .o_kanban_quick_add i'));
        assert.strictEqual(kanban.$('.o_kanban_quick_create select').val(), '"abc"',
            "should have set the correct state value by default");
        await testUtils.dom.click(kanban.$('.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2,
            "first column (abc) should now contain 2 records");

        kanban.destroy();
    });

    QUnit.test('quick create record while adding a new column', async function (assert) {
        assert.expect(10);

        var def = testUtils.makeTestPromise();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'name_create' && args.model === 'product') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        assert.containsN(kanban, '.o_kanban_group', 2);
        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 2);

        // add a new column
        assert.containsOnce(kanban, '.o_column_quick_create');
        assert.isNotVisible(kanban.$('.o_column_quick_create input'));

        await testUtils.dom.click(kanban.$('.o_quick_create_folded'));

        assert.isVisible(kanban.$('.o_column_quick_create input'));

        await testUtils.fields.editInput(kanban.$('.o_column_quick_create input'), 'new column');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group', 2);

        // click to add a new record
        await testUtils.dom.click(kanban.$buttons.find('.o-kanban-button-new'));

        // should wait for the column to be created (and view to be re-rendered
        // before opening the quick create
        assert.containsNone(kanban, '.o_kanban_quick_create');

        // unlock column creation
        def.resolve();
        await testUtils.nextTick();
        assert.containsN(kanban, '.o_kanban_group', 3);
        assert.containsOnce(kanban, '.o_kanban_quick_create');

        // quick create record in first column
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'new record');
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create .o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group:first .o_kanban_record', 3);

        kanban.destroy();
    });

    QUnit.test('close a column while quick creating a record', async function (assert) {
        assert.expect(6);

        const def = testUtils.makeTestPromise();
        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `
                <kanban on_create="quick_create" quick_create_view="some_view_ref">
                    <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    </t></templates>
                </kanban>`,
            archs: {
                'partner,some_view_ref,form': '<form><field name="int_field"/></form>',
            },
            groupBy: ['product_id'],
            async mockRPC(route, args) {
                const result = this._super(...arguments);
                if (args.method === 'load_views') {
                    await def;
                }
                return result;
            },
        });

        assert.containsN(kanban, '.o_kanban_group', 2);
        assert.containsNone(kanban, '.o_column_folded');

        // click to quick create a new record in the first column (this operation is delayed)
        await testUtils.dom.click(kanban.$('.o_kanban_group:first .o_kanban_quick_add'));

        assert.containsNone(kanban, '.o_form_view');

        // click to fold the first column
        await testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:first'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold'));

        assert.containsOnce(kanban, '.o_column_folded');

        def.resolve();
        await testUtils.nextTick();

        assert.containsNone(kanban, '.o_form_view');
        assert.containsOnce(kanban, '.o_column_folded');

        kanban.destroy();
    });

    QUnit.test('quick create record: open on a column while another column has already one', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });

        // Click on quick create in first column
        await testUtils.dom.click(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_quick_add'));
        assert.containsOnce(kanban, '.o_kanban_quick_create');
        assert.containsOnce(kanban.$('.o_kanban_group:nth-child(1)'), '.o_kanban_quick_create');

        // Click on quick create in second column
        await testUtils.dom.click(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_quick_add'));
        assert.containsOnce(kanban, '.o_kanban_quick_create');
        assert.containsOnce(kanban.$('.o_kanban_group:nth-child(2)'), '.o_kanban_quick_create');

        // Click on quick create in first column once again
        await testUtils.dom.click(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_quick_add'));
        assert.containsOnce(kanban, '.o_kanban_quick_create');
        assert.containsOnce(kanban.$('.o_kanban_group:nth-child(1)'), '.o_kanban_quick_create');

        kanban.destroy();
    });

    QUnit.test('many2many_tags in kanban views', async function (assert) {
        assert.expect(12);

        this.data.partner.records[0].category_ids = [6, 7];
        this.data.partner.records[1].category_ids = [7, 8];
        this.data.category.records.push({
            id: 8,
            name: "hello",
            color: 0,
        });

        var kanban = await createView({
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
                    assert.deepEqual(_.pick(event.data, 'mode', 'model', 'res_id', 'view_type'), {
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
        assert.hasClass($first_record.find('.o_tag:first()'),'o_tag_color_2',
            'first tag should have color 2');
        assert.verifySteps(['/web/dataset/search_read', '/web/dataset/call_kw/category/read'],
            'two RPC should have been done (one search read and one read for the m2m)');

        // Checks that second records has only one tag as one should be hidden (color 0)
        assert.strictEqual(kanban.$('.o_kanban_record').eq(1).find('.o_tag').length, 1,
            'there should be only one tag in second record');

        // Write on the record using the priority widget to trigger a re-render in readonly
        await testUtils.dom.click(kanban.$('.o_field_widget.o_priority a.o_priority_star.fa-star-o').first());
        assert.verifySteps([
            '/web/dataset/call_kw/partner/write',
            '/web/dataset/call_kw/partner/read',
            '/web/dataset/call_kw/category/read'
        ], 'five RPCs should have been done (previous 2, 1 write (triggers a re-render), same 2 at re-render');
        assert.strictEqual(kanban.$('.o_kanban_record:first()').find('.o_field_many2manytags .o_tag').length, 2,
            'first record should still contain only 2 tags');

        // click on a tag (should trigger switch_view)
        await testUtils.dom.click(kanban.$('.o_tag:contains(gold):first'));

        kanban.destroy();
    });

    QUnit.test('Do not open record when clicking on `a` with `href`', async function (assert) {
        assert.expect(5);

        this.data.partner.records = [
            { id: 1, foo: 'yop' },
        ];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<templates>' +
                            '<t t-name="kanban-box">' +
                                '<div class="oe_kanban_global_click">' +
                                    '<field name="foo"/>' +
                                    '<div>' +
                                        '<a class="o_test_link" href="#">test link</a>' +
                                    '</div>' +
                                '</div>' +
                            '</t>' +
                        '</templates>' +
                    '</kanban>',
            intercepts: {
                // when clicking on a record in kanban view,
                // it switches to form view.
                switch_view: function () {
                    throw new Error("should not switch view");
                },
            },
        });

        var $record = kanban.$('.o_kanban_record:not(.o_kanban_ghost)');
        assert.strictEqual($record.length, 1,
            "should display a kanban record");

        var $testLink = $record.find('a');
        assert.strictEqual($testLink.length, 1,
            "should contain a link in the kanban record");
        assert.ok(!!$testLink[0].href,
            "link inside kanban record should have non-empty href");

        // Mocked views prevent accessing a link with href. This is intented
        // most of the time, but not in this test which specifically needs to
        // let the browser access a link with href.
        kanban.$el.off('click', 'a');
        // Prevent the browser default behaviour when clicking on anything.
        // This includes clicking on a `<a>` with `href`, so that it does not
        // change the URL in the address bar.
        // Note that we should not specify a click listener on 'a', otherwise
        // it may influence the kanban record global click handler to not open
        // the record.
        $(document.body).on('click.o_test', function (ev) {
            assert.notOk(ev.isDefaultPrevented(),
                "should not prevented browser default behaviour beforehand");
            assert.strictEqual(ev.target, $testLink[0],
                "should have clicked on the test link in the kanban record");
            ev.preventDefault();
        });

        await testUtils.dom.click($testLink);

        $(document.body).off('click.o_test');
        kanban.destroy();
    });

    QUnit.test('o2m loaded in only one batch', async function (assert) {
        assert.expect(9);

        this.data.subtask = {
            fields: {
                name: {string: 'Name', type: 'char'}
            },
            records: [
                {id: 1, name: "subtask #1"},
                {id: 2, name: "subtask #2"},
            ]
        };
        this.data.partner.fields.subtask_ids = {
            string: 'Subtasks',
            type: 'one2many',
            relation: 'subtask'
        };
        this.data.partner.records[0].subtask_ids = [1];
        this.data.partner.records[1].subtask_ids = [2];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="subtask_ids" widget="many2many_tags"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        await kanban.reload();
        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'read',
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'read',
        ]);
        kanban.destroy();
    });

    QUnit.test('m2m loaded in only one batch', async function (assert) {
        assert.expect(9);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="category_ids" widget="many2many_tags"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        await kanban.reload(kanban);
        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'read',
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'read',
        ]);
        kanban.destroy();
    });

    QUnit.test('fetch reference in only one batch', async function (assert) {
        assert.expect(9);

        this.data.partner.records[0].ref_product = 'product,3';
        this.data.partner.records[1].ref_product = 'product,5';
        this.data.partner.fields.ref_product = {
            string: "Reference Field",
            type: 'reference',
        };

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div class="oe_kanban_global_click">' +
                                '<field name="ref_product"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        await kanban.reload();
        assert.verifySteps([
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'name_get',
            'web_read_group',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            'name_get',
        ]);
        kanban.destroy();
    });

    QUnit.test('wait x2manys batch fetches to re-render', async function (assert) {
        assert.expect(7);
        var done = assert.async();

        var def = Promise.resolve();
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="category_ids" widget="many2many_tags"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                var result = this._super(route, args);
                if (args.method === 'read') {
                    return def.then(function() {
                        return result;
                    });
                }
                return result;
            },
        });

        def = testUtils.makeTestPromise();
        assert.containsN(kanban, '.o_tag', 2);
        assert.containsN(kanban, '.o_kanban_group', 2);
        kanban.update({groupBy: ['state']});
        def.then(async function () {
            assert.containsN(kanban, '.o_kanban_group', 2);
            await testUtils.nextTick();
            assert.containsN(kanban, '.o_kanban_group', 3);

            assert.containsN(kanban, '.o_tag', 2,
            'Should display 2 tags after update');
            assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_tag').text(),
                'gold', 'First category should be \'gold\'');
            assert.strictEqual(kanban.$('.o_kanban_group:eq(2) .o_tag').text(),
                'silver', 'Second category should be \'silver\'');
            kanban.destroy();
            done();
        });
        await testUtils.nextTick();
        def.resolve();
    });

    QUnit.test('can drag and drop a record from one column to the next', async function (assert) {
        assert.expect(9);

        // @todo: remove this resequenceDef whenever the jquery upgrade branch
        // is merged.  This is currently necessary to simulate the reality: we
        // need the click handlers to be executed after the end of the drag and
        // drop operation, not before.
        var resequenceDef = testUtils.makeTestPromise();

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        this.data.partner.fields.sequence = {type: 'number', string: "Sequence"};
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" on_create="quick_create">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div class="oe_kanban_global_click"><field name="foo"/>' +
                                '<t t-if="widget.editable"><span class="thisiseditable">edit</span></t>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.ok(true, "should call resequence");
                    return resequenceDef.then(_.constant(true));
                }
                return this._super(route, args);
            },
        });
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2);
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2);
        assert.containsN(kanban, '.thisiseditable', 4);
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        envIDs = [3, 2, 4, 1]; // first record of first column moved to the bottom of second column
        await testUtils.dom.dragAndDrop($record, $group, {withTrailingClick: true});

        resequenceDef.resolve();
        await testUtils.nextTick();
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 3);
        assert.containsN(kanban, '.thisiseditable', 4);
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        resequenceDef.resolve();
        kanban.destroy();
    });

    QUnit.test('drag and drop a record, grouped by selection', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
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
                    return Promise.resolve(true);
                }
                if (args.model === 'partner' && args.method === 'write') {
                    assert.deepEqual(args.args[1], {state: 'def'});
                }
                return this._super(route, args);
            },
        });
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record');

        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dom.dragAndDrop($record, $group);
        await nextTick();  // wait for resequence after drag and drop

        assert.containsNone(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2);
        kanban.destroy();
    });

    QUnit.test('prevent drag and drop of record if grouped by readonly', async function (assert) {
        assert.expect(12);

        this.data.partner.fields.foo.readonly = true;
        var kanban = await createView({
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
                    return Promise.resolve();
                }
                if (args.model === 'partner' && args.method === 'write') {
                    throw new Error('should not be draggable');
                }
                return this._super(route, args);
            },
        });
        // simulate an update coming from the searchview, with another groupby given
        await kanban.update({groupBy: ['state']});
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record');

        // drag&drop a record in another column
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dom.dragAndDrop($record, $group);
        await nextTick();  // wait for resequence after drag and drop
        // should not be draggable
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record');

        // simulate an update coming from the searchview, with another groupby given
        await kanban.update({groupBy: ['foo']});
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2);

        // drag&drop a record in another column
        $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dom.dragAndDrop($record, $group);
        await nextTick();  // wait for resequence after drag and drop
        // should not be draggable
        assert.containsOnce(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record');
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2);

        // drag&drop a record in the same column
        var $record1 = kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(0)');
        var $record2 = kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(1)');
        assert.strictEqual($record1.text(), "blipDEF", "first record should be DEF");
        assert.strictEqual($record2.text(), "blipGHI", "second record should be GHI");
        await testUtils.dom.dragAndDrop($record2, $record1, {position: 'top'});
        // should still be able to resequence
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(0)').text(), "blipGHI",
            "records should have been resequenced");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record:eq(1)').text(), "blipDEF",
            "records should have been resequenced");

        kanban.destroy();
    });

    QUnit.test('prevent drag and drop if grouped by date/datetime field', async function (assert) {
        assert.expect(5);

        this.data.partner.records[0].date = '2017-01-08';
        this.data.partner.records[1].date = '2017-01-09';
        this.data.partner.records[2].date = '2017-02-08';
        this.data.partner.records[3].date = '2017-02-10';

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['date:month'],
        });

        assert.strictEqual(kanban.$('.o_kanban_group').length, 2, "should have 2 columns");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 2,
                        "1st column should contain 2 records of January month");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length , 2,
                        "2nd column should contain 2 records of February month");

        // drag&drop a record in another column
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dragAndDrop($record, $group);

        // should not drag&drop record
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length , 2,
                        "Should remain same records in first column(2 records)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length , 2,
                        "Should remain same records in 2nd column(2 record)");
        kanban.destroy();
    });

    QUnit.test('completely prevent drag and drop if records_draggable set to false', async function (assert) {
        assert.expect(6);

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" records_draggable="false">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['product_id'],
        });

        // testing initial state
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2);
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2);
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // attempt to drag&drop a record in another column
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dom.dragAndDrop($record, $group, {withTrailingClick: true});

        // should not drag&drop record
        assert.containsN(kanban, '.o_kanban_group:nth-child(1) .o_kanban_record', 2,
            "First column should still contain 2 records");
        assert.containsN(kanban, '.o_kanban_group:nth-child(2) .o_kanban_record', 2,
            "Second column should still contain 2 records");
        assert.deepEqual(kanban.exportState().resIds, envIDs, "Records should not have moved");

        kanban.destroy();
    });

    QUnit.test('prevent drag and drop of record if onchange fails', async function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            product_id: function (obj) {}
        };

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<field name="product_id"/>' +
                        '<templates>' +
                            '<t t-name="kanban-box"><div>' +
                                '<field name="foo"/>' +
                                '<field name="product_id"/>' +
                            '</div></t>' +
                        '</templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/onchange') {
                    return Promise.reject({});
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        // drag&drop a record in another column
        var $record = kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record:first');
        var $group = kanban.$('.o_kanban_group:nth-child(2)');
        await testUtils.dom.dragAndDrop($record, $group);
        // should not be dropped, card should reset back to first column
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 2,
                        "column should now contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 records");

        kanban.destroy();
    });

    QUnit.test('kanban view with default_group_by', async function (assert) {
        assert.expect(7);
        this.data.partner.records.product_id = 1;
        this.data.product.records.push({id: 1, display_name: "third product"});

        var readGroupCount = 0;
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test" default_group_by="bar">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/web_read_group') {
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

        assert.hasClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped');
        assert.containsN(kanban, '.o_kanban_group', 2, "should have " + 2 + " columns");

        // simulate an update coming from the searchview, with another groupby given
        await kanban.update({groupBy: ['product_id']});
        assert.containsN(kanban, '.o_kanban_group', 2, "should now have " + 3 + " columns");

        // simulate an update coming from the searchview, removing the previously set groupby
        await kanban.update({groupBy: []});
        assert.containsN(kanban, '.o_kanban_group', 2, "should have " + 2 + " columns again");
        kanban.destroy();
    });

    QUnit.test('kanban view without groupby menu', async function (assert) {
        assert.expect(3);

        const searchMenuTypesOriginal = KanbanView.prototype.searchMenuTypes;
        KanbanView.prototype.searchMenuTypes = ['filter', 'favorite'];

        const actionManager = await createActionManager({
            actions: [{
                id: 11,
                name: 'Partners Action 11',
                res_model: 'partner',
                type: 'ir.actions.act_window',
                views: [[3, 'kanban']],
                search_view_id: [9, 'search'],
                context: {
                    search_default_itsName: 1,
                },
            }],
            archs: {
                'partner,3,kanban': `<kanban class="o_kanban_test" default_group_by="bar">
                    <field name="bar"/>
                    <templates><t t-name="kanban-box">
                    <div><field name="foo"/></div>
                    </t></templates></kanban>`,

                'partner,9,search': `<search>
                    <filter name="filterA" string="A" domain="[]"/>
                    <filter string="candle" name="itsName" context="{'group_by': 'foo'}"/>
                    </search>`,
            },
            data: this.data,
            mockRPC: function (route, args) {
                if (args.method === 'read_group') {
                    throw new Error("Should not do a read_group RPC");
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(11);
        await testUtils.nextTick();

        assert.doesNotHaveClass(actionManager.$('.o_kanban_view'), 'o_kanban_grouped');
        assert.containsNone(actionManager, '.o_control_panel .o_cp_right button:contains(Group By)',
            "there should not be groupby dropdown");
        await testUtils.fields.triggerKey('press', actionManager.$('.o_control_panel .o_searchview_input'), 97);
        assert.containsNone(actionManager,
            '.o_searchview .o_searchview_autocomplete:contains("Group by: candle")',
            `filter suggestion should not have Group by suggestion`
        );

        actionManager.destroy();
        KanbanView.prototype.searchMenuTypes = searchMenuTypesOriginal;
    });

    QUnit.test('kanban view with default_group_by and without groupby menu', async function (assert) {
        assert.expect(2);

        const searchMenuTypesOriginal = KanbanView.prototype.searchMenuTypes;
        KanbanView.prototype.searchMenuTypes = ['filter', 'favorite'];
        this.data.partner.records.product_id = 1;
        this.data.product.records.push({ id: 1, display_name: "third product" });

        const kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: `<kanban class="o_kanban_test" default_group_by="bar">
                        <field name="bar"/>
                        <templates><t t-name="kanban-box">
                        <div><field name="foo"/></div>
                    '</t></templates></kanban>`,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/web_read_group') {
                    throw new Error("Should not do a read_group RPC");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped');
        assert.containsNone(kanban, '.o_control_panel .o_cp_right button:contains(Group By)',
            "there should not be groupby dropdown");

        kanban.destroy();
        KanbanView.prototype.searchMenuTypes = searchMenuTypesOriginal;
    });

    QUnit.test('kanban view with create=False', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
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

    QUnit.test('clicking on a link triggers correct event', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div><a type="edit">Edit</a></div>' +
                '</t></templates></kanban>',
        });

        testUtils.mock.intercept(kanban, 'switch_view', function (event) {
            assert.deepEqual(event.data, {
                view_type: 'form',
                res_id: 1,
                mode: 'edit',
                model: 'partner',
            });
        });
        await testUtils.dom.click(kanban.$('a').first());
        kanban.destroy();
    });

    QUnit.test('environment is updated when (un)folding groups', async function (assert) {
        assert.expect(3);

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
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
        });

        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // fold the second group and check that the res_ids it contains are no
        // longer in the environment
        envIDs = [1, 3];
        await testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_kanban_toggle_fold'));
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // re-open the second group and check that the res_ids it contains are
        // back in the environment
        envIDs = [1, 3, 2, 4];
        await testUtils.dom.click(kanban.$('.o_kanban_group:last'));
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        kanban.destroy();
    });

    QUnit.test('create a column in grouped on m2o', async function (assert) {
        assert.expect(14);

        var nbRPCs = 0;
        var kanban = await createView({
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
                //Create column will call resequence to set column order
                if (route === '/web/dataset/resequence') {
                    assert.ok(true, "should call resequence");
                    return Promise.resolve(true);
                }
                return this._super(route, args);
            },
        });
        assert.containsOnce(kanban, '.o_column_quick_create', "should have a quick create column");
        assert.notOk(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should not be visible");

        await testUtils.dom.click(kanban.$('.o_quick_create_folded'));

        assert.ok(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should be visible");

        // discard the column creation and click it again
        await kanban.$('.o_column_quick_create input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ESCAPE,
            which: $.ui.keyCode.ESCAPE,
        }));
        assert.notOk(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should not be visible after discard");

        await testUtils.dom.click(kanban.$('.o_quick_create_folded'));
        assert.ok(kanban.$('.o_column_quick_create input').is(':visible'),
            "the input should be visible");

        await kanban.$('.o_column_quick_create input').val('new value').trigger('input');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        assert.strictEqual(kanban.$('.o_kanban_group:last span:contains(new value)').length, 1,
            "the last column should be the newly created one");
        assert.ok(_.isNumber(kanban.$('.o_kanban_group:last').data('id')),
            'the created column should have the correct id');
        assert.doesNotHaveClass(kanban.$('.o_kanban_group:last'), 'o_column_folded',
            'the created column should not be folded');

        // fold and unfold the created column, and check that no RPC is done (as there is no record)
        nbRPCs = 0;
        await testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_kanban_toggle_fold'));
        assert.hasClass(kanban.$('.o_kanban_group:last'),'o_column_folded',
            'the created column should now be folded');
        await testUtils.dom.click(kanban.$('.o_kanban_group:last'));
        assert.doesNotHaveClass(kanban.$('.o_kanban_group:last'), 'o_column_folded');
        assert.strictEqual(nbRPCs, 0, 'no rpc should have been done when folding/unfolding');

        // quick create a record
        await testUtils.kanban.clickCreate(kanban);
        assert.hasClass(kanban.$('.o_kanban_group:first() > div:nth(1)'),'o_kanban_quick_create',
            "clicking on create should open the quick_create in the first column");
        kanban.destroy();
    });

    QUnit.test('auto fold group when reach the limit', async function (assert) {
        assert.expect(9);

        var data = this.data;
        for (var i = 0; i < 12; i++) {
            data.product.records.push({
                id: (8 + i),
                name: ("column"),
            });
            data.partner.records.push({
                id: (20 + i),
                foo: ("dumb entry"),
                product_id: (8 + i),
            });
        }

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    return this._super.apply(this, arguments).then(function (result) {
                        result.groups[2].__fold = true;
                        result.groups[8].__fold = true;
                        return result;
                    });
                }
                return this._super(route, args);
            },
        });

        // we look if column are fold/unfold according what is expected
        assert.doesNotHaveClass(kanban.$('.o_kanban_group:nth-child(2)'), 'o_column_folded');
        assert.doesNotHaveClass(kanban.$('.o_kanban_group:nth-child(4)'), 'o_column_folded');
        assert.doesNotHaveClass(kanban.$('.o_kanban_group:nth-child(10)'), 'o_column_folded');
        assert.hasClass(kanban.$('.o_kanban_group:nth-child(3)'), 'o_column_folded');
        assert.hasClass(kanban.$('.o_kanban_group:nth-child(9)'), 'o_column_folded');

        // we look if columns are actually fold after we reached the limit
        assert.hasClass(kanban.$('.o_kanban_group:nth-child(13)'), 'o_column_folded');
        assert.hasClass(kanban.$('.o_kanban_group:nth-child(14)'), 'o_column_folded');

        // we look if we have the right count of folded/unfolded column
        assert.containsN(kanban, '.o_kanban_group:not(.o_column_folded)', 10);
        assert.containsN(kanban, '.o_kanban_group.o_column_folded', 4);

        kanban.destroy();
    });

    QUnit.test('hide and display help message (ESC) in kanban quick create', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
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
        });

        await testUtils.dom.click(kanban.$('.o_quick_create_folded'));
        assert.ok(kanban.$('.o_discard_msg').is(':visible'),
            'the ESC to discard message is visible');

        // click outside the column (to lose focus)
        await testUtils.dom.clickFirst(kanban.$('.o_kanban_header'));
        assert.notOk(kanban.$('.o_discard_msg').is(':visible'),
            'the ESC to discard message is no longer visible');

        kanban.destroy();
    });

    QUnit.test('delete a column in grouped on m2o', async function (assert) {
        assert.expect(37);

        testUtils.mock.patch(KanbanRenderer, {
            _renderGrouped: function () {
                this._super.apply(this, arguments);
                // set delay and revert animation time to 0 so dummy drag and drop works
                if (this.$el.sortable('instance')) {
                    this.$el.sortable('option', {delay: 0, revert: 0});
                }
            },
        });

        var resequencedIDs;

        var kanban = await createView({
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
                    return Promise.resolve(true);
                }
                if (args.method) {
                    assert.step(args.method);
                }
                return this._super(route, args);
            },
        });

        // check the initial rendering
        assert.containsN(kanban, '.o_kanban_group', 2, "should have two columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 3,
            'first column should be [3, "hello"]');
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 5,
            'second column should be [5, "xmo"]');
        assert.strictEqual(kanban.$('.o_kanban_group:last .o_column_title').text(), 'xmo',
            'second column should have correct title');
        assert.containsN(kanban, '.o_kanban_group:last .o_kanban_record', 2,
            "second column should have two records");

        // check available actions in kanban header's config dropdown
        assert.ok(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold').length,
                        "should be able to fold the column");
        assert.ok(kanban.$('.o_kanban_group:first .o_column_edit').length,
                        "should be able to edit the column");
        assert.ok(kanban.$('.o_kanban_group:first .o_column_delete').length,
                        "should be able to delete the column");
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_archive_records').length, "should not be able to archive all the records");
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_unarchive_records').length, "should not be able to restore all the records");

        // delete second column (first cancel the confirm request, then confirm)
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_delete'));
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        await testUtils.modal.clickButton('Cancel'); // click on cancel
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 5,
            'column [5, "xmo"] should still be there');
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_delete'));
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        await testUtils.modal.clickButton('Ok'); // click on confirm
        assert.strictEqual(kanban.$('.o_kanban_group:last').data('id'), 3,
            'last column should now be [3, "hello"]');
        assert.containsN(kanban, '.o_kanban_group', 2, "should still have two columns");
        assert.ok(!_.isNumber(kanban.$('.o_kanban_group:first').data('id')),
            'first column should have no id (Undefined column)');
        // check available actions on 'Undefined' column
        assert.ok(kanban.$('.o_kanban_group:first .o_kanban_toggle_fold').length,
                        "should be able to fold the column");
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_delete').length,
            'Undefined column could not be deleted');
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_edit').length,
            'Undefined column could not be edited');
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_archive_records').length, "Records of undefined column could not be archived");
        assert.ok(!kanban.$('.o_kanban_group:first .o_column_unarchive_records').length, "Records of undefined column could not be restored");
        assert.verifySteps(['web_read_group', 'unlink', 'web_read_group']);
        assert.strictEqual(kanban.renderer.widgets.length, 2,
            "the old widgets should have been correctly deleted");

        // test column drag and drop having an 'Undefined' column
        await testUtils.dom.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:last'), {position: 'right'}
        );
        assert.strictEqual(resequencedIDs, undefined,
            "resequencing require at least 2 not Undefined columns");
        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_quick_create_folded'));
        kanban.$('.o_column_quick_create input').val('once third column');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));
        var newColumnID = kanban.$('.o_kanban_group:last').data('id');
        await testUtils.dom.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:last'), {position: 'right'}
        );
        assert.deepEqual([3, newColumnID], resequencedIDs,
            "moving the Undefined column should not affect order of other columns");
        await testUtils.dom.dragAndDrop(
            kanban.$('.o_kanban_header_title:first'),
            kanban.$('.o_kanban_header_title:nth(1)'), {position: 'right'}
        );
        await nextTick(); // wait for resequence after drag and drop
        assert.deepEqual([newColumnID, 3], resequencedIDs,
            "moved column should be resequenced accordingly");
        assert.verifySteps(['name_create', 'read', 'read', 'read']);

        kanban.destroy();
        testUtils.mock.unpatch(KanbanRenderer);
    });

    QUnit.test('create a column, delete it and create another one', async function (assert) {
        assert.expect(5);

        var kanban = await createView({
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

        assert.containsN(kanban, '.o_kanban_group', 2, "should have two columns");

        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_quick_create_folded'));
        kanban.$('.o_column_quick_create input').val('new column 1');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group', 3, "should have two columns");

        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:last'));
        await testUtils.dom.click(kanban.$('.o_kanban_group:last .o_column_delete'));
        await testUtils.modal.clickButton('Ok');

        assert.containsN(kanban, '.o_kanban_group', 2, "should have twos columns");

        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_quick_create_folded'));
        kanban.$('.o_column_quick_create input').val('new column 2');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        assert.containsN(kanban, '.o_kanban_group', 3, "should have three columns");
        assert.strictEqual(kanban.$('.o_kanban_group:last span:contains(new column 2)').length, 1,
            "the last column should be the newly created one");
        kanban.destroy();
    });

    QUnit.test('edit a column in grouped on m2o', async function (assert) {
        assert.expect(12);

        var nbRPCs = 0;
        var kanban = await createView({
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
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group[data-id=5]'));
        await testUtils.dom.click(kanban.$('.o_kanban_group[data-id=5] .o_column_edit'));
        assert.containsOnce(document.body, '.modal .o_form_editable',
            "a form view should be open in a modal");
        assert.strictEqual($('.modal .o_form_editable input').val(), 'xmo',
            'the name should be "xmo"');
        await testUtils.fields.editInput($('.modal .o_form_editable input'), 'ged'); // change the value
        nbRPCs = 0;
        await testUtils.dom.click($('.modal-header .close'));
        assert.containsNone(document.body, '.modal');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'xmo',
            'title of the column should still be "xmo"');
        assert.strictEqual(nbRPCs, 0, 'no RPC should have been done');

        // edit the title of column [5, 'xmo'] and discard
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group[data-id=5]'));
        await testUtils.dom.click(kanban.$('.o_kanban_group[data-id=5] .o_column_edit'));
        await testUtils.fields.editInput($('.modal .o_form_editable input'), 'ged'); // change the value
        nbRPCs = 0;
        await testUtils.modal.clickButton('Discard');
        assert.containsNone(document.body, '.modal');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'xmo',
            'title of the column should still be "xmo"');
        assert.strictEqual(nbRPCs, 0, 'no RPC should have been done');

        // edit the title of column [5, 'xmo'] and save
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group[data-id=5]'));
        await testUtils.dom.click(kanban.$('.o_kanban_group[data-id=5] .o_column_edit'));
        await testUtils.fields.editInput($('.modal .o_form_editable input'), 'ged'); // change the value
        nbRPCs = 0;
        await testUtils.modal.clickButton('Save'); // click on save
        assert.ok(!$('.modal').length, 'the modal should be closed');
        assert.strictEqual(kanban.$('.o_kanban_group[data-id=5] .o_column_title').text(), 'ged',
            'title of the column should be "ged"');
        assert.strictEqual(nbRPCs, 4, 'should have done 1 write, 1 read_group and 2 search_read');
        kanban.destroy();
    });

    QUnit.test('edit a column propagates right context', async function (assert) {
        assert.expect(4);

        const kanban = await createView({
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
            session: {user_context: {lang: 'brol'}},
            mockRPC: function (route, args) {
                let context;
                if (route === '/web/dataset/search_read' && args.model === 'partner') {
                    context = args.context;
                    assert.strictEqual(context.lang, 'brol',
                        'lang is present in context for partner operations');
                }
                if (args.model === 'product') {
                    context = args.kwargs.context;
                    assert.strictEqual(context.lang, 'brol',
                        'lang is present in context for product operations');
                }
                return this._super.apply(this, arguments);
            },
        });
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group[data-id=5]'));
        await testUtils.dom.click(kanban.$('.o_kanban_group[data-id=5] .o_column_edit'));
        kanban.destroy();
    });

    QUnit.test('quick create column should be opened if there is no column', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            domain: [['foo', '=', 'norecord']],
        });

        assert.containsNone(kanban, '.o_kanban_group');
        assert.containsOnce(kanban, '.o_column_quick_create');
        assert.ok(kanban.$('.o_column_quick_create input').is(':visible'),
            "the quick create should be opened");

        kanban.destroy();
    });

    QUnit.test('quick create several columns in a row', async function (assert) {
        assert.expect(10);

        var kanban = await createView({
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
        });

        assert.containsN(kanban, '.o_kanban_group', 2,
            "should have two columns");
        assert.containsOnce(kanban, '.o_column_quick_create',
            "should have a ColumnQuickCreate widget");
        assert.containsOnce(kanban, '.o_column_quick_create .o_quick_create_folded:visible',
            "the ColumnQuickCreate should be folded");
        assert.containsNone(kanban, '.o_column_quick_create .o_quick_create_unfolded:visible',
            "the ColumnQuickCreate should be folded");

        // add a new column
        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_quick_create_folded'));
        assert.containsNone(kanban, '.o_column_quick_create .o_quick_create_folded:visible',
            "the ColumnQuickCreate should be unfolded");
        assert.containsOnce(kanban, '.o_column_quick_create .o_quick_create_unfolded:visible',
            "the ColumnQuickCreate should be unfolded");
        kanban.$('.o_column_quick_create input').val('New Column 1');
        await testUtils.dom.click(kanban.$('.o_column_quick_create .btn-primary'));
        assert.containsN(kanban, '.o_kanban_group', 3,
            "should now have three columns");

        // add another column
        assert.containsNone(kanban, '.o_column_quick_create .o_quick_create_folded:visible',
            "the ColumnQuickCreate should still be unfolded");
        assert.containsOnce(kanban, '.o_column_quick_create .o_quick_create_unfolded:visible',
            "the ColumnQuickCreate should still be unfolded");
        kanban.$('.o_column_quick_create input').val('New Column 2');
        await testUtils.dom.click(kanban.$('.o_column_quick_create .btn-primary'));
        assert.containsN(kanban, '.o_kanban_group', 4,
            "should now have four columns");

        kanban.destroy();
    });

    QUnit.test('quick create column and examples', async function (assert) {
        assert.expect(12);

        kanbanExamplesRegistry.add('test', {
            examples:[{
                name: "A first example",
                columns: ["Column 1", "Column 2", "Column 3"],
                description: "Some description",
            }, {
                name: "A second example",
                columns: ["Col 1", "Col 2"],
            }],
        });

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban examples="test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });

        assert.containsOnce(kanban, '.o_column_quick_create',
            "should have a ColumnQuickCreate widget");

        // open the quick create
        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_quick_create_folded'));

        assert.containsOnce(kanban, '.o_column_quick_create .o_kanban_examples:visible',
            "should have a link to see examples");

        // click to see the examples
        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_kanban_examples'));

        assert.strictEqual($('.modal .o_kanban_examples_dialog').length, 1,
            "should have open the examples dialog");
        assert.strictEqual($('.modal .o_kanban_examples_dialog_nav li').length, 2,
            "should have two examples (in the menu)");
        assert.strictEqual($('.modal .o_kanban_examples_dialog_nav a').text(),
            ' A first example  A second example ', "example names should be correct");
        assert.strictEqual($('.modal .o_kanban_examples_dialog_content .tab-pane').length, 2,
            "should have two examples");

        var $firstPane = $('.modal .o_kanban_examples_dialog_content .tab-pane:first');
        assert.strictEqual($firstPane.find('.o_kanban_examples_group').length, 3,
            "there should be 3 stages in the first example");
        assert.strictEqual($firstPane.find('h6').text(), 'Column 1Column 2Column 3',
            "column titles should be correct");
        assert.strictEqual($firstPane.find('.o_kanban_examples_description').text().trim(),
            "Some description", "the correct description should be displayed");

        var $secondPane = $('.modal .o_kanban_examples_dialog_content .tab-pane:nth(1)');
        assert.strictEqual($secondPane.find('.o_kanban_examples_group').length, 2,
            "there should be 2 stages in the second example");
        assert.strictEqual($secondPane.find('h6').text(), 'Col 1Col 2',
            "column titles should be correct");
        assert.strictEqual($secondPane.find('.o_kanban_examples_description').text().trim(),
            "", "there should be no description for the second example");

        kanban.destroy();
    });

    QUnit.test('quick create column and examples background with ghostColumns titles', async function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        kanbanExamplesRegistry.add('test', {
            ghostColumns: ["Ghost 1", "Ghost 2", "Ghost 3", "Ghost 4"],
            examples:[{
                name: "A first example",
                columns: ["Column 1", "Column 2", "Column 3"],
                description: "Some description",
            }, {
                name: "A second example",
                columns: ["Col 1", "Col 2"],
            }],
        });

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban examples="test">' +
                        '<field name="product_id"/>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
        });

        assert.containsOnce(kanban, '.o_kanban_example_background',
            "should have ExamplesBackground when no data");
        assert.strictEqual(kanban.$('.o_kanban_examples_group h6').text(), 'Ghost 1Ghost 2Ghost 3Ghost 4',
            "ghost title should be correct");
        assert.containsOnce(kanban, '.o_column_quick_create',
            "should have a ColumnQuickCreate widget");
        assert.containsOnce(kanban, '.o_column_quick_create .o_kanban_examples:visible',
            "should not have a link to see examples as there is no examples registered");

        kanban.destroy();
    });

    QUnit.test('quick create column and examples background without ghostColumns titles', async function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        var kanban = await createView({
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
        });

        assert.containsOnce(kanban, '.o_kanban_example_background',
            "should have ExamplesBackground when no data");
        assert.strictEqual(kanban.$('.o_kanban_examples_group h6').text(), 'Column 1Column 2Column 3Column 4',
            "ghost title should be correct");
        assert.containsOnce(kanban, '.o_column_quick_create',
            "should have a ColumnQuickCreate widget");
        assert.containsNone(kanban, '.o_column_quick_create .o_kanban_examples:visible',
            "should not have a link to see examples as there is no examples registered");

        kanban.destroy();
    });

    QUnit.test('if view was not grouped at start, it can be grouped and ungrouped', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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

        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped');
        await kanban.update({groupBy: ['product_id']});
        assert.hasClass(kanban.$('.o_kanban_view'),'o_kanban_grouped');
        await kanban.update({groupBy: []});
        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped');

        kanban.destroy();
    });

    QUnit.test('no content helper when no data', async function (assert) {
        assert.expect(3);

        var records = this.data.partner.records;

        this.data.partner.records = [];

        var kanban = await createView({
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

        assert.containsOnce(kanban, '.o_view_nocontent',
            "should display the no content helper");

        assert.strictEqual(kanban.$('.o_view_nocontent p.hello:contains(add a partner)').length, 1,
            "should have rendered no content helper from action");

        this.data.partner.records = records;
        await kanban.reload();

        assert.containsNone(kanban, '.o_view_nocontent',
            "should not display the no content helper");
        kanban.destroy();
    });

    QUnit.test('no nocontent helper for grouped kanban with empty groups', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
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
                if (args.method === 'web_read_group') {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    return this._super.apply(this, arguments).then(function (result) {
                        _.each(result.groups, function (group) {
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

        assert.containsN(kanban, '.o_kanban_group', 2,
            "there should be two columns");
        assert.containsNone(kanban, '.o_kanban_record',
            "there should be no records");

        kanban.destroy();
    });

    QUnit.test('no nocontent helper for grouped kanban with no records', async function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        var kanban = await createView({
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

        assert.containsNone(kanban, '.o_kanban_group',
            "there should be no columns");
        assert.containsNone(kanban, '.o_kanban_record',
            "there should be no records");
        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (we are in 'column creation mode')");
        assert.containsOnce(kanban, '.o_column_quick_create',
            "there should be a column quick create");
        kanban.destroy();
    });

    QUnit.test('no nocontent helper is shown when no longer creating column', async function (assert) {
        assert.expect(3);

        this.data.partner.records = [];

        var kanban = await createView({
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

        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (we are in 'column creation mode')");

        // creating a new column
        kanban.$('.o_column_quick_create .o_input').val('applejack');
        await testUtils.dom.click(kanban.$('.o_column_quick_create .o_kanban_add'));

        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (still in 'column creation mode')");

        // leaving column creation mode
        kanban.$('.o_column_quick_create .o_input').trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ESCAPE,
            which: $.ui.keyCode.ESCAPE,
        }));

        assert.containsOnce(kanban, '.o_view_nocontent',
            "there should be a nocontent helper");

        kanban.destroy();
    });

    QUnit.test('no nocontent helper is hidden when quick creating a column', async function (assert) {
        assert.expect(2);

        this.data.partner.records = [];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="foo"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    var result = {
                        groups: [
                            {__domain: [['product_id', '=', 3]], product_id_count: 0, product_id: [3, 'hello']},
                        ],
                        length: 1,
                    };
                    return Promise.resolve(result);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.containsOnce(kanban, '.o_view_nocontent',
            "there should be a nocontent helper");

        await testUtils.dom.click(kanban.$('.o_kanban_add_column'));

        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (we are in 'column creation mode')");

        kanban.destroy();
    });

    QUnit.test('remove nocontent helper after adding a record', async function (assert) {
        assert.expect(2);

        this.data.partner.records = [];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    var result = {
                        groups: [
                            {__domain: [['product_id', '=', 3]], product_id_count: 0, product_id: [3, 'hello']},
                        ],
                        length: 1,
                    };
                    return Promise.resolve(result);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.containsOnce(kanban, '.o_view_nocontent',
            "there should be a nocontent helper");

        // add a record
        await testUtils.dom.click(kanban.$('.o_kanban_quick_add'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create .o_input'), 'twilight sparkle');
        await testUtils.dom.click(kanban.$('.o_kanban_quick_create button.o_kanban_add'));

        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (there is now one record)");

        kanban.destroy();
    });

    QUnit.test('remove nocontent helper when adding a record', async function (assert) {
        assert.expect(2);

        this.data.partner.records = [];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    var result = {
                        groups: [
                            {__domain: [['product_id', '=', 3]], product_id_count: 0, product_id: [3, 'hello']},
                        ],
                        length: 1,
                    };
                    return Promise.resolve(result);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        assert.containsOnce(kanban, '.o_view_nocontent',
            "there should be a nocontent helper");

        // add a record
        await testUtils.dom.click(kanban.$('.o_kanban_quick_add'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create .o_input'), 'twilight sparkle');

        assert.containsNone(kanban, '.o_view_nocontent',
            "there should be no nocontent helper (there is now one record)");

        kanban.destroy();
    });

    QUnit.test('nocontent helper is displayed again after canceling quick create', async function (assert) {
        assert.expect(1);

        this.data.partner.records = [];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                            '<div><field name="name"/></div>' +
                        '</t></templates>' +
                    '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    var result = {
                        groups: [
                            {__domain: [['product_id', '=', 3]], product_id_count: 0, product_id: [3, 'hello']},
                        ],
                        length: 1,
                    };
                    return Promise.resolve(result);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                action: {
                    help: "No content helper",
                },
            },
        });

        // add a record
        await testUtils.dom.click(kanban.$('.o_kanban_quick_add'));

        await testUtils.dom.click(kanban.$('.o_kanban_view'));

        assert.containsOnce(kanban, '.o_view_nocontent',
            "there should be again a nocontent helper");

        kanban.destroy();
    });

    QUnit.test('nocontent helper for grouped kanban with no records with no group_create', async function (assert) {
        assert.expect(4);

        this.data.partner.records = [];

        var kanban = await createView({
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

        assert.containsNone(kanban, '.o_kanban_group',
            "there should be no columns");
        assert.containsNone(kanban, '.o_kanban_record',
            "there should be no records");
        assert.containsNone(kanban, '.o_view_nocontent',
            "there should not be a nocontent helper");
        assert.containsNone(kanban, '.o_column_quick_create',
            "there should not be a column quick create");
        kanban.destroy();
    });

    QUnit.test('buttons with modifiers', async function (assert) {
        assert.expect(2);

        this.data.partner.records[1].bar = false; // so that test is more complete

        var kanban = await createView({
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

        assert.containsOnce(kanban, ".o_btn_test_1",
            "kanban should have one buttons of type 1");
        assert.containsN(kanban, ".o_btn_test_2", 3,
            "kanban should have three buttons of type 2");
        kanban.destroy();
    });

    QUnit.test('button executes action and reloads', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
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
        testUtils.mock.intercept(kanban, 'execute_action', function (event) {
            count++;
            event.data.on_closed();
        });
        await testUtils.dom.click($('button[data-name="a1"]').first());
        assert.strictEqual(count, 1, "should have triggered a execute action");

        await testUtils.dom.click($('button[data-name="a1"]').first());
        assert.strictEqual(count, 1, "double-click on kanban actions should be debounced");

        assert.verifySteps([
            '/web/dataset/search_read',
            '/web/dataset/call_kw/partner/read'
        ], 'a read should be done after the call button to reload the record');

        kanban.destroy();
    });

    QUnit.test('button executes action and check domain', async function (assert) {
        assert.expect(2);

        var data = this.data;
        data.partner.fields.active = {string: "Active", type: "boolean", default: true};
        for (var k in this.data.partner.records) {
            data.partner.records[k].active = true;
        }

        var kanban = await createView({
            View: KanbanView,
            model: "partner",
            data: data,
            arch:
                '<kanban>' +
                    '<templates><div t-name="kanban-box">' +
                        '<field name="foo"/>' +
                        '<field name="active"/>' +
                        '<button type="object" name="a1" />' +
                        '<button type="object" name="toggle_active" />' +
                    '</div></templates>' +
                '</kanban>',
        });

        testUtils.mock.intercept(kanban, 'execute_action', function (event) {
            data.partner.records[0].active = false;
            event.data.on_closed();
        });

        assert.strictEqual(kanban.$('.o_kanban_record:contains(yop)').length, 1, "should display 'yop' record");
        await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) button[data-name="toggle_active"]'));
        assert.strictEqual(kanban.$('.o_kanban_record:contains(yop)').length, 0, "should remove 'yop' record from the view");

        kanban.destroy();
    });

    QUnit.test('button executes action with domain field not in view', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: "partner",
            data: this.data,
            domain: [['bar', '=', true]],
            arch:
                '<kanban>' +
                    '<templates><div t-name="kanban-box">' +
                        '<field name="foo"/>' +
                        '<button type="object" name="a1" />' +
                        '<button type="object" name="toggle_action" />' +
                    '</div></templates>' +
                '</kanban>',
        });

        testUtils.mock.intercept(kanban, 'execute_action', function (event) {
            event.data.on_closed();
        });

        try {
            await testUtils.dom.click(kanban.$('.o_kanban_record:contains(yop) button[data-name="toggle_action"]'));
            assert.strictEqual(true, true, 'Everything went fine');
        } catch (e) {
            assert.strictEqual(true, false, 'Error triggered at action execution');
        }
        kanban.destroy();
    });

    QUnit.test('rendering date and datetime', async function (assert) {
        assert.expect(2);

        this.data.partner.records[0].date = "2017-01-25";
        this.data.partner.records[1].datetime= "2016-12-12 10:55:05";

        var kanban = await createView({
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

    QUnit.test('evaluate conditions on relational fields', async function (assert) {
        assert.expect(3);

        this.data.partner.records[0].product_id = false;

        var kanban = await createView({
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

    QUnit.test('resequence columns in grouped by m2o', async function (assert) {
        assert.expect(6);
        this.data.product.fields.sequence = {string: "Sequence", type: "integer"};

        var envIDs = [1, 3, 2, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
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
        });

        assert.hasClass(kanban.$('.o_kanban_view'),'ui-sortable',
            "columns should be sortable");
        assert.containsN(kanban, '.o_kanban_group', 2,
            "should have two columns");
        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 3,
            "first column should be id 3 before resequencing");
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // there is a 100ms delay on the d&d feature (jquery sortable) for
        // kanban columns, making it hard to test. So we rather bypass the d&d
        // for this test, and directly call the event handler
        envIDs = [2, 4, 1, 3]; // the columns will be inverted
        kanban._onResequenceColumn({data: {ids: [5, 3]}});
        await nextTick();  // wait for resequencing before re-rendering
        await kanban.update({}, {reload: false}); // re-render without reloading

        assert.strictEqual(kanban.$('.o_kanban_group:first').data('id'), 5,
            "first column should be id 5 after resequencing");
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        kanban.destroy();
    });

    QUnit.test('properly evaluate more complex domains', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
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
                                '<button type="object" attrs="{\'invisible\':[\'|\', (\'bar\',\'=\',True), (\'category_ids\', \'!=\', [])]}" class="btn btn-primary float-right" name="channel_join_and_get_info">Join</button>' +
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
        });

        assert.containsOnce(kanban, 'button.oe_kanban_action_button',
            "only one button should be visible");
        kanban.destroy();
    });

    QUnit.test('edit the kanban color with the colorpicker', async function (assert) {
        assert.expect(5);

        var writeOnColor;

        this.data.category.records[0].color = 12;

        var kanban = await createView({
            View: KanbanView,
            model: 'category',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="color"/>' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div color="color">' +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
                                            '<span class="fa fa-bars fa-lg"/>' +
                                    '</a>' +
                                    '<ul class="dropdown-menu" role="menu">' +
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

        assert.containsNone(kanban, '.o_kanban_record.oe_kanban_color_12',
            "no record should have the color 12");
        assert.strictEqual($firstRecord.find('.oe_kanban_colorpicker').length, 1,
            "there should be a color picker");
        assert.strictEqual($firstRecord.find('.oe_kanban_colorpicker').children().length, 12,
            "the color picker should have 12 children (the colors)");

        // Set a color
        testUtils.kanban.toggleRecordDropdown($firstRecord);
        await testUtils.dom.click($firstRecord.find('.oe_kanban_colorpicker a.oe_kanban_color_9'));
        assert.ok(writeOnColor, "should write on the color field");
        $firstRecord = kanban.$('.o_kanban_record:first()'); // First record is reloaded here
        assert.ok($firstRecord.is('.oe_kanban_color_9'),
            "the first record should have the color 9");

        kanban.destroy();
    });

    QUnit.test('load more records in column', async function (assert) {
        assert.expect(13);

        var envIDs = [1, 2, 4]; // the ids that should be in the environment during this test
        var kanban = await createView({
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
                    assert.step(args.limit + ' - ' +  args.offset);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 2,
            "there should be 2 records in the column");
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // load more
        envIDs = [1, 2, 3, 4]; // id 3 will be loaded
        await testUtils.dom.click(kanban.$('.o_kanban_group:eq(1)').find('.o_kanban_load_more'));

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 3,
            "there should now be 3 records in the column");
        assert.verifySteps(['2 - undefined', '2 - undefined', '2 - 2'],
            "the records should be correctly fetched");
        assert.deepEqual(kanban.exportState().resIds, envIDs);

        // reload
        await kanban.reload();
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 3,
            "there should still be 3 records in the column after reload");
        assert.deepEqual(kanban.exportState().resIds, envIDs);
        assert.verifySteps(['4 - undefined', '2 - undefined']);

        kanban.destroy();
    });

    QUnit.test('load more records in column with x2many', async function (assert) {
        assert.expect(10);

        this.data.partner.records[0].category_ids = [7];
        this.data.partner.records[1].category_ids = [];
        this.data.partner.records[2].category_ids = [6];
        this.data.partner.records[3].category_ids = [];

        // record [2] will be loaded after

        var kanban = await createView({
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
                    assert.step(String(args.args[0]));
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

        assert.verifySteps(['7'], "only the appearing category should be fetched");

        // load more
        await testUtils.dom.click(kanban.$('.o_kanban_group:eq(1)').find('.o_kanban_load_more'));

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 3,
            "there should now be 3 records in the column");

        assert.verifySteps(['6'], "the other categories should not be fetched");

        kanban.destroy();
    });

    QUnit.test('update buttons after column creation', async function (assert) {
        assert.expect(2);

        this.data.partner.records = [];

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['product_id'],
        });

        assert.isNotVisible(kanban.$buttons.find('.o-kanban-button-new'),
            "Create button should be hidden");

        await testUtils.dom.click(kanban.$('.o_column_quick_create'));
        kanban.$('.o_column_quick_create input').val('new column');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        assert.isVisible(kanban.$buttons.find('.o-kanban-button-new'),
            "Create button should now be visible");
        kanban.destroy();
    });

    QUnit.test('group_by_tooltip option when grouping on a many2one', async function (assert) {
        assert.expect(12);
        delete this.data.partner.records[3].product_id;
        var kanban = await createView({
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

        assert.hasClass(kanban.$('.o_kanban_view'),'o_kanban_grouped',
                        "should have classname 'o_kanban_grouped'");
        assert.containsN(kanban, '.o_kanban_group', 2, "should have " + 2 + " columns");

        // simulate an update coming from the searchview, with another groupby given
        await kanban.update({groupBy: ['product_id']});
        assert.containsN(kanban, '.o_kanban_group', 3, "should have " + 3 + " columns");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(1) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(2) .o_kanban_record').length, 2,
                        "column should contain 2 record(s)");
        assert.strictEqual(kanban.$('.o_kanban_group:nth-child(3) .o_kanban_record').length, 1,
                        "column should contain 1 record(s)");
        assert.ok(kanban.$('.o_kanban_group:first span.o_column_title:contains(Undefined)').length,
            "first column should have a default title for when no value is provided");
        assert.ok(!kanban.$('.o_kanban_group:first .o_kanban_header_title').data('original-title'),
            "tooltip of first column should not defined, since group_by_tooltip title and the many2one field has no value");
        assert.ok(kanban.$('.o_kanban_group:eq(1) span.o_column_title:contains(hello)').length,
            "second column should have a title with a value from the many2one");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_header_title').data('original-title'),
            "<div>Kikou</br>hello</div>",
            "second column should have a tooltip with the group_by_tooltip title and many2one field value");

        kanban.destroy();
    });

    QUnit.test('move a record then put it again in the same column', async function (assert) {
        assert.expect(6);

        this.data.partner.records = [];

        var kanban = await createView({
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

        await testUtils.dom.click(kanban.$('.o_column_quick_create'));
        kanban.$('.o_column_quick_create input').val('column1');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        await testUtils.dom.click(kanban.$('.o_column_quick_create'));
        kanban.$('.o_column_quick_create input').val('column2');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        await testUtils.dom.click(kanban.$('.o_kanban_group:eq(1) .o_kanban_quick_add i'));
        var $quickCreate = kanban.$('.o_kanban_group:eq(1) .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'new partner');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 0,
                        "column should contain 0 record");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 1,
                        "column should contain 1 records");

        var $record = kanban.$('.o_kanban_group:eq(1) .o_kanban_record:eq(0)');
        var $group = kanban.$('.o_kanban_group:eq(0)');
        await testUtils.dom.dragAndDrop($record, $group);
        await nextTick();  // wait for resequencing after drag and drop

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 1,
                        "column should contain 1 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 0,
                        "column should contain 0 records");

        $record = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)');
        $group = kanban.$('.o_kanban_group:eq(1)');

        await testUtils.dom.dragAndDrop($record, $group);
        await nextTick();  // wait for resequencing after drag and drop

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 0,
                        "column should contain 0 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_record').length, 1,
                        "column should contain 1 records");
        kanban.destroy();
    });

    QUnit.test('resequence a record twice', async function (assert) {
        assert.expect(10);

        this.data.partner.records = [];

        var nbResequence = 0;
        var kanban = await createView({
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
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        await testUtils.dom.click(kanban.$('.o_column_quick_create'));
        kanban.$('.o_column_quick_create input').val('column1');
        await testUtils.dom.click(kanban.$('.o_column_quick_create button.o_kanban_add'));

        await testUtils.dom.click(kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_add i'));
        var $quickCreate = kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'record1');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        await testUtils.dom.click(kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_add i'));
        $quickCreate = kanban.$('.o_kanban_group:eq(0) .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('input'), 'record2');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record2",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record1",
                        "records should be correctly ordered");

        var $record1 = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)');
        var $record2 = kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)');
        await testUtils.dom.dragAndDrop($record1, $record2, {position: 'top'});

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record1",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record2",
                        "records should be correctly ordered");

        await testUtils.dom.dragAndDrop($record2, $record1, {position: 'top'});

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record').length, 2,
                        "column should contain 2 records");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)').text(), "record2",
                        "records should be correctly ordered");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(1)').text(), "record1",
                        "records should be correctly ordered");
        assert.strictEqual(nbResequence, 2, "should have resequenced twice");
        kanban.destroy();
    });

    QUnit.test('basic support for widgets', async function (assert) {
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

        var kanban = await createView({
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

    QUnit.test('subwidgets with on_attach_callback when changing record color', async function (assert) {
        assert.expect(3);

        var counter = 0;
        var MyTestWidget = AbstractField.extend({
            on_attach_callback: function () {
                counter++;
            },
        });
        fieldRegistry.add('test_widget', MyTestWidget);

        var kanban = await createView({
            View: KanbanView,
            model: 'category',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="color"/>' +
                        '<templates>' +
                            '<t t-name="kanban-box">' +
                                '<div color="color">' +
                                    '<div class="o_dropdown_kanban dropdown">' +
                                        '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
                                            '<span class="fa fa-bars fa-lg"/>' +
                                        '</a>' +
                                        '<ul class="dropdown-menu" role="menu">' +
                                            '<li>' +
                                                '<ul class="oe_kanban_colorpicker"/>' +
                                            '</li>' +
                                        '</ul>' +
                                    '</div>' +
                                '<field name="name" widget="test_widget"/>' +
                                '</div>' +
                            '</t>' +
                        '</templates>' +
                    '</kanban>',
        });

        // counter should be 2 as there are 2 records
        assert.strictEqual(counter, 2, "on_attach_callback should have been called twice");

        // set a color to kanban record
        var $firstRecord = kanban.$('.o_kanban_record:first()');
        testUtils.kanban.toggleRecordDropdown($firstRecord);
        await testUtils.dom.click($firstRecord.find('.oe_kanban_colorpicker a.oe_kanban_color_9'));

        // first record has replaced its $el with a new one
        $firstRecord = kanban.$('.o_kanban_record:first()');
        assert.hasClass($firstRecord, 'oe_kanban_color_9');
        assert.strictEqual(counter, 3, "on_attach_callback method should be called 3 times");

        delete fieldRegistry.map.test_widget;
        kanban.destroy();
    });

    QUnit.test('column progressbars properly work', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
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

        assert.containsN(kanban, '.o_kanban_counter', this.data.product.records.length,
            "kanban counters should have been created");

        assert.strictEqual(parseInt(kanban.$('.o_kanban_counter_side').last().text()), 36,
            "counter should display the sum of int_field values");
        kanban.destroy();
    });

    QUnit.test('column progressbars: "false" bar is clickable', async function (assert) {
        assert.expect(8);

        this.data.partner.records.push({id: 5, bar: true, foo: false, product_id: 5, state: "ghi"});
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="bar"/>' +
                    '<field name="int_field"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        assert.containsN(kanban, '.o_kanban_group', 2);
        assert.strictEqual(kanban.$('.o_kanban_counter:last .o_kanban_counter_side').text(), "4");
        assert.containsN(kanban, '.o_kanban_counter_progress:last .progress-bar', 4);
        assert.containsOnce(kanban, '.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]',
            "should have false kanban color");
        assert.hasClass(kanban.$('.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]'), 'bg-muted-full');

        await testUtils.dom.click(kanban.$('.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]'));

        assert.hasClass(kanban.$('.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]'), 'progress-bar-animated');
        assert.hasClass(kanban.$('.o_kanban_group:last'), 'o_kanban_group_show_muted');
        assert.strictEqual(kanban.$('.o_kanban_counter:last .o_kanban_counter_side').text(), "1");

        kanban.destroy();
    });

    QUnit.test('column progressbars: "false" bar with sum_field', async function (assert) {
        assert.expect(4);

        this.data.partner.records.push({id: 5, bar: true, foo: false, int_field: 15, product_id: 5, state: "ghi"});
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="bar"/>' +
                    '<field name="int_field"/>' +
                    '<field name="foo"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        assert.containsN(kanban, '.o_kanban_group', 2);
        assert.strictEqual(kanban.$('.o_kanban_counter:last .o_kanban_counter_side').text(), "51");

        await testUtils.dom.click(kanban.$('.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]'));

        assert.hasClass(kanban.$('.o_kanban_counter_progress:last .progress-bar[data-filter="__false"]'), 'progress-bar-animated');
        assert.strictEqual(kanban.$('.o_kanban_counter:last .o_kanban_counter_side').text(), "15");

        kanban.destroy();
    });

    QUnit.test('column progressbars should not crash in non grouped views', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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
            mockRPC: function (route, args) {
                assert.step(route)
                return this._super(route, args);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_record').text(), 'namenamenamename',
            "should have renderer 4 records");

        assert.verifySteps(['/web/dataset/search_read'], "no read on progress bar data is done");
        kanban.destroy();
    });

    QUnit.test('column progressbars: creating a new column should create a new progressbar', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
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
        await testUtils.dom.click($columnQuickCreate.find('.o_quick_create_folded'));
        $columnQuickCreate.find('input').val('test');
        await testUtils.dom.click($columnQuickCreate.find('.btn-primary'));

        assert.containsN(kanban, '.o_kanban_counter', nbProgressBars + 1,
            "a new column with a new column progressbar should have been created");

        kanban.destroy();
    });

    QUnit.test('column progressbars on quick create properly update counter', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
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

        var initialCount = parseInt(kanban.$('.o_kanban_counter_side:first').text());
        await testUtils.dom.click(kanban.$('.o_kanban_quick_add:first'));
        await testUtils.fields.editInput(kanban.$('.o_kanban_quick_create input'), 'Test');
        await testUtils.dom.click(kanban.$('.o_kanban_add'));
        var lastCount = parseInt(kanban.$('.o_kanban_counter_side:first').text());
        await nextTick();  // await update
        await nextTick();  // await read
        assert.strictEqual(lastCount, initialCount + 1,
            "kanban counters should have updated on quick create");

        kanban.destroy();
    });

    QUnit.test('column progressbars are working with load more', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            domain: [['bar', '=', true]],
            arch:
                '<kanban limit="1">' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="id"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        // we have 1 record shown, load 2 more and check it worked
        await testUtils.dom.click(kanban.$('.o_kanban_group').find('.o_kanban_load_more'));
        await testUtils.dom.click(kanban.$('.o_kanban_group').find('.o_kanban_load_more'));
        var shownIDs = _.map(kanban.$('.o_kanban_record'), function(record) {
            return parseInt(record.innerText);
        });
        assert.deepEqual(shownIDs, [1, 2, 3], "intended records are loaded");

        kanban.destroy();
    });

    QUnit.test('column progressbars on archiving records update counter', async function (assert) {
        assert.expect(4);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="active"/>' +
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
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/action_archive') {
                    var partnerIDS = args.args[0];
                    var records = this.data.partner.records
                    _.each(partnerIDS, function(partnerID) {
                        _.find(records, function (record) {
                            return record.id === partnerID; 
                        }).active = false;
                    })
                    this.data.partner.records[0].active;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_counter_side').text(), "36",
            "counter should contain the correct value");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_counter_progress > .progress-bar:first').data('originalTitle'), "1 yop",
            "the counter progressbars should be correctly displayed");

        // archive all records of the second columns
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:eq(1)'));
        await testUtils.dom.click(kanban.$('.o_column_archive_records:visible'));
        await testUtils.dom.click($('.modal-footer button:first'));

        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_counter_side').text(), "0",
            "counter should contain the correct value");
        assert.strictEqual(kanban.$('.o_kanban_group:eq(1) .o_kanban_counter_progress > .progress-bar:first').data('originalTitle'), "0 yop",
            "the counter progressbars should have been correctly updated");

        kanban.destroy();
    });

    QUnit.test('kanban with progressbars: correctly update env when archiving records', async function (assert) {
        assert.expect(2);

        // add active field on partner model and make all records active
        this.data.partner.fields.active = {string: 'Active', type: 'char', default: true};

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<field name="active"/>' +
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
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/action_archive') {
                    var partnerIDS = args.args[0];
                    var records = this.data.partner.records
                    _.each(partnerIDS, function(partnerID) {
                        _.find(records, function (record) {
                            return record.id === partnerID; 
                        }).active = false;
                    })
                    this.data.partner.records[0].active;
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.deepEqual(kanban.exportState().resIds, [1, 2, 3, 4]);

        // archive all records of the first column
        testUtils.kanban.toggleGroupSettings(kanban.$('.o_kanban_group:first'));
        await testUtils.dom.click(kanban.$('.o_column_archive_records:visible'));
        await testUtils.dom.click($('.modal-footer button:first'));

        assert.deepEqual(kanban.exportState().resIds, [1, 2, 3]);

        kanban.destroy();
    });

    QUnit.test('RPCs when (re)loading kanban view progressbars', async function (assert) {
        assert.expect(9);

        var kanban = await createView({
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
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
        });

        await kanban.reload();

        assert.verifySteps([
            // initial load
            'web_read_group',
            'read_progress_bar',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
            // reload
            'web_read_group',
            'read_progress_bar',
            '/web/dataset/search_read',
            '/web/dataset/search_read',
        ]);

        kanban.destroy();
    });

    QUnit.test('drag & drop records grouped by m2o with progressbar', async function (assert) {
        assert.expect(4);

        this.data.partner.records[0].product_id = false;

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="int_field"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['product_id'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    return Promise.resolve(true);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_counter_side').text(), "1",
            "counter should contain the correct value");

        await testUtils.dom.dragAndDrop(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)'), kanban.$('.o_kanban_group:eq(1)'));
        await nextTick();  // wait for update resulting from drag and drop
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_counter_side').text(), "0",
            "counter should contain the correct value");

        await testUtils.dom.dragAndDrop(kanban.$('.o_kanban_group:eq(1) .o_kanban_record:eq(2)'), kanban.$('.o_kanban_group:eq(0)'));
        await nextTick();  // wait for update resulting from drag and drop
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_counter_side').text(), "1",
            "counter should contain the correct value");

        await testUtils.dom.dragAndDrop(kanban.$('.o_kanban_group:eq(0) .o_kanban_record:eq(0)'), kanban.$('.o_kanban_group:eq(1)'));
        await nextTick();  // wait for update resulting from drag and drop
        assert.strictEqual(kanban.$('.o_kanban_group:eq(0) .o_kanban_counter_side').text(), "0",
            "counter should contain the correct value");

        kanban.destroy();
    });

    QUnit.test('progress bar subgroup count recompute', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch:
                '<kanban>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\'/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            groupBy: ['bar'],
        });

        var $secondGroup = kanban.$('.o_kanban_group:eq(1)');
        var initialCount = parseInt($secondGroup.find('.o_kanban_counter_side').text());
        assert.strictEqual(initialCount, 3,
            "Initial count should be Three");
        await testUtils.dom.click($secondGroup.find('.bg-success-full'));
        var lastCount = parseInt($secondGroup.find('.o_kanban_counter_side').text());
        assert.strictEqual(lastCount, 1,
            "kanban counters should vary according to what subgroup is selected");

        kanban.destroy();
    });

    QUnit.test('column progressbars on quick create with quick_create_view are updated', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban on_create="quick_create" quick_create_view="some_view_ref">' +
                    '<field name="int_field"/>' +
                    '<progressbar field="foo" colors=\'{"yop": "success", "gnap": "warning", "blip": "danger"}\' sum_field="int_field"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div>' +
                            '<field name="name"/>' +
                        '</div>' +
                    '</t></templates>' +
                '</kanban>',
            archs: {
                'partner,some_view_ref,form': '<form>' +
                    '<field name="int_field"/>' +
                '</form>',
            },
            groupBy: ['bar'],
        });

        var initialCount = parseInt(kanban.$('.o_kanban_counter_side:first').text());

        await testUtils.kanban.clickCreate(kanban);
        // fill the quick create and validate
        var $quickCreate = kanban.$('.o_kanban_group:first .o_kanban_quick_create');
        await testUtils.fields.editInput($quickCreate.find('.o_field_widget[name=int_field]'), '44');
        await testUtils.dom.click($quickCreate.find('button.o_kanban_add'));

        var lastCount = parseInt(kanban.$('.o_kanban_counter_side:first').text());
        assert.strictEqual(lastCount, initialCount + 44,
            "kanban counters should have been updated on quick create");

        kanban.destroy();
    });

    QUnit.test('keep adding quickcreate in first column after a record from this column was moved', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
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
            groupBy: ['foo'],
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    return Promise.resolve(true);
                }
                return this._super(route, args);
            },
        });

        var $quickCreateGroup;
        var $groups;
        await _quickCreateAndTest();
        await testUtils.dom.dragAndDrop($groups.first().find('.o_kanban_record:first'), $groups.eq(1));
        await _quickCreateAndTest();
        kanban.destroy();

        async function _quickCreateAndTest() {
            await testUtils.kanban.clickCreate(kanban);
            $quickCreateGroup = kanban.$('.o_kanban_quick_create').closest('.o_kanban_group');
            $groups = kanban.$('.o_kanban_group');
            assert.strictEqual($quickCreateGroup[0], $groups[0],
                "quick create should have been added in the first column");
        }
    });

    QUnit.test('test displaying image (URL, image field not set)', async function (assert) {
        assert.expect(1);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                      '<field name="id"/>' +
                      '<templates><t t-name="kanban-box"><div>' +
                          '<img t-att-src="kanban_image(\'partner\', \'image\', record.id.raw_value)"/>' +
                      '</div></t></templates>' +
                  '</kanban>',
        });

        // since the field image is not set, kanban_image will generate an URL
        var imageOnRecord = kanban.$('img[data-src*="/web/image"][data-src*="&id=1"]');
        assert.strictEqual(imageOnRecord.length, 1, "partner with image display image by url");

        kanban.destroy();
    });

    QUnit.test('test displaying image (binary & placeholder)', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                      '<field name="id"/>' +
                      '<field name="image"/>' +
                      '<templates><t t-name="kanban-box"><div>' +
                          '<img t-att-src="kanban_image(\'partner\', \'image\', record.id.raw_value)"/>' +
                      '</div></t></templates>' +
                  '</kanban>',
            mockRPC: function (route, args) {
                if (route === 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==') {
                    assert.ok("The view's image should have been fetched.");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        var placeholders = kanban.$('img[data-src$="/web/static/src/img/placeholder.png"]');
        assert.strictEqual(placeholders.length, this.data.partner.records.length - 1,
            "partner with no image should display the placeholder");

        kanban.destroy();
    });

    QUnit.test('test displaying image (for another record)', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                      '<field name="id"/>' +
                      '<field name="image"/>' +
                      '<templates><t t-name="kanban-box"><div>' +
                          '<img t-att-src="kanban_image(\'partner\', \'image\', 1)"/>' +
                      '</div></t></templates>' +
                  '</kanban>',
            mockRPC: function (route, args) {
                if (route === 'data:image/gif;base64,R0lGODlhAQABAAD/ACwAAAAAAQABAAACAA==') {
                    assert.ok("The view's image should have been fetched.");
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        // the field image is set, but we request the image for a specific id
        // -> for the record matching the ID, the base64 should be returned
        // -> for all the other records, the image should be displayed by url
        var imageOnRecord = kanban.$('img[data-src*="/web/image"][data-src*="&id=1"]');
        assert.strictEqual(imageOnRecord.length, this.data.partner.records.length - 1,
            "display image by url when requested for another record");

        kanban.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', async function (assert) {
        assert.expect(1);

        var instanceNumber = 0;
        testUtils.mock.patch(mixins.ParentedMixin, {
            init: function () {
                instanceNumber++;
                return this._super.apply(this, arguments);
            },
            destroy: function () {
                if (!this.isDestroyed()) {
                    instanceNumber--;
                }
                return this._super.apply(this, arguments);
            }
        });

        var params = {
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<field name="int_field"/>' +
                    '<field name="qux"/>' +
                    '<field name="product_id"/>' +
                    '<field name="category_ids"/>' +
                    '<field name="state"/>' +
                    '<field name="date"/>' +
                    '<field name="datetime"/>' +
                    '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates>' +
                '</kanban>',
        };

        var kanban = await createView(params);
        kanban.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        kanban = await createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        kanban.__destroy();

        // + 1 (parent)
        assert.strictEqual(instanceNumber, initialInstanceNumber + 1,
            "every widget must be destroyed exept the parent");

        kanban.destroy();

        testUtils.mock.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('grouped kanban becomes ungrouped when clearing domain then clearing groupby', async function (assert) {
        // in this test, we simulate that clearing the domain is slow, so that
        // clearing the groupby does not corrupt the data handled while
        // reloading the kanban view.
        assert.expect(4);

        var prom = makeTestPromise();

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            domain: [['foo', '=', 'norecord']],
            groupBy: ['bar'],
            mockRPC: function (route, args) {
                var result = this._super(route, args);
                if (args.method === 'web_read_group') {
                    var isFirstUpdate = _.isEmpty(args.kwargs.domain) &&
                                        args.kwargs.groupby &&
                                        args.kwargs.groupby[0] === 'bar';
                    if (isFirstUpdate) {
                        return prom.then(function () {
                            return result;
                        });
                    }
                }
                return result;
            },
        });

        assert.hasClass(kanban.$('.o_kanban_view'),'o_kanban_grouped',
            "the kanban view should be grouped");
        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'o_kanban_ungrouped',
            "the kanban view should not be ungrouped");

        kanban.update({domain: []}); // 1st update on kanban view
        kanban.update({groupBy: false}); // 2n update on kanban view
        prom.resolve(); // simulate slow 1st update of kanban view

        await nextTick();
        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'o_kanban_grouped',
            "the kanban view should not longer be grouped");
        assert.hasClass(kanban.$('.o_kanban_view'),'o_kanban_ungrouped',
            "the kanban view should have become ungrouped");

        kanban.destroy();
    });

    QUnit.test('quick_create on grouped kanban without column', async function (assert) {
        assert.expect(1);
        this.data.partner.records = [];
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            // force group_create to false, otherwise the CREATE button in control panel is hidden
            arch: '<kanban class="o_kanban_test" group_create="0" on_create="quick_create"><templates><t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="name"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            groupBy: ['product_id'],

            intercepts: {
                switch_view: function (event) {
                    assert.ok(true, "switch_view was called instead of quick_create");
                },
            },
        });
        await testUtils.kanban.clickCreate(kanban);
        kanban.destroy();
    });

    QUnit.test('keyboard navigation on kanban basic rendering', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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

        var $fisrtCard = kanban.$('.o_kanban_record:first');
        var $secondCard = kanban.$('.o_kanban_record:eq(1)');

        $fisrtCard.focus();
        assert.strictEqual(document.activeElement, $fisrtCard[0], "the kanban cards are focussable");

        $fisrtCard.trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT, }));
        assert.strictEqual(document.activeElement, $secondCard[0], "the second card should be focussed");

        $secondCard.trigger($.Event('keydown', { which: $.ui.keyCode.LEFT, keyCode: $.ui.keyCode.LEFT, }));
        assert.strictEqual(document.activeElement, $fisrtCard[0], "the first card should be focussed");
        kanban.destroy();
    });

    QUnit.test('keyboard navigation on kanban grouped rendering', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
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

        var $firstColumnFisrtCard = kanban.$('.o_kanban_record:first');
        var $secondColumnFirstCard = kanban.$('.o_kanban_group:eq(1) .o_kanban_record:first');
        var $secondColumnSecondCard = kanban.$('.o_kanban_group:eq(1) .o_kanban_record:eq(1)');

        $firstColumnFisrtCard.focus();

        //RIGHT should select the next column
        $firstColumnFisrtCard.trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT, keyCode: $.ui.keyCode.RIGHT, }));
        assert.strictEqual(document.activeElement, $secondColumnFirstCard[0], "RIGHT should select the first card of the next column");

        //DOWN should move up one card
        $secondColumnFirstCard.trigger($.Event('keydown', { which: $.ui.keyCode.DOWN, keyCode: $.ui.keyCode.DOWN, }));
        assert.strictEqual(document.activeElement, $secondColumnSecondCard[0], "DOWN should select the second card of the current column");

        //LEFT should go back to the first column
        $secondColumnSecondCard.trigger($.Event('keydown', { which: $.ui.keyCode.LEFT, keyCode: $.ui.keyCode.LEFT, }));
        assert.strictEqual(document.activeElement, $firstColumnFisrtCard[0], "LEFT should select the first card of the first column");

        kanban.destroy();
    });

    QUnit.test('keyboard navigation on kanban grouped rendering with empty columns', async function (assert) {
        assert.expect(2);

        var data = this.data;
        data.partner.records[1].state = "abc";

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: data,
            arch: '<kanban class="o_kanban_test">' +
                        '<field name="bar"/>' +
                        '<templates><t t-name="kanban-box">' +
                        '<div><field name="foo"/></div>' +
                    '</t></templates></kanban>',
            groupBy: ['state'],
            mockRPC: function (route, args) {
                if (args.method === 'web_read_group') {
                    // override read_group to return empty groups, as this is
                    // the case for several models (e.g. project.task grouped
                    // by stage_id)
                    return this._super.apply(this, arguments).then(function (result) {
                        // add 2 empty columns in the middle
                        result.groups.splice(1, 0, {state_count: 0, state: 'def',
                                           __domain: [["state", "=", "def"]]});
                        result.groups.splice(1, 0, {state_count: 0, state: 'def',
                                           __domain: [["state", "=", "def"]]});

                        // add 1 empty column in the beginning and the end
                        result.groups.unshift({state_count: 0, state: 'def',
                                        __domain: [["state", "=", "def"]]});
                        result.groups.push({state_count: 0, state: 'def',
                                    __domain: [["state", "=", "def"]]});
                        return result;
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        /**
         * DEF columns are empty
         *
         *    | DEF | ABC  | DEF | DEF | GHI  | DEF
         *    |-----|------|-----|-----|------|-----
         *    |     | yop  |     |     | gnap |
         *    |     | blip |     |     | blip |
         */
        var $yop = kanban.$('.o_kanban_record:first');
        var $gnap = kanban.$('.o_kanban_group:eq(4) .o_kanban_record:first');

        $yop.focus();

        //RIGHT should select the next column that has a card
        $yop.trigger($.Event('keydown', { which: $.ui.keyCode.RIGHT,
            keyCode: $.ui.keyCode.RIGHT, }));
        assert.strictEqual(document.activeElement, $gnap[0],
            "RIGHT should select the first card of the next column that has a card");

        //LEFT should go back to the first column that has a card
        $gnap.trigger($.Event('keydown', { which: $.ui.keyCode.LEFT,
            keyCode: $.ui.keyCode.LEFT, }));
        assert.strictEqual(document.activeElement, $yop[0],
            "LEFT should select the first card of the first column that has a card");

        kanban.destroy();
    });

    QUnit.test('keyboard navigation on kanban when the focus is on a link that ' +
     'has an action and the kanban has no oe_kanban_global_... class', async function (assert) {
        assert.expect(1);
        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                    '<div><a type="edit">Edit</a></div>' +
                '</t></templates></kanban>',
        });

        testUtils.mock.intercept(kanban, 'switch_view', function (event) {
            assert.deepEqual(event.data, {
                view_type: 'form',
                res_id: 1,
                mode: 'edit',
                model: 'partner',
            }, 'When selecting focusing a card and hitting ENTER, the first link or button is clicked');
        });
        kanban.$('.o_kanban_record').first().focus().trigger($.Event('keydown', {
            keyCode: $.ui.keyCode.ENTER,
            which: $.ui.keyCode.ENTER,
        }));
        await testUtils.nextTick();

        kanban.destroy();
    });

    QUnit.test('asynchronous rendering of a field widget (ungrouped)', async function (assert) {
        assert.expect(4);

        var fooFieldProm = makeTestPromise();
        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return fooFieldProm;
            },
            start: function () {
                this.$el.html('LOADED');
            },
        }));

        var kanbanController;
        testUtils.createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                        '<div><field name="foo" widget="asyncwidget"/></div>' +
                '</t></templates></kanban>',
        }).then(function (kanban) {
            kanbanController = kanban;
        });

        assert.strictEqual($('.o_kanban_record').length, 0, "kanban view is not ready yet");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($('.o_kanban_record').text(), "LOADEDLOADEDLOADEDLOADED");

        // reload with a domain
        fooFieldProm = makeTestPromise();
        kanbanController.reload({domain: [['id', '=', 1]]});
        await nextTick();

        assert.strictEqual($('.o_kanban_record').text(), "LOADEDLOADEDLOADEDLOADED");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($('.o_kanban_record').text(), "LOADED");

        kanbanController.destroy();
        delete fieldRegistry.map.asyncWidget;
    });

    QUnit.test('asynchronous rendering of a field widget (grouped)', async function (assert) {
        assert.expect(4);

        var fooFieldProm = makeTestPromise();
        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return fooFieldProm;
            },
            start: function () {
                this.$el.html('LOADED');
            },
        }));

        var kanbanController;
        testUtils.createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                        '<div><field name="foo" widget="asyncwidget"/></div>' +
                '</t></templates></kanban>',
            groupBy: ['foo'],
        }).then(function (kanban) {
            kanbanController = kanban;
        });

        assert.strictEqual($('.o_kanban_record').length, 0, "kanban view is not ready yet");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($('.o_kanban_record').text(), "LOADEDLOADEDLOADEDLOADED");

        // reload with a domain
        fooFieldProm = makeTestPromise();
        kanbanController.reload({domain: [['id', '=', 1]]});
        await nextTick();

        assert.strictEqual($('.o_kanban_record').text(), "LOADEDLOADEDLOADEDLOADED");

        fooFieldProm.resolve();
        await nextTick();
        assert.strictEqual($('.o_kanban_record').text(), "LOADED");

        kanbanController.destroy();
        delete fieldRegistry.map.asyncWidget;
    });
    QUnit.test('asynchronous rendering of a field widget with display attr', async function (assert) {
        assert.expect(3);

        var fooFieldDef = makeTestPromise();
        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return fooFieldDef;
            },
            start: function () {
                this.$el.html('LOADED');
            },
        }));

        var kanbanController;
        testUtils.createAsyncView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                        '<div><field name="foo" display="right" widget="asyncwidget"/></div>' +
                '</t></templates></kanban>',
        }).then(function (kanban) {
            kanbanController = kanban;
        });

        assert.containsNone(document.body, '.o_kanban_record');

        fooFieldDef.resolve();
        await nextTick();
        assert.strictEqual(kanbanController.$('.o_kanban_record').text(),
            "LOADEDLOADEDLOADEDLOADED");
        assert.hasClass(kanbanController.$('.o_kanban_record:first .o_field_char'), 'float-right');

        kanbanController.destroy();
        delete fieldRegistry.map.asyncWidget;
    });

    QUnit.test('asynchronous rendering of a widget', async function (assert) {
        assert.expect(2);

        var widgetDef = makeTestPromise();
        widgetRegistry.add('asyncwidget', Widget.extend({
            willStart: function () {
                return widgetDef;
            },
            start: function () {
                this.$el.html('LOADED');
            },
        }));

        var kanbanController;
        testUtils.createAsyncView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                        '<div><widget name="asyncwidget"/></div>' +
                '</t></templates></kanban>',
        }).then(function (kanban) {
            kanbanController = kanban;
        });

        assert.containsNone(document.body, '.o_kanban_record');

        widgetDef.resolve();
        await nextTick();
        assert.strictEqual(kanbanController.$('.o_kanban_record .o_widget').text(),
            "LOADEDLOADEDLOADEDLOADED");

        kanbanController.destroy();
        delete widgetRegistry.map.asyncWidget;
    });

    QUnit.test('update kanban with asynchronous field widget', async function (assert) {
        assert.expect(3);

        var fooFieldDef = makeTestPromise();
        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return fooFieldDef;
            },
            start: function () {
                this.$el.html('LOADED');
            },
        }));

        var kanban = await testUtils.createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test"><templates><t t-name="kanban-box">' +
                        '<div><field name="foo" widget="asyncwidget"/></div>' +
                '</t></templates></kanban>',
            domain: [['id', '=', '0']], // no record matches this domain
        });

        assert.containsNone(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        kanban.update({domain: []}); // this rendering will be async

        assert.containsNone(kanban, '.o_kanban_record:not(.o_kanban_ghost)');

        fooFieldDef.resolve();
        await nextTick();

        assert.strictEqual(kanban.$('.o_kanban_record').text(),
            "LOADEDLOADEDLOADEDLOADED");

        kanban.destroy();
        delete widgetRegistry.map.asyncWidget;
    });

    QUnit.test('set cover image', async function (assert) {
        assert.expect(6);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                    '<templates>' +
                        '<t t-name="kanban-box">' +
                            '<div>' +
                                '<field name="name"/>' +
                                '<div class="o_dropdown_kanban dropdown">' +
                                    '<a class="dropdown-toggle o-no-caret btn" data-toggle="dropdown" href="#">' +
                                        '<span class="fa fa-bars fa-lg"/>' +
                                    '</a>' +
                                    '<div class="dropdown-menu" role="menu">' +
                                        '<a type="set_cover" data-field="displayed_image_id" class="dropdown-item">Set Cover Image</a>'+
                                    '</div>' +
                                '</div>' +
                                '<div>'+
                                    '<field name="displayed_image_id" widget="attachment_image"/>'+
                                '</div>'+
                            '</div>' +
                        '</t>' +
                    '</templates>' +
                '</kanban>',
            mockRPC: function (route, args) {
                if (args.model === 'partner' && args.method === 'write') {
                    assert.step(String(args.args[0][0]));
                    return this._super(route, args);
                }
                return this._super(route, args);
            },
        });

        var $firstRecord = kanban.$('.o_kanban_record:first');
        testUtils.kanban.toggleRecordDropdown($firstRecord);
        await testUtils.dom.click($firstRecord.find('[data-type=set_cover]'));
        assert.containsNone($firstRecord, 'img', "Initially there is no image.");

        await testUtils.dom.click($('.modal').find("img[data-id='1']"));
        await testUtils.modal.clickButton('Select');
        assert.containsOnce(kanban, 'img[data-src*="/web/image/1"]');

        var $secondRecord = kanban.$('.o_kanban_record:nth(1)');
        testUtils.kanban.toggleRecordDropdown($secondRecord);
        await testUtils.dom.click($secondRecord.find('[data-type=set_cover]'));
        $('.modal').find("img[data-id='2']").dblclick();
        await testUtils.nextTick();
        assert.containsOnce(kanban, 'img[data-src*="/web/image/2"]');
        assert.verifySteps(["1", "2"], "should writes on both kanban records");

        kanban.destroy();
    });

    QUnit.test('ungrouped kanban with handle field', async function (assert) {
        assert.expect(4);

        var envIDs = [1, 2, 3, 4]; // the ids that should be in the environment during this test

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<field name="int_field" widget="handle" />' +
                    '<templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.deepEqual(args.ids, envIDs,
                        "should write the sequence in correct order");
                    return Promise.resolve(true);
                }
                return this._super(route, args);
            },
        });

        assert.hasClass(kanban.$('.o_kanban_view'), 'ui-sortable');
        assert.strictEqual(kanban.$('.o_kanban_record:not(.o_kanban_ghost)').text(),
            'yopblipgnapblip');

        var $record = kanban.$('.o_kanban_view .o_kanban_record:first');
        var $to = kanban.$('.o_kanban_view .o_kanban_record:nth-child(4)');
        envIDs = [2, 3, 4, 1]; // first record of moved after last one
        await testUtils.dom.dragAndDrop($record, $to, {position: "bottom"});

        assert.strictEqual(kanban.$('.o_kanban_record:not(.o_kanban_ghost)').text(),
            'blipgnapblipyop');

        kanban.destroy();
    });

    QUnit.test('ungrouped kanban without handle field', async function (assert) {
        assert.expect(3);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban>' +
                    '<templates><t t-name="kanban-box">' +
                    '<div>' +
                        '<field name="foo"/>' +
                    '</div>' +
                '</t></templates></kanban>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/resequence') {
                    assert.ok(false, "should not trigger a resequencing");
                }
                return this._super(route, args);
            },
        });

        assert.doesNotHaveClass(kanban.$('.o_kanban_view'), 'ui-sortable');
        assert.strictEqual(kanban.$('.o_kanban_record:not(.o_kanban_ghost)').text(),
            'yopblipgnapblip');

        var $draggedRecord = kanban.$('.o_kanban_view .o_kanban_record:first');
        var $to = kanban.$('.o_kanban_view .o_kanban_record:nth-child(4)');
        await testUtils.dom.dragAndDrop($draggedRecord, $to, {position: "bottom"});

        assert.strictEqual(kanban.$('.o_kanban_record:not(.o_kanban_ghost)').text(),
            'yopblipgnapblip');

        kanban.destroy();
    });

    QUnit.test('click on image field in kanban with oe_kanban_global_click', async function (assert) {
        assert.expect(2);

        var kanban = await createView({
            View: KanbanView,
            model: 'partner',
            data: this.data,
            arch: '<kanban class="o_kanban_test">' +
                        '<templates><t t-name="kanban-box">' +
                            '<div class="oe_kanban_global_click">' +
                                '<field name="image" widget="image"/>' +
                            '</div>' +
                        '</t></templates>' +
                    '</kanban>',
            mockRPC: function (route) {
                if (route.startsWith('data:image')) {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                switch_view: function (event) {
                    assert.deepEqual(_.pick(event.data, 'mode', 'model', 'res_id', 'view_type'), {
                        mode: 'readonly',
                        model: 'partner',
                        res_id: 1,
                        view_type: 'form',
                    }, "should trigger an event to open the clicked record in a form view");
                },
            },
        });

        assert.containsN(kanban, '.o_kanban_record:not(.o_kanban_ghost)', 4);

        await testUtils.dom.click(kanban.$('.o_field_image').first());

        kanban.destroy();
    });
});

});
