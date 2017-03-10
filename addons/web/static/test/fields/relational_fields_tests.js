odoo.define('web.relational_fields_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var ListView = require('web.ListView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('relational_fields', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean", default: true},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1] },
                    p: {string: "one2many field", type: "one2many", relation: 'partner', relation_field: 'trululu'},
                    turtles: {string: "one2many turtle field", type: "one2many", relation: 'turtle'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    color: {
                        type: "selection",
                        selection: [['red', "Red"], ['black', "Black"]],
                        default: 'red',
                    },
                    date: {string: "Some Date", type: "date"},
                    datetime: {string: "Datetime Field", type: 'datetime'},
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
                }, {
                    id: 4,
                    display_name: "aaa",
                    bar: false,
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
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
                    name: {string: "Partner Type", type: "char"},
                    color: {string: "Color index", type: "int"},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
            turtle: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    turtle_foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    turtle_bar: {string: "Bar", type: "boolean", default: true},
                    turtle_int: {string: "int", type: "integer", sortable: true},
                    turtle_qux: {string: "Qux", type: "float", digits: [16,1], required: true, default: 1.5},
                    turtle_trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    product_id: {string: "Product", type: "many2one", relation: 'product', required: true},
                },
                records: [{
                    id: 1,
                    display_name: "leonardo",
                    turtle_bar: true,
                    turtle_foo: "yop",
                }, {
                    id: 2,
                    display_name: "donatello",
                    turtle_bar: true,
                    turtle_foo: "blip",
                    turtle_int: 9,
                }, {
                    id: 3,
                    display_name: "raphael",
                    turtle_bar: false,
                    turtle_foo: "kawa",
                    turtle_int: 21,
                    turtle_qux: 9.8,
                }],
            }
        };
    }
}, function () {

    QUnit.module('FieldMany2One');

    QUnit.test('many2ones in form views', function (assert) {
        assert.expect(4);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action') {
                    assert.deepEqual(args.args[0], [4], "should call get_formview_action with correct id");
                    return $.when({
                        res_id: 17,
                        type: 'ir.actions.act_window',
                        target: 'current',
                        res_model: 'res.partner'
                    });
                }
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [4], "should call get_formview_id with correct id");
                    return $.when(false);
                }
                return this._super(route, args);
            },
        });

        testUtils.intercept(form, 'do_action', function (event) {
            assert.strictEqual(event.data.action.res_id, 17,
                "should do a do_action with correct parameters");
        });
        testUtils.intercept(form, 'load_views', function (event) {
            // temporarily prevent the fields_view from being loaded (to prevent a crash)
            // TODO: specify a fields_view and test that we can edit the record in the dialog
            event.stopPropagation();
        });

        assert.strictEqual(form.$('a.o_form_uri:contains(aaa)').length, 1,
                        "should contain a link");
        form.$('a.o_form_uri').click(); // click on the link in readonly mode (should trigger do_action)

        form.$buttons.find('.o_form_button_edit').click();

        form.$('.o_external_button').click(); // click on the external button (should do an RPC)

        // TODO: test that we can edit the record in the dialog, and that the value is correctly
        // updated on close
        form.destroy();
    });

    QUnit.test('many2one readonly fields with option "no_open"', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu" options="{&quot;no_open&quot;: True}" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('a.o_form_uri').length, 0, "should not have an anchor");
        form.destroy();
    });

    QUnit.test('many2one in edit mode', function (assert) {
        assert.expect(16);

        // create 10 partners to have the 'Search More' option in the autocomplete dropdown
        for (var i=0; i<10; i++) {
            var id = 20 + i;
            this.data.partner.records.push({id: id, display_name: "Partner " + id});
        }

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,list': '<tree string="Partners"><field name="display_name"/></tree>',
                'partner,false,search': '<search string="Partners">' +
                                            '<field name="display_name" string="Name"/>' +
                                        '</search>',
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[1].trululu, 20, "should write the correct id");
                }
                return this._super.apply(this, arguments);
            },
        });

        // the SelectCreateDialog requests the session, so intercept its custom
        // event to specify a fake session to prevent it from crashing
        testUtils.intercept(form, 'get_session', function (event) {
            event.data.callback({user_context: {}});
        });

        form._toEditMode();
        var $dropdown = form.$('.o_form_field_many2one input').autocomplete('widget');

        form.$('.o_form_field_many2one input').click();
        assert.ok($dropdown.is(':visible'),
                    'clicking on the m2o input should open the dropdown if it is not open yet');
        assert.strictEqual($dropdown.find('li:not(.o_m2o_dropdown_option)').length, 7,
                    'autocomplete should contains 7 suggestions');
        assert.strictEqual($dropdown.find('li.o_m2o_dropdown_option').length, 2,
                    'autocomplete should contain "Search More" and Create and Edit..."');

        form.$('.o_form_field_many2one input').click();
        assert.ok(!$dropdown.is(':visible'),
                    'clicking on the m2o input should close the dropdown if it is open');

        // change the value of the m2o with a suggestion of the dropdown
        form.$('.o_form_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!$dropdown.is(':visible'), 'clicking on a value should close the dropdown');
        assert.strictEqual(form.$('.o_form_field_many2one input').val(), 'first record',
                    'value of the m2o should have been correctly updated');

        // change the value of the m2o with a record in the 'Search More' modal
        form.$('.o_form_field_many2one input').click();
        // click on 'Search More' (mouseenter required by ui-autocomplete)
        $dropdown.find('.o_m2o_dropdown_option:contains(Search)').mouseenter().click();
        assert.ok($('.modal .o_list_view').length, "should have opened a list view in a modal");
        assert.ok(!$('.modal .o_list_view .o_list_record_selector').length,
            "there should be no record selector in the list view");
        assert.ok(!$('.modal .modal-footer .o_select_button').length,
            "there should be no 'Select' button in the footer");
        assert.ok($('.modal tbody tr').length > 10, "list should contain more than 10 records");
        // filter the list using the searchview
        $('.modal .o_searchview_input').trigger({type: 'keypress', which: 80}); // P
        $('.modal .o_searchview_input').trigger({type: 'keydown', which: 13}); // enter
        assert.strictEqual($('.modal tbody tr').length, 10,
            "list should be restricted to records containing a P (10 records)");
        // choose a record
        $('.modal tbody tr:contains(Partner 20)').click(); // choose record 'Partner 20'
        assert.ok(!$('.modal').length, "should have closed the modal");
        assert.ok(!$dropdown.is(':visible'), 'should have closed the dropdown');
        assert.strictEqual(form.$('.o_form_field_many2one input').val(), 'Partner 20',
                    'value of the m2o should have been correctly updated');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('a.o_form_uri').text(), 'Partner 20',
            "should display correct value after save");

        form.destroy();
    });

    QUnit.test('many2one field with option always_reload', function (assert) {
        assert.expect(4);
        var count = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="trululu" options="{\'always_reload\': True}"/>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    count++;
                    return $.when([[1, "first record\nand some address"]]);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(count, 1, "an extra name_get should have been done");
        assert.ok(form.$('a:contains(and some address)').length,
            "should display additional result");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('input').val(), "first record",
            "actual field value should be displayed to be edited");

        form.$buttons.find('.o_form_button_save').click();

        assert.ok(form.$('a:contains(and some address)').length,
            "should still display additional result");
        form.destroy();
    });

    // QUnit.test('onchange on a many2one to a different model', function (assert) {
        // This test is commented because the mock server does not give the correct response.
        // It should return a couple [id, display_name], but I don't know the logic used
        // by the server, so it's hard to emulate it correctly
    //     assert.expect(2);

    //     this.data.partner.records[0].product_id = 41;
    //     this.data.partner.onchanges = {
    //         foo: function(obj) {
    //             obj.product_id = 37;
    //         },
    //     };

    //     var form = createView({
    //         View: FormView,
    //         model: 'partner',
    //         data: this.data,
    //         arch: '<form>' +
    //                 '<field name="foo"/>' +
    //                 '<field name="product_id"/>' +
    //             '</form>',
    //         res_id: 1,
    //     });
    //     form.$buttons.find('.o_form_button_edit').click();
    //     assert.strictEqual(form.$('input').eq(1).val(), 'xpad', "initial product_id val should be xpad");

    //     form.$('input').eq(0).val("let us trigger an onchange").trigger('input');

    //     assert.strictEqual(form.$('input').eq(1).val(), 'xphone', "onchange should have been applied");
    // });

    QUnit.test('autocompletion in a many2one, in form view with a domain', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                domain: [['trululu', '=', 4]]
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, [], "should not have a domain");
                }
                return this._super(route, args);
            }
        });
        form.$buttons.find('.o_form_button_edit').click();

        form.$('input').click();
        form.destroy();
    });

    QUnit.test('autocompletion in a many2one, in form view with a date field', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar"/>' +
                    '<field name="date"/>' +
                    '<field name="trululu" domain="[(\'bar\',\'=\',True)]"/>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, [["bar", "=", true]], "should not have a domain");
                }
                return this._super(route, args);
            },
        });
        form.$buttons.find('.o_form_button_edit').click();

        form.$('input:eq(2)').click();
        form.destroy();
    });

    QUnit.test('creating record with many2one with option always_reload', function (assert) {
        assert.expect(2);

        this.data.partner.fields.trululu.default = 1;
        this.data.partner.onchanges = {
            trululu: function (obj) {
                obj.trululu = 2; //[2, "second record"];
            },
        };

        var count = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="trululu" options="{\'always_reload\': True}"/>' +
                '</form>',
            mockRPC: function (route, args) {
                count++;
                if (args.method === 'name_get' && args.args[0][0] === 2) {
                    return $.when([[2, "hello world\nso much noise"]]);
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(count, 3, "should have done 3 rpcs (default_get, onchange, name_get)");
        assert.strictEqual(form.$('input').val(), 'hello world',
            "should have taken the correct display name");
        form.destroy();
    });

    QUnit.test('selecting a many2one, then discarding', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="product_id"/>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('a').text(), '', 'the tag a should be empty');
        form.$buttons.find('.o_form_button_edit').click();

        form.$('.o_form_field_many2one input').click();
        form.$('.o_form_field_many2one input').autocomplete('widget').find('a').first().click();


        assert.strictEqual(form.$('input').val(), "xphone", "should have selected xphone");

        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual(form.$('a').text(), '', 'the tag a should be empty');
        form.destroy();
    });

    QUnit.test('domain and context are correctly used when doing a name_search in a m2o', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<field name="product_id" ' +
                        'domain="[[\'foo\', \'=\', \'bar\'], [\'foo\', \'=\', foo]]" ' +
                        'context="{\'hello\': \'world\', \'test\': foo}"/>' +
                    '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            session: {user_context: {hey: "ho"}},
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/name_search') {
                    assert.deepEqual(
                        args.kwargs.args,
                        [['foo', '=', 'bar'], ['foo', '=', 'yop']],
                        'the field attr domain should have been used for the RPC (and evaluated)');
                    assert.deepEqual(
                        args.kwargs.context,
                        {hey: "ho", hello: "world", test: "yop"},
                        'the field attr context should have been used for the '
                        + 'RPC (evaluated and merged with the session one)');
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').first().click();

        form.destroy();
    });

    QUnit.module('FieldOne2Many');

    QUnit.test('one2many basic properties', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].p = [2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        });


        assert.strictEqual(form.$('td.o_list_record_selector').length, 0,
                        "embedded one2many should not have a selector");
        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            "embedded one2many should not be editable");
        assert.ok(!form.$('td.o_list_record_delete').length,
            "embedded one2many records should not have a trash icon");

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o_form_field_x2many_list_row_add').length,
            "embedded one2many should now be editable");

        assert.strictEqual(form.$('.o_form_field_x2many_list_row_add').attr('colspan'), "2",
            "should have colspan 2 (one for field foo, one for being below trash icon)");

        assert.ok(form.$('td.o_list_record_delete').length,
            "embedded one2many records should have a trash icon");
        form.destroy();
    });

    QUnit.test('one2many with date and datetime', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].p = [2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        });
        // FIXME: this test is locale dependant. we need to do it right.
        assert.strictEqual(form.$('td:contains(01/25/2017)').length, 1,
            "should have formatted the date");
        assert.strictEqual(form.$('td:contains(12/12/2016 10:55:05)').length, 1,
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
            arch:'<form string="Partners">' +
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

    QUnit.test('embedded one2many with widget', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].p = [2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        assert.strictEqual(form.$('span.o_row_handle').length, 1, "should have 1 handles");
        form.destroy();
    });

    QUnit.test('one2many field when using the pager', function (assert) {
        assert.expect(13);

        var ids = [];
        for (var i=0; i<45; i++) {
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
        // records, but that is already in cache so only 1 RPC (the read for the
        // main record) should have been done
        form.pager.previous();
        assert.strictEqual(count, 5, 'one RPC should have been done');
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'one2many kanban should contain 40 cards for record 1');

        // move to the second page of the o2m: 1 RPC should have been done to fetch
        // the 2 subrecords of page 2, and those records should now be displayed
        form.$('.o_x2m_control_panel .o_pager_next').click();
        assert.strictEqual(count, 6, 'one RPC should have been done');
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 2,
            'one2many kanban should contain 2 cards for record 1 at page 2');

        // move to record 2 again and check that everything is correctly updated
        // (only one RPC should be done, to read the record 2)
        form.pager.next();
        assert.strictEqual(count, 7, 'one RPC should have been done');
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 3,
            'one2many kanban should contain 3 cards for record 2');

        // move back to record 1 and move to page 2 again: all o2m records should
        // be in cache
        form.pager.previous();
        assert.strictEqual(count, 8, 'one RPC should have been done'); // the read of record 1
        form.$('.o_x2m_control_panel .o_pager_next').click();
        assert.strictEqual(count, 8, 'no more RPC should have been done');
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 2,
            'one2many kanban should contain 2 cards for record 1 at page 2');
        form.destroy();
    });

    QUnit.test('sorting one2many fields', function (assert) {
        assert.expect(4);

        this.data.partner.fields.foo.sortable = true;
        this.data.partner.records.push({id: 23, foo: "abc"});
        this.data.partner.records.push({id: 24, foo: "xyz"});
        this.data.partner.records.push({id: 25, foo: "def"});
        this.data.partner.records[0].p = [23,24,25];

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

        form.$('table thead th:contains(Foo)').click();
        assert.strictEqual(rpcCount, 0,
            'sort should be in memory, no extra RPCs should have been done');
        assert.ok(form.$('table tbody tr:eq(2) td:contains(xyz)').length,
            "the 3rd record is the one with 'xyz' value");

        form.$('table thead th:contains(Foo)').click();
        assert.ok(form.$('table tbody tr:eq(2) td:contains(abc)').length,
            "the 3rd record is the one with 'abc' value");

        form.destroy();
    });

    QUnit.test('one2many list field edition', function (assert) {
        assert.expect(7);

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody td').first().click();
        assert.ok(form.$('.o_field_one2many tbody td').first().hasClass('o_edit_mode'),
            "first row of o2m should be in edition");
        form.$('.o_field_one2many tbody td').first().find('input').val("new value").trigger('input');
        assert.ok(form.$('.o_field_one2many tbody td').first().hasClass('o_edit_mode'),
            "first row of o2m should still be in edition");

        // // leave o2m edition
        form.$el.click();
        assert.ok(!form.$('.o_field_one2many tbody td').first().hasClass('o_edit_mode'),
            "first row of o2m should be readonly again");

        // discard changes
        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'new value',
            "changes shouldn't have been discarding yet, waiting for user confirmation");
        $('.modal .modal-footer .btn-primary').click();
        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'relational record 1',
            "display name of first record in o2m list should be 'relational record 1'");

        // edit again and save
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody td').first().click();
        form.$('.o_field_one2many tbody td').first().find('input').val("new value").trigger('input');
        form.$el.click();
        form.$buttons.find('.o_form_button_save').click();
        // FIXME: this next test doesn't actually test that the save works, because the relational
        // data isn't reloaded when clicking on save (it doesn't work for now actually)
        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'new value',
            "display name of first record in o2m list should be 'new value'");

        form.destroy();
    });

    QUnit.test('one2many list: create action disabled', function (assert) {
        assert.expect(2);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree create="0">' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in readonly');
        form.destroy();
    });

    QUnit.test('one2many list: deleting one record', function (assert) {
        assert.expect(5);
        this.data.partner.records[0].p = [2, 4];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.strictEqual(commands.length, 2,
                        'should have generated two commands');
                    assert.ok(commands[0][0] === 4 && commands[0][1] === 4,
                        'should have generated the command 4 (LINK_TO) with id 4');
                    assert.ok(commands[1][0] === 2 && commands[1][1] === 2,
                        'should have generated the command 2 (DELETE) with id 2');
                }
                return this._super.apply(this, arguments);
            },
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('td.o_list_record_delete span').length, 2,
            "should have 2 delete buttons");

        form.$('td.o_list_record_delete span').first().click();

        assert.strictEqual(form.$('td.o_list_record_delete span').length, 1,
            "should have 1 delete button (a record is supposed to have been deleted)");

        // save and check that the correct command has been generated
        form.$buttons.find('.o_form_button_save').click();

        // FIXME: it would be nice to test that the view is re-rendered correctly,
        // but as the relational data isn't re-fetched, the rendering is ok even
        // if the changes haven't been saved
        form.destroy();
    });

    QUnit.test('one2many kanban: edition', function (assert) {
        assert.expect(13);

        this.data.partner.records[0].p = [2];
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
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
                                        '<span><t t-esc="record.display_name.value"/></span>' +
                                    '</div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(!form.$('.o_kanban_view .delete_icon').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_form_field_one2many .o-kanban-button-new').length,
            '"Create" button should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
            'should contain 1 record');
        assert.strictEqual(form.$('.o_kanban_record span').text(), 'second record',
            'display_name of subrecord should be the one in DB');
        assert.ok(form.$('.o_kanban_view .delete_icon').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_form_field_one2many .o-kanban-button-new').length,
            '"Create" button should be visible in edit');

        // edit existing subrecord
        form.$('.oe_kanban_global_click').click();

        $('.modal .o_form_view .o_form_input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_kanban_record span').text(), 'new name',
            'value of subrecord should have been updated');

        // create a new subrecord
        form.$('.o-kanban-button-new').click();
        $('.modal .o_form_view .o_form_input').val('new subrecord 1').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save and close
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_kanban_record:nth(1) span').text(), 'new subrecord 1',
            'value of newly created subrecord should be "new subrecord 1"');

        // create two new subrecords
        form.$('.o-kanban-button-new').click();
        $('.modal .o_form_view .o_form_input').val('new subrecord 2').trigger('input');
        $('.modal .modal-footer .btn-primary:nth(1)').click(); // save and new
        $('.modal .o_form_view .o_form_input').val('new subrecord 3').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save and close
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 4,
            'should contain 4 records');

        // delete subrecords
        form.$('.o_kanban_view .delete_icon:first()').click();
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 3,
            'should contain 3 records');
        form.$('.o_kanban_view .delete_icon:first()').click();
        form.$('.o_kanban_view .delete_icon:first()').click();
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 1,
            'should contain 1 records');
        assert.strictEqual(form.$('.o_kanban_record span').text(), 'new subrecord 3',
            'the remaining subrecord should be "new subrecord 3"');
        form.destroy();
    });

    QUnit.test('one2many kanban: create action disabled', function (assert) {
        assert.expect(3);

        this.data.partner.records[0].p = [4];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<kanban create="0">' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div class="oe_kanban_global_click">' +
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
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

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(!form.$('.o-kanban-button-new').length,
            '"Add" button should not be available in edit');
        assert.ok(form.$('.o_kanban_view .delete_icon').length,
            'delete icon should be visible in edit');
        form.destroy();
    });

    QUnit.test('one2many list (non editable): edition', function (assert) {
        assert.expect(9);

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
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'second record',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should not visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody tr:first() td:eq(1)').click();

        $('.modal .o_form_view .o_form_input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');

        // create new subrecords
        // TODO when 'Add an item' will be implemented

        // delete subrecords
        form.$('.o_list_record_delete:first()').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 1,
            'should contain 1 subrecord');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'aaa',
            'the remaining subrecord should be "aaa"');
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

        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in readonly');

        form.$('.o_list_view tbody td:first()').click();
        assert.ok($('.modal .o_form_readonly').length,
            'in readonly, clicking on a subrecord should open it in readonly in a dialog');
        $('.modal .o_form_button_cancel').click(); // close the dialog

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should be available in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody td:first()').click();
        assert.strictEqual($('.modal').length, 0,
            'in edit, clicking on a subrecord should not open a dialog');
        assert.ok(form.$('.o_list_view tbody tr:first()').hasClass('o_selected_row'),
            'first row should be in edition');
        form.$('.o_list_view .o_form_input:first()').val('new name').trigger('input');

        form.$('.o_list_view tbody tr:nth(1) td:first').click(); // click on second record to validate the first one
        assert.ok(!form.$('.o_list_view tbody tr:first').hasClass('o_selected_row'),
            'first row should not be in edition anymore');
        assert.strictEqual(form.$('.o_list_view tbody td:first').text(), 'new name',
            'value of subrecord should have been updated');

        // create new subrecords
        // TODO when 'Add an item' will be implemented
        form.destroy();
    });

    QUnit.test('onchange in a one2many', function (assert) {
        assert.expect(1);

        this.data.partner.records.push({
            id: 3,
            foo: "relational record 1",
        });
        this.data.partner.records[1].p = [3];
        this.data.partner.onchanges = {p: true};

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
                    return $.when({value: { p: [
                        [5],                             // delete all
                        [0, 0, {foo: "from onchange"}],  // create new
                    ]}});
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody td').first().click();
        form.$('.o_field_one2many tbody td').first().find('input').val("new value").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'from onchange',
            "display name of first record in o2m list should be 'new value'");
        form.destroy();
    });

    QUnit.test('one2many, default_get and onchange (basic)', function (assert) {
        assert.expect(1);

        this.data.partner.fields.p.default = [
            [6, 0, []],                  // replace with zero ids
        ];
        this.data.partner.onchanges = {p: true};

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({value: { p: [
                        [5],                             // delete all
                        [0, 0, {foo: "from onchange"}],  // create new
                    ]}});
                }
                return this._super(route, args);
            },
        });

        assert.ok(form.$('td:contains(from onchange)').length,
            "should have 'from onchange' value in one2many");
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

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o_list_view tbody tr:eq(0) td:first').hasClass('o_readonly'),
            "first record should have display_name in readonly mode");

        assert.notOk(form.$('.o_list_view tbody tr:eq(1) td:first').hasClass('o_readonly'),
            "second record should not have display_name in readonly mode");
        form.destroy();
    });

    QUnit.test('pager of one2many field in new record', function (assert) {
        assert.expect(2);

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
            archs: {
                'partner,false,form':
                    '<form string="Partner"><field name="foo"/></form>',
            },
        });

        assert.ok(!form.$('.o_x2m_control_panel .o_cp_pager div').is(':visible'),
            'o2m pager should be hidden');

        // click to create a subrecord
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
        $('.modal .o_form_input').val('new record').trigger('input');
        $('.modal .modal-footer button:eq(0)').click(); // save and close

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
                [1, 2, {product_id: [37, "xphone"]}], // update existing record
                [0, 0, {product_id: [41, "xpad"]}]
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
                    assert.deepEqual(args.args[1].p, [[4, 2, false], [0, false, {product_id: 41}]],
                        "should trigger onchange with correct parameters");
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.strictEqual(form.$('tbody td:contains(xphone)').length, 1,
            "should have properly fetched the many2one nameget");
        assert.strictEqual(form.$('tbody td:contains(xpad)').length, 0,
            "should not display 'xpad' anywhere");

        form.$buttons.find('.o_form_button_edit').click();

        form.$('tbody td.o_form_field_x2many_list_row_add a').click();

        $('.modal .o_form_field_many2one input').click();

        var $dropdown = $('.modal .o_form_field_many2one input').autocomplete('widget');

        $dropdown.find('li:eq(1) a').mouseenter();
        $dropdown.find('li:eq(1) a').click();

        $('.modal .modal-footer button:eq(0)').click(); // save and close

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
                    assert.deepEqual(args.args[1].p, [[0, false, {
                        int_field: 123, product_id: 41
                    }]]);
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        form.$('tbody td.o_form_field_x2many_list_row_add a').click();

        // write in the many2one field, value = 37 (xphone)
        $('.modal .o_form_field_many2one input').click();
        var $dropdown = $('.modal .o_form_field_many2one input').autocomplete('widget');
        $dropdown.find('li:eq(0) a').mouseenter();
        $dropdown.find('li:eq(0) a').click();

        // write in the integer field
        $('.modal .modal-body input.o_field_widget').val('123').trigger('input');

        // save and close
        $('.modal .modal-footer button:eq(0)').click();

        assert.strictEqual(form.$('tbody td:contains(xphone)').length, 1,
            "should display 'xphone' in a td");

        // reopen the record in form view
        form.$('tbody td:contains(xphone)').click();

        assert.strictEqual($('.modal .modal-body input').val(), "xphone",
            "should display 'xphone' in an input");

        $('.modal .modal-body input.o_field_widget').val('456').trigger('input');

        // discard
        $('.modal .modal-footer span:contains(Discard)').click();

        // reopen the record in form view
        form.$('tbody td:contains(xphone)').click();

        assert.strictEqual($('.modal .modal-body input.o_field_widget').val(), "123",
            "should display 123 (previous change has been discarded)");

        // write in the many2one field, value = 41 (xpad)
        $('.modal .o_form_field_many2one input').click();
        $dropdown = $('.modal .o_form_field_many2one input').autocomplete('widget');
        $dropdown.find('li:eq(1) a').mouseenter();
        $dropdown.find('li:eq(1) a').click();

        // save and close
        $('.modal .modal-footer button:eq(0)').click();

        assert.strictEqual(form.$('tbody td:contains(xpad)').length, 1,
            "should display 'xpad' in a td");

        // save the record
        form.$buttons.find('.o_form_button_save').click();
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

        form.$buttons.find('.o_form_button_edit').click();
        // open a modal
        form.$('tr.o_data_row:eq(0) td:contains(xphone)').click();

        // write in the many2one field
        $('.modal .o_form_field_many2one input').click();

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

        form.$buttons.find('.o_form_button_edit').click();

        form.$('tr.o_data_row:eq(0) td:contains(xphone)').click();

        // trigger a name search
        form.$('table td input.o_form_input').click();

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
        form.$buttons.find('.o_form_button_edit').click();

        form.$('tbody td.o_form_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('td input.o_field_widget.o_form_input').length, 1,
            "should have created a row in edit mode");

        form.$('td input.o_field_widget.o_form_input').val('a').trigger('input');

        assert.strictEqual(form.$('td input.o_field_widget.o_form_input').length, 1,
            "should not have unselected the row after edition");

        form.$('td input.o_field_widget.o_form_input').val('abc').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
        form.destroy();
    });

    QUnit.test('one2many with many2many widget: create', function (assert) {
        assert.expect(10);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_form_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal .o_data_row').length, 2,
            "sould have 2 records in the select view (the last one is not displayed because it is already selected)");

        $('.modal .o_data_row:first .o_list_record_selector input').click();
        $('.modal .o_select_button').click();
        $('.o_form_button_save').click();
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_form_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal .o_data_row').length, 1,
            "sould have 1 record in the select view");

        $('.modal-footer button:eq(1)').click();
        $('.modal input.o_form_field[name="turtle_foo"]').val('tototo').trigger('input');
        $('.modal input.o_form_field[name="turtle_int"]').val(50).trigger('input');
        var $many2one = $('.modal [name="product_id"] input').click();
        var $dropdown = $many2one.autocomplete('widget');
        $dropdown.find('li:first a').mouseenter();
        $dropdown.find('li:first a').click();

        $('.modal-footer button:contains(&):first').click();

        assert.strictEqual($('.modal').length, 0, "sould close the modals");

        assert.strictEqual(form.$('.o_data_row').length, 3,
            "sould have 3 records in one2many list");
        assert.strictEqual(form.$('.o_data_row').text(), "blip1.59yop1.5tototo1.550xphone",
            "sould display the record values in one2many list");

        $('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('one2many with many2many widget: edition', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.deepEqual(args.args[1], {"product_id":37}, "should write only the product_id on the turtle record");
                }
                if (route === '/web/dataset/call_kw/partner/write') {
                    assert.strictEqual(args.args[0][0], 1, "should write on the partner record 1");
                    assert.strictEqual(args.args[1].turtles[0][0], 6, "should send only a 'replace with' command");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$('.o_data_row:first').click();
        $('.modal .o_form_button_cancel').click();
        form.$buttons.find('.o_form_button_edit').click();

        // edit the first one2many record
        form.$('.o_data_row:first').click();
        var $many2one = $('.modal [name="product_id"] input').click();
        var $dropdown = $many2one.autocomplete('widget');
        $dropdown.find('li:first a').mouseenter();
        $dropdown.find('li:first a').click();
        $('.modal-footer button:first').click();

        $('.o_form_button_save').click(); // don't save anything because the one2many does not change

        // add a one2many record
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_form_field_x2many_list_row_add a').click();
        $('.modal .o_data_row:first .o_list_record_selector input').click();
        $('.modal .o_select_button').click();

        // edit the second one2many record
        form.$('.o_data_row:eq(1)').click();
        $many2one = $('.modal [name="product_id"] input').click();
        $dropdown = $many2one.autocomplete('widget');
        $dropdown.find('li:first a').mouseenter();
        $dropdown.find('li:first a').click();
        $('.modal-footer button:first').click();

        $('.o_form_button_save').click();

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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
        form.destroy();
    });

    QUnit.test('parent data is properly sent on an onchange rpc', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges = {bar: function () {}};
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
        form.destroy();
    });

    QUnit.test('parent data is properly sent on an onchange rpc, new record', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges = {bar: function () {}};
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
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    var fieldValues = args.args[1];
                    assert.strictEqual(fieldValues.trululu.foo, "My little Foo Value",
                        "should have properly sent the parent foo value");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_form_field_x2many_list_row_add a').click();
        $('.modal-footer button.btn-primary').first().click();

        assert.strictEqual($('.modal').length, 1, "should still have an open modal");
        assert.strictEqual($('.modal tbody label.o_form_invalid').length, 1,
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
                    assert.strictEqual(event.data.record_id, 2,
                        'should call with correct id');
                    assert.strictEqual(event.data.model, 'partner',
                        'should call with correct model');
                    assert.strictEqual(event.data.action_data.name, 'method_name',
                        "should call correct method");
                    assert.strictEqual(event.data.action_data.type, 'object',
                        'should have correct type');
                },
            },
        });

        form.$('.o_list_button button').click();

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
                    assert.strictEqual(event.data.record_id, 2,
                        'should call with correct id');
                    assert.strictEqual(event.data.model, 'partner',
                        'should call with correct model');
                    assert.strictEqual(event.data.action_data.name, 'method_name',
                        "should call correct method");
                    assert.strictEqual(event.data.action_data.type, 'object',
                        'should have correct type');
                },
            },
        });

        form.$('.oe_kanban_action_button').click();

        form.destroy();
    });

    QUnit.module('FieldMany2Many');

    QUnit.test('many2many kanban: edition', function (assert) {
        assert.expect(28);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 15, display_name: "red", color: 6});
        this.data.partner_type.records.push({id: 18, display_name: "yellow", color: 4});
        this.data.partner_type.records.push({id: 21, display_name: "blue", color: 1});

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy">' +
                        '<kanban>' +
                            '<field name="display_name"/>' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div class="oe_kanban_global_click">' +
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
                                        '<span><t t-esc="record.display_name.value"/></span>' +
                                    '</div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            archs: {
                'partner_type,false,form': '<form string="Types"><field name="display_name"/></form>',
                'partner_type,false,list': '<tree string="Types"><field name="display_name"/></tree>',
                'partner_type,false,search': '<search string="Types">' +
                                                '<field name="name" string="Name"/>' +
                                            '</search>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner_type/write') {
                    assert.strictEqual(args.args[1].display_name, "new name", "should write 'new_name'");
                }
                if (route === '/web/dataset/call_kw/partner_type/create') {
                    assert.strictEqual(args.args[0].display_name, "A new type", "should create 'A new type'");
                }
                if (route === '/web/dataset/call_kw/partner/write') {
                    var commands = args.args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(commands[0][0], 6, "generated command should be REPLACE WITH");
                    // get the created type's id
                    var createdType = _.findWhere(this.data.partner_type.records, {
                        display_name: "A new type"
                    });
                    var ids = _.sortBy([12, 15, 18, 21].concat(createdType.id), _.identity.bind(_));
                    assert.ok(_.isEqual(_.sortBy(commands[0][2], _.identity.bind(_)), ids),
                        "new value should be " + ids);
                }
                return this._super.apply(this, arguments);
            },
        });

        // the SelectCreateDialog requests the session, so intercept its custom
        // event to specify a fake session to prevent it from crashing
        testUtils.intercept(form, 'get_session', function (event) {
            event.data.callback({user_context: {}});
        });

        assert.ok(!form.$('.o_kanban_view .delete_icon').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_form_field_many2many .o-kanban-button-new').length,
            '"Add" button should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_kanban_record:first() span').text(), 'gold',
            'display_name of subrecord should be the one in DB');
        assert.ok(form.$('.o_kanban_view .delete_icon').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_form_field_many2many .o-kanban-button-new').length,
            '"Add" button should be visible in edit');

        // edit existing subrecord
        form.$('.oe_kanban_global_click:first()').click();

        $('.modal .o_form_view .o_form_input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_kanban_record:first() span').text(), 'new name',
            'value of subrecord should have been updated');

        // add subrecords
        // -> single select
        form.$('.o_form_field_many2many .o-kanban-button-new').click();
        assert.ok($('.modal .o_list_view').length, "should have opened a list view in a modal");
        assert.strictEqual($('.modal .o_list_view tbody .o_list_record_selector').length, 3,
            "list view should contain 3 records");
        $('.modal .o_list_view tbody tr:contains(red)').click(); // select red
        assert.ok(!$('.modal .o_list_view').length, "should have closed the modal");
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 3,
            'kanban should now contain 3 records');
        assert.ok(form.$('.o_kanban_record:contains(red)').length,
            'record "red" should be in the kanban');

        // -> multiple select
        form.$('.o_form_field_many2many .o-kanban-button-new').click();
        assert.ok($('.modal .o_select_button').prop('disabled'), "select button should be disabled");
        assert.strictEqual($('.modal .o_list_view tbody .o_list_record_selector').length, 2,
            "list view should contain 2 records");
        $('.modal .o_list_view thead .o_list_record_selector input').click(); // select all
        $('.modal .o_select_button').click(); // validate selection
        assert.ok(!$('.modal .o_select_button').prop('disabled'), "select button should be enabled");
        assert.ok(!$('.modal .o_list_view').length, "should have closed the modal");
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 5,
            'kanban should now contain 5 records');
        // -> created record
        form.$('.o_form_field_many2many .o-kanban-button-new').click();
        $('.modal .modal-footer .btn-primary:nth(1)').click(); // click on 'Create'
        assert.ok($('.modal .o_form_view.o_form_editable').length,
            "should have opened a form view in edit mode, in a modal");
        $('.modal .o_form_view input').val('A new type').trigger('input');
        $('.modal:nth(1) .modal-footer .btn-primary:first()').click(); // click on 'Save & Close'
        assert.ok(!$('.modal').length, "should have closed both modals");
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 6,
            'kanban should now contain 6 records');
        assert.ok(form.$('.o_kanban_record:contains(A new type)').length,
            'the newly created type should be in the kanban');

        // delete subrecords
        form.$('.o_kanban_record:contains(silver) .delete_icon').click();
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 5,
            'should contain 5 records');
        assert.ok(!form.$('.o_kanban_record:contains(silver)').length,
            'the removed record should not be in kanban anymore');

        // save the record
        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
    });

    QUnit.test('many2many kanban: create action disabled', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].timmy = [12, 14];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy">' +
                        '<kanban create="0">' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div class="oe_kanban_global_click">' +
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
                                        '<span><t t-esc="record.display_name.value"/></span>' +
                                    '</div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                    '</field>' +
                '</form>',
            archs: {
                'partner_type,false,list': '<tree><field name="name"/></tree>',
                'partner_type,false,search': '<search>' +
                                            '<field name="display_name" string="Name"/>' +
                                        '</search>',
            },
            res_id: 1,
            session: {user_context: {}},
        });

        assert.ok(!form.$('.o-kanban-button-new').length,
            '"Add" button should not be available in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o-kanban-button-new').length,
            '"Add" button should be available in edit');
        assert.ok(form.$('.o_kanban_view .delete_icon').length,
            'delete icon should be visible in edit');

        form.$('.o-kanban-button-new').click(); // click on 'Add'
        assert.strictEqual($('.modal .modal-footer .btn-primary').length, 1, // only button 'Select'
            '"Create" button should not be available in the modal');

        form.destroy();
    });

    QUnit.test('many2many list (non editable): edition', function (assert) {
        assert.expect(9);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.fields.float_field = {string: 'Float', type: 'float'};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree>' +
                            '<field name="display_name"/><field name="float_field"/>' +
                        '</tree>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'gold',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should be visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody tr:first()').click();

        $('.modal .o_form_view .o_form_input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');

        // create new subrecords
        // TODO when 'Add an item' will be implemented

        // delete subrecords
        form.$('.o_list_record_delete:first()').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 1,
            'should contain 1 subrecord');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'silver',
            'the remaining subrecord should be "aaa"');
        form.destroy();
    });

    QUnit.test('many2many list (editable): edition', function (assert) {
        assert.expect(11);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.fields.float_field = {string: 'Float', type: 'float'};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree editable="top">' +
                            '<field name="display_name"/><field name="float_field"/>' +
                        '</tree>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'gold',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" should not visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody td:first()').click();
        assert.ok(!$('.modal').length,
            'in edit, clicking on a subrecord should not open a dialog');
        assert.ok(form.$('.o_list_view tbody tr:first()').hasClass('o_selected_row'),
            'first row should be in edition');
        form.$('.o_list_view .o_form_input:first()').val('new name').trigger('input');
        // FIXME: this doesn"t work for now as the x2many fields are reset on field changed
        // form.$('.o_list_view tbody td:nth(1)').click(); // click on second record to validate the first one
        // assert.ok(!form.$('.o_list_view tbody tr:first()').hasClass('o_selected_row'),
        //     'first row should not be in edition anymore');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');

        // add new subrecords
        // TODO when 'Add an item' will be implemented

        // delete subrecords
        form.$('.o_list_record_delete:first()').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 1,
            'should contain 1 subrecord');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'silver',
            'the remaining subrecord should be "aaa"');
        form.destroy();
    });

    QUnit.test('many2many list: create action disabled', function (assert) {
        assert.expect(2);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree create="0">' +
                            '<field name="name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(!form.$('.o_form_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in edit either');

        form.destroy();
    });

    QUnit.module('FieldStatus');

    QUnit.test('static statusbar widget on many2one field', function (assert) {
        assert.expect(5);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";
        this.data.partner.records.forEach(function (record) {
            record.bar = true;
        });
        var count = 0;
        var nb_fields_fetched;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="trululu" widget="statusbar"/>' +
                    // the following field seem useless, but its presence was the
                    // cause of a crash when evaluating the field domain.
                    '<field name="timmy"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    count++;
                    nb_fields_fetched = args.fields.length;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.strictEqual(count, 1, 'once search_read should have been done to fetch the relational values');
        assert.strictEqual(nb_fields_fetched, 1, 'search_read should only fetch field id');
        assert.strictEqual(form.$('.o_statusbar_status button').length, 3, "should have 3 status");
        assert.strictEqual(form.$('.o_statusbar_status button.disabled').length, 3,
            "all status should be disabled");
        assert.ok(form.$('.o_statusbar_status button[data-value="4"]').hasClass('btn-primary'),
            "selected status should be btn-primary");

        form.destroy();
    });

    QUnit.test('clickable statusbar widget on many2one field', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="trululu" widget="statusbar" clickable="True"/>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('.o_statusbar_status button[data-value="4"]').hasClass('btn-primary disabled'),
            "selected status should be btn-primary and disabled");
        assert.strictEqual(form.$('.o_statusbar_status button.btn-default:not(.disabled)').length, 2,
            "other status should be btn-default and not disabled");
        form.destroy();
    });

    QUnit.test('statusbar with no status', function (assert) {
        assert.expect(2);

        this.data.product.records = [];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="product_id" widget="statusbar"/>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('.o_statusbar_status').hasClass('o_form_field_empty'),
            'statusbar widget should have class o_form_field_empty');
        assert.strictEqual(form.$('.o_statusbar_status').children().length, 0,
            'statusbar widget should be empty');
        form.destroy();
    });

    QUnit.test('statusbar with dynamic domain', function (assert) {
        assert.expect(5);

        this.data.partner.fields.trululu.domain = "[('int_field', '>', qux)]";
        this.data.partner.records[2].int_field = 0;

        var rpcCount = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<field name="trululu" widget="statusbar"/>' +
                    '<field name="qux"/>' +
                    '<field name="foo"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/search_read') {
                    rpcCount++;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_statusbar_status button.disabled').length, 3, "should have 3 status");
        assert.strictEqual(rpcCount, 1, "should have done 1 search_read rpc");
        form.$('input:first').val(9.5).trigger("input").trigger("change");
        assert.strictEqual(form.$('.o_statusbar_status button.disabled').length, 2, "should have 2 status");
        assert.strictEqual(rpcCount, 2, "should have done 1 more search_read rpc");
        form.$('input:last').val("hey").trigger("input").trigger("change");
        assert.strictEqual(rpcCount, 2, "should not have done 1 more search_read rpc");

        form.destroy();
    });

    QUnit.module('FieldSelection');

    QUnit.test('widget selection in a list view', function (assert) {
        assert.expect(3);

        this.data.partner.records.forEach(function (r) {
            r.color = 'red';
        });

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree string="Colors" editable="top">' +
                        '<field name="color"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('td:contains(Red)').length, 3,
            "should have 3 rows with correct value");
        list.$('td:contains(Red):first').click();

        var $td = list.$('tbody tr.o_selected_row td:not(.o_list_record_selector)');

        assert.strictEqual($td.find('select').length, 1, "td should have a child 'select'");
        assert.strictEqual($td.contents().length, 1, "select tag should be only child of td");
        list.destroy();
    });

    QUnit.test('widget selection on a many2one field', function (assert) {
        assert.expect(7);

        var count = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="product_id" widget="selection"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                count++;
                return this._super(route, args);
            },
        });

        assert.ok(!form.$('select').length, "should not have a select tag in dom");
        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('select').length, "should have a select tag in dom");
        assert.ok(form.$('option:contains(xphone)').length, "should have fetched xphone option");
        assert.ok(form.$('option:contains(xpad)').length, "should have fetched xpad option");

        assert.strictEqual(form.$('select').val(), "false", "should not have any value");
        form.$('select').val(37).trigger('input');
        assert.strictEqual(form.$('select').val(), "37", "should have a value of xphone");

        count = 0;
        form.reload();
        assert.strictEqual(count, 1, "should not reload product_id relation");
        form.destroy();
    });

    QUnit.module('FieldMany2ManyTags');

    QUnit.test('fieldmany2many tags: rendering and edition', function (assert) {
        assert.expect(17);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 13, display_name: "red", color: 8});
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'no_create_edit\': True}"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    var commands = args.args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(commands[0][0], 6, "generated command should be REPLACE WITH");
                    assert.ok(_.isEqual(_.sortBy(commands[0][2], _.identity.bind(_)), [12, 13]),
                        "new value should be [12, 13]");
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(form.$('.o_form_field_many2manytags > span').length, 2,
            "should contain 2 tags");
        assert.ok(form.$('span:contains(gold)').length,
            'should have fetched and rendered gold partner tag');
        assert.ok(form.$('span:contains(silver)').length,
            'should have fetched and rendered silver partner tag');
        assert.strictEqual(form.$('span:first()').data('color'), 2,
            'should have correctly fetched the color');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_form_field_many2manytags > span').length, 2,
            "should still contain 2 tags in edit mode");
        assert.ok(form.$('.o_tag_color_2 .o_badge_text:contains(gold)').length,
            'first tag should still contain "gold" and be color 2 in edit mode');
        assert.strictEqual(form.$('.o_form_field_many2manytags .o_delete').length, 2,
            "tags should contain a delete button");

        // add an other existing tag
        var $input = form.$('.o_form_field_many2manytags input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 1,
            "autocomplete dropdown should have 1 entry");
        assert.strictEqual($input.autocomplete('widget').find('li a:contains("red")').length, 1,
            "autocomplete dropdown should contain 'red'");
        $input.autocomplete('widget').find('li').click(); // add 'red'
        assert.strictEqual(form.$('.o_form_field_many2manytags > span').length, 3,
            "should contain 3 tags");
        assert.ok(form.$('.o_form_field_many2manytags > span:contains("red")').length,
            "should contain newly added tag 'red'");
        assert.ok(form.$('.o_form_field_many2manytags > span[data-color=8]:contains("red")').length,
            "should have fetched the color of added tag");

        // remove tag with id 14
        form.$('.o_form_field_many2manytags span[data-id=14] .o_delete').click();
        assert.strictEqual(form.$('.o_form_field_many2manytags > span').length, 2,
            "should contain 2 tags");
        assert.ok(!form.$('.o_form_field_many2manytags > span:contains("silver")').length,
            "should not contain tag 'silver' anymore");

        // save the record (should do the write RPC with the correct commands)
        form.$buttons.find('.o_form_button_save').click();

        // TODO: it would be nice to test the behaviors of the autocomplete dropdown
        // (like refining the research, creating new tags...), but ui-autocomplete
        // makes it difficult to test
        form.destroy();
    });

    QUnit.test('fieldmany2many tags in a new record', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/create') {
                    var commands = args.args[0].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(commands[0][0], 6, "generated command should be REPLACE WITH");
                    assert.ok(_.isEqual(commands[0][2], [12]), "new value should be [12]");
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.ok(form.$('.o_form_view').hasClass('o_form_editable'), "form should be in edit mode");

        var $input = form.$('.o_form_field_many2manytags input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')");
        $input.autocomplete('widget').find('li:first()').click(); // adds a tag
        assert.strictEqual(form.$('.o_form_field_many2manytags > span').length, 1,
            "should contain 1 tag");
        assert.ok(form.$('.o_form_field_many2manytags > span:contains("gold")').length,
            "should contain newly added tag 'gold'");

        // save the record (should do the write RPC with the correct commands)
        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
    });

    QUnit.test('fieldmany2many tags: update color', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].timmy = [12, 14];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
        });

        // Update the color in readonly
        form.$('span:first()').click();
        $('.o_colorpicker span[data-color="1"]').trigger('mousedown'); // choose color 1
        assert.strictEqual(form.$('span:first()').data('color'), 1,
            'should have correctly updated the color (in readonly)');

        // Update the color in edit
        form.$buttons.find('.o_form_button_edit').click();
        form.$('span:first()').click();
        $('.o_colorpicker span[data-color="6"]').trigger('mousedown'); // choose color 6
        assert.strictEqual(form.$('span:first()').data('color'), 6,
            'should have correctly updated the color (in edit)');
        form.destroy();
    });

    QUnit.module('FieldRadio');

    QUnit.test('fieldradio widget on a many2one in a new record', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id" widget="radio"/>' +
                '</form>',
        });

        assert.ok(form.$('div.o_radio_item').length, "should have rendered outer div");
        assert.strictEqual(form.$('input.o_form_radio').length, 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(xphone)').length, "one of them should be xphone");
        assert.strictEqual(form.$('input:checked').length, 0, "none of the input should be checked");

        form.$("input.o_form_radio:first").click();

        assert.strictEqual(form.$('input:checked').length, 1, "one of the input should be checked");

        form.$buttons.find('.o_form_button_save').click();

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.product_id, 37, "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('fieldradio widget on a selection in a new record', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="color" widget="radio"/>' +
                '</form>',
        });


        assert.ok(form.$('div.o_radio_item').length, "should have rendered outer div");
        assert.strictEqual(form.$('input.o_form_radio').length, 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(Red)').length, "one of them should be Red");

        // click on 2nd option
        form.$("input.o_form_radio").eq(1).click();

        form.$buttons.find('.o_form_button_save').click();

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.color, 'black', "should have saved record with correct value");
        form.destroy();
    });

    QUnit.module('FieldMany2ManyCheckBoxes');

    QUnit.test('widget many2many_checkboxes', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].timmy = [12];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('div.o_form_field div.o_checkbox').length, 2,
            "should have fetched and displayed the 2 values of the many2many");

        assert.ok(form.$('div.o_form_field div.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('div.o_form_field div.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        assert.ok(form.$('div.o_form_field div.o_checkbox input').prop('disabled'),
            "the checkboxes should be disabled");

        form.$buttons.find('.o_form_button_edit').click();

        assert.notOk(form.$('div.o_form_field div.o_checkbox input').prop('disabled'),
            "the checkboxes should not be disabled");

        form.$('div.o_form_field div.o_checkbox input').eq(1).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.deepEqual(this.data.partner.records[0].timmy, [12, 14],
            "should have added the second element to the many2many");

        form.destroy();
    });
});
});
});
