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
                    user_id: {string: "User", type: 'many2one', relation: 'user'},
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
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 12, display_name: "gold", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                ]
            },
            turtle: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    turtle_foo: {string: "Foo", type: "char"},
                    turtle_bar: {string: "Bar", type: "boolean", default: true},
                    turtle_int: {string: "int", type: "integer", sortable: true},
                    turtle_qux: {string: "Qux", type: "float", digits: [16,1], required: true, default: 1.5},
                    turtle_description: {string: "Description", type: "text"},
                    turtle_trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    product_id: {string: "Product", type: "many2one", relation: 'product', required: true},
                    partner_ids: {string: "Partner", type: "many2many", relation: 'partner'},
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
                    partner_ids: [2,4],
                }, {
                    id: 3,
                    display_name: "raphael",
                    turtle_bar: false,
                    turtle_foo: "kawa",
                    turtle_int: 21,
                    turtle_qux: 9.8,
                    partner_ids: [],
                }],
            },
            user: {
                fields: {
                    name: {string: "Name", type: "char"}
                },
                records: [{
                    id: 17,
                    name: "Aline",
                }, {
                    id: 19,
                    name: "Christine",
                }]
            },
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

        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');

        form.$('.o_field_many2one input').click();
        assert.ok($dropdown.is(':visible'),
                    'clicking on the m2o input should open the dropdown if it is not open yet');
        assert.strictEqual($dropdown.find('li:not(.o_m2o_dropdown_option)').length, 7,
                    'autocomplete should contains 7 suggestions');
        assert.strictEqual($dropdown.find('li.o_m2o_dropdown_option').length, 2,
                    'autocomplete should contain "Search More" and Create and Edit..."');

        form.$('.o_field_many2one input').click();
        assert.ok(!$dropdown.is(':visible'),
                    'clicking on the m2o input should close the dropdown if it is open');

        // change the value of the m2o with a suggestion of the dropdown
        form.$('.o_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!$dropdown.is(':visible'), 'clicking on a value should close the dropdown');
        assert.strictEqual(form.$('.o_field_many2one input').val(), 'first record',
                    'value of the m2o should have been correctly updated');

        // change the value of the m2o with a record in the 'Search More' modal
        form.$('.o_field_many2one input').click();
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
        assert.strictEqual(form.$('.o_field_many2one input').val(), 'Partner 20',
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

        form.$('.o_field_many2one input').click();
        form.$('.o_field_many2one input').autocomplete('widget').find('a').first().click();


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

    QUnit.test('quick create on a many2one', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="product_id"/>' +
                        '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/name_create') {
                    assert.strictEqual(args.args[0], 'new partner',
                        "should name create a new product");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$('.o_field_many2one input').focus();
        form.$('.o_field_many2one input').val('new partner').trigger('keyup').trigger('focusout');

        $('.modal .modal-footer .btn-primary').first().click();

        form.destroy();
    });

    QUnit.test('no_create option on a many2one', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="product_id" options="{\'no_create\': True}"/>' +
                        '</sheet>' +
                '</form>',
        });

        form.$('.o_field_many2one input').focus();
        form.$('.o_field_many2one input').val('new partner').trigger('keyup').trigger('focusout');

        assert.strictEqual($('.modal').length, 0, "should not display the create modal");
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
        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            "embedded one2many should not be editable");
        assert.ok(!form.$('td.o_list_record_delete').length,
            "embedded one2many records should not have a trash icon");

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o_field_x2many_list_row_add').length,
            "embedded one2many should now be editable");

        assert.strictEqual(form.$('.o_field_x2many_list_row_add').attr('colspan'), "2",
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
            session: {
                tzOffset: 120
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
        // records
        form.pager.previous();
        assert.strictEqual(count, 6, 'two RPCs should have been done');
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'one2many kanban should contain 40 cards for record 1');

        // move to the second page of the o2m: 1 RPC should have been done to fetch
        // the 2 subrecords of page 2, and those records should now be displayed
        form.$('.o_x2m_control_panel .o_pager_next').click();
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
        form.$('.o_x2m_control_panel .o_pager_next').click();
        assert.strictEqual(count, 12, 'one RPC should have been done');
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody td').first().click();
        assert.ok(form.$('.o_field_one2many tbody td').first().parent().hasClass('o_selected_row'),
            "first row of o2m should be in edition");
        form.$('.o_field_one2many tbody td').first().find('input').val("new value").trigger('input');
        assert.ok(form.$('.o_field_one2many tbody td').first().parent().hasClass('o_selected_row'),
            "first row of o2m should still be in edition");

        // // leave o2m edition
        form.$el.click();
        assert.ok(!form.$('.o_field_one2many tbody td').first().parent().hasClass('o_selected_row'),
            "first row of o2m should be readonly again");

        // discard changes
        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'new value',
            "changes shouldn't have been discarded yet, waiting for user confirmation");
        $('.modal .modal-footer .btn-primary').click();
        assert.strictEqual(form.$('.o_field_one2many tbody td').first().text(), 'relational record 1',
            "display name of first record in o2m list should be 'relational record 1'");

        // edit again and save
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody td').first().click();
        form.$('.o_field_one2many tbody td').first().find('input').val("new value").trigger('input');
        form.$el.click();
        form.$buttons.find('.o_form_button_save').click();
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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
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
        assert.expect(14);

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
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
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

        form.$buttons.find('.o_form_button_edit').click();

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

        // edit existing subrecord
        form.$('.oe_kanban_global_click').click();

        $('.modal .o_form_view input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_kanban_record span:first').text(), 'new name',
            'value of subrecord should have been updated');

        // create a new subrecord
        form.$('.o-kanban-button-new').click();
        $('.modal .o_form_view input').val('new subrecord 1').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save and close
        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_kanban_record:nth(1) span').text(), 'new subrecord 1',
            'value of newly created subrecord should be "new subrecord 1"');

        // create two new subrecords
        form.$('.o-kanban-button-new').click();
        $('.modal .o_form_view input').val('new subrecord 2').trigger('input');
        $('.modal .modal-footer .btn-primary:nth(1)').click(); // save and new
        $('.modal .o_form_view input').val('new subrecord 3').trigger('input');
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
        assert.strictEqual(form.$('.o_kanban_record span:first').text(), 'new subrecord 3',
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
                        p: [[1, 2, {display_name: 'new name'}], [2, 4, false]]
                    }, "should have sent the correct commands");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'second record',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should not visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody tr:first() td:eq(1)').click();

        $('.modal .o_form_view input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');
        assert.strictEqual(nbWrite, 0, "should not have write anything in DB");

        // create new subrecords
        // TODO when 'Add an item' will be implemented

        // delete subrecords
        form.$('.o_list_record_delete:nth(1)').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 1,
            'should contain 1 subrecord');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'the remaining subrecord should be "new name"');

        form.$buttons.find('.o_form_button_save').click(); // save the record
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

        form.$('.o_list_view tbody td:first()').click();
        assert.ok($('.modal .o_form_readonly').length,
            'in readonly, clicking on a subrecord should open it in readonly in a dialog');
        $('.modal .o_form_button_cancel').click(); // close the dialog

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" link should be available in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody td:first()').click();
        assert.strictEqual($('.modal').length, 0,
            'in edit, clicking on a subrecord should not open a dialog');
        assert.ok(form.$('.o_list_view tbody tr:first()').hasClass('o_selected_row'),
            'first row should be in edition');
        form.$('.o_list_view input:first()').val('new name').trigger('input');

        form.$('.o_list_view tbody tr:nth(1) td:first').click(); // click on second record to validate the first one
        assert.ok(!form.$('.o_list_view tbody tr:first').hasClass('o_selected_row'),
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_selected_row > td input').val('kartoffel').trigger('input');

        // click again on Add an item
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('td:contains(kartoffel)').length, 1,
            "should have one td with the new value");
        assert.strictEqual(form.$('.o_selected_row > td input').length, 1,
            "should have one other new td");
        assert.strictEqual(form.$('tr.o_data_row').length, 2, "should have 2 data rows");

        // enter another value and save
        form.$('.o_selected_row > td input').val('gemuse').trigger('input');
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 2, "should have 2 data rows");
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
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "should have 1 data rows");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 3,
            "should have 3 data rows");

        // cancel the edition
        form.$buttons.find('.o_form_button_cancel').click();
        $('.modal-footer button.btn-primary').first().click();
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "should have 1 data rows");

        form.destroy();
    });

    QUnit.test('one2many list (editable): edition, part 4', function (assert) {
        assert.expect(3);

        this.data.turtle.onchanges = {
            turtle_trululu: function (obj) {
                if (obj.turtle_trululu) {
                    obj.turtle_description = "Some Description";
                }
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
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should have 0 data rows");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('textarea').val(), "",
            "field turtle_description should be empty");

        // add a value in the turtle_trululu field to trigger an onchange
        var $dropdown = form.$('.o_field_many2one[name=turtle_trululu] input')
                            .autocomplete('widget');
        form.$('.o_field_many2one[name=turtle_trululu] input').click();
        $dropdown.find('a:contains(first record)').mouseenter().click();
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
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should have 0 data rows");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('label.o_form_label').first().click();
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should still have 0 data rows");

        // click on Add an item again, then click on save
        form.$('.o_field_x2many_list_row_add a').click();
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should still have 0 data rows");

        assert.verifySteps(['read', 'default_get', 'default_get']);
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
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should have 0 data rows");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "should have 1 data rows");

        // adding a value in the non required field, so it is dirty, but with
        // a missing required field
        form.$('input[name="turtle_int"]').val('12345').trigger('input');

        // click elsewhere,
        form.$('label.o_form_label').click();
        assert.strictEqual($('.modal').length, 1,
            'a confirmation model should be opened');

        // click on cancel, the line should still be selected
        $('.modal .modal-footer button.btn-default').click();
        assert.strictEqual(form.$('tr.o_data_row.o_selected_row').length, 1,
            "should still have 1 selected data row");

        // click elsewhere, and click on ok (on the confirmation dialog)
        form.$('label.o_form_label').click();
        $('.modal .modal-footer button.btn-primary').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should have 0 data rows (invalid line has been discarded");

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
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should have 0 data rows");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        // input some text in required turtle_foo field
        form.$('input[name="turtle_foo"]').val('aubergine').trigger('input');
        assert.strictEqual(form.$('input[name="turtle_int"]').val(), "9",
            "onchange should have been triggered");

        // save and check everything is fine
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_data_row td:contains(aubergine)').length, 1,
            "should have one row with turtle_foo value");
        assert.strictEqual(form.$('.o_data_row td:contains(9)').length, 1,
            "should have one row with turtle_int value");

        assert.verifySteps(['read', 'default_get', 'onchange', 'onchange', 'write', 'read', 'read']);
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

    QUnit.test('one2many and onchange (with integer)', function (assert) {
        assert.expect(4);

        this.data.turtle.onchanges = {
            turtle_int: function (obj) {}
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        form.$buttons.find('.o_form_button_edit').click();

        form.$('td:contains(9)').click();
        form.$('td input[name="turtle_int"]').val("3").trigger('input');

        // the 'change' event is triggered on the input when we focus somewhere
        // else, for example by clicking in the body.  However, if we try to
        // programmatically click in the body, it does not trigger a change
        // event, so we simply trigger it directly instead.
        form.$('td input[name="turtle_int"]').trigger('change');

        assert.verifySteps(['read', 'read', 'onchange']);
        form.destroy();
    });

    QUnit.test('one2many and onchange (with date)', function (assert) {
        assert.expect(6);

        this.data.partner.onchanges = {
            date: function (obj) {}
        };
        this.data.partner.records[0].p = [2];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        form.$buttons.find('.o_form_button_edit').click();

        form.$('td:contains(01/25/2017)').click();
        form.$('.o_datepicker_input').click();
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        form.$('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        form.$('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        form.$('.bootstrap-datetimepicker-widget .month').eq(1).click();  // February
        form.$('.day:contains(22)').click(); // select the 22 February

        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps(['read', 'read', 'onchange', 'write', 'read']);
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

        assert.ok(form.$('.o_list_view tbody tr:eq(0) td:first').hasClass('o_readonly_modifier'),
            "first record should have display_name in readonly mode");

        assert.notOk(form.$('.o_list_view tbody tr:eq(1) td:first').hasClass('o_readonly_modifier'),
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
        $('.modal input').val('new record').trigger('input');
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

        form.$('tbody td.o_field_x2many_list_row_add a').click();

        $('.modal .o_field_many2one input').click();

        var $dropdown = $('.modal .o_field_many2one input').autocomplete('widget');

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
                        display_name: false, int_field: 123, product_id: 41
                    }]]);
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        form.$('tbody td.o_field_x2many_list_row_add a').click();

        // write in the many2one field, value = 37 (xphone)
        $('.modal .o_field_many2one input').click();
        var $dropdown = $('.modal .o_field_many2one input').autocomplete('widget');
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
        $('.modal .o_field_many2one input').click();
        $dropdown = $('.modal .o_field_many2one input').autocomplete('widget');
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
        $('.modal .o_field_many2one input').click();

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
        form.$('table td input').click();

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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

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

        form.$('tbody td.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('td input.o_field_widget').length, 1,
            "should have created a row in edit mode");

        form.$('td input.o_field_widget').val('a').trigger('input');

        assert.strictEqual(form.$('td input.o_field_widget').length, 1,
            "should not have unselected the row after edition");

        form.$('td input.o_field_widget').val('abc').trigger('input');
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
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
        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal .o_data_row').length, 2,
            "sould have 2 records in the select view (the last one is not displayed because it is already selected)");

        $('.modal .o_data_row:first .o_list_record_selector input').click();
        $('.modal .o_select_button').click();
        $('.o_form_button_save').click();
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal .o_data_row').length, 1,
            "sould have 1 record in the select view");

        $('.modal-footer button:eq(1)').click();
        $('.modal input.o_field_widget[name="turtle_foo"]').val('tototo').trigger('input');
        $('.modal input.o_field_widget[name="turtle_int"]').val(50).trigger('input');
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
        form.$('.o_field_x2many_list_row_add a').click();
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();
        $('.modal-footer button.btn-primary').first().click();

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

    QUnit.test('one2many kanban with edit type action and domain widget (widget wich use SpecialData)', function (assert) {
        assert.expect(1);

        this.data.turtle.fields.model_name = {string: "Domain Condition Model", type: "char"};
        this.data.turtle.fields.condition = {string: "Domain Condition", type: "char"};
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
                                        '<div> <a type="edit"> Edit </a> </div>' +
                                    '</t>' +
                                '</templates>' +
                            '</kanban>' +
                            '<form>' +
                                '<field name="product_id" widget="statusbar"/>' +
                                '<field name="model_name"/>' +
                                '<field name="condition" widget="domain" options="{\'model\': \'model_name\'}"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 1,
        });

        form.$('.oe_kanban_action:eq(0)').click();
        assert.strictEqual($('.o_domain_selector').length, 1, "should add domain selector widget");
        form.destroy();
    });

    QUnit.test('one2many without inline tree arch', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].turtles = [2,3];

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

        assert.strictEqual(form.$('.o_field_widget[name="turtles"] .o_list_view').length, 1,
            'should display one2many list view in the modal');

        assert.strictEqual(form.$('.o_data_row').length, 2,
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

        assert.strictEqual(form.$('.o_data_row').length, 2,
            'should display the 2 turtles');
        assert.strictEqual(form.$('.o_data_row:first td:nth(1)').text(), 'xphone',
            "should correctly display the m2o");
        assert.strictEqual(form.$('.o_data_row:first td:nth(2) .badge').length, 2,
            "m2m should contain two tags");
        assert.strictEqual(form.$('.o_data_row:first td:nth(2) .badge:first span').text(),
            'second record', "m2m values should have been correctly fetched");

        form.$('.o_data_row:first').click();

        assert.strictEqual($('.modal .o_field_widget').text(), "xphone",
            'should display the form view dialog with the many2one value');
        $('.modal-footer button').click(); // close the modal

        form.$buttons.find('.o_form_button_edit').click();

        // edit the m2m of first row
        form.$('.o_list_view tbody td:first()').click();
        // remove a tag
        form.$('.o_field_many2manytags .badge:contains(aaa) .o_delete').click();
        assert.strictEqual(form.$('.o_selected_row .o_field_many2manytags .o_badge_text:contains(aaa)').length, 0,
            "tag should have been correctly removed");
        // add a tag
        var $m2mInput = form.$('.o_selected_row .o_field_many2manytags input');
        $m2mInput.click();
        $m2mInput.autocomplete('widget').find('li:first()').click();
        assert.strictEqual(form.$('.o_selected_row .o_field_many2manytags .o_badge_text:contains(first record)').length, 1,
            "tag should have been correctly added");

        // edit the m2o of first row
        var $m2oInput = form.$('.o_selected_row .o_field_many2one:first input');
        $m2oInput.click();
        $m2oInput.autocomplete('widget').find('li:contains(xpad)').mouseover().click();
        assert.strictEqual(form.$('.o_selected_row .o_field_many2one:first input').val(), 'xpad',
            "m2o value should have been updated");

        // save (should correctly generate the commands)
        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('load view for x2many in one2many', function (assert) {
        assert.expect(2);

        this.data.turtle.records[1].product_id = 37;
        this.data.partner.records[0].turtles = [2,3];
        this.data.partner.records[2].turtles = [1,3];

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

        assert.strictEqual(form.$('.o_data_row').length, 2,
            'should display the 2 turtles');

        form.$('.o_data_row:first').click();

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

        form.$('.o_data_row:first').click();

        assert.strictEqual($('.modal .o_field_widget[name="turtle_foo"]').text(), 'blip',
            'should open the modal and display the form field');

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

        form.$('.o_data_row:first').click();

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

        assert.strictEqual(form.$('.o_field_widget .o_kanban_view').length, 1,
            "should have one inner kanban view for the one2many field");
        assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 0,
            "should not have kanban records yet");

        // // switch to edit mode and create a new kanban record
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_widget .o-kanban-button-new').click();

        // save & close the modal
        assert.strictEqual($('.modal-content input.o_field_widget').val(), 'My little Foo Value',
            "should already have the default value for field foo");
        $('.modal-content .btn-primary').first().click();

        assert.strictEqual(form.$('.o_field_widget .o_kanban_view').length, 1,
            "should have one inner kanban view for the one2many field");
        assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost)').length, 1,
            "should now have one kanban record");
        assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_id').text(),
            '', "should not have a value for the id field");
        assert.strictEqual(form.$('.o_field_widget .o_kanban_view .o_kanban_record:not(.o_kanban_ghost) .o_test_foo').text(),
            'My little Foo Value', "should have a value for the foo field");

        // save the view to force a create of the new record in the one2many
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_field_widget .o_kanban_view').length, 1,
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
        form.$buttons.find('.o_form_button_edit').click();

        form.$('.o_data_row:first td:first').click();
        assert.strictEqual(form.$('input[name="turtle_foo"]')[0], document.activeElement,
            "turtle foo field should have focus");

        form.$('input[name="turtle_foo"]').trigger({type: 'keydown', which: $.ui.keyCode.TAB});
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
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should start with one data row");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 2,
            "should have 2 data rows");
        assert.strictEqual(form.$('tr.o_data_row:first input').val(), 'default foo turtle',
            "first row should be the new value");
        assert.ok(form.$('tr.o_data_row:first').hasClass('o_selected_row'),
            "first row should be selected");

        form.$buttons.find('.o_form_button_save').click();
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
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should start with one data row");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 2,
            "should have 2 data rows");
        assert.strictEqual(form.$('tr.o_data_row:eq(1) input').val(), 'default foo turtle',
            "second row should be the new value");
        assert.ok(form.$('tr.o_data_row:eq(1)').hasClass('o_selected_row'),
            "second row should be selected");

        form.$buttons.find('.o_form_button_save').click();
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

        assert.strictEqual(form.$('.o_field_one2many .o_kanban_view').length, 1,
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
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
            "int_field should start with value 0");
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
            "int_field should still be 0 (no onchange should have been done yet");

        assert.verifySteps(['read', 'default_get'], "no onchange should have been applied");

        form.$('.o_field_widget[name="turtle_foo"]').val("some text").trigger('input');
        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
            "int_field should now be 1 (the onchange should have been done");

        form.destroy();
    });

    QUnit.test('one2many list editable: trigger onchange when row is valid', function (assert) {
        // should omit require fields that aren't in the view as they (obviously)
        // have no value, when checking the validity of required fields
        // shouldn't consider numerical fields with value 0 as unset
        assert.expect(11);

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
                'turtle,false,list' : '<tree editable="top">' +
                        '<field name="turtle_qux"/>' +
                        '<field name="turtle_bar"/>' +
                        '<field name="turtle_int"/>' +
                        '<field name="turtle_foo"/>' +
                        '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</tree>',
            },
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
            "int_field should start with value 0");

        // add a new row (which is invalid at first)
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
            "int_field should still be 0 (no onchange should have been done yet)");
        assert.verifySteps(['read', 'default_get'], "no onchange should have been applied");

        // fill turtle_foo field
        form.$('.o_field_widget[name="turtle_foo"]').val("some text").trigger('input');
        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "0",
            "int_field should still be 0 (no onchange should have been done yet)");
        assert.verifySteps(['read', 'default_get'], "no onchange should have been applied");

        // fill partner_ids field with a tag (all required fields will then be set)
        var $m2mInput = form.$('.o_field_widget[name=partner_ids] input');
        $m2mInput.click();
        $m2mInput.autocomplete('widget').find('li:first()').click();
        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "1",
            "int_field should now be 1 (the onchange should have been done");

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
        assert.ok(!form.$('.o_field_many2many .o-kanban-button-new').length,
            '"Add" button should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_kanban_record:not(.o_kanban_ghost)').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_kanban_record:first() span').text(), 'gold',
            'display_name of subrecord should be the one in DB');
        assert.ok(form.$('.o_kanban_view .delete_icon').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_field_many2many .o-kanban-button-new').length,
            '"Add" button should be visible in edit');

        // edit existing subrecord
        form.$('.oe_kanban_global_click:first()').click();

        $('.modal .o_form_view input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_kanban_record:first() span').text(), 'new name',
            'value of subrecord should have been updated');

        // add subrecords
        // -> single select
        form.$('.o_field_many2many .o-kanban-button-new').click();
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
        form.$('.o_field_many2many .o-kanban-button-new').click();
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
        form.$('.o_field_many2many .o-kanban-button-new').click();
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
        assert.expect(27);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 15, display_name: "bronze", color: 6});
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
            archs: {
                'partner_type,false,list': '<tree><field name="display_name"/></tree>',
                'partner_type,false,search': '<search><field name="display_name"/></search>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(_.last(route.split('/')));
                if (args.method === 'write' && args.model === 'partner') {
                    assert.deepEqual(args.args[1].timmy, [
                        [6, false, [12, 15]],
                    ]);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'gold',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should be visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody tr:first()').click();

        $('.modal .o_form_view input').val('new name').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');

        // add new subrecords
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal .o_list_view').length, 1,
            "a modal should be open");
        assert.strictEqual($('.modal .o_list_view .o_data_row').length, 1,
            "the list should contain one row");
        $('.modal .o_list_view .o_data_row').click(); // select a record
        assert.strictEqual($('.modal .o_list_view').length, 0,
            "the modal should be closed");
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 3,
            'should contain 3 subrecords');

        // delete subrecords
        form.$('.o_list_record_delete:nth(1)').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 subrecords');
        assert.strictEqual(form.$('.o_list_view .o_data_row td:first').text(), 'new name',
            'the updated row still has the correct values');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 subrecords');
        assert.strictEqual(form.$('.o_list_view .o_data_row td:first').text(),
            'new name', 'the updated row still has the correct values');

        assert.verifySteps([
            'read', // main record
            'read', // relational field
            'read', // relational record in dialog
            'write', // save relational record from dialog
            'read', // relational field (updated)
            'search_read', // list view in dialog
            'read', // relational field (updated)
            'write', // save main record
            'read', // main record
            'read', // relational field
        ]);

        form.destroy();
    });

    QUnit.test('many2many list (editable): edition', function (assert) {
        assert.expect(30);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 15, display_name: "bronze", color: 6});
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
                    '</field>' +
                '</form>',
            archs: {
                'partner_type,false,list': '<tree><field name="display_name"/></tree>',
                'partner_type,false,search': '<search><field name="display_name"/></search>',
            },
            mockRPC: function (route, args) {
                assert.step(_.last(route.split('/')));
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1].timmy, [
                        [6, false, [12, 15]],
                        [1, 12, {display_name: 'new name'}],
                    ]);
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.ok(!form.$('.o_list_record_delete').length,
            'delete icon should not be visible in readonly');
        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should not be visible in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 records');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'gold',
            'display_name of first subrecord should be the one in DB');
        assert.ok(form.$('.o_list_record_delete').length,
            'delete icon should be visible in edit');
        assert.ok(form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" should not visible in edit');

        // edit existing subrecord
        form.$('.o_list_view tbody td:first()').click();
        assert.ok(!$('.modal').length,
            'in edit, clicking on a subrecord should not open a dialog');
        assert.ok(form.$('.o_list_view tbody tr:first()').hasClass('o_selected_row'),
            'first row should be in edition');
        form.$('.o_list_view input:first()').val('new name').trigger('input');
        assert.ok(form.$('.o_list_view .o_data_row:first').hasClass('o_selected_row'),
            'first row should still be in edition');
        assert.strictEqual(form.$('.o_list_view input[name=display_name]').get(0),
            document.activeElement, 'edited field should still have the focus');
        form.$el.click(); // click outside the list to validate the row
        assert.ok(!form.$('.o_list_view tbody tr:first').hasClass('o_selected_row'),
            'first row should not be in edition anymore');
        assert.strictEqual(form.$('.o_list_view tbody td:first()').text(), 'new name',
            'value of subrecord should have been updated');
        assert.verifySteps(['read', 'read']);

        // add new subrecords
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal .o_list_view').length, 1,
            "a modal should be open");
        assert.strictEqual($('.modal .o_list_view .o_data_row').length, 1,
            "the list should contain one row");
        $('.modal .o_list_view .o_data_row').click(); // select a record
        assert.strictEqual($('.modal .o_list_view').length, 0,
            "the modal should be closed");
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 3,
            'should contain 3 subrecords');

        // delete subrecords
        form.$('.o_list_record_delete:nth(1)').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 subrecord');
        assert.strictEqual(form.$('.o_list_view tbody .o_data_row td:first').text(),
            'new name', 'the updated row still has the correct values');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_list_view td.o_list_number').length, 2,
            'should contain 2 subrecords');
        assert.strictEqual(form.$('.o_list_view .o_data_row td:first').text(),
            'new name', 'the updated row still has the correct values');

        assert.verifySteps([
            'read', // main record
            'read', // relational field
            'search_read', // list view in dialog
            'read', // relational field (updated)
            'write', // save main record
            'read', // main record
            'read', // relational field
        ]);

        form.destroy();
    });

    QUnit.test('many2many: create & delete attributes', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].timmy = [12, 14];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree create="true" delete="true">' +
                            '<field name="color"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_x2many_list_row_add').length, 1, "should have the 'Add an item' link");
        assert.strictEqual(form.$('.o_list_record_delete').length, 2, "should have the 'Add an item' link");

        form.destroy();

        form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree create="false" delete="false">' +
                            '<field name="color"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_x2many_list_row_add').length, 0, "should not have the 'Add an item' link");
        assert.strictEqual(form.$('.o_list_record_delete').length, 0, "should not have the 'Add an item' link");

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

        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in readonly');

        form.$buttons.find('.o_form_button_edit').click();

        assert.ok(!form.$('.o_field_x2many_list_row_add').length,
            '"Add an item" link should not be available in edit either');

        form.destroy();
    });

    QUnit.test('many2many list with x2many: add a record', function (assert) {
        assert.expect(18);

        this.data.partner_type.fields.m2m = {
            string: "M2M", type: "many2many", relation: 'turtle',
        };
        this.data.partner_type.records[0].m2m = [1, 2];
        this.data.partner_type.records[1].m2m = [2, 3];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy"/>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner_type,false,list': '<tree>' +
                        '<field name="display_name"/>' +
                        '<field name="m2m" widget="many2many_tags"/>' +
                    '</tree>',
                'partner_type,false,search': '<search>' +
                        '<field name="display_name" string="Name"/>' +
                    '</search>',
            },
            mockRPC: function (route, args) {
                assert.step(_.last(route.split('/')) + ' on ' + args.model);
                if (args.model === 'turtle') {
                    assert.step(args.args[0]); // the read ids
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal .o_data_row:first').click(); // add a first record to the relation

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "the record should have been added to the relation");
        assert.strictEqual(form.$('.o_data_row:first .o_badge_text').text(), 'leonardodonatello',
            "inner m2m should have been fetched and correctly displayed");

        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal .o_data_row:first').click(); // add a second record to the relation

        assert.strictEqual(form.$('.o_data_row').length, 2,
            "the second record should have been added to the relation");
        assert.strictEqual(form.$('.o_data_row:nth(1) .o_badge_text').text(), 'donatelloraphael',
            "inner m2m should have been fetched and correctly displayed");

        assert.verifySteps([
            'read on partner',
            'search_read on partner_type',
            'read on turtle',
            [1, 2, 3],
            'read on partner_type',
            'read on turtle',
            [1, 2],
            'search_read on partner_type',
            'read on turtle',
            [2, 3],
            'read on partner_type',
            'read on turtle',
            [2, 3],
        ]);

        form.destroy();
    });

    QUnit.module('FieldStatus');

    QUnit.test('static statusbar widget on many2one field', function (assert) {
        assert.expect(5);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";
        this.data.partner.records[1].bar = false;

        var count = 0;
        var nb_fields_fetched;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                    // the following field seem useless, but its presence was the
                    // cause of a crash when evaluating the field domain.
                    '<field name="timmy" invisible="1"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    count++;
                    nb_fields_fetched = args.kwargs.fields.length;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            config: {
                isMobile: false,
            },
        });

        assert.strictEqual(count, 1, 'once search_read should have been done to fetch the relational values');
        assert.strictEqual(nb_fields_fetched, 1, 'search_read should only fetch field id');
        assert.strictEqual(form.$('.o_statusbar_status button:not(.dropdown-toggle)').length, 2, "should have 2 status");
        assert.strictEqual(form.$('.o_statusbar_status button:disabled').length, 2,
            "all status should be disabled");
        assert.ok(form.$('.o_statusbar_status button[data-value="4"]').hasClass('btn-primary'),
            "selected status should be btn-primary");

        form.destroy();
    });

    QUnit.test('static statusbar widget on many2one field with domain', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" domain="[(\'user_id\',\'=\',uid)]" widget="statusbar"/></header>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    assert.deepEqual(args.kwargs.domain, ['|', ['id', '=', 4], ['user_id', '=', 17]],
                        "search_read should sent the correct domain");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            session: {user_context: {uid: 17}},
        });

        form.destroy();
    });

    QUnit.test('clickable statusbar widget on many2one field', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" clickable="True"/></header>' +
                '</form>',
            res_id: 1,
            config: {
                isMobile: false,
            },
        });

        var $selectedStatus = form.$('.o_statusbar_status button[data-value="4"]');
        assert.ok($selectedStatus.hasClass('btn-primary') && $selectedStatus.hasClass('disabled'),
            "selected status should be btn-primary and disabled");
        var $clickable = form.$('.o_statusbar_status button.btn-default:not(.dropdown-toggle):not(:disabled)');
        assert.strictEqual($clickable.length, 2,
            "other status should be btn-default and not disabled");
        $clickable.last().click(); // (last is visually the first here (css))
        var $status = form.$('.o_statusbar_status button[data-value="1"]');
        assert.ok($status.hasClass("btn-primary") && $status.hasClass("disabled"),
            "value should have been updated");

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
                    '<header><field name="product_id" widget="statusbar"/></header>' +
                '</form>',
            res_id: 1,
            config: {
                isMobile: false,
            },
        });

        assert.ok(form.$('.o_statusbar_status').hasClass('o_field_empty'),
            'statusbar widget should have class o_field_empty');
        assert.strictEqual(form.$('.o_statusbar_status').children().length, 0,
            'statusbar widget should be empty');
        form.destroy();
    });

    QUnit.test('statusbar with domain but no value (create mode)', function (assert) {
        assert.expect(1);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                '</form>',
            config: {
                isMobile: false,
            },
        });

        assert.strictEqual(form.$('.o_statusbar_status button:disabled').length, 2, "should have 2 status");

        form.destroy();
    });

    QUnit.test('clickable statusbar should change m2o fetching domain in edit mode', function (assert) {
        assert.expect(2);

        this.data.partner.fields.trululu.domain = "[('bar', '=', True)]";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" clickable="True"/></header>' +
                '</form>',
            res_id: 1,
            config: {
                isMobile: false,
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        var $buttons = form.$('.o_statusbar_status button:not(.dropdown-toggle)');
        assert.strictEqual($buttons.length, 3, "there should be 3 status");
        $buttons.last().click(); // (last is visually the first here (css))
        assert.strictEqual(form.$('.o_statusbar_status button:not(.dropdown-toggle)').length, 2,
            "there should be 2 status left");

        form.destroy();
    });

    QUnit.test('statusbar fold_field option and statusbar_visible attribute', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].bar = false;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" options="{\'fold_field\': \'bar\'}"/>' +
                    '<field name="color" widget="statusbar" statusbar_visible="red"/></header>' +
                '</form>',
            res_id: 1,
            config: {
                isMobile: false,
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_statusbar_status:first .dropdown-menu button.disabled').length, 1, "should have 1 folded status");
        assert.strictEqual(form.$('.o_statusbar_status:last button.disabled').length, 1, "should have 1 status (other discarded)");

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
                    '<header><field name="trululu" widget="statusbar"/></header>' +
                    '<field name="qux"/>' +
                    '<field name="foo"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_read') {
                    rpcCount++;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            config: {
                isMobile: false,
            },
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

    QUnit.test('widget selection,  edition and on many2one field', function (assert) {
        assert.expect(15);

        this.data.partner.onchanges = {product_id: function () {}};
        this.data.partner.records[0].product_id = 37;
        this.data.partner.records[0].trululu = false;

        var count = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="product_id" widget="selection"/>' +
                        '<field name="trululu" widget="selection"/>' +
                        '<field name="color" widget="selection"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                count++;
                assert.step(args.method);
                return this._super(route, args);
            },
        });

        assert.ok(!form.$('select').length, "should not have a select tag in dom");
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('select').length, 3,
            "should have 3 select tag in dom");
        assert.strictEqual(form.$('select[name="product_id"] option:contains(xphone)').length, 1,
            "should have fetched xphone option");
        assert.strictEqual(form.$('select[name="product_id"] option:contains(xpad)').length, 1,
            "should have fetched xpad option");
        assert.strictEqual(form.$('select[name="product_id"]').val(), "37",
            "should have correct product_id value");
        assert.strictEqual(form.$('select[name="trululu"]').val(), "false",
            "should not have any value in trululu field");
        form.$('select[name="product_id"]').val(41).trigger('change');

        assert.strictEqual(form.$('select[name="product_id"]').val(), "41",
            "should have a value of xphone");

        assert.strictEqual(form.$('select[name="color"]').val(), "\"red\"",
            "should have correct value in color field");

        assert.verifySteps(['read', 'name_search', 'name_search', 'onchange']);
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
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 2,
            "should contain 2 tags");
        assert.ok(form.$('span:contains(gold)').length,
            'should have fetched and rendered gold partner tag');
        assert.ok(form.$('span:contains(silver)').length,
            'should have fetched and rendered silver partner tag');
        assert.strictEqual(form.$('span:first()').data('color'), 2,
            'should have correctly fetched the color');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 2,
            "should still contain 2 tags in edit mode");
        assert.ok(form.$('.o_tag_color_2 .o_badge_text:contains(gold)').length,
            'first tag should still contain "gold" and be color 2 in edit mode');
        assert.strictEqual(form.$('.o_field_many2manytags .o_delete').length, 2,
            "tags should contain a delete button");

        // add an other existing tag
        var $input = form.$('.o_field_many2manytags input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 1,
            "autocomplete dropdown should have 1 entry");
        assert.strictEqual($input.autocomplete('widget').find('li a:contains("red")').length, 1,
            "autocomplete dropdown should contain 'red'");
        $input.autocomplete('widget').find('li').click(); // add 'red'
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 3,
            "should contain 3 tags");
        assert.ok(form.$('.o_field_many2manytags > span:contains("red")').length,
            "should contain newly added tag 'red'");
        assert.ok(form.$('.o_field_many2manytags > span[data-color=8]:contains("red")').length,
            "should have fetched the color of added tag");

        // remove tag with id 14
        form.$('.o_field_many2manytags span[data-id=14] .o_delete').click();
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 2,
            "should contain 2 tags");
        assert.ok(!form.$('.o_field_many2manytags > span:contains("silver")').length,
            "should not contain tag 'silver' anymore");

        // save the record (should do the write RPC with the correct commands)
        form.$buttons.find('.o_form_button_save').click();

        // TODO: it would be nice to test the behaviors of the autocomplete dropdown
        // (like refining the research, creating new tags...), but ui-autocomplete
        // makes it difficult to test
        form.destroy();
    });

    QUnit.test('fieldmany2many tags view a domain', function (assert) {
        assert.expect(7);

        this.data.partner.fields.timmy.domain = [['id', '<', 50]];
        this.data.partner.records[0].timmy = [12];
        this.data.partner_type.records.push({id: 99, display_name: "red", color: 8});

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'no_create_edit\': True}"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, [['id', '<', 50], ['id', 'not in', [12]]],
                        "domain sent to name_search should be correct");
                    return $.when([[14, 'silver']]);
                }
                return this._super.apply(this, arguments);
            }
        });
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 1,
            "should contain 1 tag");
        assert.ok(form.$('span:contains(gold)').length,
            'should have fetched and rendered gold partner tag');

        form.$buttons.find('.o_form_button_edit').click();

        // add an other existing tag
        var $input = form.$('.o_field_many2manytags input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 1,
            "autocomplete dropdown should have 1 entry");
        assert.strictEqual($input.autocomplete('widget').find('li a:contains("silver")').length, 1,
            "autocomplete dropdown should contain 'silver'");
        $input.autocomplete('widget').find('li').click(); // add 'silver'
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 2,
            "should contain 2 tags");
        assert.ok(form.$('.o_field_many2manytags > span:contains("silver")').length,
            "should contain newly added tag 'silver'");

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

        var $input = form.$('.o_field_many2manytags input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')");
        $input.autocomplete('widget').find('li:first()').click(); // adds a tag
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 1,
            "should contain 1 tag");
        assert.ok(form.$('.o_field_many2manytags > span:contains("gold")').length,
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

    QUnit.test('fieldmany2many tags in editable list', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].timmy = [12];

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch:'<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</tree>',
        });

        assert.strictEqual(list.$('.o_data_row:first .o_field_many2manytags .badge').length, 1,
            "m2m field should contain one tag");

        // edit first row
        list.$('.o_data_row:first td:nth(2)').click();

        var $m2o = list.$('.o_data_row:first .o_field_many2manytags .o_field_many2one');
        assert.strictEqual($m2o.length, 1, "a many2one widget should have been instantiated");

        // add a tag
        var $input = $m2o.find('input');
        $input.click();
        $input.autocomplete('widget').find('li:first()').click(); // adds a tag

        assert.strictEqual(list.$('.o_data_row:first .o_field_many2manytags .badge').length, 2,
            "m2m field should contain 2 tags");

        // leave edition
        list.$('.o_data_row:nth(1) td:nth(2)').click();

        assert.strictEqual(list.$('.o_data_row:first .o_field_many2manytags .badge').length, 2,
            "m2m field should contain 2 tags");

        list.destroy();
    });

    QUnit.test('field many2many_tags keeps focus when being edited', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        this.data.partner.onchanges.foo = function (obj) {
            obj.timmy = [[5]]; // DELETE command
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 1,
            "should contain one tag");

        // update foo, which will trigger an onchange and update timmy
        // -> m2mtags input should not have taken the focus
        form.$('input:first').focus();
        form.$('input:first').val('trigger onchange').trigger('input');
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 0,
            "should contain no tags");
        assert.strictEqual(form.$('input:first').get(0), document.activeElement,
            "foo input should have kept the focus");

        // add a tag -> m2mtags input should still have the focus
        form.$('.o_field_many2manytags input').click(); // opens the dropdown
        form.$('.o_field_many2manytags input').autocomplete('widget').find('li:first').click();
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 1,
            "should contain a tag");
        assert.strictEqual(form.$('.o_field_many2manytags input').get(0), document.activeElement,
            "m2m tags input should have kept the focus");

        // remove a tag -> m2mtags input should still have the focus
        form.$('.o_field_many2manytags .o_delete').click();
        assert.strictEqual(form.$('.o_field_many2manytags > span').length, 0,
            "should contain no tags");
        assert.strictEqual(form.$('.o_field_many2manytags input').get(0), document.activeElement,
            "m2m tags input should have kept the focus");

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
        assert.strictEqual(form.$('input.o_radio_input').length, 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(xphone)').length, "one of them should be xphone");
        assert.strictEqual(form.$('input:checked').length, 0, "none of the input should be checked");

        form.$("input.o_radio_input:first").click();

        assert.strictEqual(form.$('input:checked').length, 1, "one of the input should be checked");

        form.$buttons.find('.o_form_button_save').click();

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.product_id, 37, "should have saved record with correct value");
        form.destroy();
    });

    QUnit.test('fieldradio change value by onchange', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {bar: function (obj) {
            obj.product_id = obj.bar ? 41 : 37;
            obj.color = obj.bar ? 'red' : 'black';
        }};

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="bar"/>' +
                    '<field name="product_id" widget="radio"/>' +
                    '<field name="color" widget="radio"/>' +
                '</form>',
        });

        form.$("input[type='checkbox']").click();
        assert.strictEqual(form.$('input.o_radio_input[data-value="37"]:checked').length, 1, "one of the input should be checked");
        assert.strictEqual(form.$('input.o_radio_input[data-value="black"]:checked').length, 1, "the other of the input should be checked");
        form.$("input[type='checkbox']").click();
        assert.strictEqual(form.$('input.o_radio_input[data-value="41"]:checked').length, 1, "the other of the input should be checked");
        assert.strictEqual(form.$('input.o_radio_input[data-value="red"]:checked').length, 1, "one of the input should be checked");

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
        assert.strictEqual(form.$('input.o_radio_input').length, 2, "should have 2 possible choices");
        assert.ok(form.$('label.o_form_label:contains(Red)').length, "one of them should be Red");

        // click on 2nd option
        form.$("input.o_radio_input").eq(1).click();

        form.$buttons.find('.o_form_button_save').click();

        var newRecord = _.last(this.data.partner.records);
        assert.strictEqual(newRecord.color, 'black', "should have saved record with correct value");
        form.destroy();
    });

    QUnit.module('FieldMany2ManyCheckBoxes');

    QUnit.test('widget many2many_checkboxes', function (assert) {
        assert.expect(10);

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

        assert.strictEqual(form.$('div.o_field_widget div.o_checkbox').length, 2,
            "should have fetched and displayed the 2 values of the many2many");

        assert.ok(form.$('div.o_field_widget div.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        assert.ok(form.$('div.o_field_widget div.o_checkbox input').prop('disabled'),
            "the checkboxes should be disabled");

        form.$buttons.find('.o_form_button_edit').click();

        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').prop('disabled'),
            "the checkboxes should not be disabled");

        // add a m2m value
        form.$('div.o_field_widget div.o_checkbox input').eq(1).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.deepEqual(this.data.partner.records[0].timmy, [12, 14],
            "should have added the second element to the many2many");
        assert.strictEqual(form.$('input:checked').length, 2,
            "both checkboxes should be checked");

        // remove a m2m value
        form.$buttons.find('.o_form_button_edit').click();
        form.$('div.o_field_widget div.o_checkbox input').eq(0).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.deepEqual(this.data.partner.records[0].timmy, [14],
            "should have removed the first element to the many2many");
        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.ok(form.$('div.o_field_widget div.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        form.destroy();
    });

    QUnit.module('FieldMany2ManyBinaryMultiFiles');

    QUnit.test('widget many2many_binary', function (assert) {
        assert.expect(14);
        this.data['ir.attachment'] = {
            fields: {
                name: {string:"Name", type: "char"},
                mimetype: {string: "Mimetype", type: "char"},
            },
            records: [{
                id: 17,
                name: 'Marley&Me.jpg',
                mimetype: 'jpg',
            }],
        };
        this.data.turtle.fields.picture_ids = {
            string: "Pictures",
            type: "many2many",
            relation: 'ir.attachment',
        };
        this.data.turtle.records[0].picture_ids = [17];

        var form = createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch:'<form string="Turtles">' +
                    '<group><field name="picture_ids" widget="many2many_binary"/></group>' +
                '</form>',
            archs: {
                'ir.attachment,false,list': '<tree string="Pictures"><field name="name"/></tree>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(route);
                if (route === '/web/dataset/call_kw/ir.attachment/read') {
                    assert.deepEqual(args.args[1], ['name', 'datas_fname', 'mimetype']);
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload').length, 1,
            "there should be the attachment widget");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .oe_attachments').children().length, 1,
            "there should be no attachment");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attach').length, 0,
            "there should not be an Add button (readonly)");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .oe_attachment .oe_delete').length, 0,
            "there should not be a Delete button (readonly)");

        // to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attach').length, 1,
            "there should be an Add button");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_attach').text().trim(), "Pictures",
            "the button should be correctly named");
        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .o_hidden_input_file form').length, 1,
            "there should be a hidden form to upload attachments");

        // TODO: add an attachment
        // no idea how to test this

        // delete the attachment
        form.$('div.o_field_widget.oe_fileupload .oe_attachment .oe_delete').click();


        assert.verifySteps([
            '/web/dataset/call_kw/turtle/read',
            '/web/dataset/call_kw/ir.attachment/read',
        ]);

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('div.o_field_widget.oe_fileupload .oe_attachments').children().length, 0,
            "there should be no attachment");

        form.destroy();
    });
});
});
});
