odoo.define('web.field_one_to_many_tests', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var ListRenderer = require('web.ListRenderer');
var relationalFields = require('web.relational_fields');
var testUtils = require('web.test_utils');
var fieldUtils = require('web.field_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

    QUnit.module('relational_fields', {
        beforeEach: function () {
            this.data = {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
                        p: { string: "one2many field", type: "one2many", relation: 'partner', relation_field: 'trululu' },
                        turtles: { string: "one2many turtle field", type: "one2many", relation: 'turtle', relation_field: 'turtle_trululu' },
                        trululu: { string: "Trululu", type: "many2one", relation: 'partner' },
                        timmy: { string: "pokemon", type: "many2many", relation: 'partner_type' },
                        product_id: { string: "Product", type: "many2one", relation: 'product' },
                        color: {
                            type: "selection",
                            selection: [['red', "Red"], ['black', "Black"]],
                            default: 'red',
                            string: "Color",
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: 'datetime' },
                        user_id: { string: "User", type: 'many2one', relation: 'user' },
                        reference: {
                            string: "Reference Field", type: 'reference', selection: [
                                ["product", "Product"], ["partner_type", "Partner Type"], ["partner", "Partner"]]
                        },
                    },
                    records: [{
                        id: 1,
                        display_name: "first record",
                        bar: true,
                        foo: "yop",
                        int_field: 10,
                        qux: 0.44,
                        p: [],
                        turtles: [2],
                        timmy: [],
                        trululu: 4,
                        user_id: 17,
                        reference: 'product,37',
                    }, {
                        id: 2,
                        display_name: "second record",
                        bar: true,
                        foo: "blip",
                        int_field: 9,
                        qux: 13,
                        p: [],
                        timmy: [],
                        trululu: 1,
                        product_id: 37,
                        date: "2017-01-25",
                        datetime: "2016-12-12 10:55:05",
                        user_id: 17,
                    }, {
                        id: 4,
                        display_name: "aaa",
                        bar: false,
                    }],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" }
                    },
                    records: [{
                        id: 37,
                        display_name: "xphone",
                    }, {
                        id: 41,
                        display_name: "xpad",
                    }]
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ]
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        turtle_foo: { string: "Foo", type: "char" },
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_qux: { string: "Qux", type: "float", digits: [16, 1], required: true, default: 1.5 },
                        turtle_description: { string: "Description", type: "text" },
                        turtle_trululu: { string: "Trululu", type: "many2one", relation: 'partner' },
                        turtle_ref: {
                            string: "Reference", type: 'reference', selection: [
                                ["product", "Product"], ["partner", "Partner"]]
                        },
                        product_id: { string: "Product", type: "many2one", relation: 'product', required: true },
                        partner_ids: { string: "Partner", type: "many2many", relation: 'partner' },
                    },
                    records: [{
                        id: 1,
                        display_name: "leonardo",
                        turtle_bar: true,
                        turtle_foo: "yop",
                        partner_ids: [],
                    }, {
                        id: 2,
                        display_name: "donatello",
                        turtle_bar: true,
                        turtle_foo: "blip",
                        turtle_int: 9,
                        partner_ids: [2, 4],
                    }, {
                        id: 3,
                        display_name: "raphael",
                        product_id: 37,
                        turtle_bar: false,
                        turtle_foo: "kawa",
                        turtle_int: 21,
                        turtle_qux: 9.8,
                        partner_ids: [],
                        turtle_ref: 'product,37',
                    }],
                    onchanges: {},
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: { string: "one2many partners field", type: "one2many", relation: 'partner', relation_field: 'user_id' },
                    },
                    records: [{
                        id: 17,
                        name: "Aline",
                        partner_ids: [1, 2],
                    }, {
                        id: 19,
                        name: "Christine",
                    }]
                },
            };
        }
    }, function () {
        QUnit.module('FieldOne2Many');

        QUnit.test('New record with a o2m also with 2 new records, ordered, and resequenced', function (assert) {
            assert.expect(3);

            // Needed to have two new records in a single stroke
            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [
                        [5],
                        [0, 0, { trululu: false }],
                        [0, 0, { trululu: false }],
                    ]
                }
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo" />' +
                    '<field name="p">' +
                    '<tree editable="bottom" default_order="int_field">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="trululu"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                viewOptions: {
                    mode: 'create',
                },
                mockRPC: function (route, args) {
                    assert.step(args.method + ' ' + args.model)
                    return this._super(route, args);
                },
            });

            // change the int_field through drag and drop
            // that way, we'll trigger the sorting and the name_get
            // of the lines of "p"
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            // Only those two should have been called
            // name_get on trululu would trigger an traceback
            assert.verifySteps(['default_get partner', 'onchange partner']);

            form.destroy();
        });

        QUnit.test('O2M List with pager, decoration and default_order: add and cancel adding', function (assert) {
            assert.expect(3);

            // The decoration on the list implies that its condition will be evaluated
            // against the data of the field (actual records *displayed*)
            // If one data is wrongly formed, it will crash
            // This test adds then cancels a record in a paged, ordered, and decorated list
            // That implies prefetching of records for sorting
            // and evaluation of the decoration against *visible records*

            this.data.partner.records[0].p = [2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom" limit="1" decoration-muted="foo != False" default_order="display_name">' +
                    '<field name="foo" invisible="1"/>' +
                    '<field name="display_name" />' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list .o_field_x2many_list_row_add a'));

            var $dataRows = form.$('.o_field_x2many_list .o_data_row');
            assert.equal($dataRows.length, 2,
                'There should be 2 rows');

            var $expectedSelectedRow = $dataRows.eq(1);
            var $actualSelectedRow = form.$('.o_selected_row');
            assert.equal($actualSelectedRow[0], $expectedSelectedRow[0],
                'The selected row should be the new one');

            // Cancel Creation
            var escapeKey = $.ui.keyCode.ESCAPE;
            $actualSelectedRow.find('input').trigger(
                $.Event('keydown', { which: escapeKey, keyCode: escapeKey }));

            $dataRows = form.$('.o_field_x2many_list .o_data_row');
            assert.equal($dataRows.length, 1,
                'There should be 1 row');

            form.destroy();
        });

        QUnit.test('O2M with parented m2o and domain on parent.m2o', function (assert) {
            assert.expect(3);

            /* records in an o2m can have a m2o pointing to themselves
                * in that case, a domain evaluation on that field followed by name_search
                * shouldn't send virtual_ids to the server
                */

            this.data.turtle.fields.parent_id = { string: "Parent", type: "many2one", relation: 'turtle' };
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="parent_id" />' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'turtle,false,form': '<form><field name="parent_id" domain="[(\'id\', \'in\', parent.turtles)]"/></form>',
                },
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/turtle/name_search') {
                        // We are going to pass twice here
                        // First time, we really have nothing
                        // Second time, a virtual_id has been created
                        assert.deepEqual(args.kwargs.args, [['id', 'in', []]]);
                    }
                    return this._super(route, args);
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list[name=turtles] .o_field_x2many_list_row_add a'));

            testUtils.fields.many2one.clickOpenDropdown('parent_id');
            testUtils.fields.many2one.clickHighlightedItem('parent_id');

            var $modal = $('.modal-content');

            testUtils.dom.click($modal.eq(1).find('.modal-footer .btn-primary').eq(0));
            testUtils.dom.click($modal.eq(0).find('.modal-footer .btn-primary').eq(1));

            assert.equal(form.$('.o_data_row').length, 1,
                'The main record should have the new record in its o2m');

            $modal = $('.modal-content');
            testUtils.dom.click($modal.find('.o_field_many2one input'));

            form.destroy();
        });

        QUnit.test('one2many list editable with cell readonly modifier', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[1].turtles = [1, 2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="turtles" invisible="1"/>' +
                    '<field name="foo" attrs="{&quot;readonly&quot; : [(&quot;turtles&quot;, &quot;!=&quot;, [])] }"/>' +
                    '<field name="qux" attrs="{&quot;readonly&quot; : [(&quot;turtles&quot;, &quot;!=&quot;, [])] }"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/write') {
                        assert.deepEqual(args.args[1].p[1][2], { foo: 'ff', qux: 99 },
                            'The right values should be written');
                    }
                    return this._super(route, args);
                }
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            var $targetInput = $('.o_selected_row .o_input[name=foo]');
            assert.equal($targetInput[0], document.activeElement,
                'The first input of the line should have the focus');

            // Simulating hitting the 'f' key twice
            testUtils.fields.editInput($targetInput, 'f');
            testUtils.fields.editInput($targetInput, $targetInput.val() + 'f');

            assert.equal($targetInput[0], document.activeElement,
                'The first input of the line should still have the focus');

            // Simulating a TAB key
            $targetInput.trigger($.Event('keydown', { which: 9, keyCode: 9 }));

            var $secondTarget = $('.o_selected_row .o_input[name=qux]');

            assert.equal($secondTarget[0], document.activeElement,
                'The second input of the line should have the focus after the TAB press');


            testUtils.fields.editInput($secondTarget, 9);
            testUtils.fields.editInput($secondTarget, $secondTarget.val() + 9);

            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('one2many basic properties', function (assert) {
            assert.expect(6);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="Partner page">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                intercepts: {
                    load_filters: function (event) {
                        throw new Error('Should not load filters');
                    },
                },
            });


            assert.containsNone(form, 'td.o_list_record_selector',
                "embedded one2many should not have a selector");
            assert.ok(!form.$('.o_field_x2many_list_row_add').length,
                "embedded one2many should not be editable");
            assert.ok(!form.$('td.o_list_record_remove').length,
                "embedded one2many records should not have a remove icon");

            testUtils.form.clickEdit(form);

            assert.ok(form.$('.o_field_x2many_list_row_add').length,
                "embedded one2many should now be editable");

            assert.hasAttrValue(form.$('.o_field_x2many_list_row_add'), 'colspan', "2",
                "should have colspan 2 (one for field foo, one for being below remove icon)");

            assert.ok(form.$('td.o_list_record_remove').length,
                "embedded one2many records should have a remove icon");
            form.destroy();
        });

        QUnit.test('transferring class attributes in one2many sub fields', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo" class="hey"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            assert.containsOnce(form, 'td.hey',
                'should have a td with the desired class');

            testUtils.form.clickEdit(form);

            assert.containsOnce(form, 'td.hey',
                'should have a td with the desired class');

            testUtils.dom.click(form.$('td.o_data_cell'));

            assert.containsOnce(form, 'input[name="turtle_foo"].hey',
                'should have an input with the desired class');

            form.destroy();
        });

        QUnit.test('one2many with date and datetime', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="Partner page">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="date"/>' +
                    '<field name="datetime"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                session: {
                    getTZOffset: function () {
                        return 120;
                    },
                },
            });
            assert.strictEqual(form.$('td:eq(0)').text(), "01/25/2017",
                "should have formatted the date");
            assert.strictEqual(form.$('td:eq(1)').text(), "12/12/2016 12:55:05",
                "should have formatted the datetime");
            form.destroy();
        });

        QUnit.test('rendering with embedded one2many', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            assert.strictEqual(form.$('th:contains(Foo)').length, 1,
                "embedded one2many should have a column titled according to foo");
            assert.strictEqual(form.$('td:contains(blip)').length, 1,
                "embedded one2many should have a cell with relational value");
            form.destroy();
        });

        QUnit.test('use the limit attribute in arch (in field o2m inline tree view)', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1, 2, 3];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="2">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.model === 'turtle') {
                        assert.deepEqual(args.args[0], [1, 2],
                            'should only load first 2 records');
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, '.o_data_row', 2,
                'should display 2 data rows');
            form.destroy();
        });

        QUnit.test('use the limit attribute in arch (in field o2m non inline tree view)', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1, 2, 3];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles"/>' +
                    '</form>',
                archs: {
                    'turtle,false,list': '<tree limit="2"><field name="turtle_foo"/></tree>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.model === 'turtle' && args.method === 'read') {
                        assert.deepEqual(args.args[0], [1, 2],
                            'should only load first 2 records');
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, '.o_data_row', 2,
                'should display 2 data rows');
            form.destroy();
        });

        QUnit.test('one2many with default_order on view not inline', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [1, 2, 3];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="Turtles">' +
                    '<field name="turtles"/>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                archs: {
                    'turtle,false,list': '<tree default_order="turtle_foo">' +
                        '<field name="turtle_int"/>' +
                        '<field name="turtle_foo"/>' +
                        '</tree>',
                },
                res_id: 1,
            });
            assert.strictEqual(form.$('.o_field_one2many .o_list_view .o_data_row').text(), "9blip21kawa0yop",
                "the default order should be correctly applied");
            form.destroy();
        });

        QUnit.test('embedded one2many with widget', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            assert.containsOnce(form, 'span.o_row_handle', "should have 1 handles");
            form.destroy();
        });

        QUnit.test('embedded one2many with handle widget', function (assert) {
            assert.expect(10);

            var nbConfirmChange = 0;
            testUtils.mock.patch(ListRenderer, {
                confirmChange: function () {
                    nbConfirmChange++;
                    return this._super.apply(this, arguments);
                },
            });

            this.data.partner.records[0].turtles = [1, 2, 3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="turtles">' +
                    '<tree default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.mock.intercept(form, "field_changed", function (event) {
                assert.step(event.data.changes.turtles.data.turtle_int.toString());
            }, true);

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
                "should have the 3 rows in the correct order");

            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
                "should still have the 3 rows in the correct order");
            assert.strictEqual(nbConfirmChange, 0, "should not have confirmed any change yet");

            // Drag and drop the second line in first position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            assert.strictEqual(nbConfirmChange, 1, "should have confirmed changes only once");
            assert.verifySteps(["0", "1"],
                "sequences values should be incremental starting from the previous minimum one");

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
                "should have the 3 rows in the new order");

            testUtils.form.clickSave(form);

            assert.deepEqual(_.map(this.data.turtle.records, function (turtle) {
                return _.pick(turtle, 'id', 'turtle_foo', 'turtle_int');
            }), [
                    { id: 1, turtle_foo: "yop", turtle_int: 1 },
                    { id: 2, turtle_foo: "blip", turtle_int: 0 },
                    { id: 3, turtle_foo: "kawa", turtle_int: 21 }
                ], "should have save the changed sequence");

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
                "should still have the 3 rows in the new order");

            testUtils.mock.unpatch(ListRenderer);

            form.destroy();
        });

        QUnit.test('onchange for embedded one2many in a one2many with a second page', function (assert) {
            assert.expect(1);

            this.data.turtle.fields.partner_ids.type = 'one2many';
            this.data.turtle.records[0].partner_ids = [1];
            // we need a second page, so we set two records and only display one per page
            this.data.partner.records[0].turtles = [1, 2];

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [1, 1, {
                            turtle_foo: "hop",
                            partner_ids: [[5], [4, 1]],
                        }],
                        [1, 2, {
                            turtle_foo: "blip",
                            partner_ids: [[5], [4, 2], [4, 4]],
                        }],
                    ];
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="1">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        var expectedResultTurtles = [
                            [1, 1, {
                                turtle_foo: "hop",
                            }],
                            [1, 2, {
                                partner_ids: [[4, 2, false], [4, 4, false]],
                                turtle_foo: "blip",
                            }],
                        ];
                        assert.deepEqual(args.args[1].turtles, expectedResultTurtles,
                            "the right values should be written");
                    }
                    return this._super.apply(this, arguments);
                }
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_data_cell').eq(1));
            var $cell = form.$('.o_selected_row .o_input[name=turtle_foo]');
            testUtils.fields.editSelect($cell, "hop");
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('onchange for embedded one2many in a one2many updated by server', function (assert) {
            // here we test that after an onchange, the embedded one2many field has
            // been updated by a new list of ids by the server response, to this new
            // list should be correctly sent back at save time
            assert.expect(3);

            this.data.turtle.fields.partner_ids.type = 'one2many';
            this.data.partner.records[0].turtles = [2];
            this.data.turtle.records[1].partner_ids = [2];

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [1, 2, {
                            turtle_foo: "hop",
                            partner_ids: [[5], [4, 2], [4, 4]],
                        }],
                    ];
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/write') {
                        var expectedResultTurtles = [
                            [1, 2, {
                                partner_ids: [[4, 2, false], [4, 4, false]],
                                turtle_foo: "hop",
                            }],
                        ];
                        assert.deepEqual(args.args[1].turtles, expectedResultTurtles,
                            'The right values should be written');
                    }
                    return this._super.apply(this, arguments);
                }
            });

            assert.deepEqual(form.$('.o_many2many_tags_cell').text().trim(), "second record",
                "the partner_ids should be as specified at initialization");

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_data_cell').eq(1));
            var $cell = form.$('.o_selected_row .o_input[name=turtle_foo]');
            testUtils.fields.editSelect($cell, "hop");
            testUtils.form.clickSave(form);

            assert.deepEqual(form.$('.o_many2many_tags_cell').text().trim().split(/\s+/),
                ["second", "record", "aaa"],
                'The partner_ids should have been updated');

            form.destroy();
        });

        QUnit.test('onchange for embedded one2many with handle widget', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1, 2, 3];
            var partnerOnchange = 0;
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    partnerOnchange++;
                },
            };
            var turtleOnchange = 0;
            this.data.turtle.onchanges = {
                turtle_int: function (obj) {
                    turtleOnchange++;
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="turtles">' +
                    '<tree default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);

            // Drag and drop the second line in first position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            assert.strictEqual(turtleOnchange, 2, "should trigger one onchange per line updated");
            assert.strictEqual(partnerOnchange, 1, "should trigger only one onchange on the parent");

            form.destroy();
        });

        QUnit.test('onchange for embedded one2many with handle widget using same sequence', function (assert) {
            assert.expect(4);

            this.data.turtle.records[0].turtle_int = 1;
            this.data.turtle.records[1].turtle_int = 1;
            this.data.turtle.records[2].turtle_int = 1;
            this.data.partner.records[0].turtles = [1, 2, 3];
            var turtleOnchange = 0;
            this.data.turtle.onchanges = {
                turtle_int: function () {
                    turtleOnchange++;
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="turtles">' +
                    '<tree default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].turtles, [[4, 2, false], [1, 1, { "turtle_int": 2 }], [1, 3, { "turtle_int": 3 }]],
                            "should change all lines that have changed (the first one doesn't change because it has the same sequence)");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);


            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
                "should have the 3 rows in the correct order");

            // Drag and drop the second line in first position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
                "should still have the 3 rows in the correct order");
            assert.strictEqual(turtleOnchange, 3, "should update all lines");

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('onchange (with command 5) for embedded one2many with handle widget', function (assert) {
            assert.expect(3);

            var ids = [];
            for (var i = 10; i < 50; i++) {
                var id = 10 + i;
                ids.push(id);
                this.data.turtle.records.push({
                    id: id,
                    turtle_int: 0,
                    turtle_foo: "#" + id,
                });
            }
            ids.push(1, 2, 3);
            this.data.partner.records[0].turtles = ids;
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [[5]].concat(obj.turtles);
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));
            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
                "should have the 3 rows in the correct order");

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:first td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:first input:first'), 'blurp');

            // Drag and drop the third line in second position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(2),
                form.$('.o_field_one2many tbody tr').eq(1),
                { position: 'top' }
            );

            assert.strictEqual(form.$('.o_data_cell').text(), "blurpkawablip", "should display to record in 'turtle_int' order");

            testUtils.form.clickSave(form);
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            assert.strictEqual(form.$('.o_data_cell:not(.o_handle_cell)').text(), "blurpkawablip",
                "should display to record in 'turtle_int' order");

            form.destroy();
        });

        QUnit.test('onchange with modifiers for embedded one2many on the second page', function (assert) {
            assert.expect(7);

            var data = this.data;
            var ids = [];
            for (var i = 10; i < 60; i++) {
                var id = 10 + i;
                ids.push(id);
                data.turtle.records.push({
                    id: id,
                    turtle_int: 0,
                    turtle_foo: "#" + id,
                });
            }
            ids.push(1, 2, 3);
            data.partner.records[0].turtles = ids;
            data.partner.onchanges = {
                turtles: function (obj) {
                    // TODO: make this test more 'difficult'
                    // For now, the server only returns UPDATE commands (no LINK TO)
                    // even though it should do it (for performance reasons)
                    // var turtles = obj.turtles.splice(0, 20);

                    var turtles = [];
                    turtles.unshift([5]);
                    // create UPDATE commands for each records (this is the server
                    // usual answer for onchange)
                    for (var k in obj.turtles) {
                        var change = obj.turtles[k];
                        var record = _.findWhere(data.turtle.records, { id: change[1] });
                        if (change[0] === 1) {
                            _.extend(record, change[2]);
                        }
                        turtles.push([1, record.id, record]);
                    }
                    obj.turtles = turtles;
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" default_order="turtle_int" limit="10">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_qux" attrs="{\'readonly\': [(\'turtle_foo\', \'=\', False)]}"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
                "should display the records in order");

            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:first td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:first input:first'), 'blurp');

            // the domain fail if the widget does not use the allready loaded data.
            testUtils.form.clickDiscard(form);

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "blurp#21#22#23#24#25#26#27#28#29",
                "should display the records in order with the changes");

            testUtils.dom.click($('.modal .modal-footer button:first'));

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
                "should cancel changes and display the records in order");

            testUtils.form.clickEdit(form);

            // Drag and drop the third line in second position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(2),
                form.$('.o_field_one2many tbody tr').eq(1),
                { position: 'top' }
            );

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#30#31#32#33#34#35#36#37#38",
                "should display the records in order after resequence (display record with turtle_int=0)");

            // Drag and drop the third line in second position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(2),
                form.$('.o_field_one2many tbody tr').eq(1),
                { position: 'top' }
            );

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#39#40#41#42#43#44#45#46#47",
                "should display the records in order after resequence (display record with turtle_int=0)");

            testUtils.form.clickDiscard(form);

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#39#40#41#42#43#44#45#46#47",
                "should display the records in order after resequence");

            testUtils.dom.click($('.modal .modal-footer button:first'));

            assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
                "should cancel changes and display the records in order");

            form.destroy();
        });

        QUnit.test('onchange followed by edition on the second page', function (assert) {
            assert.expect(12);

            var ids = [];
            for (var i = 1; i < 85; i++) {
                var id = 10 + i;
                ids.push(id);
                this.data.turtle.records.push({
                    id: id,
                    turtle_int: id / 3 | 0,
                    turtle_foo: "#" + i,
                });
            }
            ids.splice(41, 0, 1, 2, 3);
            this.data.partner.records[0].turtles = ids;
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [[5]].concat(obj.turtles);
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top" default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:eq(1) td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:eq(1) input:first'), 'value 1');
            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:eq(2) td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:eq(2) input:first'), 'value 2');

            assert.containsN(form, '.o_data_row', 40, "should display 40 records");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 0, "should display '#39' at the first line");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 40, "should display 39 records and the create line");
            assert.containsOnce(form, '.o_data_row:first .o_field_char', "should display the create line in first position");
            assert.strictEqual(form.$('.o_data_row:first .o_field_char').val(), "", "should an empty input");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 1, "should display '#39' at the second line");

            testUtils.fields.editInput(form.$('.o_data_row input:first'), 'value 3');

            assert.containsOnce(form, '.o_data_row:first .o_field_char', "should display the create line in first position after onchange");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 1, "should display '#39' at the second line after onchange");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 40, "should display 39 records and the create line");
            assert.containsOnce(form, '.o_data_row:first .o_field_char', "should display the create line in first position");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(value 3))').index(), 1, "should display the created line at the second position");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 2, "should display '#39' at the third line");

            form.destroy();
        });

        QUnit.test('onchange followed by edition on the second page (part 2)', function (assert) {
            assert.expect(8);

            var ids = [];
            for (var i = 1; i < 85; i++) {
                var id = 10 + i;
                ids.push(id);
                this.data.turtle.records.push({
                    id: id,
                    turtle_int: id / 3 | 0,
                    turtle_foo: "#" + i,
                });
            }
            ids.splice(41, 0, 1, 2, 3);
            this.data.partner.records[0].turtles = ids;
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [[5]].concat(obj.turtles);
                },
            };

            // bottom order

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:eq(1) td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:eq(1) input:first'), 'value 1');
            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:eq(2) td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:eq(2) input:first'), 'value 2');

            assert.containsN(form, '.o_data_row', 40, "should display 40 records");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#77))').index(), 39, "should display '#77' at the last line");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 41, "should display 41 records and the create line");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#76))').index(), 38, "should display '#76' at the penultimate line");
            assert.strictEqual(form.$('.o_data_row:has(.o_field_char)').index(), 40, "should display the create line at the last position");

            testUtils.fields.editInput(form.$('.o_data_row input:first'), 'value 3');
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 42, "should display 42 records and the create line");
            assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#76))').index(), 38, "should display '#76' at the penultimate line");
            assert.strictEqual(form.$('.o_data_row:has(.o_field_char)').index(), 41, "should display the create line at the last position");

            form.destroy();
        });

        QUnit.test('onchange returning a command 6 for an x2many', function (assert) {
            assert.expect(2);

            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[6, false, [1, 2, 3]]];
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "there should be one record in the relation");

            // change the value of foo to trigger the onchange
            testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'some value');

            assert.containsN(form, '.o_data_row', 3,
                "there should be three records in the relation");

            form.destroy();
        });

        QUnit.test('x2many fields inside x2manys are fetched after an onchange', function (assert) {
            assert.expect(6);

            this.data.turtle.records[0].partner_ids = [1];
            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[5], [4, 1], [4, 2], [4, 3]];
                },
            };

            var checkRPC = false;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (checkRPC && args.method === 'read' && args.model === 'partner') {
                        assert.deepEqual(args.args[1], ['display_name'],
                            "should only read the display_name for the m2m tags");
                        assert.deepEqual(args.args[0], [1],
                            "should only read the display_name of the unknown record");
                    }
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "there should be one record in the relation");
            assert.strictEqual(form.$('.o_data_row .o_field_widget[name=partner_ids]').text().replace(/\s/g, ''),
                'secondrecordaaa', "many2many_tags should be correctly displayed");

            // change the value of foo to trigger the onchange
            checkRPC = true; // enable flag to check read RPC for the m2m field
            testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'some value');

            assert.containsN(form, '.o_data_row', 3,
                "there should be three records in the relation");
            assert.strictEqual(form.$('.o_data_row:first .o_field_widget[name=partner_ids]').text().trim(),
                'first record', "many2many_tags should be correctly displayed");

            form.destroy();
        });

        QUnit.test('reference fields inside x2manys are fetched after an onchange', function (assert) {
            assert.expect(5);

            this.data.turtle.records[1].turtle_ref = 'product,41';
            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[5], [4, 1], [4, 2], [4, 3]];
                },
            };

            var checkRPC = false;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_ref" class="ref_field"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (checkRPC && args.method === 'name_get') {
                        assert.deepEqual(args.args[0], [37],
                            "should only fetch the name_get of the unknown record");
                    }
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "there should be one record in the relation");
            assert.strictEqual(form.$('.ref_field').text().trim(), 'xpad',
                "reference field should be correctly displayed");

            // change the value of foo to trigger the onchange
            checkRPC = true; // enable flag to check read RPC for reference field
            testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'some value');

            assert.containsN(form, '.o_data_row', 3,
                "there should be three records in the relation");
            assert.strictEqual(form.$('.ref_field').text().trim(), 'xpadxphone',
                "reference fields should be correctly displayed");

            form.destroy();
        });

        QUnit.test('onchange on one2many containing x2many in form view', function (assert) {
            assert.expect(16);

            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.turtles = [[0, false, { turtle_foo: 'new record' }]];
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="partner_ids">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'partner,false,list': '<tree><field name="foo"/></tree>',
                    'partner,false,search': '<search></search>',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "the onchange should have created one record in the relation");

            // open the created o2m record in a form view, and add a m2m subrecord
            // in its relation
            testUtils.dom.click(form.$('.o_data_row'));

            assert.strictEqual($('.modal').length, 1, "should have opened a dialog");
            assert.strictEqual($('.modal .o_data_row').length, 0,
                "there should be no record in the one2many in the dialog");

            // add a many2many subrecord
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));

            assert.strictEqual($('.modal').length, 2,
                "should have opened a second dialog");

            // select a many2many subrecord
            testUtils.dom.click($('.modal:nth(1) .o_list_view .o_data_cell:first'));

            assert.strictEqual($('.modal').length, 1,
                "second dialog should be closed");
            assert.strictEqual($('.modal .o_data_row').length, 1,
                "there should be one record in the one2many in the dialog");
            assert.notOk($('.modal .o_x2m_control_panel .o_cp_pager div').is(':visible'),
                'm2m pager should be hidden');

            // click on 'Save & Close'
            testUtils.dom.click($('.modal-footer .btn-primary:first'));

            assert.strictEqual($('.modal').length, 0, "dialog should be closed");

            // reopen o2m record, and another m2m subrecord in its relation, but
            // discard the changes
            testUtils.dom.click(form.$('.o_data_row'));

            assert.strictEqual($('.modal').length, 1, "should have opened a dialog");
            assert.strictEqual($('.modal .o_data_row').length, 1,
                "there should be one record in the one2many in the dialog");

            // add another m2m subrecord
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));

            assert.strictEqual($('.modal').length, 2,
                "should have opened a second dialog");

            testUtils.dom.click($('.modal:nth(1) .o_list_view .o_data_cell:first'));

            assert.strictEqual($('.modal').length, 1,
                "second dialog should be closed");
            assert.strictEqual($('.modal .o_data_row').length, 2,
                "there should be two records in the one2many in the dialog");

            // click on 'Discard'
            testUtils.dom.clickFirst($('.modal-footer .btn-secondary'));

            assert.strictEqual($('.modal').length, 0, "dialog should be closed");

            // reopen o2m record to check that second changes have properly been discarded
            testUtils.dom.click(form.$('.o_data_row'));

            assert.strictEqual($('.modal').length, 1, "should have opened a dialog");
            assert.strictEqual($('.modal .o_data_row').length, 1,
                "there should be one record in the one2many in the dialog");

            form.destroy();
        });

        QUnit.test('embedded one2many with handle widget with minimum setValue calls', function (assert) {
            var done = assert.async();
            assert.expect(20);


            this.data.turtle.records[0].turtle_int = 6;
            this.data.turtle.records.push({
                id: 4,
                turtle_int: 20,
                turtle_foo: "a1",
            }, {
                    id: 5,
                    turtle_int: 9,
                    turtle_foo: "a2",
                }, {
                    id: 6,
                    turtle_int: 2,
                    turtle_foo: "a3",
                }, {
                    id: 7,
                    turtle_int: 11,
                    turtle_foo: "a4",
                });
            this.data.partner.records[0].turtles = [1, 2, 3, 4, 5, 6, 7];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="turtles">' +
                    '<tree default_order="turtle_int">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.mock.intercept(form, "field_changed", function (event) {
                assert.step(form.model.get(event.data.changes.turtles.id).res_id);
            }, true);

            testUtils.form.clickEdit(form);

            var steps = [];
            var positions = [
                [6, 0, 'top', [3, 6, 1, 2, 5, 7, 4]], // move the last to the first line
                [5, 1, 'top', [7, 6, 1, 2, 5]], // move the penultimate to the second line
                [2, 5, 'center', [1, 2, 5, 6]], // move the third to the penultimate line
            ];
            function dragAndDrop() {
                var pos = positions.shift();

                testUtils.dom.dragAndDrop(
                    form.$('.ui-sortable-handle').eq(pos[0]),
                    form.$('tbody tr').eq(pos[1]),
                    { position: pos[2] }
                );

                steps = steps.concat(pos[3]);
                assert.verifySteps(steps,
                    "sequences values should be apply from the begin index to the drop index");

                if (positions.length) {

                    setTimeout(dragAndDrop, 10);

                } else {

                    assert.deepEqual(_.pluck(form.model.get(form.handle).data.turtles.data, 'data'), [
                        { id: 3, turtle_foo: "kawa", turtle_int: 2 },
                        { id: 7, turtle_foo: "a4", turtle_int: 3 },
                        { id: 1, turtle_foo: "yop", turtle_int: 4 },
                        { id: 2, turtle_foo: "blip", turtle_int: 5 },
                        { id: 5, turtle_foo: "a2", turtle_int: 6 },
                        { id: 6, turtle_foo: "a3", turtle_int: 7 },
                        { id: 4, turtle_foo: "a1", turtle_int: 8 }
                    ], "sequences must be apply correctly");

                    form.destroy();
                    done();
                }
            }

            dragAndDrop();
        });

        QUnit.test('embedded one2many (editable list) with handle widget', function (assert) {
            assert.expect(8);

            this.data.partner.records[0].p = [1, 2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<notebook>' +
                    '<page string="P page">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="int_field" widget="handle"/>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.mock.intercept(form, "field_changed", function (event) {
                assert.step(event.data.changes.p.data.int_field.toString());
            }, true);

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "My little Foo Valueblipyop",
                "should have the 3 rows in the correct order");

            testUtils.form.clickEdit(form);
            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "My little Foo Valueblipyop",
                "should still have the 3 rows in the correct order");

            // Drag and drop the second line in first position
            testUtils.dom.dragAndDrop(
                form.$('.ui-sortable-handle').eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            assert.verifySteps(["0", "1"],
                "sequences values should be incremental starting from the previous minimum one");

            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipMy little Foo Valueyop",
                "should have the 3 rows in the new order");

            testUtils.dom.click(form.$('tbody tr:first td:first'));

            assert.strictEqual(form.$('tbody tr:first td.o_data_cell:not(.o_handle_cell) input').val(), "blip",
                "should edit the correct row");

            testUtils.form.clickSave(form);
            assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipMy little Foo Valueyop",
                "should still have the 3 rows in the new order");

            form.destroy();
        });

        QUnit.test('one2many field when using the pager', function (assert) {
            assert.expect(13);

            var ids = [];
            for (var i = 0; i < 45; i++) {
                var id = 10 + i;
                ids.push(id);
                this.data.partner.records.push({
                    id: id,
                    display_name: "relational record " + id,
                });
            }
            this.data.partner.records[0].p = ids.slice(0, 42);
            this.data.partner.records[1].p = ids.slice(42);

            var count = 0;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<kanban>' +
                    '<field name="display_name"/>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div><t t-esc="record.display_name"/></div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</form>',
                viewOptions: {
                    ids: [1, 2],
                    index: 0,
                },
                mockRPC: function () {
                    count++;
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
            });

            // we are on record 1, which has 90 related record (first 40 should be
            // displayed), 2 RPCs (read) should have been done, one on the main record
            // and one for the O2M
            assert.strictEqual(count, 2, 'two RPCs should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
                'one2many kanban should contain 40 cards for record 1');

            // move to record 2, which has 3 related records (and shouldn't contain the
            // related records of record 1 anymore). Two additional RPCs should have
            // been done
            form.pager.next();
            assert.strictEqual(count, 4, 'two RPCs should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 3,
                'one2many kanban should contain 3 cards for record 2');

            // move back to record 1, which should contain again its first 40 related
            // records
            form.pager.previous();
            assert.strictEqual(count, 6, 'two RPCs should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
                'one2many kanban should contain 40 cards for record 1');

            // move to the second page of the o2m: 1 RPC should have been done to fetch
            // the 2 subrecords of page 2, and those records should now be displayed
            testUtils.dom.click(form.$('.o_x2m_control_panel .o_pager_next'));
            assert.strictEqual(count, 7, 'one RPC should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 2,
                'one2many kanban should contain 2 cards for record 1 at page 2');

            // move to record 2 again and check that everything is correctly updated
            form.pager.next();
            assert.strictEqual(count, 9, 'two RPCs should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 3,
                'one2many kanban should contain 3 cards for record 2');

            // move back to record 1 and move to page 2 again: all data should have
            // been correctly reloaded
            form.pager.previous();
            assert.strictEqual(count, 11, 'two RPCs should have been done');
            testUtils.dom.click(form.$('.o_x2m_control_panel .o_pager_next'));
            assert.strictEqual(count, 12, 'one RPC should have been done');
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 2,
                'one2many kanban should contain 2 cards for record 1 at page 2');
            form.destroy();
        });

        QUnit.test('edition of one2many field with pager', function (assert) {
            assert.expect(31);

            var ids = [];
            for (var i = 0; i < 45; i++) {
                var id = 10 + i;
                ids.push(id);
                this.data.partner.records.push({
                    id: id,
                    display_name: "relational record " + id,
                });
            }
            this.data.partner.records[0].p = ids;

            var saveCount = 0;
            var checkRead = false;
            var readIDs;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<kanban>' +
                    '<field name="display_name"/>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click">' +
                    '<a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>' +
                    '<span><t t-esc="record.display_name.value"/></span>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'partner,false,form': '<form><field name="display_name"/></form>',
                },
                mockRPC: function (route, args) {
                    if (args.method === 'read' && checkRead) {
                        readIDs = args.args[0];
                        checkRead = false;
                    }
                    if (args.method === 'write') {
                        saveCount++;
                        var nbCommands = args.args[1].p.length;
                        var nbLinkCommands = _.filter(args.args[1].p, function (command) {
                            return command[0] === 4;
                        }).length;
                        switch (saveCount) {
                            case 1:
                                assert.strictEqual(nbCommands, 46,
                                    "should send 46 commands (one for each record)");
                                assert.strictEqual(nbLinkCommands, 45,
                                    "should send a LINK_TO command for each existing record");
                                assert.deepEqual(args.args[1].p[45], [0, args.args[1].p[45][1], {
                                    display_name: 'new record',
                                }], "should sent a CREATE command for the new record");
                                break;
                            case 2:
                                assert.strictEqual(nbCommands, 46,
                                    "should send 46 commands");
                                assert.strictEqual(nbLinkCommands, 45,
                                    "should send a LINK_TO command for each existing record");
                                assert.deepEqual(args.args[1].p[45], [2, 10, false],
                                    "should sent a DELETE command for the deleted record");
                                break;
                            case 3:
                                assert.strictEqual(nbCommands, 47,
                                    "should send 47 commands");
                                assert.strictEqual(nbLinkCommands, 43,
                                    "should send a LINK_TO command for each existing record");
                                assert.deepEqual(args.args[1].p[43],
                                    [0, args.args[1].p[43][1], { display_name: 'new record page 1' }],
                                    "should sent correct CREATE command");
                                assert.deepEqual(args.args[1].p[44],
                                    [0, args.args[1].p[44][1], { display_name: 'new record page 2' }],
                                    "should sent correct CREATE command");
                                assert.deepEqual(args.args[1].p[45],
                                    [2, 11, false],
                                    "should sent correct DELETE command");
                                assert.deepEqual(args.args[1].p[46],
                                    [2, 52, false],
                                    "should sent correct DELETE command");
                                break;
                        }
                    }
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
            });

            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
                'there should be 40 records on page 1');
            assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
                '1-40 / 45', "pager range should be correct");

            // add a record on page one
            checkRead = true;
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o-kanban-button-new'));
            testUtils.fields.editInput($('.modal input'), 'new record');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            // checks
            assert.strictEqual(readIDs, undefined, "should not have read any record");
            assert.strictEqual(form.$('span:contains(new record)').length, 0,
                "new record should be on page 2");
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
                'there should be 40 records on page 1');
            assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
                '1-40 / 46', "pager range should be correct");
            assert.strictEqual(form.$('.o_kanban_record:first span:contains(new record)').length,
                0, 'new record should not be on page 1');
            // save
            testUtils.form.clickSave(form);

            // delete a record on page one
            checkRead = true;
            testUtils.form.clickEdit(form);
            assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 10)').length,
                1, 'first record should be the one with id 10 (next checks rely on that)');
            testUtils.dom.click(form.$('.delete_icon:first'));
            // checks
            assert.deepEqual(readIDs, [50],
                "should have read a record (to display 40 records on page 1)");
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
                'there should be 40 records on page 1');
            assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
                '1-40 / 45', "pager range should be correct");
            // save
            testUtils.form.clickSave(form);

            // add and delete records in both pages
            testUtils.form.clickEdit(form);
            checkRead = true;
            readIDs = undefined;
            // add and delete a record in page 1
            testUtils.dom.click(form.$('.o-kanban-button-new'));
            testUtils.fields.editInput($('.modal input'), 'new record page 1');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 11)').length,
                1, 'first record should be the one with id 11 (next checks rely on that)');
            testUtils.dom.click(form.$('.delete_icon:first'));
            assert.deepEqual(readIDs, [51],
                "should have read a record (to display 40 records on page 1)");
            // add and delete a record in page 2
            testUtils.dom.click(form.$('.o_x2m_control_panel .o_pager_next'));
            assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 52)').length,
                1, 'first record should be the one with id 52 (next checks rely on that)');
            checkRead = true;
            readIDs = undefined;
            testUtils.dom.click(form.$('.delete_icon:first'));
            testUtils.dom.click(form.$('.o-kanban-button-new'));
            testUtils.fields.editInput($('.modal input'), 'new record page 2');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            assert.strictEqual(readIDs, undefined, "should not have read any record");
            // checks
            assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 5,
                'there should be 5 records on page 2');
            assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
                '41-45 / 45', "pager range should be correct");
            assert.strictEqual(form.$('.o_kanban_record span:contains(new record page 1)').length,
                1, 'new records should be on page 2');
            assert.strictEqual(form.$('.o_kanban_record span:contains(new record page 2)').length,
                1, 'new records should be on page 2');
            // save
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('edition of one2many field, with onchange and not inline sub view', function (assert) {
            assert.expect(2);

            this.data.turtle.onchanges.turtle_int = function (obj) {
                obj.turtle_foo = String(obj.turtle_int);
            };
            this.data.partner.onchanges.turtles = function () { };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles"/>' +
                    '</form>',
                archs: {
                    'turtle,false,list': '<tree><field name="turtle_foo"/></tree>',
                    'turtle,false,form': '<form><group><field name="turtle_foo"/><field name="turtle_int"/></group></form>',
                },
                mockRPC: function (route, args) {
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
            });
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput($('input[name="turtle_int"]'), '5');
            testUtils.dom.click($('.modal-footer button.btn-primary').first());
            assert.strictEqual(form.$('tbody tr:eq(1) td.o_data_cell').text(), '5',
                'should display 5 in the foo field');
            testUtils.dom.click(form.$('tbody tr:eq(1) td.o_data_cell'));

            testUtils.fields.editInput($('input[name="turtle_int"]'), '3');
            testUtils.dom.click($('.modal-footer button.btn-primary').first());
            assert.strictEqual(form.$('tbody tr:eq(1) td.o_data_cell').text(), '3',
                'should now display 3 in the foo field');
            form.destroy();
        });

        QUnit.test('sorting one2many fields', function (assert) {
            assert.expect(4);

            this.data.partner.fields.foo.sortable = true;
            this.data.partner.records.push({ id: 23, foo: "abc" });
            this.data.partner.records.push({ id: 24, foo: "xyz" });
            this.data.partner.records.push({ id: 25, foo: "def" });
            this.data.partner.records[0].p = [23, 24, 25];

            var rpcCount = 0;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function () {
                    rpcCount++;
                    return this._super.apply(this, arguments);
                },
            });

            rpcCount = 0;
            assert.ok(form.$('table tbody tr:eq(2) td:contains(def)').length,
                "the 3rd record is the one with 'def' value");
            form.renderer._render = function () {
                throw "should not render the whole form";
            };

            testUtils.dom.click(form.$('table thead th:contains(Foo)'));
            assert.strictEqual(rpcCount, 0,
                'sort should be in memory, no extra RPCs should have been done');
            assert.ok(form.$('table tbody tr:eq(2) td:contains(xyz)').length,
                "the 3rd record is the one with 'xyz' value");

            testUtils.dom.click(form.$('table thead th:contains(Foo)'));
            assert.ok(form.$('table tbody tr:eq(2) td:contains(abc)').length,
                "the 3rd record is the one with 'abc' value");

            form.destroy();
        });

        QUnit.test('one2many list field edition', function (assert) {
            assert.expect(6);

            this.data.partner.records.push({
                id: 3,
                display_name: "relational record 1",
            });
            this.data.partner.records[1].p = [3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 2,
            });

            // edit the first line of the o2m
            assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'relational record 1',
                "display name of first record in o2m list should be 'relational record 1'");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_one2many tbody td').first());
            assert.hasClass(form.$('.o_field_one2many tbody td').first().parent(),'o_selected_row',
                "first row of o2m should be in edition");
            testUtils.fields.editInput(form.$('.o_field_one2many tbody td').first().find('input'), "new value");
            assert.hasClass(form.$('.o_field_one2many tbody td').first().parent(),'o_selected_row',
                "first row of o2m should still be in edition");

            // // leave o2m edition
            testUtils.dom.click(form.$el);
            assert.doesNotHaveClass(form.$('.o_field_one2many tbody td').first().parent(), 'o_selected_row',
                "first row of o2m should be readonly again");

            // discard changes
            testUtils.form.clickDiscard(form);
            assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'new value',
                "changes shouldn't have been discarded yet, waiting for user confirmation");
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));
            assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'relational record 1',
                "display name of first record in o2m list should be 'relational record 1'");

            // edit again and save
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_one2many tbody td').first());
            testUtils.fields.editInput(form.$('.o_field_one2many tbody td').first().find('input'), "new value");
            testUtils.dom.click(form.$el);
            testUtils.form.clickSave(form);
            // FIXME: this next test doesn't pass as the save of updates of
            // relational data is temporarily disabled
            // assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'new value',
            //     "display name of first record in o2m list should be 'new value'");

            form.destroy();
        });

        QUnit.test('one2many list: create action disabled', function (assert) {
            assert.expect(2);
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree create="0">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            assert.ok(!form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" link should not be available in readonly');

            testUtils.form.clickEdit(form);

            assert.ok(!form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" link should not be available in readonly');
            form.destroy();
        });

        QUnit.test('one2many list: unlink two records', function (assert) {
            assert.expect(9);
            this.data.partner.records[0].p = [1, 2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p" widget="many2many">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/write') {
                        var commands = args.args[1].p;
                        assert.strictEqual(commands.length, 3,
                            'should have generated three commands');
                        assert.ok(commands[0][0] === 4 && commands[0][1] === 4,
                            'should have generated the command 4 (LINK_TO) with id 4');
                        assert.ok(commands[1][0] === 3 && commands[1][1] === 1,
                            'should have generated the command 3 (UNLINK) with id 1');
                        assert.ok(commands[2][0] === 3 && commands[2][1] === 2,
                            'should have generated the command 3 (UNLINK) with id 2');
                    }
                    return this._super.apply(this, arguments);
                },
                archs: {
                    'partner,false,form':
                        '<form string="Partner"><field name="display_name"/></form>',
                },
            });
            testUtils.form.clickEdit(form);

            assert.containsN(form, 'td.o_list_record_remove button', 3,
                "should have 3 remove buttons");

            assert.hasClass(form.$('td.o_list_record_remove button').first(),'fa fa-times',
                "should have X icons to remove (unlink) records");

            testUtils.dom.click(form.$('td.o_list_record_remove button').first());

            assert.containsN(form, 'td.o_list_record_remove button', 2,
                "should have 2 remove buttons (a record is supposed to have been unlinked)");

            testUtils.dom.click(form.$('tr.o_data_row').first());
            assert.strictEqual($('.modal .modal-footer .o_btn_remove').length, 1,
                'there should be a modal having Remove Button');
            testUtils.dom.click($('.modal .modal-footer .o_btn_remove'));

            assert.containsOnce(form, 'td.o_list_record_remove button',
                "should have 1 delete button (another record is supposed to have been unlinked)");

            // save and check that the correct command has been generated
            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('one2many list: deleting two records', function (assert) {
            assert.expect(9);
            this.data.partner.records[0].p = [1, 2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/write') {
                        var commands = args.args[1].p;
                        assert.strictEqual(commands.length, 3,
                            'should have generated three commands');
                        assert.ok(commands[0][0] === 4 && commands[0][1] === 4,
                            'should have generated the command 4 (LINK_TO) with id 4');
                        assert.ok(commands[1][0] === 2 && commands[1][1] === 1,
                            'should have generated the command 2 (DELETE) with id 1');
                        assert.ok(commands[2][0] === 2 && commands[2][1] === 2,
                            'should have generated the command 2 (DELETE) with id 2');
                    }
                    return this._super.apply(this, arguments);
                },
                archs: {
                    'partner,false,form':
                        '<form string="Partner"><field name="display_name"/></form>',
                },
            });
            testUtils.form.clickEdit(form);

            assert.containsN(form, 'td.o_list_record_remove button', 3,
                "should have 3 remove buttons");

            assert.hasClass(form.$('td.o_list_record_remove button').first(),'fa fa-trash-o',
                "should have trash bin icons to remove (delete) records");

            testUtils.dom.click(form.$('td.o_list_record_remove button').first());

            assert.containsN(form, 'td.o_list_record_remove button', 2,
                "should have 2 remove buttons (a record is supposed to have been deleted)");

            testUtils.dom.click(form.$('tr.o_data_row').first());
            assert.strictEqual($('.modal .modal-footer .o_btn_remove').length, 1,
                'there should be a modal having Remove Button');
            testUtils.dom.click($('.modal .modal-footer .o_btn_remove'));

            assert.containsOnce(form, 'td.o_list_record_remove button',
                "should have 1 remove button (another record is supposed to have been deleted)");

            // save and check that the correct command has been generated
            testUtils.form.clickSave(form);

            // FIXME: it would be nice to test that the view is re-rendered correctly,
            // but as the relational data isn't re-fetched, the rendering is ok even
            // if the changes haven't been saved
            form.destroy();
        });

        QUnit.test('one2many kanban: edition', function (assert) {
            assert.expect(17);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<kanban>' +
                    // color will be in the kanban but not in the form
                    '<field name="color"/>' +
                    '<field name="display_name"/>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click">' +
                    '<a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>' +
                    '<span><t t-esc="record.display_name.value"/></span>' +
                    '<span><t t-esc="record.color.value"/></span>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    // foo will be in the form but not in the kanban
                    '<field name="foo"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            assert.ok(!form.$('.o_kanban_view .delete_icon').length,
                'delete icon should not be visible in readonly');
            assert.ok(!form.$('.o_field_one2many .o-kanban-button-new').length,
                '"Create" button should not be visible in readonly');

            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
                'should contain 1 record');
            assert.strictEqual(form.$('.o_kanban_record span:first').text(), 'second record',
                'display_name of subrecord should be the one in DB');
            assert.strictEqual(form.$('.o_kanban_record span:nth(1)').text(), 'Red',
                'color of subrecord should be the one in DB');
            assert.ok(form.$('.o_kanban_view .delete_icon').length,
                'delete icon should be visible in edit');
            assert.ok(form.$('.o_field_one2many .o-kanban-button-new').length,
                '"Create" button should be visible in edit');
            assert.hasClass(form.$('.o_field_one2many .o-kanban-button-new'),'btn-secondary',
                "'Create' button should have className 'btn-secondary'");
            assert.strictEqual(form.$('.o_field_one2many .o-kanban-button-new').text().trim(), "Add",
                'Create button should have "Add" label');

            // edit existing subrecord
            testUtils.dom.click(form.$('.oe_kanban_global_click'));

            testUtils.fields.editInput($('.modal .o_form_view input').first(), 'new name');
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));
            assert.strictEqual(form.$('.o_kanban_record span:first').text(), 'new name',
                'value of subrecord should have been updated');

            // create a new subrecord
            testUtils.dom.click(form.$('.o-kanban-button-new'));
            testUtils.fields.editInput($('.modal .o_form_view input').first(), 'new subrecord 1');
            testUtils.dom.clickFirst($('.modal .modal-footer .btn-primary'));
            assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
                'should contain 2 records');
            assert.strictEqual(form.$('.o_kanban_record:nth(1) span').text(), 'new subrecord 1',
                'value of newly created subrecord should be "new subrecord 1"');

            // create two new subrecords
            testUtils.dom.click(form.$('.o-kanban-button-new'));
            testUtils.fields.editInput($('.modal .o_form_view input').first(), 'new subrecord 2');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:nth(1)'));
            testUtils.fields.editInput($('.modal .o_form_view input').first(), 'new subrecord 3');
            testUtils.dom.clickFirst($('.modal .modal-footer .btn-primary'));
            assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 4,
                'should contain 4 records');

            // delete subrecords
            testUtils.dom.click(form.$('.oe_kanban_global_click').first());
            assert.strictEqual($('.modal .modal-footer .o_btn_remove').length, 1,
                'There should be a modal having Remove Button');
            testUtils.dom.click($('.modal .modal-footer .o_btn_remove'));
            assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 3,
                'should contain 3 records');
            testUtils.dom.click(form.$('.o_kanban_view .delete_icon:first()'));
            testUtils.dom.click(form.$('.o_kanban_view .delete_icon:first()'));
            assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
                'should contain 1 records');
            assert.strictEqual(form.$('.o_kanban_record span:first').text(), 'new subrecord 3',
                'the remaining subrecord should be "new subrecord 3"');
            form.destroy();
        });

        QUnit.test('one2many kanban (editable): properly handle create_text node option', function (assert) {
            assert.expect(1);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles" options="{\'create_text\': \'Add turtle\'}" mode="kanban">' +
                    '<kanban>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div class="oe_kanban_details">' +
                    '<field name="display_name"/>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);
            assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o-kanban-button-new').text().trim(),
                "Add turtle", "In O2M Kanban, Add button should have 'Add turtle' label");

            form.destroy();
        });

        QUnit.test('one2many kanban: create action disabled', function (assert) {
            assert.expect(3);

            this.data.partner.records[0].p = [4];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<kanban create="0">' +
                    '<field name="display_name"/>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div class="oe_kanban_global_click">' +
                    '<a t-if="!read_only_mode" type="delete" class="fa fa-times float-right delete_icon"/>' +
                    '<span><t t-esc="record.display_name.value"/></span>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            assert.ok(!form.$('.o-kanban-button-new').length,
                '"Add" button should not be available in readonly');

            testUtils.form.clickEdit(form);

            assert.ok(!form.$('.o-kanban-button-new').length,
                '"Add" button should not be available in edit');
            assert.ok(form.$('.o_kanban_view .delete_icon').length,
                'delete icon should be visible in edit');
            form.destroy();
        });

        QUnit.test('editable one2many list, pager is updated', function (assert) {
            assert.expect(1);

            this.data.turtle.records.push({ id: 4, turtle_foo: 'stephen hawking' });
            this.data.partner.records[0].turtles = [1, 2, 3, 4];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a record, then click in form view to confirm it
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$el);

            assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_cp_pager').text().trim(), '1-3 / 5',
                "pager should display the correct total");
            form.destroy();
        });

        QUnit.test('one2many list (non editable): edition', function (assert) {
            assert.expect(12);

            var nbWrite = 0;
            this.data.partner.records[0].p = [2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="display_name"/><field name="qux"/>' +
                    '</tree>' +
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        nbWrite++;
                        assert.deepEqual(args.args[1], {
                            p: [[1, 2, { display_name: 'new name' }], [2, 4, false]]
                        }, "should have sent the correct commands");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.ok(!form.$('.o_list_record_remove').length,
                'remove icon should not be visible in readonly');
            assert.ok(!form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" should not be visible in readonly');

            testUtils.form.clickEdit(form);

            assert.containsN(form, '.o_list_view td.o_list_number', 2,
                'should contain 2 records');
            assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'second record',
                'display_name of first subrecord should be the one in DB');
            assert.ok(form.$('.o_list_record_remove').length,
                'remove icon should be visible in edit');
            assert.ok(form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" should not visible in edit');

            // edit existing subrecord
            testUtils.dom.click(form.$('.o_list_view tbody tr:first() td:eq(1)'));

            testUtils.fields.editInput($('.modal .o_form_view input'), 'new name');
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));
            assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
                'value of subrecord should have been updated');
            assert.strictEqual(nbWrite, 0, "should not have write anything in DB");

            // create new subrecords
            // TODO when 'Add an item' will be implemented

            // remove subrecords
            testUtils.dom.click(form.$('.o_list_record_remove:nth(1)'));
            assert.containsOnce(form, '.o_list_view td.o_list_number',
                'should contain 1 subrecord');
            assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
                'the remaining subrecord should be "new name"');

            testUtils.form.clickSave(form); // save the record
            assert.strictEqual(nbWrite, 1, "should have write the changes in DB");

            form.destroy();
        });

        QUnit.test('one2many list (editable): edition', function (assert) {
            assert.expect(7);

            this.data.partner.records[0].p = [2, 4];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="display_name"/><field name="qux"/>' +
                    '</tree>' +
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            assert.ok(!form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" link should not be available in readonly');

            testUtils.dom.click(form.$('.o_list_view tbody td:first()'));
            assert.ok($('.modal .o_form_readonly').length,
                'in readonly, clicking on a subrecord should open it in readonly in a dialog');
            testUtils.dom.click($('.modal .o_form_button_cancel'));

            testUtils.form.clickEdit(form);

            assert.ok(form.$('.o_field_x2many_list_row_add').length,
                '"Add an item" link should be available in edit');

            // edit existing subrecord
            testUtils.dom.click(form.$('.o_list_view tbody td:first()'));
            assert.strictEqual($('.modal').length, 0,
                'in edit, clicking on a subrecord should not open a dialog');
            assert.hasClass(form.$('.o_list_view tbody tr:first()'),'o_selected_row',
                'first row should be in edition');
            testUtils.fields.editInput(form.$('.o_list_view input:first()'), 'new name');

            testUtils.dom.click(form.$('.o_list_view tbody tr:nth(1) td:first'));
            assert.doesNotHaveClass(form.$('.o_list_view tbody tr:first'), 'o_selected_row',
                'first row should not be in edition anymore');
            assert.strictEqual(form.$('.o_list_view tbody td:first').text(), 'new name',
                'value of subrecord should have been updated');

            // create new subrecords
            // TODO when 'Add an item' will be implemented
            form.destroy();
        });

        QUnit.test('one2many list (editable): edition, part 2', function (assert) {
            assert.expect(8);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        assert.strictEqual(args.args[1].p[0][0], 0,
                            "should send a 0 command for field p");
                        assert.strictEqual(args.args[1].p[1][0], 0,
                            "should send a second 0 command for field p");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            // edit mode, then click on Add an item and enter a value
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_selected_row > td input'), 'kartoffel');

            // click again on Add an item
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.strictEqual(form.$('td:contains(kartoffel)').length, 1,
                "should have one td with the new value");
            assert.containsOnce(form, '.o_selected_row > td input',
                "should have one other new td");
            assert.containsN(form, 'tr.o_data_row', 2, "should have 2 data rows");

            // enter another value and save
            testUtils.fields.editInput(form.$('.o_selected_row > td input'), 'gemuse');
            testUtils.form.clickSave(form);
            assert.containsN(form, 'tr.o_data_row', 2, "should have 2 data rows");
            assert.strictEqual(form.$('td:contains(kartoffel)').length, 1,
                "should have one td with the new value");
            assert.strictEqual(form.$('td:contains(gemuse)').length, 1,
                "should have one td with the new value");

            form.destroy();
        });

        QUnit.test('one2many list (editable): edition, part 3', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
            });

            // edit mode, then click on Add an item 2 times
            assert.containsOnce(form, 'tr.o_data_row',
                "should have 1 data rows");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsN(form, 'tr.o_data_row', 3,
                "should have 3 data rows");

            // cancel the edition
            testUtils.form.clickDiscard(form);
            testUtils.dom.click($('.modal-footer button.btn-primary').first());
            assert.containsOnce(form, 'tr.o_data_row',
                "should have 1 data rows");

            form.destroy();
        });

        QUnit.test('one2many list (editable): edition, part 4', function (assert) {
            assert.expect(3);
            var i = 0;

            this.data.turtle.onchanges = {
                turtle_trululu: function (obj) {
                    if (i) {
                        obj.turtle_description = "Some Description";
                    }
                    i++;
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_trululu"/>' +
                    '<field name="turtle_description"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
            });

            // edit mode, then click on Add an item
            assert.containsNone(form, 'tr.o_data_row',
                "should have 0 data rows");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.strictEqual(form.$('textarea').val(), "",
                "field turtle_description should be empty");

            // add a value in the turtle_trululu field to trigger an onchange
            testUtils.fields.many2one.clickOpenDropdown('turtle_trululu');
            testUtils.fields.many2one.clickHighlightedItem('turtle_trululu');
            assert.strictEqual(form.$('textarea').val(), "Some Description",
                "field turtle_description should be set to the result of the onchange");
            form.destroy();
        });

        QUnit.test('one2many list (editable): discarding required empty data', function (assert) {
            assert.expect(7);

            this.data.turtle.fields.turtle_foo.required = true;
            delete this.data.turtle.fields.turtle_foo.default;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            // edit mode, then click on Add an item, then click elsewhere
            assert.containsNone(form, 'tr.o_data_row',
                "should have 0 data rows");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('label.o_form_label').first());
            assert.containsNone(form, 'tr.o_data_row',
                "should still have 0 data rows");

            // click on Add an item again, then click on save
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.form.clickSave(form);
            assert.containsNone(form, 'tr.o_data_row',
                "should still have 0 data rows");

            assert.verifySteps(['read', 'default_get', 'default_get']);
            form.destroy();
        });

        QUnit.test('editable one2many list, adding line when only one page', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [1, 2, 3];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a record, to reach the page size limit
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // the record currently being added should not count in the pager
            assert.isNotVisible(form.$('.o_field_widget[name=turtles] .o_cp_pager'));

            form.destroy();
        });

        QUnit.test('editable one2many list, adding line, then discarding', function (assert) {
            assert.expect(2);

            this.data.turtle.records.push({ id: 4, turtle_foo: 'stephen hawking' });
            this.data.partner.records[0].turtles = [1, 2, 3, 4];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a record, then discard
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.form.clickDiscard(form);

            // confirm the discard operation
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));

            assert.isVisible(form.$('.o_field_widget[name=turtles] .o_cp_pager'));
            assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_cp_pager').text().trim(), '1-3 / 4',
                "pager should display correct values");

            form.destroy();
        });

        QUnit.test('editable one2many list, required field and pager', function (assert) {
            assert.expect(1);

            this.data.turtle.records.push({ id: 4, turtle_foo: 'stephen hawking' });
            this.data.turtle.fields.turtle_foo.required = true;
            this.data.partner.records[0].turtles = [1, 2, 3, 4];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a (empty) record
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // go on next page. The new record is not valid and should be discarded
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));
            assert.containsOnce(form, 'tr.o_data_row');

            form.destroy();
        });

        QUnit.test('editable one2many list, required field, pager and confirm discard', function (assert) {
            assert.expect(3);

            this.data.turtle.records.push({ id: 4, turtle_foo: 'stephen hawking' });
            this.data.turtle.fields.turtle_foo.required = true;
            this.data.partner.records[0].turtles = [1, 2, 3, 4];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a record with a dirty state, but not valid
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('input[name="turtle_int"]'), 4321);

            // go to next page. The new record is not valid, but dirty. we should
            // see a confirm dialog
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_cp_pager').text().trim(), '1-3 / 4',
                "pager should still display the correct total");

            // click on cancel
            testUtils.dom.click($('.modal .modal-footer .btn-secondary'));

            assert.strictEqual(form.$('.o_field_widget[name=turtles] .o_cp_pager').text().trim(), '1-3 / 4',
                "pager should again display the correct total");
            assert.containsOnce(form, '.o_field_one2many input.o_field_invalid',
                "there should be an invalid input in the one2many");
            form.destroy();
        });

        QUnit.test('editable one2many list, adding, discarding, and pager', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // add a 4 records record (to make the pager appear)
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // go on next page
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            // discard
            testUtils.form.clickDiscard(form);
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));

            assert.containsOnce(form, 'tr.o_data_row');
            assert.isNotVisible(form.$('.o_field_widget[name=turtles] .o_cp_pager'));

            form.destroy();
        });

        QUnit.test('unselecting a line with missing required data', function (assert) {
            assert.expect(5);

            this.data.turtle.fields.turtle_foo.required = true;
            delete this.data.turtle.fields.turtle_foo.default;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
            });

            // edit mode, then click on Add an item, then click elsewhere
            assert.containsNone(form, 'tr.o_data_row',
                "should have 0 data rows");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, 'tr.o_data_row',
                "should have 1 data rows");

            // adding a value in the non required field, so it is dirty, but with
            // a missing required field
            testUtils.fields.editInput(form.$('input[name="turtle_int"]'), '12345');

            // click elsewhere,
            testUtils.dom.click(form.$('label.o_form_label'));
            assert.strictEqual($('.modal').length, 1,
                'a confirmation model should be opened');

            // click on cancel, the line should still be selected
            testUtils.dom.click($('.modal .modal-footer button.btn-secondary'));
            assert.containsOnce(form, 'tr.o_data_row.o_selected_row',
                "should still have 1 selected data row");

            // click elsewhere, and click on ok (on the confirmation dialog)
            testUtils.dom.click(form.$('label.o_form_label'));
            testUtils.dom.click($('.modal .modal-footer button.btn-primary'));
            assert.containsNone(form, 'tr.o_data_row',
                "should have 0 data rows (invalid line has been discarded");

            form.destroy();
        });

        QUnit.test('pressing enter in a o2m with a required empty field', function (assert) {
            assert.expect(4);

            this.data.turtle.fields.turtle_foo.required = true;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            // edit mode, then click on Add an item, then click elsewhere
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            form.$('input[name="turtle_foo"]').trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            assert.hasClass(form.$('input[name="turtle_foo"]'),'o_field_invalid',
                "input should be marked invalid");
            assert.verifySteps(['read', 'default_get']);
            form.destroy();
        });

        QUnit.test('editing a o2m, with required field and onchange', function (assert) {
            assert.expect(12);

            this.data.turtle.fields.turtle_foo.required = true;
            delete this.data.turtle.fields.turtle_foo.default;
            this.data.turtle.onchanges = {
                turtle_foo: function (obj) {
                    obj.turtle_int = obj.turtle_foo.length;
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    if (args.method) {
                        assert.step(args.method);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            // edit mode, then click on Add an item
            assert.containsNone(form, 'tr.o_data_row',
                "should have 0 data rows");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // input some text in required turtle_foo field
            testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), 'aubergine');
            assert.strictEqual(form.$('input[name="turtle_int"]').val(), "9",
                "onchange should have been triggered");

            // save and check everything is fine
            testUtils.form.clickSave(form);
            assert.strictEqual(form.$('.o_data_row td:contains(aubergine)').length, 1,
                "should have one row with turtle_foo value");
            assert.strictEqual(form.$('.o_data_row td:contains(9)').length, 1,
                "should have one row with turtle_int value");

            assert.verifySteps(['read', 'default_get', 'onchange', 'onchange', 'write', 'read', 'read']);
            form.destroy();
        });

        QUnit.test('editable o2m, pressing ESC discard current changes', function (assert) {
            assert.expect(5);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, 'tr.o_data_row',
                "there should be one data row");

            form.$('input[name="turtle_foo"]').trigger({ type: 'keydown', which: $.ui.keyCode.ESCAPE });
            assert.containsNone(form, 'tr.o_data_row',
                "data row should have been discarded");
            assert.verifySteps(['read', 'default_get']);
            form.destroy();
        });

        QUnit.test('editable o2m with required field, pressing ESC discard current changes', function (assert) {
            assert.expect(5);

            this.data.turtle.fields.turtle_foo.required = true;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, 'tr.o_data_row',
                "there should be one data row");

            form.$('input[name="turtle_foo"]').trigger({ type: 'keydown', which: $.ui.keyCode.ESCAPE });
            assert.containsNone(form, 'tr.o_data_row',
                "data row should have been discarded");
            assert.verifySteps(['read', 'default_get']);
            form.destroy();
        });

        QUnit.test('pressing escape in editable o2m list in dialog', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "partner,false,form": '<form>' +
                        '<field name="p">' +
                        '<tree editable="bottom">' +
                        '<field name="display_name"/>' +
                        '</tree>' +
                        '</field>' +
                        '</form>',
                },
                viewOptions: {
                    mode: 'edit',
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));

            assert.strictEqual($('.modal .o_data_row.o_selected_row').length, 1,
                "there should be a row in edition in the dialog");

            // trigger keydown ESCAPE in the edited row
            $('.modal .o_data_cell input').trigger({ type: 'keydown', which: $.ui.keyCode.ESCAPE });

            assert.strictEqual($('.modal').length, 1,
                "dialog should still be open");
            assert.strictEqual($('.modal .o_data_row').length, 0,
                "the row should have been removed");

            form.destroy();
        });

        QUnit.test('editable o2m with onchange and required field: delete an invalid line', function (assert) {
            assert.expect(5);

            this.data.partner.onchanges = {
                turtles: function () { },
            };
            this.data.partner.records[0].turtles = [1];
            this.data.turtle.records[0].product_id = 37;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                viewOptions: {
                    mode: 'edit',
                },
            });

            testUtils.dom.click(form.$('.o_data_cell:first'));
            form.$('.o_field_widget[name="product_id"] input').val('').trigger('keyup');
            assert.verifySteps(['read', 'read'], 'no onchange should be done as line is invalid');
            testUtils.dom.click(form.$('.o_list_record_remove'));
            assert.verifySteps(['read', 'read', 'onchange'], 'onchange should have been done');

            form.destroy();
        });

        QUnit.test('onchange in a one2many', function (assert) {
            assert.expect(1);

            this.data.partner.records.push({
                id: 3,
                foo: "relational record 1",
            });
            this.data.partner.records[1].p = [3];
            this.data.partner.onchanges = { p: true };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return $.when({
                            value: {
                                p: [
                                    [5],                             // delete all
                                    [0, 0, { foo: "from onchange" }],  // create new
                                ]
                            }
                        });
                    }
                    return this._super(route, args);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_one2many tbody td').first());
            testUtils.fields.editInput(form.$('.o_field_one2many tbody td').first().find('input'), "new value");
            testUtils.form.clickSave(form);

            assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'from onchange',
                "display name of first record in o2m list should be 'new value'");
            form.destroy();
        });

        QUnit.test('one2many, default_get and onchange (basic)', function (assert) {
            assert.expect(1);

            this.data.partner.fields.p.default = [
                [6, 0, []],                  // replace with zero ids
            ];
            this.data.partner.onchanges = { p: true };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return $.when({
                            value: {
                                p: [
                                    [5],                             // delete all
                                    [0, 0, { foo: "from onchange" }],  // create new
                                ]
                            }
                        });
                    }
                    return this._super(route, args);
                },
            });

            assert.ok(form.$('td:contains(from onchange)').length,
                "should have 'from onchange' value in one2many");
            form.destroy();
        });

        QUnit.test('one2many and default_get (with date)', function (assert) {
            assert.expect(1);

            this.data.partner.fields.p.default = [
                [0, false, { date: '2017-10-08' }],
            ];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="date"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            assert.strictEqual(form.$('.o_data_cell').text(), '10/08/2017',
                "should correctly display the date");

            form.destroy();
        });

        QUnit.test('one2many and onchange (with integer)', function (assert) {
            assert.expect(4);

            this.data.turtle.onchanges = {
                turtle_int: function (obj) { }
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('td:contains(9)'));
            testUtils.fields.editInput(form.$('td input[name="turtle_int"]'), "3");

            // the 'change' event is triggered on the input when we focus somewhere
            // else, for example by clicking in the body.  However, if we try to
            // programmatically click in the body, it does not trigger a change
            // event, so we simply trigger it directly instead.
            form.$('td input[name="turtle_int"]').trigger('change');

            assert.verifySteps(['read', 'read', 'onchange']);
            form.destroy();
        });

        QUnit.test('one2many and onchange (with date)', function (assert) {
            assert.expect(7);

            this.data.partner.onchanges = {
                date: function (obj) { }
            };
            this.data.partner.records[0].p = [2];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="date"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('td:contains(01/25/2017)'));
            testUtils.dom.click(form.$('.o_datepicker_input'));
            testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch').first());
            testUtils.dom.click($('.bootstrap-datetimepicker-widget .picker-switch:eq(1)'));
            testUtils.dom.click($('.bootstrap-datetimepicker-widget .year:contains(2017)'));
            testUtils.dom.click($('.bootstrap-datetimepicker-widget .month').eq(1));
            testUtils.dom.click($('.day:contains(22)'));

            testUtils.form.clickSave(form);

            assert.verifySteps(['read', 'read', 'onchange', 'write', 'read', 'read']);
            form.destroy();
        });

        QUnit.test('one2many and onchange (with command DELETE_ALL)', function (assert) {
            assert.expect(5);

            this.data.partner.onchanges = {
                foo: function (obj) {
                    obj.p = [[5]];
                },
                p: function () { }, // dummy onchange on the o2m to execute _isX2ManyValid()
            };
            this.data.partner.records[0].p = [2];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (method, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].p, [
                            [0, args.args[1].p[0][1], { display_name: 'z' }],
                            [2, 2, false],
                        ], "correct commands should be sent");
                    }
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "o2m should contain one row");

            // empty o2m by triggering the onchange
            testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'trigger onchange');

            assert.containsNone(form, '.o_data_row',
                "rows of the o2m should have been deleted");

            // add two new subrecords
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'x');
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'y');

            assert.containsN(form, '.o_data_row', 2,
                "o2m should contain two rows");

            // empty o2m by triggering the onchange
            testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'trigger onchange again');

            assert.containsNone(form, '.o_data_row',
                "rows of the o2m should have been deleted");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'z');

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('one2many and onchange only write modified field', function (assert) {
            assert.expect(2);

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5], // delete all
                        [1, 3, { // the server returns all fields
                            display_name: "coucou",
                            product_id: [37, "xphone"],
                            turtle_bar: false,
                            turtle_foo: "has changed",
                            turtle_int: 42,
                            turtle_qux: 9.8,
                            partner_ids: [],
                            turtle_ref: 'product,37',
                        }],
                    ];
                },
            };

            this.data.partner.records[0].turtles = [3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="product_id"/>' +
                    '<field name="turtle_bar"/>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_qux"/>' +
                    '<field name="turtle_ref"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (method, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].turtles, [
                            [1, 3, { display_name: 'coucou', turtle_foo: 'has changed', turtle_int: 42 }],
                        ], "correct commands should be sent (only send changed values)");
                    }
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "o2m should contain one row");

            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:first td:first'));
            testUtils.fields.editInput(form.$('.o_field_one2many .o_list_view tbody tr:first input:first'), 'blurp');

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('one2many with CREATE onchanges correctly refreshed', function (assert) {
            assert.expect(5);

            var delta = 0;
            testUtils.mock.patch(AbstractField, {
                init: function () {
                    delta++;
                    this._super.apply(this, arguments);
                },
                destroy: function () {
                    delta--;
                    this._super.apply(this, arguments);
                },
            });

            var deactiveOnchange = true;

            this.data.partner.records[0].turtles = [];
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    if (deactiveOnchange) { return; }
                    // the onchange will either:
                    //  - create a second line if there is only one line
                    //  - edit the second line if there are two lines
                    if (obj.turtles.length === 1) {
                        obj.turtles = [
                            [5], // delete all
                            [0, obj.turtles[0][1], {
                                display_name: "first",
                                turtle_int: obj.turtles[0][2].turtle_int,
                            }],
                            [0, 0, {
                                display_name: "second",
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            }],
                        ];
                    } else if (obj.turtles.length === 2) {
                        obj.turtles = [
                            [5], // delete all
                            [0, obj.turtles[0][1], {
                                display_name: "first",
                                turtle_int: obj.turtles[0][2].turtle_int,
                            }],
                            [0, obj.turtles[1][1], {
                                display_name: "second",
                                turtle_int: -obj.turtles[0][2].turtle_int,
                            }],
                        ];
                    }
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name" widget="char"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsNone(form, '.o_data_row',
                "o2m shouldn't contain any row");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            // trigger the first onchange
            deactiveOnchange = false;
            testUtils.fields.editInput(form.$('input[name="turtle_int"]'), '10');
            // put the list back in non edit mode
            testUtils.dom.click(form.$('input[name="foo"]'));
            assert.strictEqual(form.$('.o_data_row').text(), "first10second-10",
                "should correctly refresh the records");

            // trigger the second onchange
            testUtils.dom.click(form.$('.o_field_x2many_list tbody tr:first td:first'));
            testUtils.fields.editInput(form.$('input[name="turtle_int"]'), '20');

            testUtils.dom.click(form.$('input[name="foo"]'));
            assert.strictEqual(form.$('.o_data_row').text(), "first20second-20",
                "should correctly refresh the records");

            assert.containsN(form, '.o_field_widget', delta,
                "all (non visible) field widgets should have been destroyed");

            testUtils.form.clickSave(form);

            assert.strictEqual(form.$('.o_data_row').text(), "first20second-20",
                "should correctly refresh the records after save");

            form.destroy();
            testUtils.mock.unpatch(AbstractField);
        });

        QUnit.test('editable one2many with sub widgets are rendered in readonly', function (assert) {
            assert.expect(2);

            var editableWidgets = 0;
            testUtils.mock.patch(AbstractField, {
                init: function () {
                    this._super.apply(this, arguments);
                    if (this.mode === 'edit') {
                        editableWidgets++;
                    }
                },
            });

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo" widget="char" attrs="{\'readonly\': [(\'turtle_int\', \'==\', 11111)]}"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.strictEqual(editableWidgets, 1,
                "o2m is only widget in edit mode");
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));

            assert.strictEqual(editableWidgets, 3,
                "3 widgets currently in edit mode");

            form.destroy();
            testUtils.mock.unpatch(AbstractField);
        });

        QUnit.test('one2many editable list with onchange keeps the order', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].p = [1, 2, 4];
            this.data.partner.onchanges = {
                p: function () { },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.strictEqual(form.$('.o_data_cell').text(), 'first recordsecond recordaaa',
                "records should be display in the correct order");

            testUtils.dom.click(form.$('.o_data_row:first .o_data_cell'));
            testUtils.fields.editInput(form.$('.o_selected_row .o_field_widget[name=display_name]'), 'new');
            testUtils.dom.click(form.$el);

            assert.strictEqual(form.$('.o_data_cell').text(), 'newsecond recordaaa',
                "records should be display in the correct order");

            form.destroy();
        });

        QUnit.test('one2many list (editable): readonly domain is evaluated', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].p = [2, 4];
            this.data.partner.records[1].product_id = false;
            this.data.partner.records[2].product_id = 37;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="display_name" attrs=\'{"readonly": [["product_id", "=", false]]}\'/>' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);

            assert.hasClass(form.$('.o_list_view tbody tr:eq(0) td:first'),'o_readonly_modifier',
                "first record should have display_name in readonly mode");

            assert.doesNotHaveClass(form.$('.o_list_view tbody tr:eq(1) td:first'), 'o_readonly_modifier',
                "second record should not have display_name in readonly mode");
            form.destroy();
        });

        QUnit.test('pager of one2many field in new record', function (assert) {
            assert.expect(3);

            this.data.partner.records[0].p = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                        '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            assert.ok(!form.$('.o_x2m_control_panel .o_cp_pager div').is(':visible'),
                'o2m pager should be hidden');

            // click to create a subrecord
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, 'tr.o_data_row');

            assert.ok(!form.$('.o_x2m_control_panel .o_cp_pager div').is(':visible'),
                'o2m pager should be hidden');
            form.destroy();
        });

        QUnit.test('one2many list with a many2one', function (assert) {
            assert.expect(5);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[1].product_id = 37;
            this.data.partner.onchanges.p = function (obj) {
                obj.p = [
                    [5], // delete all
                    [1, 2, { product_id: [37, "xphone"] }], // update existing record
                    [0, 0, { product_id: [41, "xpad"] }]
                ];
                //
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                archs: {
                    'partner,false,form':
                        '<form string="Partner"><field name="product_id"/></form>',
                },
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        assert.deepEqual(args.args[1].p, [[4, 2, false], [0, args.args[1].p[1][1], { product_id: 41 }]],
                            "should trigger onchange with correct parameters");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.strictEqual(form.$('tbody td:contains(xphone)').length, 1,
                "should have properly fetched the many2one nameget");
            assert.strictEqual(form.$('tbody td:contains(xpad)').length, 0,
                "should not display 'xpad' anywhere");

            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));

            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickItem('product_id', 'xpad');

            testUtils.dom.click($('.modal .modal-footer button:eq(0)'));

            assert.strictEqual(form.$('tbody td:contains(xpad)').length, 1,
                "should display 'xpad' on a td");
            assert.strictEqual(form.$('tbody td:contains(xphone)').length, 1,
                "should still display xphone");
            form.destroy();
        });

        QUnit.test('one2many list with inline form view', function (assert) {
            assert.expect(5);

            this.data.partner.records[0].p = [];

            var rpcCount = 0;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<form string="Partner">' +
                    '<field name="product_id"/>' +
                    '<field name="int_field"/>' +
                    '</form>' +
                    '<tree>' +
                    '<field name="product_id"/>' +
                    '<field name="foo"/>' +  // don't remove this, it is
                    // useful to make sure the foo fieldwidget
                    // does not crash because the foo field
                    // is not in the form view
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    rpcCount++;
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].p, [[0, args.args[1].p[0][1], {
                            foo: false, int_field: 123, product_id: 41,
                        }]]);
                    }
                    return this._super(route, args);
                },
            });

            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));

            // write in the many2one field, value = 37 (xphone)
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickHighlightedItem('product_id');

            // write in the integer field
            testUtils.fields.editInput($('.modal .modal-body input.o_field_widget'), '123');

            // save and close
            testUtils.dom.click($('.modal .modal-footer button:eq(0)'));

            assert.strictEqual(form.$('tbody td:contains(xphone)').length, 1,
                "should display 'xphone' in a td");

            // reopen the record in form view
            testUtils.dom.click(form.$('tbody td:contains(xphone)'));

            assert.strictEqual($('.modal .modal-body input').val(), "xphone",
                "should display 'xphone' in an input");

            testUtils.fields.editInput($('.modal .modal-body input.o_field_widget'), '456');

            // discard
            testUtils.dom.click($('.modal .modal-footer span:contains(Discard)'));

            // reopen the record in form view
            testUtils.dom.click(form.$('tbody td:contains(xphone)'));

            assert.strictEqual($('.modal .modal-body input.o_field_widget').val(), "123",
                "should display 123 (previous change has been discarded)");

            // write in the many2one field, value = 41 (xpad)
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickItem('product_id', 'xpad');

            // save and close
            testUtils.dom.click($('.modal .modal-footer button:eq(0)'));

            assert.strictEqual(form.$('tbody td:contains(xpad)').length, 1,
                "should display 'xpad' in a td");

            // save the record
            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('one2many list with inline form view with context with parent key', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[0].product_id = 41;
            this.data.partner.records[1].product_id = 37;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="product_id"/>' +
                    '<field name="p">' +
                    '<form string="Partner">' +
                    '<field name="product_id" context="{\'partner_foo\':parent.foo, \'lalala\': parent.product_id}"/>' +
                    '</form>' +
                    '<tree>' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'name_search') {
                        assert.strictEqual(args.kwargs.context.partner_foo, "yop",
                            "should have correctly evaluated parent foo field");
                        assert.strictEqual(args.kwargs.context.lalala, 41,
                            "should have correctly evaluated parent product_id field");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            // open a modal
            testUtils.dom.click(form.$('tr.o_data_row:eq(0) td:contains(xphone)'));

            // write in the many2one field
            testUtils.dom.click($('.modal .o_field_many2one input'));

            form.destroy();
        });

        QUnit.test('value of invisible x2many fields is correctly evaluated in context', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].timmy = [12];
            this.data.partner.records[0].p = [2, 3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="product_id" context="{\'p\': p, \'timmy\': timmy}"/>' +
                    '<field name="p" invisible="1"/>' +
                    '<field name="timmy" invisible="1"/>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'name_search') {
                        assert.deepEqual(
                            args.kwargs.context, {
                                p: [[4, 2, false], [4, 3, false]],
                                timmy: [[6, false, [12]]],
                            }, 'values of x2manys should have been correctly evaluated in context');
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget[name=product_id] input'));

            form.destroy();
        });

        QUnit.test('one2many list, editable, with many2one and with context with parent key', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[1].product_id = 37;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="product_id" context="{\'partner_foo\':parent.foo}"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'name_search') {
                        assert.strictEqual(args.kwargs.context.partner_foo, "yop",
                            "should have correctly evaluated parent foo field");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('tr.o_data_row:eq(0) td:contains(xphone)'));

            // trigger a name search
            testUtils.dom.click(form.$('table td input'));

            form.destroy();
        });

        QUnit.test('one2many list, editable, with a date in the context', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[1].product_id = 37;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="date"/>' +
                    '<field name="p" context="{\'date\':date}">' +
                    '<tree editable="top">' +
                    '<field name="date"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 2,
                mockRPC: function (route, args) {
                    if (args.method === 'default_get') {
                        assert.strictEqual(args.kwargs.context.date, '2017-01-25',
                            "should have properly evaluated date key in context");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            form.destroy();
        });

        QUnit.test('one2many field with context', function (assert) {
            assert.expect(2);

            var counter = 0;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles" context="{\'turtles\':turtles}">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'default_get') {
                        var expected = counter === 0 ?
                            [[4, 2, false]] :
                            [[4, 2, false], [0, args.kwargs.context.turtles[1][1], { turtle_foo: 'hammer' }]];
                        assert.deepEqual(args.kwargs.context.turtles, expected,
                            "should have properly evaluated turtles key in context");
                        counter++;
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), 'hammer');
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            form.destroy();
        });

        QUnit.test('one2many list edition, some basic functionality', function (assert) {
            assert.expect(3);

            this.data.partner.fields.foo.default = false;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));

            assert.containsOnce(form, 'td input.o_field_widget',
                "should have created a row in edit mode");

            testUtils.fields.editInput(form.$('td input.o_field_widget'), 'a');

            assert.containsOnce(form, 'td input.o_field_widget',
                "should not have unselected the row after edition");

            testUtils.fields.editInput(form.$('td input.o_field_widget'), 'abc');
            testUtils.form.clickSave(form);

            assert.strictEqual(form.$('td:contains(abc)').length, 1,
                "should have a row with the correct value");
            form.destroy();
        });

        QUnit.test('one2many list, the context is properly evaluated and sent', function (assert) {
            assert.expect(2);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="p" context="{\'hello\': \'world\', \'abc\': int_field}">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'default_get') {
                        var context = args.kwargs.context;
                        assert.strictEqual(context.hello, "world");
                        assert.strictEqual(context.abc, 10);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            form.destroy();
        });

        QUnit.test('one2many with many2many widget: create', function (assert) {
            assert.expect(10);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles" widget="many2many">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_qux"/>' +
                    '<field name="turtle_int"/>' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '<form>' +
                    '<group>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_bar"/>' +
                    '<field name="turtle_int"/>' +
                    '<field name="product_id"/>' +
                    '</group>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'turtle,false,list': '<tree><field name="display_name"/><field name="turtle_foo"/><field name="turtle_bar"/><field name="product_id"/></tree>',
                    'turtle,false,search': '<search><field name="turtle_foo"/><field name="turtle_bar"/><field name="product_id"/></search>',
                },
                session: {},
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/turtle/create') {
                        assert.ok(args.args, "should write on the turtle record");
                    }
                    if (route === '/web/dataset/call_kw/partner/write') {
                        assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                        assert.strictEqual(args.args[1].turtles[0][0], 6, "should send only a 'replace with' command");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.strictEqual($('.modal .o_data_row').length, 2,
                "sould have 2 records in the select view (the last one is not displayed because it is already selected)");

            testUtils.dom.click($('.modal .o_data_row:first .o_list_record_selector input'));
            testUtils.dom.click($('.modal .o_select_button'));
            testUtils.dom.click($('.o_form_button_save'));
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.strictEqual($('.modal .o_data_row').length, 1,
                "sould have 1 record in the select view");

            testUtils.dom.click($('.modal-footer button:eq(1)'));
            testUtils.fields.editInput($('.modal input.o_field_widget[name="turtle_foo"]'), 'tototo');
            testUtils.fields.editInput($('.modal input.o_field_widget[name="turtle_int"]'), 50);
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickHighlightedItem('product_id');

            testUtils.dom.click($('.modal-footer button:contains(&):first'));

            assert.strictEqual($('.modal').length, 0, "sould close the modals");

            assert.containsN(form, '.o_data_row', 3,
                "sould have 3 records in one2many list");
            assert.strictEqual(form.$('.o_data_row').text(), "blip1.59yop1.50tototo1.550xphone",
                "should display the record values in one2many list");

            testUtils.dom.click($('.o_form_button_save'));

            form.destroy();
        });

        QUnit.test('one2many with many2many widget: edition', function (assert) {
            assert.expect(7);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles" widget="many2many">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_qux"/>' +
                    '<field name="turtle_int"/>' +
                    '<field name="product_id"/>' +
                    '</tree>' +
                    '<form>' +
                    '<group>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_bar"/>' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_trululu"/>' +
                    '<field name="product_id"/>' +
                    '</group>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'turtle,false,list': '<tree><field name="display_name"/><field name="turtle_foo"/><field name="turtle_bar"/><field name="product_id"/></tree>',
                    'turtle,false,search': '<search><field name="turtle_foo"/><field name="turtle_bar"/><field name="product_id"/></search>',
                },
                session: {},
                res_id: 1,
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/turtle/write') {
                        assert.strictEqual(args.args[0].length, 1, "should write on the turtle record");
                        assert.deepEqual(args.args[1], { "product_id": 37 }, "should write only the product_id on the turtle record");
                    }
                    if (route === '/web/dataset/call_kw/partner/write') {
                        assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                        assert.strictEqual(args.args[1].turtles[0][0], 6, "should send only a 'replace with' command");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.dom.click(form.$('.o_data_row:first'));
            assert.strictEqual($('.modal .modal-title').first().text().trim(), 'Open: one2many turtle field',
                "modal should use the python field string as title");
            testUtils.dom.click($('.modal .o_form_button_cancel'));
            testUtils.form.clickEdit(form);

            // edit the first one2many record
            testUtils.dom.click(form.$('.o_data_row:first'));
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickHighlightedItem('product_id');
            testUtils.dom.click($('.modal-footer button:first'));

            testUtils.dom.click($('.o_form_button_save'));

            // add a one2many record
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click($('.modal .o_data_row:first .o_list_record_selector input'));
            testUtils.dom.click($('.modal .o_select_button'));

            // edit the second one2many record
            testUtils.dom.click(form.$('.o_data_row:eq(1)'));
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickHighlightedItem('product_id');
            testUtils.dom.click($('.modal-footer button:first'));

            testUtils.dom.click($('.o_form_button_save'));

            form.destroy();
        });

        QUnit.test('new record, the context is properly evaluated and sent', function (assert) {
            assert.expect(2);

            this.data.partner.fields.int_field.default = 17;
            var n = 0;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="p" context="{\'hello\': \'world\', \'abc\': int_field}">' +
                    '<tree editable="top">' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'default_get') {
                        n++;
                        if (n === 2) {
                            var context = args.kwargs.context;
                            assert.strictEqual(context.hello, "world");
                            assert.strictEqual(context.abc, 17);
                        }
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            form.destroy();
        });

        QUnit.test('parent data is properly sent on an onchange rpc', function (assert) {
            assert.expect(1);

            this.data.partner.onchanges = { bar: function () { } };
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                    '<tree editable="top">' +
                    '<field name="bar"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        var fieldValues = args.args[1];
                        assert.strictEqual(fieldValues.trululu.foo, "yop",
                            "should have properly sent the parent foo value");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            form.destroy();
        });

        QUnit.test('parent data is properly sent on an onchange rpc, new record', function (assert) {
            assert.expect(6);

            this.data.turtle.onchanges = { turtle_bar: function () { } };
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_bar"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    if (args.method === 'onchange' && args.model === 'turtle') {
                        var fieldValues = args.args[1];
                        assert.strictEqual(fieldValues.turtle_trululu.foo, "My little Foo Value",
                            "should have properly sent the parent foo value");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            assert.verifySteps(['default_get', 'onchange', 'default_get', 'onchange']);
            form.destroy();
        });

        QUnit.test('id in one2many obtained in onchange is properly set', function (assert) {
            assert.expect(1);

            this.data.partner.onchanges.turtles = function (obj) {
                obj.turtles = [
                    [5],
                    [1, 3, { turtle_foo: "kawa" }]
                ];
            };
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="id"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            assert.strictEqual(form.$('tr.o_data_row').text(), '3kawa',
                "should have properly displayed id and foo field");
            form.destroy();
        });

        QUnit.test('id field in one2many in a new record', function (assert) {
            assert.expect(1);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="id" invisible="1"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'create') {
                        var virtualID = args.args[0].turtles[0][1];
                        assert.deepEqual(args.args[0].turtles,
                            [[0, virtualID, { turtle_foo: "cat" }]],
                            'should send proper commands');
                    }
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.dom.click(form.$('td.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('td input[name="turtle_foo"]'), 'cat');
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('sub form view with a required field', function (assert) {
            assert.expect(2);
            this.data.partner.fields.foo.required = true;
            this.data.partner.fields.foo.default = null;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<form string="Partner">' +
                    '<group><field name="foo"/></group>' +
                    '</form>' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('tbody td.o_field_x2many_list_row_add a'));
            testUtils.dom.click($('.modal-footer button.btn-primary').first());

            assert.strictEqual($('.modal').length, 1, "should still have an open modal");
            assert.strictEqual($('.modal tbody label.o_field_invalid').length, 1,
                "should have displayed invalid fields");
            form.destroy();
        });

        QUnit.test('one2many list with action button', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].p = [2];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo"/>' +
                    '<button name="method_name" type="object" icon="fa-plus"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                intercepts: {
                    execute_action: function (event) {
                        assert.deepEqual(event.data.env.currentID, 2,
                            'should call with correct id');
                        assert.strictEqual(event.data.env.model, 'partner',
                            'should call with correct model');
                        assert.strictEqual(event.data.action_data.name, 'method_name',
                            "should call correct method");
                        assert.strictEqual(event.data.action_data.type, 'object',
                            'should have correct type');
                    },
                },
            });

            testUtils.dom.click(form.$('.o_list_button button'));

            form.destroy();
        });

        QUnit.test('one2many kanban with action button', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].p = [2];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<kanban>' +
                    '<field name="foo"/>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div>' +
                    '<span><t t-esc="record.foo.value"/></span>' +
                    '<button name="method_name" type="object" class="fa fa-plus"/>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                intercepts: {
                    execute_action: function (event) {
                        assert.deepEqual(event.data.env.currentID, 2,
                            'should call with correct id');
                        assert.strictEqual(event.data.env.model, 'partner',
                            'should call with correct model');
                        assert.strictEqual(event.data.action_data.name, 'method_name',
                            "should call correct method");
                        assert.strictEqual(event.data.action_data.type, 'object',
                            'should have correct type');
                    },
                },
            });

            testUtils.dom.click(form.$('.oe_kanban_action_button'));

            form.destroy();
        });

        QUnit.test('one2many kanban with edit type action and domain widget (widget using SpecialData)', function (assert) {
            assert.expect(1);

            this.data.turtle.fields.model_name = { string: "Domain Condition Model", type: "char" };
            this.data.turtle.fields.condition = { string: "Domain Condition", type: "char" };
            _.each(this.data.turtle.records, function (record) {
                record.model_name = 'partner';
                record.condition = '[]';
            });

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles" mode="kanban">' +
                    '<kanban>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div><field name="display_name"/></div>' +
                    '<div><field name="turtle_foo"/></div>' +
                    // field without Widget in the list
                    '<div><field name="condition"/></div>' +
                    '<div> <a type="edit"> Edit </a> </div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '<form>' +
                    '<field name="product_id" widget="statusbar"/>' +
                    '<field name="model_name"/>' +
                    // field with Widget requiring specialData in the form
                    '<field name="condition" widget="domain" options="{\'model\': \'model_name\'}"/>' +
                    '</form>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.dom.click(form.$('.oe_kanban_action:eq(0)'));
            assert.strictEqual($('.o_domain_selector').length, 1, "should add domain selector widget");
            form.destroy();
        });

        QUnit.test('one2many list with onchange and domain widget (widget using SpecialData)', function (assert) {
            assert.expect(3);

            this.data.turtle.fields.model_name = { string: "Domain Condition Model", type: "char" };
            this.data.turtle.fields.condition = { string: "Domain Condition", type: "char" };
            _.each(this.data.turtle.records, function (record) {
                record.model_name = 'partner';
                record.condition = '[]';
            });
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    var virtualID = obj.turtles[1][1];
                    obj.turtles = [
                        [5], // delete all
                        [0, virtualID, {
                            display_name: "coucou",
                            product_id: [37, "xphone"],
                            turtle_bar: false,
                            turtle_foo: "has changed",
                            turtle_int: 42,
                            turtle_qux: 9.8,
                            partner_ids: [],
                            turtle_ref: 'product,37',
                            model_name: 'partner',
                            condition: '[]',
                        }],
                    ];
                },
            };
            var nbFetchSpecialDomain = 0;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles" mode="tree">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '<field name="turtle_foo"/>' +
                    // field without Widget in the list
                    '<field name="condition"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="model_name"/>' +
                    // field with Widget requiring specialData in the form
                    '<field name="condition" widget="domain" options="{\'model\': \'model_name\'}"/>' +
                    '</form>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
                mockRPC: function (route) {
                    if (route === '/web/dataset/call_kw/partner/search_count') {
                        nbFetchSpecialDomain++;
                    }
                    return this._super.apply(this, arguments);
                }
            });

            testUtils.dom.click(form.$('.o_field_one2many .o_field_x2many_list_row_add a'));
            assert.strictEqual($('.modal').length, 1, "form view dialog should be opened");
            testUtils.fields.editInput($('.modal-body input[name="model_name"]'), 'partner');
            testUtils.dom.click($('.modal-footer button:first'));

            assert.strictEqual(form.$('.o_field_one2many tbody tr:first').text(), "coucouhas changed[]",
                "the onchange should create one new record and remove the existing");

            testUtils.dom.click(form.$('.o_field_one2many .o_list_view tbody tr:eq(0) td:first'));

            testUtils.form.clickSave(form);
            assert.strictEqual(nbFetchSpecialDomain, 1,
                "should only fetch special domain once");
            form.destroy();
        });

        QUnit.test('one2many without inline tree arch', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [2, 3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="p" widget="many2many_tags"/>' + // check if the view don not call load view (widget without useSubview)
                    '<field name="turtles"/>' +
                    '<field name="timmy" invisible="1"/>' + // check if the view don not call load view in invisible
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,list": '<tree string="Turtles"><field name="turtle_bar"/><field name="display_name"/><field name="partner_ids"/></tree>',
                }
            });

            assert.containsOnce(form, '.o_field_widget[name="turtles"] .o_list_view',
                'should display one2many list view in the modal');

            assert.containsN(form, '.o_data_row', 2,
                'should display the 2 turtles');

            form.destroy();
        });

        QUnit.test('many2one and many2many in one2many', function (assert) {
            assert.expect(11);

            this.data.turtle.records[1].product_id = 37;
            this.data.partner.records[0].turtles = [2, 3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<form string="Turtles">' +
                    '<group>' +
                    '<field name="product_id"/>' +
                    '</group>' +
                    '</form>' +
                    '<tree editable="top">' +
                    '<field name="display_name"/>' +
                    '<field name="product_id"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        var commands = args.args[1].turtles;
                        assert.strictEqual(commands.length, 2,
                            "should have generated 2 commands");
                        assert.deepEqual(commands[0], [1, 2, {
                            partner_ids: [[6, false, [2, 1]]],
                            product_id: 41,
                        }], "generated commands should be correct");
                        assert.deepEqual(commands[1], [4, 3, false],
                            "generated commands should be correct");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, '.o_data_row', 2,
                'should display the 2 turtles');
            assert.strictEqual(form.$('.o_data_row:first td:nth(1)').text(), 'xphone',
                "should correctly display the m2o");
            assert.strictEqual(form.$('.o_data_row:first td:nth(2) .badge').length, 2,
                "m2m should contain two tags");
            assert.strictEqual(form.$('.o_data_row:first td:nth(2) .badge:first span').text(),
                'second record', "m2m values should have been correctly fetched");

            testUtils.dom.click(form.$('.o_data_row:first'));

            assert.strictEqual($('.modal .o_field_widget').text(), "xphone",
                'should display the form view dialog with the many2one value');
            testUtils.dom.click($('.modal-footer button'));

            testUtils.form.clickEdit(form);

            // edit the m2m of first row
            testUtils.dom.click(form.$('.o_list_view tbody td:first()'));
            // remove a tag
            testUtils.dom.click(form.$('.o_field_many2manytags .badge:contains(aaa) .o_delete'));
            assert.strictEqual(form.$('.o_selected_row .o_field_many2manytags .o_badge_text:contains(aaa)').length, 0,
                "tag should have been correctly removed");
            // add a tag
            testUtils.fields.many2one.clickOpenDropdown('partner_ids');
            testUtils.fields.many2one.clickHighlightedItem('partner_ids');
            assert.strictEqual(form.$('.o_selected_row .o_field_many2manytags .o_badge_text:contains(first record)').length, 1,
                "tag should have been correctly added");

            // edit the m2o of first row
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickItem('product_id', 'xpad');
            assert.strictEqual(form.$('.o_selected_row .o_field_many2one:first input').val(), 'xpad',
                "m2o value should have been updated");

            // save (should correctly generate the commands)
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('many2manytag in one2many, onchange, some modifiers, and more than one page', function (assert) {
            assert.expect(9);

            this.data.partner.records[0].turtles = [1, 2, 3];

            this.data.partner.onchanges.turtles = function () { };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top" limit="2">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" widget="many2many_tags" attrs="{\'readonly\': [(\'turtle_foo\', \'=\', \'a\')]}"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: { mode: 'edit' },
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            assert.containsN(form, '.o_data_row', 2,
                'there should be only 2 rows displayed');
            testUtils.dom.clickFirst(form.$('.o_list_record_remove'));
            testUtils.dom.clickFirst(form.$('.o_list_record_remove'));

            assert.containsOnce(form, '.o_data_row',
                'there should be just one remaining row');

            assert.verifySteps([
                "read",  // initial read on partner
                "read",  // initial read on turtle
                "read",  // batched read on partner (field partner_ids)
                "read",  // after first delete, read on turtle (to fetch 3rd record)
                "onchange",  // after first delete, onchange on field turtles
                "onchange"   // onchange after second delete
            ]);

            form.destroy();
        });

        QUnit.test('onchange many2many in one2many list editable', function (assert) {
            assert.expect(14);

            this.data.product.records.push({
                id: 1,
                display_name: "xenomorphe",
            });

            this.data.turtle.onchanges = {
                product_id: function (rec) {
                    if (rec.product_id) {
                        rec.partner_ids = [
                            [5],
                            [4, rec.product_id === 41 ? 1 : 2]
                        ];
                    }
                },
            };
            var partnerOnchange = function (rec) {
                if (!rec.int_field || !rec.turtles.length) {
                    return;
                }
                rec.turtles = [
                    [5],
                    [0, 0, {
                        display_name: 'new line',
                        product_id: [37, 'xphone'],
                        partner_ids: [
                            [5],
                            [4, 1]
                        ]
                    }],
                    [0, rec.turtles[0][1], {
                        display_name: rec.turtles[0][2].display_name,
                        product_id: [1, 'xenomorphe'],
                        partner_ids: [
                            [5],
                            [4, 2]
                        ]
                    }],
                ];
            };

            this.data.partner.onchanges = {
                int_field: partnerOnchange,
                turtles: partnerOnchange,
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '<field name="product_id"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
            });

            // add new line (first, xpad)
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('input[name="display_name"]'), 'first');
            testUtils.dom.click(form.$('div[name="product_id"] input'));
            // the onchange won't be generated
            testUtils.dom.click($('li.ui-menu-item a:contains(xpad)').trigger('mouseenter'));

            assert.containsOnce(form, '.o_field_many2manytags.o_input',
                'should display the line in editable mode');
            assert.strictEqual(form.$('.o_field_many2one input').val(), "xpad",
                'should display the product xpad');
            assert.strictEqual(form.$('.o_field_many2manytags.o_input .o_badge_text').text(), "first record",
                'should display the tag from the onchange');

            testUtils.dom.click(form.$('input.o_field_integer[name="int_field"]'));

            assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xpad",
                'should display the product xpad');
            assert.strictEqual(form.$('.o_field_many2manytags:not(.o_input) .o_badge_text').text(), "first record",
                'should display the tag in readonly');

            // enable the many2many onchange and generate it
            testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), '10');

            assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xenomorphexphone",
                'should display the product xphone and xenomorphe');
            assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
                'should display the name, one2many and many2many value');

            // disable the many2many onchange
            testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), '0');

            // remove and start over
            testUtils.dom.click(form.$('.o_list_record_remove:first button'));
            testUtils.dom.click(form.$('.o_list_record_remove:first button'));

            // enable the many2many onchange
            testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), '10');

            // add new line (first, xenomorphe)
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('input[name="display_name"]'), 'first');
            testUtils.dom.click(form.$('div[name="product_id"] input'));
            // generate the onchange
            testUtils.dom.click($('li.ui-menu-item a:contains(xenomorphe)').trigger('mouseenter'));

            assert.containsOnce(form, '.o_field_many2manytags.o_input',
                'should display the line in editable mode');
            assert.strictEqual(form.$('.o_field_many2one input').val(), "xenomorphe",
                'should display the product xenomorphe');
            assert.strictEqual(form.$('.o_field_many2manytags.o_input .o_badge_text').text(), "second record",
                'should display the tag from the onchange');

            // put list in readonly mode
            testUtils.dom.click(form.$('input.o_field_integer[name="int_field"]'));

            assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xenomorphexphone",
                'should display the product xphone and xenomorphe');
            assert.strictEqual(form.$('.o_field_many2manytags:not(.o_input) .o_badge_text').text(), "second recordfirst record",
                'should display the tag in readonly (first record and second record)');

            testUtils.fields.editInput(form.$('input.o_field_integer[name="int_field"]'), '10');

            assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
                'should display the name, one2many and many2many value');

            testUtils.form.clickSave(form);

            assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
                'should display the name, one2many and many2many value after save');

            form.destroy();
        });

        QUnit.test('load view for x2many in one2many', function (assert) {
            assert.expect(2);

            this.data.turtle.records[1].product_id = 37;
            this.data.partner.records[0].turtles = [2, 3];
            this.data.partner.records[2].turtles = [1, 3];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<form string="Turtles">' +
                    '<group>' +
                    '<field name="product_id"/>' +
                    '<field name="partner_ids"/>' +
                    '</group>' +
                    '</form>' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "partner,false,list": '<tree string="Partners"><field name="display_name"/></tree>',
                },
            });

            assert.containsN(form, '.o_data_row', 2,
                'should display the 2 turtles');

            testUtils.dom.click(form.$('.o_data_row:first'));

            assert.strictEqual($('.modal .o_field_widget[name="partner_ids"] .o_list_view').length, 1,
                'should display many2many list view in the modal');

            form.destroy();
        });

        QUnit.test('one2many (who contains a one2many) with tree view and without form view', function (assert) {
            assert.expect(1);

            // avoid error in _postprocess

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="partner_ids"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,form": '<form string="Turtles"><field name="turtle_foo"/></form>',
                },
            });

            testUtils.dom.click(form.$('.o_data_row:first'));

            assert.strictEqual($('.modal .o_field_widget[name="turtle_foo"]').text(), 'blip',
                'should open the modal and display the form field');

            form.destroy();
        });

        QUnit.test('one2many with x2many in form view (but not in list view)', function (assert) {
            assert.expect(1);

            // avoid error when saving the edited related record (because the
            // related x2m field is unknown in the inline list view)
            // also ensure that the changes are correctly saved

            this.data.turtle.fields.o2m = { string: "o2m", type: "one2many", relation: 'user' };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,form": '<form string="Turtles">' +
                        '<field name="partner_ids" widget="many2many_tags"/>' +
                        '</form>',
                },
                viewOptions: {
                    mode: 'edit',
                },
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].turtles, [[1, 2, {
                            partner_ids: [[6, false, [2, 4, 1]]],
                        }]]);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.dom.click(form.$('.o_data_row:first')); // edit first record

            testUtils.fields.many2one.clickOpenDropdown('partner_ids');
            testUtils.fields.many2one.clickHighlightedItem('partner_ids');

            // add a many2many tag and save
            testUtils.dom.click($('.modal .o_field_many2manytags input'));
            testUtils.fields.editInput($('.modal .o_field_many2manytags input'), 'test');
            testUtils.dom.click($('.modal .modal-footer .btn-primary')); // save

            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('many2many list in a one2many opened by a many2one', function (assert) {
            assert.expect(1);

            this.data.turtle.records[1].turtle_trululu = 2;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_trululu"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "partner,false,form": '<form string="P">' +
                        '<field name="timmy"/>' +
                        '</form>',
                    "partner_type,false,list": '<tree editable="bottom">' +
                        '<field name="display_name"/>' +
                        '</tree>',
                    "partner_type,false,search": '<search>' +
                        '</search>',
                },
                viewOptions: {
                    mode: 'edit',
                },
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/get_formview_id') {
                        return $.when(false);
                    }
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].timmy, [[6, false, [12]]],
                            'should properly write ids');
                    }
                    return this._super.apply(this, arguments);
                },
            });

            // edit the first partner in the one2many partner form view
            testUtils.dom.click(form.$('.o_data_row:first td.o_data_cell'));
            // open form view for many2one
            testUtils.dom.click(form.$('.o_external_button'));

            // click on add, to add a new partner in the m2m
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));

            // select the partner_type 'gold' (this closes the 2nd modal)
            testUtils.dom.click($('.modal td:contains(gold)'));

            // confirm the changes in the modal
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('nested x2many default values', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.model === 'partner' && args.method === 'default_get') {
                        return $.when({
                            turtles: [
                                [0, 0, { partner_ids: [[6, 0, [4]]] }],
                                [0, 0, { partner_ids: [[6, 0, [1]]] }],
                            ],
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsN(form, '.o_list_view .o_data_row', 2,
                "one2many list should contain 2 rows");
            assert.containsN(form, '.o_list_view .o_field_many2manytags[name="partner_ids"] .badge', 2,
                "m2mtags should contain two tags");
            assert.strictEqual(form.$('.o_list_view .o_field_many2manytags[name="partner_ids"] .o_badge_text').text(),
                'aaafirst record', "tag names should have been correctly loaded");

            form.destroy();
        });

        QUnit.test('one2many (who contains display_name) with tree view and without form view', function (assert) {
            assert.expect(1);

            // avoid error in _fetchX2Manys

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,form": '<form string="Turtles"><field name="turtle_foo"/></form>',
                },
            });

            testUtils.dom.click(form.$('.o_data_row:first'));

            assert.strictEqual($('.modal .o_field_widget[name="turtle_foo"]').text(), 'blip',
                'should open the modal and display the form field');

            form.destroy();
        });

        QUnit.test('one2many field with virtual ids', function (assert) {
            assert.expect(11);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<notebook>' +
                    '<page>' +
                    '<field name="p" mode="kanban">' +
                    '<kanban>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div class="oe_kanban_details">' +
                    '<div class="o_test_id">' +
                    '<field name="id"/>' +
                    '</div>' +
                    '<div class="o_test_foo">' +
                    '<field name="foo"/>' +
                    '</div>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                archs: {
                    'partner,false,form': '<form string="Associated partners">' +
                        '<field name="foo"/>' +
                        '</form>',
                },
                res_id: 4,
            });

            assert.containsOnce(form, '.o_field_widget .o_kanban_view',
                "should have one inner kanban view for the one2many field");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 0,
                "should not have kanban records yet");

            // // switch to edit mode and create a new kanban record
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget .o-kanban-button-new'));

            // save & close the modal
            assert.strictEqual($('.modal-content input.o_field_widget').val(), 'My little Foo Value',
                "should already have the default value for field foo");
            testUtils.dom.click($('.modal-content .btn-primary').first());

            assert.containsOnce(form, '.o_field_widget .o_kanban_view',
                "should have one inner kanban view for the one2many field");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 1,
                "should now have one kanban record");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_id').text(),
                '', "should not have a value for the id field");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_foo').text(),
                'My little Foo Value', "should have a value for the foo field");

            // save the view to force a create of the new record in the one2many
            testUtils.form.clickSave(form);
            assert.containsOnce(form, '.o_field_widget .o_kanban_view',
                "should have one inner kanban view for the one2many field");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 1,
                "should now have one kanban record");
            assert.notEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_id').text(),
                '', "should now have a value for the id field");
            assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_foo').text(),
                'My little Foo Value', "should still have a value for the foo field");

            form.destroy();
        });

        QUnit.test('focusing fields in one2many list', function (assert) {
            assert.expect(2);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '<field name="turtle_int"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '<field name="foo"/>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('.o_data_row:first td:first'));
            assert.strictEqual(form.$('input[name="turtle_foo"]')[0], document.activeElement,
                "turtle foo field should have focus");

            form.$('input[name="turtle_foo"]').trigger({ type: 'keydown', which: $.ui.keyCode.TAB });
            assert.strictEqual(form.$('input[name="turtle_int"]')[0], document.activeElement,
                "turtle int field should have focus");
            form.destroy();
        });

        QUnit.test('one2many list editable = top', function (assert) {
            assert.expect(6);

            this.data.turtle.fields.turtle_foo.default = "default foo turtle";
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        var commands = args.args[1].turtles;
                        assert.strictEqual(commands[0][0], 0,
                            "first command is a create");
                        assert.strictEqual(commands[1][0], 4,
                            "second command is a link to");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.form.clickEdit(form);

            assert.containsOnce(form, '.o_data_row',
                "should start with one data row");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 2,
                "should have 2 data rows");
            assert.strictEqual(form.$('tr.o_data_row:first input').val(), 'default foo turtle',
                "first row should be the new value");
            assert.hasClass(form.$('tr.o_data_row:first'),'o_selected_row',
                "first row should be selected");

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('one2many list editable = bottom', function (assert) {
            assert.expect(6);
            this.data.turtle.fields.turtle_foo.default = "default foo turtle";

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'write') {
                        var commands = args.args[1].turtles;
                        assert.strictEqual(commands[0][0], 4,
                            "first command is a link to");
                        assert.strictEqual(commands[1][0], 0,
                            "second command is a create");
                    }
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.form.clickEdit(form);

            assert.containsOnce(form, '.o_data_row',
                "should start with one data row");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, '.o_data_row', 2,
                "should have 2 data rows");
            assert.strictEqual(form.$('tr.o_data_row:eq(1) input').val(), 'default foo turtle',
                "second row should be the new value");
            assert.hasClass(form.$('tr.o_data_row:eq(1)'),'o_selected_row',
                "second row should be selected");

            testUtils.form.clickSave(form);
            form.destroy();
        });

        QUnit.test('x2many fields use their "mode" attribute', function (assert) {
            assert.expect(1);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<group>' +
                    '<field mode="kanban" name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '<kanban>' +
                    '<templates>' +
                    '<t t-name="kanban-box">' +
                    '<div>' +
                    '<field name="turtle_int"/>' +
                    '</div>' +
                    '</t>' +
                    '</templates>' +
                    '</kanban>' +
                    '</field>' +
                    '</group>' +
                    '</form>',
                res_id: 1,
            });

            assert.containsOnce(form, '.o_field_one2many .o_kanban_view',
                "should have rendered a kanban view");

            form.destroy();
        });

        QUnit.test('one2many list editable, no onchange when required field is not set', function (assert) {
            assert.expect(7);

            this.data.turtle.fields.turtle_foo.required = true;
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };
            this.data.partner.records[0].int_field = 0;
            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
                "int_field should start with value 0");
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
                "int_field should still be 0 (no onchange should have been done yet");

            assert.verifySteps(['read', 'default_get'], "no onchange should have been applied");

            testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_foo"]'), "some text");
            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
                "int_field should now be 1 (the onchange should have been done");

            form.destroy();
        });

        QUnit.test('one2many list editable: trigger onchange when row is valid', function (assert) {
            // should omit require fields that aren't in the view as they (obviously)
            // have no value, when checking the validity of required fields
            // shouldn't consider numerical fields with value 0 as unset
            assert.expect(12);

            this.data.turtle.fields.turtle_foo.required = true;
            this.data.turtle.fields.turtle_qux.required = true; // required field not in the view
            this.data.turtle.fields.turtle_bar.required = true; // required boolean field with no default
            delete this.data.turtle.fields.turtle_bar.default;
            this.data.turtle.fields.turtle_int.required = true; // required int field (default 0)
            this.data.turtle.fields.turtle_int.default = 0;
            this.data.turtle.fields.partner_ids.required = true; // required many2many
            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };
            this.data.partner.records[0].int_field = 0;
            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="turtles"/>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                archs: {
                    'turtle,false,list': '<tree editable="top">' +
                        '<field name="turtle_qux"/>' +
                        '<field name="turtle_bar"/>' +
                        '<field name="turtle_int"/>' +
                        '<field name="turtle_foo"/>' +
                        '<field name="partner_ids" widget="many2many_tags"/>' +
                        '</tree>',
                },
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
                "int_field should start with value 0");

            // add a new row (which is invalid at first)
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
                "int_field should still be 0 (no onchange should have been done yet)");
            assert.verifySteps(['load_views', 'read', 'default_get'], "no onchange should have been applied");

            // fill turtle_foo field
            testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_foo"]'), "some text");
            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
                "int_field should still be 0 (no onchange should have been done yet)");
            assert.verifySteps(['load_views', 'read', 'default_get'], "no onchange should have been applied");

            // fill partner_ids field with a tag (all required fields will then be set)
            testUtils.fields.many2one.clickOpenDropdown('partner_ids');
            testUtils.fields.many2one.clickHighlightedItem('partner_ids');
            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
                "int_field should now be 1 (the onchange should have been done");

            form.destroy();
        });

        QUnit.test('one2many list editable: \'required\' modifiers is properly working', function (assert) {
            assert.expect(3);

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };

            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo" required="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
                "int_field should start with value 10");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
                "int_field should still be 10 (no onchange, because line is not valid)");

            // fill turtle_foo field
            testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_foo"]'), "some text");

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
                "int_field should be 1 (onchange triggered, because line is now valid)");

            form.destroy();
        });

        QUnit.test('one2many list editable: \'required\' modifiers is properly working, part 2', function (assert) {
            assert.expect(3);

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.int_field = obj.turtles.length;
                },
            };

            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_foo" attrs=\'{"required": [["turtle_int", "=", 0]]}\'/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });
            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
                "int_field should start with value 10");

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
                "int_field should still be 10 (no onchange, because line is not valid)");

            // fill turtle_int field
            testUtils.fields.editInput(form.$('.o_field_widget[name="turtle_int"]'), "1");

            assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
                "int_field should be 1 (onchange triggered, because line is now valid)");

            form.destroy();
        });

        QUnit.test('one2many list editable: add new line before onchange returns', function (assert) {
            // If the user adds a new row (with a required field with onchange), selects
            // a value for that field, then adds another row before the onchange returns,
            // the editable list must wait for the onchange to return before trying to
            // unselect the first row, otherwise it will be detected as invalid.
            assert.expect(7);

            this.data.turtle.onchanges = {
                turtle_trululu: function () { },
            };

            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_trululu" required="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
            });

            // add a first line but hold the onchange back
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, '.o_data_row',
                "should have created the first row immediately");
            def = $.Deferred();
            testUtils.fields.many2one.clickOpenDropdown('turtle_trululu');
            testUtils.fields.many2one.clickHighlightedItem('turtle_trululu');

            // try to add a second line and check that it is correctly waiting
            // for the onchange to return
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.strictEqual($('.modal').length, 0, "no modal should be displayed");
            assert.strictEqual($('.o_field_invalid').length, 0,
                "no field should be marked as invalid");
            assert.containsOnce(form, '.o_data_row',
                "should wait for the onchange to create the second row");
            assert.hasClass(form.$('.o_data_row'),'o_selected_row',
                "first row should still be in edition");

            // resolve the onchange def
            def.resolve();
            assert.containsN(form, '.o_data_row', 2,
                "second row should now have been created");
            assert.doesNotHaveClass(form.$('.o_data_row:first'), 'o_selected_row',
                "first row should no more be in edition");

            form.destroy();
        });

        QUnit.test('editable list: multiple clicks on Add an item do not create invalid rows', function (assert) {
            assert.expect(3);

            this.data.turtle.onchanges = {
                turtle_trululu: function () { },
            };

            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_trululu" required="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
            });

            // click twice to add a new line
            def = $.Deferred();
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsNone(form, '.o_data_row',
                "no row should have been created yet (waiting for the onchange)");

            // resolve the onchange def
            def.resolve();
            assert.containsOnce(form, '.o_data_row',
                "only one row should have been created");
            assert.hasClass(form.$('.o_data_row:first'),'o_selected_row',
                "the created row should be in edition");

            form.destroy();
        });

        QUnit.test('editable list: value reset by an onchange', function (assert) {
            // this test reproduces a subtle behavior that may occur in a form view:
            // the user adds a record in a one2many field, and directly clicks on a
            // datetime field of the form view which has an onchange, which totally
            // overrides the value of the one2many (commands 5 and 0). The handler
            // that switches the edited row to readonly is then called after the
            // new value of the one2many field is applied (the one returned by the
            // onchange), so the row that must go to readonly doesn't exist anymore.
            assert.expect(2);

            this.data.partner.onchanges = {
                datetime: function (obj) {
                    obj.turtles = [[5], [0, 0, { display_name: 'new' }]];
                },
            };

            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="datetime"/>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
            });

            // trigger the two onchanges
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_data_row .o_field_widget'), 'a name');
            def = $.Deferred();
            testUtils.dom.click(form.$('.o_datepicker_input'));
            var dateTimeVal = fieldUtils.format.datetime(moment(), { timezone: false });
            testUtils.fields.editSelect(form.$('.o_datepicker_input'), dateTimeVal);

            // resolve the onchange def
            def.resolve();

            assert.containsOnce(form, '.o_data_row',
                "should have one record in the o2m");
            assert.strictEqual(form.$('.o_data_row .o_data_cell').text(), 'new',
                "should be the record created by the onchange");

            form.destroy();
        });

        QUnit.test('editable list: onchange that returns a warning', function (assert) {
            assert.expect(5);

            this.data.turtle.onchanges = {
                display_name: function () { },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        assert.step(args.method);
                        return $.when({
                            value: {},
                            warning: {
                                title: "Warning",
                                message: "You must first select a partner"
                            },
                        });
                    }
                    return this._super.apply(this, arguments);
                },
                viewOptions: {
                    mode: 'edit',
                },
                intercepts: {
                    warning: function () {
                        assert.step('warning');
                    },
                },
            });

            // add a line (this should trigger an onchange and a warning)
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // check if 'Add an item' still works (this should trigger an onchange
            // and a warning again)
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.verifySteps(['onchange', 'warning', 'onchange', 'warning']);

            form.destroy();
        });

        QUnit.test('editable list: contexts are correctly sent', function (assert) {
            assert.expect(5);

            this.data.partner.records[0].timmy = [12];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="foo"/>' +
                    '<field name="timmy" context="{\'key\': parent.foo}">' +
                    '<tree editable="top">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'read' && args.model === 'partner') {
                        assert.deepEqual(args.kwargs.context, {
                            active_field: 2,
                            bin_size: true,
                            someKey: 'some value',
                        }, "sent context should be correct");
                    }
                    if (args.method === 'read' && args.model === 'partner_type') {
                        assert.deepEqual(args.kwargs.context, {
                            key: 'yop',
                            active_field: 2,
                            someKey: 'some value',
                        }, "sent context should be correct");
                    }
                    if (args.method === 'write') {
                        assert.deepEqual(args.kwargs.context, {
                            active_field: 2,
                            someKey: 'some value',
                        }, "sent context should be correct");
                    }
                    return this._super.apply(this, arguments);
                },
                session: {
                    user_context: { someKey: 'some value' },
                },
                viewOptions: {
                    mode: 'edit',
                    context: { active_field: 2 },
                },
                res_id: 1,
            });

            testUtils.dom.click(form.$('.o_data_cell:first'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'abc');
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('resetting invisible one2manys', function (assert) {
            assert.expect(3);

            this.data.partner.records[0].turtles = [];
            this.data.partner.onchanges.foo = function (obj) {
                obj.turtles = [[5], [4, 1]];
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="foo"/>' +
                    '<field name="turtles" invisible="1"/>' +
                    '</form>',
                viewOptions: {
                    mode: 'edit',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.fields.editInput(form.$('input[name="foo"]'), 'abcd');
            assert.verifySteps(['read', 'onchange']);

            form.destroy();
        });

        QUnit.test('one2many: onchange that returns unknow field in list, but not in form', function (assert) {
            assert.expect(5);

            this.data.partner.onchanges = {
                name: function () { },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="name"/>' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return $.when({
                            value: {
                                p: [[5], [0, 0, { display_name: 'new', timmy: [[5], [4, 12]] }]],
                            },
                        });
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "the one2many should contain one row");
            assert.containsNone(form, '.o_field_widget[name="timmy"]',
                "timmy should not be displayed in the list view");

            testUtils.dom.click(form.$('.o_data_row td:first'));

            assert.strictEqual($('.modal .o_field_many2manytags[name="timmy"]').length, 1,
                "timmy should be displayed in the form view");
            assert.strictEqual($('.modal .o_field_many2manytags[name="timmy"] .badge').length, 1,
                "m2mtags should contain one tag");
            assert.strictEqual($('.modal .o_field_many2manytags[name="timmy"] .o_badge_text').text(),
                'gold', "tag name should have been correctly loaded");

            form.destroy();
        });

        QUnit.test('onchange and required fields with override in arch', function (assert) {
            assert.expect(4);

            this.data.partner.onchanges = {
                turtles: function (obj) { }
            };
            this.data.turtle.fields.turtle_foo.required = true;
            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_foo" required="0"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            testUtils.form.clickEdit(form);

            // triggers an onchange on partner, because the new record is valid
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.verifySteps(['read', 'default_get', 'onchange']);
            form.destroy();
        });

        QUnit.test('onchange on a one2many containing a one2many', function (assert) {
            // the purpose of this test is to ensure that the onchange specs are
            // correctly and recursively computed
            assert.expect(1);

            this.data.partner.onchanges = {
                p: function () { }
            };
            var checkOnchange = false;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree><field name="display_name"/></tree>' +
                    '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom"><field name="display_name"/></tree>' +
                    '</field>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'onchange' && checkOnchange) {
                        assert.strictEqual(args.args[3]['p.p.display_name'], '',
                            "onchange specs should be computed recursively");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));
            testUtils.fields.editInput($('.modal .o_data_cell input'), 'new record');
            checkOnchange = true;
            testUtils.dom.clickFirst($('.modal .modal-footer .btn-primary'));

            form.destroy();
        });

        QUnit.test('editing tabbed one2many (editable=bottom)', function (assert) {
            assert.expect(12);

            this.data.partner.records[0].turtles = [];
            for (var i = 0; i < 42; i++) {
                var id = 100 + i;
                this.data.turtle.records.push({ id: id, turtle_foo: 'turtle' + (id - 99) });
                this.data.partner.records[0].turtles.push(id);
            }

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    if (args.method === 'write') {
                        assert.strictEqual(args.args[1].turtles[40][0], 0, 'should send a create command');
                        assert.deepEqual(args.args[1].turtles[40][2], { turtle_foo: 'rainbow dash' });
                    }
                    return this._super.apply(this, arguments);
                },
            });


            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, 'tr.o_data_row', 41);
            assert.hasClass(form.$('tr.o_data_row').last(), 'o_selected_row');

            testUtils.fields.editInput(form.$('.o_data_row input[name="turtle_foo"]'), 'rainbow dash');
            testUtils.form.clickSave(form);

            assert.containsN(form, 'tr.o_data_row', 40);

            assert.verifySteps(['read', 'read', 'default_get', 'write', 'read', 'read']);
            form.destroy();
        });

        QUnit.test('editing tabbed one2many (editable=bottom), again...', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [];
            for (var i = 0; i < 9; i++) {
                var id = 100 + i;
                this.data.turtle.records.push({ id: id, turtle_foo: 'turtle' + (id - 99) });
                this.data.partner.records[0].turtles.push(id);
            }

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom" limit="3">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });


            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_data_row input[name="turtle_foo"]'), 'rainbow dash');
            testUtils.dom.click(form.$('.o_x2m_control_panel .o_pager_next'));
            testUtils.dom.click(form.$('.o_x2m_control_panel .o_pager_next'));

            assert.containsN(form, 'tr.o_data_row', 3,
                "should have 3 data rows on the current page");
            form.destroy();
        });

        QUnit.test('editing tabbed one2many (editable=top)', function (assert) {
            assert.expect(15);

            this.data.partner.records[0].turtles = [];
            this.data.turtle.fields.turtle_foo.default = "default foo";
            for (var i = 0; i < 42; i++) {
                var id = 100 + i;
                this.data.turtle.records.push({ id: id, turtle_foo: 'turtle' + (id - 99) });
                this.data.partner.records[0].turtles.push(id);
            }

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    if (args.method === 'write') {
                        assert.strictEqual(args.args[1].turtles[40][0], 0);
                        assert.deepEqual(args.args[1].turtles[40][2], { turtle_foo: 'rainbow dash' });
                    }
                    return this._super.apply(this, arguments);
                },
            });


            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget[name=turtles] .o_pager_next'));

            assert.containsN(form, 'tr.o_data_row', 2);

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsN(form, 'tr.o_data_row', 3);

            assert.hasClass(form.$('tr.o_data_row').first(), 'o_selected_row');

            assert.strictEqual(form.$('tr.o_data_row input').val(), 'default foo',
                "selected input should have correct string");

            testUtils.fields.editInput(form.$('.o_data_row input[name="turtle_foo"]'), 'rainbow dash');
            testUtils.form.clickSave(form);

            assert.containsN(form, 'tr.o_data_row', 40);

            assert.verifySteps(['read', 'read', 'read', 'default_get', 'write', 'read', 'read']);
            form.destroy();
        });

        QUnit.test('one2many field: change value before pending onchange returns', function (assert) {
            var done = assert.async();
            assert.expect(2);

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

            this.data.partner.onchanges = {
                int_field: function () { }
            };
            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                    '<field name="trululu"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        // delay the onchange RPC
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            def = $.Deferred();
            testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), '44');

            var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
            // set trululu before onchange
            form.$('.o_field_many2one input').val('first').trigger('keydown').trigger('keyup');
            // complete the onchange
            def.resolve();
            assert.strictEqual(form.$('.o_field_many2one input').val(), 'first',
                'should have kept the new value');
            concurrency.delay(0).then(function () {
                // check name_search result
                assert.strictEqual($dropdown.find('li:not(.o_m2o_dropdown_option)').length, 1,
                    'autocomplete should contains 1 suggestion');

                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                form.destroy();
                done();
            });
        });

        QUnit.test('focus is correctly reset after an onchange in an x2many', function (assert) {
            assert.expect(2);

            this.data.partner.onchanges = {
                int_field: function () { }
            };
            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="int_field"/>' +
                    '<button string="hello"/>' +
                    '<field name="qux"/>' +
                    '<field name="trululu"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        // delay the onchange RPC
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            def = $.Deferred();
            testUtils.fields.editAndTrigger(form.$('.o_field_widget[name=int_field]'), '44',
                ['input', { type: 'keydown', which: $.ui.keyCode.TAB }]);
            def.resolve();

            assert.strictEqual(document.activeElement, form.$('.o_field_widget[name=qux]')[0],
                "qux field should have the focus");

            testUtils.fields.many2one.clickOpenDropdown('trululu');
            testUtils.fields.many2one.clickHighlightedItem('trululu');
            assert.strictEqual(form.$('.o_field_many2one input').val(), 'first record',
                "the one2many field should have the expected value");

            form.destroy();
        });

        QUnit.test('checkbox in an x2many that triggers an onchange', function (assert) {
            assert.expect(1);

            this.data.partner.onchanges = {
                bar: function () { }
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="bar"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            testUtils.dom.click(form.$('.o_field_widget[name=bar] input'));
            assert.notOk(form.$('.o_field_widget[name=bar] input').prop('checked'),
                "the checkbox should be unticked");

            form.destroy();
        });

        QUnit.test('one2many with default value: edit line to make it invalid', function (assert) {
            assert.expect(3);

            this.data.partner.fields.p.default = [
                [0, false, { foo: "coucou", int_field: 5 }],
            ];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            // edit the line and enter an invalid value for int_field
            testUtils.dom.click(form.$('.o_data_row .o_data_cell:nth(1)'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 'e');
            testUtils.dom.click(form.$el);

            assert.containsOnce(form, '.o_data_row.o_selected_row',
                "line should not have been removed and should still be in edition");
            assert.strictEqual($('.modal').length, 1,
                "a confirmation dialog should be opened");
            assert.hasClass(form.$('.o_field_widget[name=int_field]'),'o_field_invalid',
                "should indicate that int_field is invalid");

            form.destroy();
        });

        QUnit.test('default value for nested one2manys (coming from onchange)', function (assert) {
            assert.expect(3);

            this.data.partner.onchanges.p = function (obj) {
                obj.p = [
                    [5],
                    [0, 0, { turtles: [[5], [4, 1]] }], // link record 1 by default
                ];
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<field name="p">' +
                    '<tree><field name="turtles"/></tree>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'create') {
                        assert.strictEqual(args.args[0].p[0][0], 0,
                            "should send a command 0 (CREATE) for p");
                        assert.deepEqual(args.args[0].p[0][2], { turtles: [[4, 1, false]] },
                            "should send the correct values");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            assert.strictEqual(form.$('.o_data_cell').text(), '1 record',
                "should correctly display the value of the inner o2m");

            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('display correct value after validation error', function (assert) {
            assert.expect(4);

            this.data.partner.onchanges.turtles = function () { };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        if (args.args[1].turtles[0][2].turtle_foo === 'pinky') {
                            // we simulate a validation error.  In the 'real' web client,
                            // the server error will be used by the session to display
                            // an error dialog.  From the point of view of the basic
                            // model, the deferred is just rejected.
                            return $.Deferred().reject();
                        }
                    }
                    if (args.method === 'write') {
                        assert.deepEqual(args.args[1].turtles[0], [1, 2, { turtle_foo: 'foo' }],
                            'should send the "good" value');
                    }
                    return this._super.apply(this, arguments);
                },
                viewOptions: { mode: 'edit' },
                res_id: 1,
            });

            assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'blip',
                "initial text should be correct");

            // click and edit value to 'foo', which will trigger onchange
            testUtils.dom.click(form.$('.o_data_row .o_data_cell:nth(0)'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=turtle_foo]'), 'foo');
            testUtils.dom.click(form.$el);
            assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'foo',
                "field should have been changed to foo");

            // click and edit value to 'pinky', which trigger a failed onchange
            testUtils.dom.click(form.$('.o_data_row .o_data_cell:nth(0)'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=turtle_foo]'), 'pinky');
            testUtils.dom.click(form.$el);

            assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'foo',
                "turtle_foo text should now be set back to foo");

            // we make sure here that when we save, the values are the current
            // values displayed in the field.
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('propagate context to sub views', function (assert) {
            assert.expect(5);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.strictEqual(args.kwargs.context.flutter, 'shy',
                        'view context key should be used for every rpcs');
                    return this._super.apply(this, arguments);
                },
                viewOptions: { context: { flutter: 'shy' } },
            });
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('input[name="turtle_foo"]'), 'pinky pie');
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('onchange on nested one2manys', function (assert) {
            assert.expect(6);

            this.data.partner.onchanges.display_name = function (obj) {
                if (obj.display_name) {
                    obj.p = [
                        [5],
                        [0, 0, {
                            display_name: 'test',
                            turtles: [[5], [0, 0, { display_name: 'test nested' }]],
                        }],
                    ];
                }
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<sheet>' +
                    '<field name="display_name"/>' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="turtles">' +
                    '<tree><field name="display_name"/></tree>' +
                    '</field>' +
                    '</form>' +
                    '</field>' +
                    '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    if (args.method === 'create') {
                        assert.strictEqual(args.args[0].p[0][0], 0,
                            "should send a command 0 (CREATE) for p");
                        assert.strictEqual(args.args[0].p[0][2].display_name, 'test',
                            "should send the correct values");
                        assert.strictEqual(args.args[0].p[0][2].turtles[0][0], 0,
                            "should send a command 0 (CREATE) for turtles");
                        assert.deepEqual(args.args[0].p[0][2].turtles[0][2], { display_name: 'test nested' },
                            "should send the correct values");
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.fields.editInput(form.$('.o_field_widget[name=display_name]'), 'trigger onchange');

            assert.strictEqual(form.$('.o_data_cell').text(), 'test',
                "should have added the new row to the one2many");

            // open the new subrecord to check the value of the nested o2m, and to
            // ensure that it will be saved
            testUtils.dom.click(form.$('.o_data_cell:first'));
            assert.strictEqual($('.modal .o_data_cell').text(), 'test nested',
                "should have added the new row to the nested one2many");
            testUtils.dom.clickFirst($('.modal .modal-footer .btn-primary'));

            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('one2many with multiple pages and sequence field', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [3, 2, 1];
            this.data.partner.onchanges.turtles = function () { };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="2">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" invisible="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return $.when({
                            value: {
                                turtles: [
                                    [5],
                                    [1, 1, { turtle_foo: "from onchange", partner_ids: [[5]] }],
                                ]
                            }
                        });
                    }
                    return this._super(route, args);
                },
                viewOptions: {
                    mode: 'edit',
                },
            });
            testUtils.dom.click(form.$('.o_list_record_remove:first button'));
            assert.strictEqual(form.$('.o_data_row').text(), 'from onchange',
                'onchange has been properly applied');
            form.destroy();
        });

        QUnit.test('one2many with multiple pages and sequence field, part2', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [3, 2, 1];
            this.data.partner.onchanges.turtles = function () { };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="2">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="partner_ids" invisible="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === 'onchange') {
                        return $.when({
                            value: {
                                turtles: [
                                    [5],
                                    [1, 1, { turtle_foo: "from onchange id2", partner_ids: [[5]] }],
                                    [1, 3, { turtle_foo: "from onchange id3", partner_ids: [[5]] }],
                                ]
                            }
                        });
                    }
                    return this._super(route, args);
                },
                viewOptions: {
                    mode: 'edit',
                },
            });
            testUtils.dom.click(form.$('.o_list_record_remove:first button'));
            assert.strictEqual(form.$('.o_data_row').text(), 'from onchange id2from onchange id3',
                'onchange has been properly applied');
            form.destroy();
        });

        QUnit.test('one2many with sequence field, override default_get, bottom when inline', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [3, 2, 1];

            this.data.turtle.fields.turtle_int.default = 10;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // starting condition
            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = 'ninja';
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText);
            testUtils.form.clickSave(form);

            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa" + inputText);
            form.destroy();
        });

        QUnit.test('one2many with sequence field, override default_get, top when inline', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [3, 2, 1];

            this.data.turtle.fields.turtle_int.default = 10;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // starting condition
            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = 'ninja';
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText);
            testUtils.form.clickSave(form);

            assert.strictEqual($('.o_data_cell').text(), inputText + "blipyopkawa");
            form.destroy();
        });

        QUnit.test('one2many with sequence field, override default_get, bottom when popup', function (assert) {
            assert.expect(3);

            this.data.partner.records[0].turtles = [3, 2, 1];

            this.data.turtle.fields.turtle_int.default = 10;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '<form>' +
                    // NOTE: at some point we want to fix this in the framework so that an invisible field is not required.
                    '<field name="turtle_int" invisible="1"/>' +
                    '<field name="turtle_foo"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // starting condition
            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa");

            // click add a new line
            // save the record
            // check line is at the correct place

            var inputText = 'ninja';
            testUtils.dom.click($('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput($('.o_input[name="turtle_foo"]'), inputText);
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));

            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa" + inputText);

            testUtils.dom.click($('.o_form_button_save'));
            assert.strictEqual($('.o_data_cell').text(), "blipyopkawa" + inputText);
            form.destroy();
        });

        QUnit.test('one2many with sequence field, override default_get, not last page', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [3, 2, 1];

            this.data.turtle.fields.turtle_int.default = 10;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="2">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="turtle_int"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // click add a new line
            // check turtle_int for new is the current max of the page
            testUtils.dom.click($('.o_field_x2many_list_row_add a'));
            assert.strictEqual($('.modal .o_input[name="turtle_int"]').val(), '10');
            form.destroy();
        });

        QUnit.test('one2many with sequence field, override default_get, last page', function (assert) {
            assert.expect(1);

            this.data.partner.records[0].turtles = [3, 2, 1];

            this.data.turtle.fields.turtle_int.default = 10;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="4">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="turtle_int"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // click add a new line
            // check turtle_int for new is the current max of the page +1
            testUtils.dom.click($('.o_field_x2many_list_row_add a'));
            assert.strictEqual($('.modal .o_input[name="turtle_int"]').val(), '22');
            form.destroy();
        });

        QUnit.test('one2many with sequence field, fetch name_get from empty list, field text', function (assert) {
            // There was a bug where a RPC would fail because no route was set.
            // The scenario is:
            // - create a new parent model, which has a one2many
            // - add at least 2 one2many lines which have:
            //     - a handle field
            //     - a many2one, which is not required, and we will leave it empty
            // - reorder the lines with the handle
            // -> This will call a resequence, which calls a name_get.
            // -> With the bug that would fail, if it's ok the test will pass.

            // This test will also make sure lists with
            // FieldText (turtle_description) can be reordered with a handle.
            // More specifically this will trigger a reset on a FieldText
            // while the field is not in editable mode.
            assert.expect(4);

            this.data.turtle.fields.turtle_int.default = 10;
            this.data.turtle.fields.product_id.default = 37;
            this.data.turtle.fields.not_required_product_id = {
                string: "Product",
                type: "many2one",
                relation: 'product'
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_int" widget="handle"/>' +
                    '<field name="turtle_foo"/>' +
                    '<field name="not_required_product_id"/>' +
                    '<field name="turtle_description" widget="text"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                viewOptions: {
                    mode: 'edit',
                },
            });

            // starting condition
            assert.strictEqual($('.o_data_cell:nth-child(2)').text(), "");

            var inputText1 = 'relax';
            var inputText2 = 'max';
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText1);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), inputText2);
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.strictEqual($('.o_data_cell:nth-child(2)').text(), inputText1 + inputText2);

            var $handles = form.$('.ui-sortable-handle');

            assert.equal($handles.length, 3, 'There should be 3 sequence handlers');

            testUtils.dom.dragAndDrop($handles.eq(1),
                form.$('tbody tr').first(),
                { position: 'top' }
            );

            assert.strictEqual($('.o_data_cell:nth-child(2)').text(), inputText2 + inputText1);

            form.destroy();
        });

        QUnit.test('one2many with several pages, onchange and default order', function (assert) {
            // This test reproduces a specific scenario where a one2many is displayed
            // over several pages, and has a default order such that a record that
            // would normally be on page 1 is actually on another page. Moreover,
            // there is an onchange on that one2many which converts all commands 4
            // (LINK_TO) into commands 1 (UPDATE), which is standard in the ORM.
            // This test ensures that the record displayed on page 2 is never fully
            // read.
            assert.expect(8);

            var data = this.data;
            data.partner.records[0].turtles = [1, 2, 3];
            data.turtle.records[0].partner_ids = [1];
            data.partner.onchanges = {
                turtles: function (obj) {
                    var res = _.map(obj.turtles, function (command) {
                        if (command[0] === 1) { // already an UPDATE command: do nothing
                            return command;
                        }
                        // convert LINK_TO commands to UPDATE commands
                        var id = command[1];
                        var record = _.findWhere(data.turtle.records, { id: id });
                        return [1, id, _.pick(record, ['turtle_int', 'turtle_foo', 'partner_ids'])];
                    });
                    obj.turtles = [[5]].concat(res);
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="top" limit="2" default_order="turtle_foo">' +
                    '<field name="turtle_int"/>' +
                    '<field name="turtle_foo" class="foo"/>' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var ids = args.method === 'read' ? ' [' + args.args[0] + ']' : '';
                    assert.step(args.method + ids);
                    return this._super.apply(this, arguments);
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.strictEqual(form.$('.o_data_cell.foo').text(), 'blipkawa',
                "should display two records out of three, in the correct order");

            // edit turtle_int field of first row
            testUtils.dom.click(form.$('.o_data_cell:first'));
            testUtils.fields.editInput(form.$('.o_field_widget[name=turtle_int]'), 3);
            testUtils.dom.click(form.$el);

            assert.strictEqual(form.$('.o_data_cell.foo').text(), 'blipkawa',
                "should still display the same two records");

            assert.verifySteps([
                'read [1]', // main record
                'read [1,2,3]', // one2many (turtle_foo, all records)
                'read [2,3]', // one2many (all fields in view, records of first page)
                'read [2,4]', // many2many inside one2many (partner_ids), first page only
                'onchange',
            ]);

            form.destroy();
        });

        QUnit.test('new record, with one2many with more default values than limit', function (assert) {
            assert.expect(2);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="2">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                context: { default_turtles: [1, 2, 3] },
                viewOptions: {
                    mode: 'edit',
                },
            });
            assert.strictEqual(form.$('.o_data_row').text(), 'yopblip',
                'data has been properly loaded');
            testUtils.form.clickSave(form);

            assert.strictEqual(form.$('.o_data_row').text(), 'yopblip',
                'data has been properly saved');
            form.destroy();
        });

        QUnit.test('add a new line after limit is reached should behave nicely', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1, 2, 3];

            this.data.partner.onchanges = {
                turtles: function (obj) {
                    obj.turtles = [
                        [5],
                        [1, 1, { turtle_foo: "yop" }],
                        [1, 2, { turtle_foo: "blip" }],
                        [1, 3, { turtle_foo: "kawa" }],
                        [0, obj.turtles[3][2], { turtle_foo: "abc" }],
                    ];
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree limit="3" editable="bottom">' +
                    '<field name="turtle_foo" required="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsN(form, '.o_data_row', 4, 'should have 4 data rows');
            testUtils.fields.editInput(form.$('.o_input[name="turtle_foo"]'), 'a');
            assert.containsN(form, '.o_data_row', 4,
                'should still have 4 data rows (the limit is increased to 4)');

            form.destroy();
        });

        QUnit.test('onchange in a one2many with non inline view on an existing record', function (assert) {
            assert.expect(6);

            this.data.partner.fields.sequence = { string: 'Sequence', type: 'integer' };
            this.data.partner.records[0].sequence = 1;
            this.data.partner.records[1].sequence = 2;
            this.data.partner.onchanges = { sequence: function () { } };

            this.data.partner_type.fields.partner_ids = { string: "Partner", type: "one2many", relation: 'partner' };
            this.data.partner_type.records[0].partner_ids = [1, 2];

            var form = testUtils.createView({
                View: FormView,
                model: 'partner_type',
                data: this.data,
                arch: '<form><field name="partner_ids"/></form>',
                archs: {
                    'partner,false,list': '<tree string="Vendors">' +
                        '<field name="sequence" widget="handle"/>' +
                        '<field name="display_name"/>' +
                        '</tree>',
                },
                res_id: 12,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                viewOptions: { mode: 'edit' },
            });

            // swap 2 lines in the one2many
            testUtils.dom.dragAndDrop(form.$('.ui-sortable-handle:eq(1)'), form.$('tbody tr').first(),
                { position: 'top' });
            assert.verifySteps(['load_views', 'read', 'read', 'onchange', 'onchange']);
            form.destroy();
        });

        QUnit.test('onchange in a one2many with non inline view on a new record', function (assert) {
            assert.expect(8);

            this.data.turtle.onchanges = {
                display_name: function (obj) {
                    if (obj.display_name) {
                        obj.turtle_int = 44;
                    }
                },
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form><field name="turtles"/></form>',
                archs: {
                    'turtle,false,list': '<tree editable="bottom">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_int"/>' +
                        '</tree>',
                },
                mockRPC: function (route, args) {
                    assert.step(args.method || route);
                    return this._super.apply(this, arguments);
                },
            });

            // add a row and trigger the onchange
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput(form.$('.o_data_row .o_field_widget[name=display_name]'), 'a name');

            assert.strictEqual(form.$('.o_data_row .o_field_widget[name=turtle_int]').val(), "44",
                "should have triggered the onchange");

            assert.verifySteps([
                'load_views', // load sub list
                'default_get', // main record
                'onchange', // main record
                'default_get', // sub record
                'onchange', // sub record
                'onchange', // edition of display_name of sub record
            ]);

            form.destroy();
        });

        QUnit.test('add a line, edit it and "Save & New"', function (assert) {
            assert.expect(5);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree><field name="display_name"/></tree>' +
                    '<form><field name="display_name"/></form>' +
                    '</field>' +
                    '</form>',
            });

            assert.containsNone(form, '.o_data_row',
                "there should be no record in the relation");

            // add a new record
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editInput($('.modal .o_field_widget'), 'new record');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));

            assert.strictEqual(form.$('.o_data_row .o_data_cell').text(), 'new record',
                "should display the new record");

            // reopen freshly added record and edit it
            testUtils.dom.click(form.$('.o_data_row .o_data_cell'));
            testUtils.fields.editInput($('.modal .o_field_widget'), 'new record edited');

            // save it, and choose to directly create another record
            testUtils.dom.click($('.modal .modal-footer .btn-primary:nth(1)'));

            assert.strictEqual($('.modal').length, 1,
                "the model should still be open");
            assert.strictEqual($('.modal .o_field_widget').text(), '',
                "should have cleared the input");

            testUtils.fields.editInput($('.modal .o_field_widget'), 'another new record');
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));

            assert.strictEqual(form.$('.o_data_row .o_data_cell').text(),
                'new record editedanother new record', "should display the two records");

            form.destroy();
        });

        QUnit.test('o2m add a line custom control create editable', function (assert) {
            assert.expect(5);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<control>' +
                    '<create string="Add food" context="" />' +
                    '<create string="Add pizza" context="{\'default_display_name\': \'pizza\'}"/>' +
                    '</control>' +

                    '<control>' +
                    '<create string="Add pasta" context="{\'default_display_name\': \'pasta\'}"/>' +
                    '</control>' +

                    '<field name="display_name"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="display_name"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
            });

            // new controls correctly added
            var $td = form.$('.o_field_x2many_list_row_add');
            assert.strictEqual($td.length, 1);
            assert.strictEqual($td.closest('tr').find('td').length, 1);
            assert.strictEqual($td.text(), "Add foodAdd pizzaAdd pasta");

            // click add food
            // check it's empty
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(0)'));
            assert.strictEqual($('.o_data_cell').text(), "");

            // click add pizza
            // save the modal
            // check it's pizza
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(1)'));
            // click add pasta
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(2)'));
            testUtils.form.clickSave(form);
            assert.strictEqual($('.o_data_cell').text(), "pizzapasta");

            form.destroy();
        });

        QUnit.test('o2m add a line custom control create non-editable', function (assert) {
            assert.expect(6);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<control>' +
                    '<create string="Add food" context="" />' +
                    '<create string="Add pizza" context="{\'default_display_name\': \'pizza\'}" />' +
                    '</control>' +

                    '<control>' +
                    '<create string="Add pasta" context="{\'default_display_name\': \'pasta\'}" />' +
                    '</control>' +

                    '<field name="display_name"/>' +
                    '</tree>' +
                    '<form>' +
                    '<field name="display_name"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
            });

            // new controls correctly added
            var $td = form.$('.o_field_x2many_list_row_add');
            assert.strictEqual($td.length, 1);
            assert.strictEqual($td.closest('tr').find('td').length, 1);
            assert.strictEqual($td.text(), "Add foodAdd pizzaAdd pasta");

            // click add food
            // check it's empty
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(0)'));
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            assert.strictEqual($('.o_data_cell').text(), "");

            // click add pizza
            // save the modal
            // check it's pizza
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(1)'));
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            assert.strictEqual($('.o_data_cell').text(), "pizza");

            // click add pasta
            // save the whole record
            // check it's pizzapasta
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a:eq(2)'));
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            assert.strictEqual($('.o_data_cell').text(), "pizzapasta");

            form.destroy();
        });

        QUnit.test('o2m add a line custom control create align with handle', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="int_field" widget="handle"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
            });

            // controls correctly added, at one column offset when handle is present
            var $tr = form.$('.o_field_x2many_list_row_add').closest('tr');
            assert.strictEqual($tr.find('td').length, 2);
            assert.strictEqual($tr.find('td:eq(0)').text(), "");
            assert.strictEqual($tr.find('td:eq(1)').text(), "Add a line");

            form.destroy();
        });

        QUnit.test('one2many form view with action button', function (assert) {
            // once the action button is clicked, the record is reloaded (via the
            // on_close handler, executed because the python method does not return
            // any action, or an ir.action.act_window_close) ; this test ensures that
            // it reloads the fields of the opened view (i.e. the form in this case).
            // See https://github.com/odoo/odoo/issues/24189
            assert.expect(7);

            var data = this.data;
            data.partner.records[0].p = [2];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: data,
                res_id: 1,
                arch: '<form string="Partners">' +
                    '<field name="p">' +
                    '<tree><field name="display_name"/></tree>' +
                    '<form>' +
                    '<button type="action" string="Set Timmy"/>' +
                    '<field name="timmy"/>' +
                    '</form>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'partner_type,false,list': '<tree><field name="display_name"/></tree>',
                },
                intercepts: {
                    execute_action: function (ev) {
                        data.partner.records[1].display_name = 'new name';
                        data.partner.records[1].timmy = [12];
                        ev.data.on_closed();
                    },
                },
                viewOptions: {
                    mode: 'edit',
                },
            });

            assert.containsOnce(form, '.o_data_row',
                "there should be one record in the one2many");
            assert.strictEqual(form.$('.o_data_cell').text(), 'second record',
                "initial display_name of o2m record should be correct");

            // open one2many record in form view
            testUtils.dom.click(form.$('.o_data_cell:first'));
            assert.strictEqual($('.modal .o_form_view').length, 1,
                "should have opened the form view in a dialog");
            assert.strictEqual($('.modal .o_form_view .o_data_row').length, 0,
                "there should be no record in the many2many");

            // click on the action button
            testUtils.dom.click($('.modal .o_form_view button'));
            assert.strictEqual($('.modal .o_data_row').length, 1,
                "fields in the o2m form view should have been read");
            assert.strictEqual($('.modal .o_data_cell').text(), 'gold',
                "many2many subrecord should have been fetched");

            // save the dialog
            testUtils.dom.click($('.modal .modal-footer .btn-primary'));

            assert.strictEqual(form.$('.o_data_cell').text(), 'new name',
                "fields in the o2m list view should have been read as well");

            form.destroy();
        });

        QUnit.test('onchange affecting inline unopened list view', function (assert) {
            // when we got onchange result for fields of record that were not
            // already available because they were in a inline view not already
            // opened, in a given configuration the change were applied ignoring
            // existing data, thus a line of a one2many field inside a one2many
            // field could be duplicated unexplectedly
            assert.expect(5);

            var numUserOnchange = 0;

            this.data.user.onchanges = {
                partner_ids: function (obj) {
                    if (numUserOnchange === 0) {
                        // simulate proper server onchange after save of modal with new record
                        obj.partner_ids = [
                            [5],
                            [1, 1, {
                                display_name: 'first record',
                                turtles: [
                                    [5],
                                    [1, 2, { 'display_name': 'donatello' }],
                                ],
                            }],
                            [1, 2, {
                                display_name: 'second record',
                                turtles: [
                                    [5],
                                    obj.partner_ids[1][2].turtles[0],
                                ],
                            }],
                        ];
                    }
                    numUserOnchange++;
                },
            };

            var form = createView({
                View: FormView,
                model: 'user',
                data: this.data,
                arch: '<form><sheet><group>' +
                    '<field name="partner_ids">' +
                    '<form>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>' +
                    '<tree>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</group></sheet></form>',
                res_id: 17,
            });

            // add a turtle on second partner
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_data_row:eq(1)'));
            testUtils.dom.click($('.modal .o_field_x2many_list_row_add a'));
            $('.modal input[name="display_name"]').val('michelangelo').change();
            testUtils.dom.click($('.modal .btn-primary'));
            // open first partner so changes from previous action are applied
            testUtils.dom.click(form.$('.o_data_row:eq(0)'));
            testUtils.dom.click($('.modal .btn-primary'));
            testUtils.form.clickSave(form);

            assert.strictEqual(numUserOnchange, 2,
                'there should 2 and only 2 onchange from closing the partner modal');

            testUtils.dom.click(form.$('.o_data_row:eq(0)'));
            assert.strictEqual($('.modal .o_data_row').length, 1,
                'only 1 turtle for first partner');
            assert.strictEqual($('.modal .o_data_row').text(), 'donatello',
                'first partner turtle is donatello');
            testUtils.dom.click($('.modal .o_form_button_cancel'));

            testUtils.dom.click(form.$('.o_data_row:eq(1)'));
            assert.strictEqual($('.modal .o_data_row').length, 1,
                'only 1 turtle for second partner');
            assert.strictEqual($('.modal .o_data_row').text(), 'michelangelo',
                'second partner turtle is michelangelo');
            testUtils.dom.click($('.modal .o_form_button_cancel'));

            form.destroy();
        });

        QUnit.test('click on URL should not open the record', function (assert) {
            assert.expect(2);

            this.data.partner.records[0].turtles = [1];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree>' +
                    '<field name="display_name" widget="email"/>' +
                    '<field name="turtle_foo" widget="url"/>' +
                    '</tree>' +
                    '<form></form>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            testUtils.dom.click(form.$('.o_email_cell a'));
            assert.strictEqual($('.modal .o_form_view').length, 0,
                'click should not open the modal');

            testUtils.dom.click(form.$('.o_url_cell a'));
            assert.strictEqual($('.modal .o_form_view').length, 0,
                'click should not open the modal');
            form.destroy();
        });

        QUnit.test('create and edit on m2o in o2m, and press ESCAPE', function (assert) {
            assert.expect(4);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="turtles">' +
                    '<tree editable="top">' +
                    '<field name="turtle_trululu"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                archs: {
                    'partner,false,form': '<form><field name="display_name"/></form>',
                },
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            assert.containsOnce(form, '.o_selected_row',
                "should have create a new row in edition");

            testUtils.fields.many2one.clickOpenDropdown('turtle_trululu');
            testUtils.fields.many2one.clickItem('turtle_trululu','Create and Edit...');

            assert.strictEqual($('.modal .o_form_view').length, 1,
                "should have opened a form view in a dialog");

            $('.modal .o_form_view .o_field_widget[name=display_name]').trigger($.Event('keydown', {
                which: $.ui.keyCode.ESCAPE,
                keyCode: $.ui.keyCode.ESCAPE,
            }));

            assert.strictEqual($('.modal .o_form_view').length, 0,
                "should have closed the dialog");
            assert.containsOnce(form, '.o_selected_row',
                "new row should still be present");

            form.destroy();
        });

        QUnit.test('one2many add a line should not crash if orderedResIDs is not set', function (assert) {
            // There is no assertion, the code will just crash before the bugfix.
            assert.expect(0);

            this.data.partner.records[0].turtles = [];

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<header>' +
                    '<button name="action_invoice_open" type="object" string="Validate" class="oe_highlight"/>' +
                    '</header>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                viewOptions: {
                    mode: 'edit',
                },
                intercepts: {
                    execute_action: function (event) {
                        event.data.on_fail();
                    },
                },
            });

            testUtils.dom.click($('button[name="action_invoice_open"]'));
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            form.destroy();
        });

        QUnit.test('one2many shortcut tab should not crash when there is no input widget', function (assert) {
            assert.expect(2);

            // create a one2many view which has no input (only 1 textarea in this case)
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo" widget="text"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            // add a row, fill it, then trigger the tab shortcut
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.fields.editAndTrigger(
                form.$('.o_input[name="turtle_foo"]'),
                'ninja',
                ['input', $.Event('keydown', {which: $.ui.keyCode.TAB, keyCode: $.ui.keyCode.TAB,})]
            );

            assert.strictEqual(form.$('.o_field_text').text(), 'blipninja',
                'current line should be saved');
            assert.containsOnce(form, 'textarea.o_field_text',
                'new line should be created');

            form.destroy();
        });

        QUnit.test('one2many with onchange, required field, shortcut enter', function (assert) {
            assert.expect(5);

            this.data.turtle.onchanges = {
                turtle_foo: function () { },
            };

            var def;
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo" required="1"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
                // simulate what happens in the client:
                // the new value isn't notified directly to the model
                fieldDebounce: 5000,
            });

            var value = "hello";

            // add a new line
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            // we want to add a delay to simulate an onchange
            def = $.Deferred();

            // write something in the field
            var $input = form.$('input[name="turtle_foo"]');
            testUtils.fields.editInput($input, value);

            // trigger keydown ENTER
            $input.trigger($.Event('keydown', {
                keyCode: $.ui.keyCode.ENTER,
                which: $.ui.keyCode.ENTER,
            }));

            // check that nothing changed before the onchange finished
            assert.strictEqual($input.val(), value, "input content shouldn't change");
            assert.containsOnce(form, '.o_data_row',
                "should still contain only one row");

            // unlock onchange
            def.resolve();

            // check the current line is added with the correct content and a new line is editable
            assert.strictEqual(form.$('td.o_data_cell').text(), value);
            assert.strictEqual(form.$('input[name="turtle_foo"]').val(), '');
            assert.containsN(form, '.o_data_row', 2,
                "should now contain two rows");

            form.destroy();
        });

        QUnit.test('no deadlock when leaving a one2many line with uncommitted changes', function (assert) {
            // Before unselecting a o2m line, field widgets are asked to commit their changes (new values
            // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
            // ensuring that we don't end up in a deadlock when a widget actually has some changes to
            // commit at that moment.
            assert.expect(9);
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="turtles">' +
                    '<tree editable="bottom">' +
                    '<field name="turtle_foo"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
                // we set a fieldDebounce to precisely mock the behavior of the webclient: changes are
                // not sent to the model at keystrokes, but when the input is left
                fieldDebounce: 5000,
            });

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

            testUtils.fields.editInput(form.$('.o_field_widget[name=turtles] input'), 'some foo value');

            // click to add a second row to unselect the current one, then save
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.form.clickSave(form);

            assert.containsOnce(form, '.o_form_readonly',
                "form view should be in readonly");
            assert.strictEqual(form.$('.o_data_row').text(), 'some foo value',
                "foo field should have correct value");
            assert.verifySteps([
                'default_get', // main record
                'default_get', // line 1
                'default_get', // line 2
                'create',
                'read', // main record
                'read', // line 1
            ]);

            form.destroy();
        });

        QUnit.test('one2many with extra field from server not in form', function (assert) {
            assert.expect(6);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="p" >' +
                    '<tree>' +
                    '<field name="datetime"/>' +
                    '<field name="display_name"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
                archs: {
                    'partner,false,form': '<form>' +
                        '<field name="display_name"/>' +
                        '</form>'
                },
                mockRPC: function (route, args) {
                    if (route === '/web/dataset/call_kw/partner/write') {
                        args.args[1].p[0][2].datetime = '2018-04-05 12:00:00';
                    }
                    return this._super.apply(this, arguments);
                }
            });

            testUtils.form.clickEdit(form);

            var x2mList = form.$('.o_field_x2many_list[name=p]');

            // Add a record in the list
            testUtils.dom.click(x2mList.find('.o_field_x2many_list_row_add a'));

            var modal = $('.modal-lg');

            var nameInput = modal.find('input.o_input[name=display_name]');
            testUtils.fields.editInput(nameInput, 'michelangelo');

            // Save the record in the modal (though it is still virtual)
            testUtils.dom.click(modal.find('.btn-primary').first());

            assert.equal(x2mList.find('.o_data_row').length, 1,
                'There should be 1 records in the x2m list');

            var newlyAdded = x2mList.find('.o_data_row').eq(0);

            assert.equal(newlyAdded.find('.o_data_cell').first().text(), '',
                'The create_date field should be empty');
            assert.equal(newlyAdded.find('.o_data_cell').eq(1).text(), 'michelangelo',
                'The display name field should have the right value');

            // Save the whole thing
            testUtils.form.clickSave(form);

            x2mList = form.$('.o_field_x2many_list[name=p]');

            // Redo asserts in RO mode after saving
            assert.equal(x2mList.find('.o_data_row').length, 1,
                'There should be 1 records in the x2m list');

            newlyAdded = x2mList.find('.o_data_row').eq(0);

            assert.equal(newlyAdded.find('.o_data_cell').first().text(), '04/05/2018 12:00:00',
                'The create_date field should have the right value');
            assert.equal(newlyAdded.find('.o_data_cell').eq(1).text(), 'michelangelo',
                'The display name field should have the right value');

            form.destroy();
        });

        QUnit.test('one2many invisible depends on parent field', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="product_id"/>' +
                    '</group>' +
                    '<notebook>' +
                    '<page string="Partner page">' +
                    '<field name="bar"/>' +
                    '<field name="p">' +
                    '<tree>' +
                    '<field name="foo" attrs="{\'column_invisible\': [(\'parent.product_id\', \'!=\', False)]}"/>' +
                    '<field name="bar" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                    '</tree>' +
                    '</field>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });
            assert.containsN(form, 'th', 2,
                "should be 2 columns in the one2many");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_many2one[name="product_id"] input'));
            testUtils.dom.click($('li.ui-menu-item a:contains(xpad)').trigger('mouseenter'));
            assert.containsOnce(form, 'th',
                "should be 1 column when the product_id is set");
            form.$('.o_field_many2one[name="product_id"] input').val('').trigger('keyup');
            assert.containsN(form, 'th', 2,
                "should be 2 columns in the one2many when product_id is not set");
            testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
            assert.containsOnce(form, 'th',
                "should be 1 column after the value change");
            form.destroy();
        });

        QUnit.test('one2many column visiblity depends on onchange of parent field', function (assert) {
            assert.expect(3);

            this.data.partner.records[0].p = [2];
            this.data.partner.records[0].bar = false;

            this.data.partner.onchanges.p = function (obj) {
                // set bar to true when line is added
                if (obj.p.length > 1 && obj.p[1][2].foo === 'New line') {
                    obj.bar = true;
                }
            };

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="bar"/>' +
                    '<field name="p">' +
                    '<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="int_field" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                    '</tree>' +
                    '</field>' +
                    '</form>',
                res_id: 1,
            });

            // bar is false so there should be 1 column
            assert.containsOnce(form, 'th',
                "should be only 1 column ('foo') in the one2many");
            assert.containsOnce(form, '.o_list_view .o_data_row', "should contain one row");

            testUtils.form.clickEdit(form);

            // add a new o2m record
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            form.$('.o_field_one2many input:first').focus();
            testUtils.fields.editInput(form.$('.o_field_one2many input:first'), 'New line');
            testUtils.dom.click(form.$el);

            assert.containsN(form, 'th', 2, "should be 2 columns('foo' + 'int_field')");

            form.destroy();
        });

        QUnit.test('one2many column_invisible on view not inline', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].p = [2];
            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="product_id"/>' +
                    '</group>' +
                    '<notebook>' +
                    '<page string="Partner page">' +
                    '<field name="bar"/>' +
                    '<field name="p"/>' +
                    '</page>' +
                    '</notebook>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
                archs: {
                    'partner,false,list': '<tree>' +
                        '<field name="foo" attrs="{\'column_invisible\': [(\'parent.product_id\', \'!=\', False)]}"/>' +
                        '<field name="bar" attrs="{\'column_invisible\': [(\'parent.bar\', \'=\', False)]}"/>' +
                        '</tree>',
                },
            });
            assert.containsN(form, 'th', 2,
                "should be 2 columns in the one2many");
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_many2one[name="product_id"] input'));
            testUtils.dom.click($('li.ui-menu-item a:contains(xpad)').trigger('mouseenter'));
            assert.containsOnce(form, 'th',
                "should be 1 column when the product_id is set");
            form.$('.o_field_many2one[name="product_id"] input').val('').trigger('keyup');
            assert.containsN(form, 'th', 2,
                "should be 2 columns in the one2many when product_id is not set");
            testUtils.dom.click(form.$('.o_field_boolean[name="bar"] input'));
            assert.containsOnce(form, 'th',
                "should be 1 column after the value change");
            form.destroy();
        });
    });
});
});
