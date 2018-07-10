odoo.define('web.relational_fields_tests', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var BasicModel = require('web.BasicModel');
var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var ListRenderer = require('web.ListRenderer');
var ListView = require('web.ListView');
var relationalFields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');
var fieldUtils = require('web.field_utils');

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
                    turtles: {string: "one2many turtle field", type: "one2many", relation: 'turtle', relation_field: 'turtle_trululu'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    color: {
                        type: "selection",
                        selection: [['red', "Red"], ['black', "Black"]],
                        default: 'red',
                        string: "Color",
                    },
                    date: {string: "Some Date", type: "date"},
                    datetime: {string: "Datetime Field", type: 'datetime'},
                    user_id: {string: "User", type: 'many2one', relation: 'user'},
                    reference: {string: "Reference Field", type: 'reference', selection: [
                        ["product", "Product"], ["partner_type", "Partner Type"], ["partner", "Partner"]]},
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
                    turtle_ref: {string: "Reference", type: 'reference', selection: [
                        ["product", "Product"], ["partner", "Partner"]]},
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
                    name: {string: "Name", type: "char"},
                    partner_ids: {string: "one2many partners field", type: "one2many", relation: 'partner', relation_field: 'user_id'},
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

    QUnit.module('FieldMany2One');

    QUnit.test('many2ones in form views', function (assert) {
        assert.expect(5);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu" string="custom label"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form': '<form string="Partners"><field name="display_name"/></form>',
            },
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

        assert.strictEqual(form.$('a.o_form_uri:contains(aaa)').length, 1,
                        "should contain a link");
        form.$('a.o_form_uri').click(); // click on the link in readonly mode (should trigger do_action)

        form.$buttons.find('.o_form_button_edit').click();

        form.$('.o_external_button').click(); // click on the external button (should do an RPC)

        assert.strictEqual($('.modal .modal-title').text().trim(), 'Open: custom label',
                        "dialog title should display the custom string label");

        // TODO: test that we can edit the record in the dialog, and that the value is correctly
        // updated on close
        form.destroy();
    });

    QUnit.test('editing a many2one, but not changing anything', function (assert) {
        assert.expect(2);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                            '<field name="trululu"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form': '<form string="Partners"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [4], "should call get_formview_id with correct id");
                    return $.when(false);
                }
                return this._super(route, args);
            },
            viewOptions: {
                ids: [1, 2],
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        // click on the external button (should do an RPC)
        form.$('.o_external_button').click();
        // save and close modal
        $('.modal .modal-footer .btn-primary:first').click();
        // save form
        form.$buttons.find('.o_form_button_save').click();
        // click next on pager
        form.pager.$('.o_pager_next').click();

        // this checks that the view did not ask for confirmation that the
        // record is dirty
        assert.strictEqual(form.pager.$el.text().trim(), '2 / 2',
            'pager should be at second page');
        form.destroy();
    });

    QUnit.test('context in many2one and default get', function (assert) {
        assert.expect(1);

        this.data.partner.fields.int_field.default = 14;
        this.data.partner.fields.trululu.default = 2;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="int_field"/>' +
                        '<field name="trululu"  context="{\'blip\':int_field}"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.strictEqual(args.kwargs.context.blip, 14,
                        'context should have been properly sent to the nameget rpc');
                }
                return this._super(route, args);
            },
        });
        form.destroy();
    });

    QUnit.test('editing a many2one (with form view opened with external button)', function (assert) {
        assert.expect(1);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                            '<field name="trululu"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form': '<form string="Partners"><field name="foo"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    return $.when(false);
                }
                return this._super(route, args);
            },
            viewOptions: {
                ids: [1, 2],
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        // click on the external button (should do an RPC)
        form.$('.o_external_button').click();

        $('.modal input[name="foo"]').val('brandon').trigger('input');

        // save and close modal
        $('.modal .modal-footer .btn-primary:first').click();
        // save form
        form.$buttons.find('.o_form_button_save').click();
        // click next on pager
        form.pager.$('.o_pager_next').click();

        // this checks that the view did not ask for confirmation that the
        // record is dirty
        assert.strictEqual(form.pager.$el.text().trim(), '2 / 2',
            'pager should be at second page');
        form.destroy();
    });

    QUnit.test('many2ones in form views with show_adress', function (assert) {
        assert.expect(4);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field ' +
                                'name="trululu" ' +
                                'string="custom label" ' +
                                'context="{\'search_default_customer\':1, \'show_address\': 1}" ' +
                                'options="{\'always_reload\': True}"' +
                            '/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    return this._super(route, args).then(function (result) {
                        result[0][1] += '\nStreet\nCity ZIP';
                        return result;
                    });
                }
                return this._super(route, args);
            },
            res_id: 1,
        });

        assert.strictEqual($('a.o_form_uri').html(), 'aaa<br>Street<br>City ZIP',
            "input should have a multi-line content in readonly due to show_address");
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('button.o_external_button:visible').length, 1,
            "should have an open record button");

        form.$('input.o_input').click();

        assert.strictEqual(form.$('button.o_external_button:visible').length, 1,
            "should still have an open record button");
        form.$('input.o_input').trigger('focusout');
        assert.strictEqual($('.modal button:contains(Create and edit)').length, 0,
            "there should not be a quick create modal");

        form.destroy();
    });

    QUnit.test('many2ones in form views with search more', function (assert) {
        assert.expect(3);
        this.data.partner.records.push({
            id: 5,
            display_name: "Partner 4",
        }, {
            id: 6,
            display_name: "Partner 5",
        }, {
            id: 7,
            display_name: "Partner 6",
        }, {
            id: 8,
            display_name: "Partner 7",
        }, {
            id: 9,
            display_name: "Partner 8",
        }, {
            id: 10,
            display_name: "Partner 9",
        });
        this.data.partner.fields.datetime.searchable = true;
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
            archs: {
                'partner,false,list': '<tree><field name="display_name"/></tree>',
                'partner,false,search': '<search><field name="datetime"/></search>',
            },
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('.o_m2o_dropdown_option:contains(Search)').mouseenter().click();  // Open Search More

        assert.strictEqual($('tr.o_data_row').length, 9, "should display 9 records");

        $('.o_searchview_more').click();  // Magnifying class for more filters
        $('button:contains(Filters)').click();
        $('.o_add_filter').click();  // Add a custom filter, datetime field is selected
        assert.strictEqual($('li.o_filter_condition select.o_searchview_extended_prop_field').val(), 'datetime',
            "datetime field should be selected");
        $('.o_apply_filter').click();

        assert.strictEqual($('tr.o_data_row').length, 0, "should display 0 records");
        form.destroy();
    });

    QUnit.test('onchanges on many2ones trigger when editing record in form view', function (assert) {
        assert.expect(9);

        this.data.partner.onchanges.user_id = function () {};
        this.data.user.fields.other_field = {string: "Other Field", type: "char"};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="user_id"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'user,false,form': '<form string="Users"><field name="other_field"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'get_formview_id') {
                    return $.when(false);
                }
                if (args.method === 'onchange') {
                    assert.strictEqual(args.args[1].user_id, 17,
                        "onchange is triggered with correct user_id");
                }
                return this._super(route, args);
            },
        });

        // open the many2one in form view and change something
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_external_button').click();
        $('.modal-body input[name="other_field"]').val('wood').trigger('input');

        // save the modal and make sure an onchange is triggered
        $('.modal .modal-footer .btn-primary').first().click();
        assert.verifySteps(['read', 'get_formview_id', 'read', 'write', 'onchange', 'read']);

        // save the main record, and check that no extra rpcs are done (record
        // is not dirty, only a related record was modified)
        form.$buttons.find('.o_form_button_save').click();
        assert.verifySteps(['read', 'get_formview_id', 'read', 'write', 'onchange', 'read']);
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

    QUnit.test('many2one in non edit mode', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                            '<field name="trululu"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('a.o_form_uri').length, 1,
            "should display 1 m2o link in form");
        assert.strictEqual(form.$('a.o_form_uri').attr('href'), "#id=4&model=partner",
            "href should contain id and model");

        // Remove value from many2one and then save, there should not have href with id and model on m2o anchor
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_many2one input').val('').trigger('keyup').trigger('focusout');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('a.o_form_uri').attr('href'), "#",
            "href should have #");

        form.destroy();
    });

    QUnit.test('many2one searches with correct value', function (assert) {
        var done = assert.async();
        assert.expect(6);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="trululu"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.step('search: ' + args.kwargs.name);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_many2one input').val(), 'aaa',
            "should be initially set to 'aaa'");

        form.$('.o_field_many2one input').click(); // should search with ''
        // unset the many2one -> should search again with ''
        form.$('.o_field_many2one input').val('').trigger('keydown');
        concurrency.delay(0).then(function () {
            // write 'p' -> should search with 'p'
            form.$('.o_field_many2one input').val('p').trigger('keydown').trigger('keyup');

            return concurrency.delay(0);
        }).then(function () {
            // close and re-open the dropdown -> should search with 'p' again
            form.$('.o_field_many2one input').click();
            form.$('.o_field_many2one input').click();

            assert.verifySteps(['search: ', 'search: ', 'search: p', 'search: p']);

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
            done();
        });
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

    QUnit.test('many2one field and list navigation', function (assert) {
        assert.expect(3);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="trululu"/></tree>',
        });

        // edit first input, to trigger autocomplete
        list.$('.o_data_row .o_data_cell').first().click();
        list.$('.o_data_cell input').val('').trigger('input');

        // press keydown, to select first choice
        list.$('.o_data_cell input').focus().trigger($.Event('keydown', {
            which: $.ui.keyCode.DOWN,
            keyCode: $.ui.keyCode.DOWN,
        }));

        // we now check that the dropdown is open (and that the focus did not go
        // to the next line)
        var $dropdown = list.$('.o_field_many2one input').autocomplete('widget');
        assert.ok($dropdown.is(':visible'), "dropdown should be visible");
        assert.ok(list.$('.o_data_row:eq(0)').hasClass('o_selected_row'),
            'first data row should still be selected');
        assert.ok(!list.$('.o_data_row:eq(1)').hasClass('o_selected_row'),
            'second data row should not be selected');

        list.destroy();
    });

    QUnit.test('standalone many2one field', function (assert) {
        assert.expect(3);
        var done = assert.async();

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var fixture = $('#qunit-fixture');
        var self = this;

        var model = testUtils.createModel({
            Model: BasicModel,
            data: this.data,
        });

        model.makeRecord('coucou', [{
            name: 'partner_id',
            relation: 'partner',
            type: 'many2one',
            value: [1, 'first partner'],
        }], {
            partner_id: {
                options: {
                    no_open: true,
                },
            },
        }).then(function (recordID) {
            var record = model.get(recordID);
            // create a new widget that uses the StandaloneFieldManagerMixin
            var StandaloneWidget = Widget.extend(StandaloneFieldManagerMixin, {
                init: function (parent) {
                    this._super.apply(this, arguments);
                    StandaloneFieldManagerMixin.init.call(this, parent);
                },
            });
            var parent = new StandaloneWidget(model);
            testUtils.addMockEnvironment(parent, {
                data: self.data,
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });

            var relField = new relationalFields.FieldMany2One(parent,
                'partner_id',
                record,
                {
                    mode: 'edit',
            });

            relField.appendTo(fixture);
            $('input.o_input').val('xyzzrot').trigger('input');

            concurrency.delay(0).then(function () {
                var $dropdown = $('input.o_input').autocomplete('widget');
                $dropdown.find('.o_m2o_dropdown_option:contains(Create)')
                    .first().mouseenter().click();
                assert.verifySteps(['name_search', 'name_create']);
                parent.destroy();
                model.destroy();
                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                done();
            });
        });
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

    QUnit.test('form: quick create then save directly', function (assert) {
        var done = assert.async();
        assert.expect(5);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var def = $.Deferred();
        var newRecordID;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="trululu"/>' +
                '</form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'name_create') {
                    assert.step('name_create');
                    return def.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.strictEqual(args.args[0].trululu, newRecordID,
                        "should create with the correct m2o id");
                }
                return result;
            },
        });

        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').val('b').trigger('keydown');
        concurrency.delay(0).then(function () {
            $dropdown.find('li:first()').click(); // quick create 'b'
            form.$buttons.find('.o_form_button_save').click();

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
            done();
        });
    });

    QUnit.test('list: quick create then save directly', function (assert) {
        var done = assert.async();
        assert.expect(8);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var def = $.Deferred();
        var newRecordID;
        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="top">' +
                    '<field name="trululu"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'name_create') {
                    assert.step('name_create');
                    return def.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.strictEqual(args.args[0].trululu, newRecordID,
                        "should create with the correct m2o id");
                }
                return result;
            },
        });

        list.$buttons.find('.o_list_button_add').click();

        var $dropdown = list.$('.o_field_many2one input').autocomplete('widget');
        list.$('.o_field_many2one input').val('b').trigger('keydown');
        concurrency.delay(0).then(function () {
            $dropdown.find('li:first()').click(); // quick create 'b'
            list.$buttons.find('.o_list_button_add').click();

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");
            assert.strictEqual(list.$('.o_data_row').length, 4,
                "should wait for the name_create before adding the new row");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);
            assert.strictEqual(list.$('.o_data_row:nth(1) .o_data_cell').text(), 'b',
                "created row should have the correct m2o value");
            assert.strictEqual(list.$('.o_data_row').length, 5,
                "should have added the fifth row");

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            list.destroy();
            done();
        });
    });

    QUnit.test('list in form: quick create then save directly', function (assert) {
        var done = assert.async();
        assert.expect(6);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var def = $.Deferred();
        var newRecordID;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'name_create') {
                    assert.step('name_create');
                    return def.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.strictEqual(args.args[0].p[0][2].trululu, newRecordID,
                        "should create with the correct m2o id");
                }
                return result;
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();

        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').val('b').trigger('keydown');
        concurrency.delay(0).then(function () {
            $dropdown.find('li:first()').click(); // quick create 'b'
            form.$buttons.find('.o_form_button_save').click();

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);
            assert.strictEqual(form.$('.o_data_row:first .o_data_cell').text(), 'b',
                "first row should have the correct m2o value");

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
            done();
        });
    });

    QUnit.test('list in form: quick create then add a new line directly', function (assert) {
        // required many2one inside a one2many list: directly after quick creating
        // a new many2one value (before the name_create returns), click on add an item:
        // at this moment, the many2one has still no value, and as it is required,
        // the row is discarded if a saveLine is requested. However, it should
        // wait for the name_create to return before trying to save the line.
        var done = assert.async();
        assert.expect(8);

        this.data.partner.onchanges = {
            trululu: function () {},
        };

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var def = $.Deferred();
        var newRecordID;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="trululu" required="1"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'name_create') {
                    return def.then(_.constant(result)).then(function (nameGet) {
                        newRecordID = nameGet[0];
                        return nameGet;
                    });
                }
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0].p[0][2].trululu, newRecordID);
                }
                return result;
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();

        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').val('b').trigger('keydown');
        concurrency.delay(0).then(function () {
            $dropdown.find('li:first()').click(); // quick create 'b'
            form.$('.o_field_x2many_list_row_add a').click();

            assert.strictEqual(form.$('.o_data_row').length, 1,
                "there should still be only one row");
            assert.ok(form.$('.o_data_row').hasClass('o_selected_row'),
                "the row should still be in edition");

            def.resolve();

            assert.strictEqual(form.$('.o_data_row:first .o_data_cell').text(), 'b',
                "first row should have the correct m2o value");
            assert.strictEqual(form.$('.o_data_row').length, 2,
                "there should now be 2 rows");
            assert.ok(form.$('.o_data_row:nth(1)').hasClass('o_selected_row'),
                "the second row should be in edition");

            form.$buttons.find('.o_form_button_save').click();

            assert.strictEqual(form.$('.o_data_row').length, 1,
                "there should be 1 row saved (the second one was empty and invalid)");
            assert.strictEqual(form.$('.o_data_row .o_data_cell').text(), 'b',
                "should have the correct m2o value");

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
            done();
        });
    });

    QUnit.test('list in form: create with one2many with many2one', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="display_name"/>' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({p: [[0, 0, {display_name: 'new record'}]]});
                } else if (args.method === 'name_get') {
                    // This should not be called at all and thus is not accounted for
                    // in the assert.expect. If this is called, you broke this test.
                    assert.notOk(_.str.startsWith(args.args[0][0], 'virtual_'),
                        "should not call name_get for the m2o inside o2m which has no value");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('td.o_data_cell:first').text(), 'new record',
            "should have created the new record in the o2m with the correct name");

        form.destroy();
    });

    QUnit.test('list in form: create with one2many with many2one (version 2)', function (assert) {
        // This test simulates the exact same scenario as the previous one,
        // except that the value for the many2one is explicitely set to false,
        // which is stupid, but this happens, so we have to handle it
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="display_name"/>' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({p: [[0, 0, {display_name: 'new record', trululu: false}]]});
                } else if (args.method === 'name_get') {
                    // This should not be called at all and thus is not accounted for
                    // in the assert.expect. If this is called, you broke this test.
                    assert.notOk(_.str.startsWith(args.args[0][0], 'virtual_'),
                        "should not call name_get for the m2o inside o2m which has no value");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('td.o_data_cell:first').text(), 'new record',
            "should have created the new record in the o2m with the correct name");

        form.destroy();
    });

    QUnit.test('item not dropped on discard with empty required field (default_get)', function (assert) {
        // This test simulates discarding a record that has been created with
        // one of its required field that is empty. When we discard the changes
        // on this empty field, it should not assume that this record should be
        // abandonned, since it has been added (even though it is a new record).
        assert.expect(8);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="display_name"/>' +
                                '<field name="trululu" required="1"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({ p: [[0, 0, { display_name: 'new record', trululu: false }]] });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('tr.o_data_row').length, 1,
            "should have created the new record in the o2m");
        assert.strictEqual($('td.o_data_cell').first().text(), "new record",
            "should have the correct displayed name");

        var requiredElement = $('td.o_data_cell.o_required_modifier');
        assert.strictEqual(requiredElement.length, 1,
            "should have a required field on this record");
        assert.strictEqual(requiredElement.text(), "",
            "should have empty string in the required field on this record");

        requiredElement.click();
        // discard by clicking on body
        $('body').click();

        assert.strictEqual($('tr.o_data_row').length, 1,
            "should still have the record in the o2m");
        assert.strictEqual($('td.o_data_cell').first().text(), "new record",
            "should still have the correct displayed name");

        // update selector of required field element
        requiredElement = $('td.o_data_cell.o_required_modifier');
        assert.strictEqual(requiredElement.length, 1,
            "should still have the required field on this record");
        assert.strictEqual(requiredElement.text(), "",
            "should still have empty string in the required field on this record");
        form.destroy();
    });

    QUnit.test('list in form: name_get with unique ids (default_get)', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].display_name = "MyTrululu";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({
                        p: [
                            [0, 0, { trululu: 1 }],
                            [0, 0, { trululu: 1 }]
                        ]
                    });
                }
                if (args.method === 'name_get') {
                    assert.deepEqual(args.args[0], _.uniq(args.args[0]),
                        "should not have duplicates in name_get rpc");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('td.o_data_cell').text(), "MyTrululuMyTrululu",
            "both records should have the correct display_name for trululu field");

        form.destroy();
    });

    QUnit.test('list in form: show name of many2one fields in multi-page (default_get)', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom" limit="1">' +
                                '<field name="display_name"/>' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({
                        p: [
                            [0, 0, { display_name: 'record1', trululu: 1 }],
                            [0, 0, { display_name: 'record2', trululu: 2 }]
                        ]
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('td.o_data_cell').first().text(),
            "record1", "should show display_name of 1st record");
        assert.strictEqual(form.$('td.o_data_cell').first().next().text(),
            "first record", "should show display_name of trululu of 1st record");

        form.$('button.o_pager_next').click();

        assert.strictEqual(form.$('td.o_data_cell').first().text(),
            "record2", "should show display_name of 2nd record");
        assert.strictEqual(form.$('td.o_data_cell').first().next().text(),
            "second record", "should show display_name of trululu of 2nd record");

        form.destroy();
    });

    QUnit.test('list in form: item not dropped on discard with empty required field (onchange in default_get)', function (assert) {
        // variant of the test "list in form: discard newly added element with
        // empty required field (default_get)", in which the `default_get`
        // performs an `onchange` at the same time. This `onchange` may create
        // some records, which should not be abandoned on discard, similarly
        // to records created directly by `default_get`
        assert.expect(7);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        this.data.partner.onchanges = {
            product_id: function (obj) {
                if (obj.product_id === 37) {
                    obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                }
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                '<field name="product_id"/>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="display_name"/>' +
                            '<field name="trululu" required="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({
                        product_id: 37,
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // check that there is a record in the editable list with empty string as required field
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should have a row in the editable list");
        assert.strictEqual($('td.o_data_cell').first().text(), "entry",
            "should have the correct displayed name");
        var requiredField = $('td.o_data_cell.o_required_modifier');
        assert.strictEqual(requiredField.length, 1,
            "should have a required field on this record");
        assert.strictEqual(requiredField.text(), "",
            "should have empty string in the required field on this record");

        // click on empty required field in editable list record
        requiredField.click();
        // click off so that the required field still stay empty
        $('body').click();

        // record should not be dropped
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should not have dropped record in the editable list");
        assert.strictEqual($('td.o_data_cell').first().text(), "entry",
            "should still have the correct displayed name");
        assert.strictEqual($('td.o_data_cell.o_required_modifier').text(), "",
            "should still have empty string in the required field");

        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        form.destroy();
    });

    QUnit.test('list in form: item not dropped on discard with empty required field (onchange on list after default_get)', function (assert) {
        // discarding a record from an `onchange` in a `default_get` should not
        // abandon the record. This should not be the case for following
        // `onchange`, except if an onchange make some changes on the list:
        // in particular, if an onchange make changes on the list such that
        // a record is added, this record should not be dropped on discard
        assert.expect(8);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        this.data.partner.onchanges = {
            product_id: function (obj) {
                if (obj.product_id === 37) {
                    obj.p = [[0, 0, { display_name: "entry", trululu: false }]];
                }
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                '<field name="product_id"/>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="display_name"/>' +
                            '<field name="trululu" required="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        });

        // check no record in list
        assert.strictEqual(form.$('.o_data_row').length, 0,
            "should have no row in the editable list");

        // select product_id to force on_change in editable list
        form.$('.o_field_widget[name="product_id"] .o_input').click();
        $('.ui-menu-item').first().click();

        // check that there is a record in the editable list with empty string as required field
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should have a row in the editable list");
        assert.strictEqual($('td.o_data_cell').first().text(), "entry",
            "should have the correct displayed name");
        var requiredField = $('td.o_data_cell.o_required_modifier');
        assert.strictEqual(requiredField.length, 1,
            "should have a required field on this record");
        assert.strictEqual(requiredField.text(), "",
            "should have empty string in the required field on this record");

        // click on empty required field in editable list record
        requiredField.click();
        // click off so that the required field still stay empty
        $('body').click();

        // record should not be dropped
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should not have dropped record in the editable list");
        assert.strictEqual($('td.o_data_cell').first().text(), "entry",
            "should still have the correct displayed name");
        assert.strictEqual($('td.o_data_cell.o_required_modifier').text(), "",
            "should still have empty string in the required field");

        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        form.destroy();
    });

    QUnit.test('item dropped on discard with empty required field with "Add an item" (invalid on "ADD")', function (assert) {
        // when a record in a list is added with "Add an item", it should
        // always be dropped on discard if some required field are empty
        // at the record creation.
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="display_name"/>' +
                            '<field name="trululu" required="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        });

        // Click on "Add an item"
        form.$('.o_field_x2many_list_row_add a').click();
        var charField = form.$('.o_field_widget.o_field_char[name="display_name"]');
        var requiredField = form.$('.o_field_widget.o_required_modifier[name="trululu"]');
        charField.val("some text");
        assert.strictEqual(charField.length, 1,
            "should have a char field 'display_name' on this record");
        assert.notOk(charField.hasClass('o_required_modifier'),
            "the char field should not be required on this record");
        assert.strictEqual(charField.val(), "some text",
            "should have entered text in the char field on this record");
        assert.strictEqual(requiredField.length, 1,
            "should have a required field 'trululu' on this record");
        assert.strictEqual(requiredField.val().trim(), "",
            "should have empty string in the required field on this record");

        // click on empty required field in editable list record
        requiredField.click();
        // click off so that the required field still stay empty
        $('body').click();

        // record should be dropped
        assert.strictEqual(form.$('.o_data_row').length, 0,
            "should have dropped record in the editable list");

        form.destroy();
    });

    QUnit.test('item not dropped on discard with empty required field with "Add an item" (invalid on "UPDATE")', function (assert) {
        // when a record in a list is added with "Add an item", it should
        // be temporarily added to the list when it is valid (e.g. required
        // fields are non-empty). If the record is updated so that the required
        // field is empty, and it is discarded, then the record should not be
        // dropped.
        assert.expect(8);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="display_name"/>' +
                            '<field name="trululu" required="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        });

        assert.strictEqual(form.$('.o_data_row').length, 0,
            "should initially not have any record in the list");

        // Click on "Add an item"
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should have a temporary record in the list");

        var $inputEditMode = form.$('.o_field_widget.o_required_modifier[name="trululu"] input');
        assert.strictEqual($inputEditMode.length, 1,
            "should have a required field 'trululu' on this record");
        assert.strictEqual($inputEditMode.val(), "",
            "should have empty string in the required field on this record");

        // add something to required field and leave edit mode of the record
        $inputEditMode.click();
        $('li.ui-menu-item').first().click();
        $('body').click(); // leave edit mode on the line

        var $inputReadonlyMode = form.$('.o_data_cell.o_required_modifier');
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should not have dropped valid record when leaving edit mode");
        assert.strictEqual($inputReadonlyMode.text(), "first record",
            "should have put some content in the required field on this record");

        // remove the required field and leave edit mode of the record
        $('.o_data_row').click(); // enter edit mode on the line
        $inputEditMode.click();
        $inputEditMode.val("");
        $('body').click();

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should not have dropped record in the list on discard (invalid on UPDATE)");
        assert.strictEqual($inputReadonlyMode.text(), "first record",
            "should keep previous valid required field content on this record");

        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
        form.destroy();
    });

    QUnit.test('list in form: default_get with x2many create', function (assert) {
        assert.expect(5);

        var displayName = 'brandon is the new timmy';
        this.data.partner.onchanges.timmy = function (obj) {
            assert.deepEqual(
                obj.timmy,
                [
                    [6, false, []],
                    [0, obj.timmy[1][1], {display_name: displayName, name: 'brandon'}]
                ],
                "should have properly created the x2many command list");
            obj.int_field = obj.timmy.length;
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="timmy">' +
                            '<tree editable="bottom">' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                        '<field name="int_field"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({timmy: [[0, 0, {display_name: 'brandon is the new timmy', name: 'brandon'}]]});
                }
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {
                        int_field: 2,
                        timmy: [
                            [6, false, []],
                            [0, args.args[0].timmy[1][1], {display_name: displayName, name: 'brandon'}],
                        ],
                    }, "should send the correct values to create");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual($('td.o_data_cell:first').text(), 'brandon is the new timmy',
            "should have created the new record in the m2m with the correct name");
        assert.strictEqual($('input.o_field_integer').val(), '2',
            "should have called and executed the onchange properly");

        // edit the subrecord and save
        displayName = 'new value';
        form.$('.o_data_cell').click();
        form.$('.o_data_cell input').val(displayName).trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('list in form: default_get with x2many create and onchange', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges.turtles = function (obj) {
            assert.deepEqual(
                obj.turtles,
                [
                    [4, 2, false],
                    [1, 2, {turtle_foo: 'blip'}],
                    [4, 3, false],
                    [1, 3, {turtle_foo: 'kawa'}]
                ],
                "should have properly created the x2many command list");
        };

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
                        '<field name="int_field"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({turtles: [[6, 0, [2,3]]]});
                }
                if (args.method === 'create') {
                    // it would be even better if we did not send the current
                    // unchanged state with the command 1, but this seems more
                    // difficult.
                    assert.deepEqual(args.args[0].turtles, [
                        [4, 2, false],
                        [1, 2, {turtle_foo: 'blip'}],
                        [4, 3, false],
                        [1, 3, {turtle_foo: 'kawa'}]
                    ], 'should send proper commands to create method');
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('list in form: call button in sub view', function (assert) {
        assert.expect(6);

        this.data.partner.records[0].p = [2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="bottom">' +
                                '<field name="product_id"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/get_formview_id') {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.strictEqual(event.data.env.model, 'product',
                        'should call with correct model in env');
                    assert.strictEqual(event.data.env.currentID, 37,
                        'should call with correct currentID in env');
                    assert.deepEqual(event.data.env.resIDs, [37],
                        'should call with correct resIDs in env');
                },
            },
            archs: {
                'product,false,form': '<form string="Partners">' +
                                        '<header>' +
                                            '<button name="action" type="action" string="Just do it !"/>' +
                                            '<button name="object" type="object" string="Just don\'t do it !"/>' +
                                            '<field name="display_name"/>' +
                                        '</header>' +
                                      '</form>',
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('td.o_data_cell:first').click();  // edit first one2many line
        form.$('.o_external_button').click();  // open product sub view in modal
        $('button:contains("Just do it !")').click(); // click on action button
        $('button:contains("Just don\'t do it !")').click(); // click on object button

        form.destroy();
    });

    QUnit.test('X2Many sequence list in modal', function (assert) {
        assert.expect(5);

        this.data.partner.fields.sequence = {string: 'Sequence', type: 'integer'};
        this.data.partner.records[0].sequence = 1;
        this.data.partner.records[1].sequence = 2;
        this.data.partner.onchanges = {
            sequence: function (obj) {
                if (obj.id === 2) {
                    obj.sequence = 1;
                    assert.step('onchange sequence');
                }
            },
        };

        this.data.product.fields.turtle_ids = {string: 'Turtles', type: 'one2many', relation: 'turtle'};
        this.data.product.records[0].turtle_ids = [1];

        this.data.turtle.fields.partner_types_ids = {string: "Partner", type: "one2many", relation: 'partner'};
        this.data.turtle.fields.type_id = {string: "Partner Type", type: "many2one", relation: 'partner_type'};

        this.data.partner_type.fields.partner_ids = {string: "Partner", type: "one2many", relation: 'partner'};
        this.data.partner_type.records[0].partner_ids = [1,2];

        testUtils.createAsyncView({
            View: FormView,
            model: 'product',
            data: this.data,
            arch: '<form>' +
                        '<field name="name"/>' +
                        '<field name="turtle_ids" widget="one2many_list">' +
                            '<tree string="Turtles" editable="bottom">' +
                                '<field name="type_id"/>' +
                            '</tree>' +
                        '</field>' +
                '</form>',
            archs: {
                'partner_type,false,form': '<form><field name="partner_ids"/></form>',
                'partner,false,list': '<tree string="Vendors">' +
                                            '<field name="display_name"/>' +
                                            '<field name="sequence" widget="handle"/>' +
                                      '</tree>',
            },
            res_id: 37,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/read') {
                    return $.when([{id: 37, name: 'xphone', display_name: 'leonardo', turtle_ids: [1]}]);
                }
                if (route === '/web/dataset/call_kw/turtle/read') {
                    return $.when([{id: 1, type_id: [12, 'gold']}]);
                }
                if (route === '/web/dataset/call_kw/partner_type/get_formview_id') {
                    return $.when(false)
                }
                if (route === '/web/dataset/call_kw/partner_type/read') {
                    return $.when([{id: 12, partner_ids: [1,2], display_name: 'gold'}])
                }
                if (route === '/web/dataset/call_kw/partner_type/write') {
                    assert.step('partner_type write');
                }
                return this._super.apply(this, arguments);
            },
        }).then(function(form) {
            form.$buttons.find('.o_form_button_edit').click();
            form.$('.o_data_cell').click();
            form.$('.o_external_button').click();

            var $modal = $('.modal-dialog');
            assert.equal($modal.length, 1,
                'There should be 1 modal opened');

            var $handles = $modal.find('.ui-sortable-handle');
            assert.equal($handles.length, 2,
                'There should be 2 sequence handlers');

            testUtils.dragAndDrop($handles.eq(1), $modal.find('tbody tr').first());

            // Saving the modal and then the original model
            $modal.find('.modal-footer .btn-primary').click();
            form.$buttons.find('.o_form_button_save').click();

            assert.verifySteps(['onchange sequence', 'partner_type write']);

            form.destroy();
        });
    });

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
        assert.expect(4);

        this.data.partner.records[0].timmy = [12];

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
                    '<field name="trululu" context="{\'timmy\': timmy}" domain="[[\'id\', \'in\', timmy]]"/>' +
                    '<field name="timmy" widget="many2many_tags" invisible="1"/>' +
                '</form>',
            res_id: 1,
            session: {user_context: {hey: "ho"}},
            mockRPC: function (route, args) {
                if (args.method === 'name_search' && args.model === 'product') {
                    assert.deepEqual(
                        args.kwargs.args,
                        [['foo', '=', 'bar'], ['foo', '=', 'yop']],
                        'the field attr domain should have been used for the RPC (and evaluated)');
                    assert.deepEqual(
                        args.kwargs.context,
                        {hey: "ho", hello: "world", test: "yop"},
                        'the field attr context should have been used for the ' +
                        'RPC (evaluated and merged with the session one)');
                    return $.when([]);
                }
                if (args.method === 'name_search' && args.model === 'partner') {
                    assert.deepEqual(args.kwargs.args, [['id', 'in', [12]]],
                        'the field attr domain should have been used for the RPC (and evaluated)');
                    assert.deepEqual(args.kwargs.context, {hey: 'ho', timmy: [[6, false, [12]]]},
                        'the field attr context should have been used for the RPC (and evaluated)');
                    return $.when([]);
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_widget[name=product_id] input').click();

        form.$('.o_field_widget[name=trululu] input').click();

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

    QUnit.test('slow create on a many2one', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<field name="product_id" options="{\'quick_create\': False}"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form':
                    '<form>' +
                        '<field name="name"/>' +
                    '</form>',
            },
        });

        // cancel the many2one creation with Cancel button
        form.$('.o_field_many2one input').focus().val('new product').trigger('keyup').trigger('blur');
        assert.strictEqual($('.modal').length, 1, "there should be one opened modal");
        $('.modal .modal-footer .btn:contains(Cancel)').click();
        assert.strictEqual(form.$('.o_field_many2one input').val(), "",
            'the many2one should not set a value as its creation has been cancelled (with Cancel button)');

        // cancel the many2one creation with Close button
        form.$('.o_field_many2one input').focus().val('new product').trigger('keyup').trigger('blur');
        $('.modal .modal-header button').click();
        assert.strictEqual(form.$('.o_field_many2one input').val(), "",
            'the many2one should not set a value as its creation has been cancelled (with Close button)');

        // select a new value then cancel the creation of the new one --> restore the previous
        form.$('.o_field_many2one input').click();
        form.$('.o_field_many2one input').autocomplete('widget').find('a').first().click();
        assert.strictEqual(form.$('input').val(), "xphone", "should have selected xphone");
        form.$('.o_field_many2one input').focus().val('new product').trigger('keyup').trigger('blur');
        assert.strictEqual($('.modal').length, 1, "there should be one opened modal");
        $('.modal .modal-footer .btn:contains(Cancel)').click();
        assert.strictEqual(form.$('.o_field_many2one input').val(), "xphone",
            'should have restored the many2one with its previous selected value (xphone)');

        // confirm the many2one creation
        form.$('.o_field_many2one input').focus();
        form.$('.o_field_many2one input').val('new partner').trigger('keyup').trigger('blur');
        $('.modal .modal-footer .btn-primary').click();
        assert.strictEqual($('.modal .o_form_view').length, 1,
            'a new modal should be opened and contain a form view');

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

    QUnit.test('can_create and can_write option on a many2one', function (assert) {
        assert.expect(5);

        this.data.product.options = {
            can_create: "false",
            can_write: "false",
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<field name="product_id" can_create="false" can_write="false"/>' +
                        '</sheet>' +
                '</form>',
            archs: {
                'product,false,form': '<form string="Products"><field name="display_name"/></form>',
            },
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/product/get_formview_id') {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$('.o_field_many2one input').click();
        assert.strictEqual($('.ui-autocomplete .o_m2o_dropdown_option:contains(Create)').length, 0,
            "there shouldn't be any option to search and create");

        $('.ui-autocomplete li:contains(xpad)').mouseenter().click();
        assert.strictEqual(form.$('.o_field_many2one input').val(), "xpad",
            "the correct record should be selected");
        assert.strictEqual(form.$('.o_field_many2one .o_external_button').length, 1,
            "there should be an external button displayed");

        form.$('.o_field_many2one .o_external_button').click();
        assert.strictEqual($('.modal .o_form_view.o_form_readonly').length, 1,
            "there should be a readonly form view opened");

        $('.modal .o_form_button_cancel').click();

        form.$('.o_field_many2one input').val('new product').trigger('keyup').trigger('focusout');

        assert.strictEqual($('.modal').length, 0, "should not display the create modal");
        form.destroy();
    });

    QUnit.test('pressing enter in a m2o in an editable list', function (assert) {
        assert.expect(9);
        var done = assert.async();
        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="product_id"/></tree>',
        });

        list.$('td.o_data_cell:first').click();
        assert.strictEqual(list.$('.o_selected_row').length, 1,
            "should have a row in edit mode");

        // we now write 'a' and press enter to check that the selection is
        // working, and prevent the navigation
        list.$('td.o_data_cell input:first').val('a').trigger('input');
        concurrency.delay(0).then(function () {
            var $input = list.$('td.o_data_cell input:first');
            var $dropdown = $input.autocomplete('widget');
            assert.ok($dropdown.is(':visible'), "autocomplete dropdown should be visible");

            // we now trigger ENTER to select first choice
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            assert.strictEqual($input[0], document.activeElement,
                "input should still be focused");

            // we now trigger again ENTER to make sure we can move to next line
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));

            assert.notOk(document.contains($input[0]),
                "input should no longer be in dom");
            assert.ok(list.$('tr.o_data_row:eq(1)').hasClass('o_selected_row'),
                "second row should now be selected");

            // we now write again 'a' in the cell to select xpad. We will now
            // test with the tab key
            list.$('td.o_data_cell input:first').val('a').trigger('input');
            return concurrency.delay(0);
        }).then(function () {
            var $input = list.$('td.o_data_cell input:first');
            var $dropdown = $input.autocomplete('widget');
            assert.ok($dropdown.is(':visible'), "autocomplete dropdown should be visible");
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.TAB,
                keyCode: $.ui.keyCode.TAB,
            }));
            assert.strictEqual($input[0], document.activeElement,
                "input should still be focused");

            // we now trigger again ENTER to make sure we can move to next line
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.TAB,
                keyCode: $.ui.keyCode.TAB,
            }));

            assert.notOk(document.contains($input[0]),
                "input should no longer be in dom");
            assert.ok(list.$('tr.o_data_row:eq(2)').hasClass('o_selected_row'),
                "third row should now be selected");
            list.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            done();
        });
    });

    QUnit.test('pressing ENTER on a \'no_quick_create\' many2one should not trigger M2ODialog', function (assert) {
        var done = assert.async();
        assert.expect(2);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="trululu" options="{\'no_quick_create\': True}"/>' +
                    '<field name="foo"/>' +
                '</form>',
            archs: {
                'partner,false,form': '<form string="Partners"><field name="display_name"/></form>',
            },
        });

        var $input = form.$('.o_field_many2one input');
        $input.val("Something that does not exist").trigger('input');
        $('.ui-autocomplete .ui-menu-item a:contains(Create and)').trigger('mouseenter');
        concurrency.delay(0).then(function() {
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            $input.trigger($.Event('keypress', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            $input.trigger($.Event('keyup', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            concurrency.delay(0).then(function() {
                $input.blur();
                assert.strictEqual($('.modal').length, 1,
                    "should have one modal in body");
                // Check that discarding clears $input
                $('.modal .o_form_button_cancel').click();
                assert.strictEqual($input.val(), '',
                    "the field should be empty");
                form.destroy();
                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                done();
            });
        });
    });

    QUnit.test('many2one in editable list + onchange, with enter [REQUIRE FOCUS]', function (assert) {
        assert.expect(6);
        var done = assert.async();
        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        this.data.partner.onchanges.product_id = function (obj) {
            obj.int_field = obj.product_id || 0;
        };

        var def = $.Deferred();

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="product_id"/><field name="int_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        list.$('td.o_data_cell:first').click();
        list.$('td.o_data_cell input:first').val('a').trigger('input');
        concurrency.delay(0).then(function () {
            var $input = list.$('td.o_data_cell input:first');
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            $input.trigger($.Event('keyup', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            def.resolve();
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            assert.strictEqual($('div.modal').length, 0, "should not have any modal in DOM");
            assert.verifySteps(['name_search', 'onchange', 'write', 'read']);
            list.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            done();
        });
    });

    QUnit.test('many2one in editable list + onchange, with enter, part 2 [REQUIRE FOCUS]', function (assert) {
        // this is the same test as the previous one, but the onchange is just
        // resolved slightly later
        assert.expect(6);
        var done = assert.async();
        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        this.data.partner.onchanges.product_id = function (obj) {
            obj.int_field = obj.product_id || 0;
        };

        var def = $.Deferred();

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="product_id"/><field name="int_field"/></tree>',
            mockRPC: function (route, args) {
                if (args.method) {
                    assert.step(args.method);
                }
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return def.then(_.constant(result));
                }
                return result;
            },
        });

        list.$('td.o_data_cell:first').click();
        list.$('td.o_data_cell input:first').val('a').trigger('input');
        concurrency.delay(0).then(function () {
            var $input = list.$('td.o_data_cell input:first');
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            $input.trigger($.Event('keyup', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            $input.trigger($.Event('keydown', {
                which: $.ui.keyCode.ENTER,
                keyCode: $.ui.keyCode.ENTER,
            }));
            def.resolve();
            assert.strictEqual($('div.modal').length, 0, "should not have any modal in DOM");
            assert.verifySteps(['name_search', 'onchange', 'write', 'read']);
            list.destroy();
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            done();
        });
    });

    QUnit.test('many2one: domain updated by an onchange', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="int_field"/>' +
                    '<field name="trululu"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    domain = [['id', 'in', [10]]];
                    return $.when({
                        domain: {
                            trululu: domain,
                            unexisting_field: domain,
                        }
                    });
                }
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        // trigger a name_search (domain should be [])
        form.$('.o_field_widget[name=trululu] input').click();
        // close the dropdown
        form.$('.o_field_widget[name=trululu] input').click();
        // trigger an onchange that will update the domain
        form.$('.o_field_widget[name=int_field]').val(2).trigger('input');
        // trigger a name_search (domain should be [['id', 'in', [10]]])
        form.$('.o_field_widget[name=trululu] input').click();

        form.destroy();
    });

    QUnit.test('many2one in one2many: domain updated by an onchange', function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            trululu: function () {},
        };

        var domain = [];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="trululu"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        // add a first row with a specific domain for the m2o
        domain = [['id', 'in', [10]]]; // domain for subrecord 1
        form.$('.o_field_x2many_list_row_add a').click(); // triggers the onchange
        form.$('.o_field_widget[name=trululu] input').click(); // triggers the name_search

        // add a second row with another domain for the m2o
        domain = [['id', 'in', [5]]]; // domain for subrecord 2
        form.$('.o_field_x2many_list_row_add a').click(); // triggers the onchange
        form.$('.o_field_widget[name=trululu] input').click(); // triggers the name_search

        // check again the first row to ensure that the domain hasn't change
        domain = [['id', 'in', [10]]]; // domain for subrecord 1 should have been kept
        form.$('.o_data_row:first .o_data_cell').click();
        form.$('.o_field_widget[name=trululu] input').click(); // triggers the name_search

        form.destroy();
    });

    QUnit.test('updating a many2one from a many2many', function (assert) {
        assert.expect(4);

        this.data.turtle.records[1].turtle_trululu = 1;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group>' +
                        '<field name="turtles">' +
                            '<tree editable="bottom">' +
                                '<field name="display_name"/>' +
                                '<field name="turtle_trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner,false,form': '<form string="Trululu"><field name="display_name"/></form>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [1], "should call get_formview_id with correct id");
                    return $.when(false);
                }
                return this._super(route, args);
            },
        });

        // Opening the modal
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_data_row td:contains(first record)').click();
        form.$('.o_external_button').click();
        assert.strictEqual($('.modal').length, 1,
            "should have one modal in body");

        // Changing the 'trululu' value
        $('.modal input[name="display_name"]').val('test').trigger('input');
        $('.modal button.btn-primary').click();

        // Test whether the value has changed
        assert.strictEqual($('.modal').length, 0,
            "the modal should be closed");
        assert.equal(form.$('.o_data_cell:contains(test)').text(), 'test',
            "the partner name should have been updated to 'test'");

        form.destroy();
    });

    QUnit.test('x2many list sorted by many2one', function (assert) {
        assert.expect(3);

        this.data.partner.records[0].p = [1, 2, 4];
        this.data.partner.fields.trululu.sortable = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="id"/>' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_data_row .o_list_number').text(), '124',
            "should have correct order initially");

        form.$('.o_list_view thead th:nth(1)').click();

        assert.strictEqual(form.$('.o_data_row .o_list_number').text(), '412',
            "should have correct order (ASC)");

        form.$('.o_list_view thead th:nth(1)').click();

        assert.strictEqual(form.$('.o_data_row .o_list_number').text(), '214',
            "should have correct order (DESC)");

        form.destroy();
    });

    QUnit.test('many2many list add *many* records, remove, re-add', function (assert) {
        assert.expect(5);

        this.data.partner.fields.timmy.domain = [['color', '=', 2]];
        this.data.partner.fields.timmy.onChange = true;
        this.data.partner_type.fields.product_ids = {string: "Product", type: "many2many", relation: 'product'};

        for (var i=0; i<50; i++) {
            var new_record_partner_type = {id: 100+i, display_name: "batch" + i, color: 2};
            this.data.partner_type.records.push(new_record_partner_type);
        }

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="timmy" widget="many2many">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                            '<field name="product_ids" widget="many2many_tags"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner_type,false,list': '<tree><field name="display_name"/></tree>',
                'partner_type,false,search': '<search><field name="display_name"/><field name="color"/></search>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [1], "should call get_formview_id with correct id");
                    return $.when(false);
                }
                return this._super(route, args);
            },
        });

        // First round: add 51 records in batch
        form.$buttons.find('.btn.btn-primary.btn-sm.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        var $modal = $('.modal-dialog.modal-lg');

        assert.equal($modal.length, 1,
            'There should be one modal');

        $modal.find('thead input[type=checkbox]').click(); //select all the records we created in batch + 'gold'

        $modal.find('.btn.btn-sm.btn-primary.o_select_button').click();

        var m2m_records = form.$('.o_field_many2many.o_field_widget.o_field_x2many.o_field_x2many_list .o_data_cell:not(.o_many2many_tags_cell)');
        assert.equal(m2m_records.length, 51,
            'We should have added all the records present in the search view to the m2m field'); // the 50 in batch + 'gold'

        form.$buttons.find('.btn.btn-primary.btn-sm.o_form_button_save').click();

        // Secound round: remove one record
        form.$buttons.find('.btn.btn-primary.btn-sm.o_form_button_edit').click();
        var trash_buttons = form.$('.o_field_many2many.o_field_widget.o_field_x2many.o_field_x2many_list .o_list_record_delete');

        trash_buttons.first().click();

        var pager_limit = form.$('.o_field_many2many.o_field_widget.o_field_x2many.o_field_x2many_list .o_pager_limit');
        assert.equal(pager_limit.text(), '50',
            'We should have 50 records in the m2m field');

        // Third round: re-add 1 records
        form.$('.o_field_x2many_list_row_add a').click();

        $modal = $('.modal-dialog.modal-lg');

        assert.equal($modal.length, 1,
            'There should be one modal');

        $modal.find('thead input[type=checkbox]').click();

        $modal.find('.btn.btn-sm.btn-primary.o_select_button').click();
        
        pager_limit = form.$('.o_field_many2many.o_field_widget.o_field_x2many.o_field_x2many_list .o_pager_limit');
        assert.equal(pager_limit.text(), '51',
            'We should have 51 records in the m2m field');

        form.destroy();
    });

    QUnit.module('FieldOne2Many');

    QUnit.test('New record with a o2m also with 2 new records, ordered, and resequenced', function (assert) {
        assert.expect(3);

        // Needed to have two new records in a single stroke
        this.data.partner.onchanges = {
            foo: function(obj) {
                obj.p = [
                            [5],
                            [0, 0, {trululu: false}],
                            [0, 0, {trululu: false}],
                ]
            }
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(1),
            form.$('tbody tr').first(),
            {position: 'top'}
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

        this.data.partner.records[0].p = [2,4];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_field_x2many_list .o_field_x2many_list_row_add a').click();

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
            $.Event('keydown', {which: escapeKey, keyCode: escapeKey}));

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

        this.data.turtle.fields.parent_id = {string: "Parent", type: "many2one", relation: 'turtle'};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree>' +
                            '<field name="parent_id" />' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            archs: {
                'turtle,false,form': '<form><field name="parent_id" domain="[(\'id\', \'in\', parent.turtles)]"/></form>',
            },

            mockRPC: function(route, args) {
                if (route === '/web/dataset/call_kw/turtle/name_search') {
                    // We are going to pass twice here
                    // First time, we really have nothing
                    // Second time, a virtual_id has been created
                    assert.deepEqual(args.kwargs.args, [['id', 'in', []]]);
                }
                return this._super(route, args);
            }
        });

        form.$('.o_field_x2many_list[name=turtles] .o_field_x2many_list_row_add a').click();
        var $modal = $('.modal-content');

        var $turtleParent = $modal.find('.o_field_many2one input');
        var $dropdown = $turtleParent.autocomplete('widget');

        $turtleParent.click();

        $dropdown.find('li.o_m2o_dropdown_option:contains(Create)').first().mouseenter().click();

        $modal = $('.modal-content');

        $modal.eq(1).find('.modal-footer .btn-primary').eq(0).click(); // Confirm new Record
        $modal.eq(0).find('.modal-footer .btn-primary').eq(1).click(); // Save & New

        assert.equal(form.$('.o_data_row').length, 1,
            'The main record should have the new record in its o2m');

        $modal = $('.modal-content');
        $modal.find('.o_field_many2one input').click();

        form.destroy();
    });

    QUnit.test('one2many list editable with cell readonly modifier', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].turtles = [1,2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.deepEqual(args.args[1].p[1][2], {foo: 'ff', qux: 99},
                        'The right values should be written');
                }
                return this._super(route, args);
            }
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        var $targetInput = $('.o_selected_row .o_input[name=foo]');
        assert.equal($targetInput[0], document.activeElement,
            'The first input of the line should have the focus');

        // Simulating hitting the 'f' key twice
        $targetInput.val('f').trigger('input');
        $targetInput.val($targetInput.val() + 'f').trigger('input');

        assert.equal($targetInput[0], document.activeElement,
            'The first input of the line should still have the focus');

        // Simulating a TAB key
        $targetInput.trigger($.Event('keydown', {which: 9, keyCode:9}));

        var $secondTarget = $('.o_selected_row .o_input[name=qux]');

        assert.equal($secondTarget[0], document.activeElement,
            'The second input of the line should have the focus after the TAB press');


        $secondTarget.val(9).trigger('input');
        $secondTarget.val($secondTarget.val() + 9).trigger('input');

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

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

    QUnit.test('transferring class attributes in one2many sub fields', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree editable="bottom">' +
                            '<field name="turtle_foo" class="hey"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('td.hey').length, 1,
            'should have a td with the desired class');

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('td.hey').length, 1,
            'should have a td with the desired class');

        form.$('td.o_data_cell').click();

        assert.strictEqual(form.$('input[name="turtle_foo"].hey').length, 1,
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

    QUnit.test('use the limit attribute in arch (in field o2m inline tree view)', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].turtles = [1,2,3];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                '<field name="turtles">' +
                    '<tree limit="2">' +
                        '<field name="turtle_foo"/>' +
                    '</tree>' +
                '</field>' +
            '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.model === 'turtle') {
                    assert.deepEqual(args.args[0], [1,2],
                        'should only load first 2 records');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_data_row').length, 2,
            'should display 2 data rows');
        form.destroy();
    });

    QUnit.test('use the limit attribute in arch (in field o2m non inline tree view)', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].turtles = [1,2,3];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                '<field name="turtles"/>' +
            '</form>',
            archs: {
                'turtle,false,list': '<tree limit="2"><field name="turtle_foo"/></tree>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.model === 'turtle') {
                    assert.deepEqual(args.args[0], [1,2],
                        'should only load first 2 records');
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_data_row').length, 2,
            'should display 2 data rows');
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

    QUnit.test('embedded one2many with handle widget', function (assert) {
        assert.expect(10);

        var nbConfirmChange = 0;
        testUtils.patch(ListRenderer, {
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
            arch:'<form string="Partners">' +
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

        testUtils.intercept(form, "field_changed", function (event) {
            assert.step(event.data.changes.turtles.data.turtle_int.toString());
        }, true);

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
            "should have the 3 rows in the correct order");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
            "should still have the 3 rows in the correct order");
        assert.strictEqual(nbConfirmChange, 0, "should not have confirmed any change yet");

        // Drag and drop the second line in first position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(1),
            form.$('tbody tr').first(),
            {position: 'top'}
        );

        assert.strictEqual(nbConfirmChange, 1, "should have confirmed changes only once");
        assert.verifySteps(["0", "1"],
            "sequences values should be incremental starting from the previous minimum one");

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
            "should have the 3 rows in the new order");

        form.$buttons.find('.o_form_button_save').click();

        assert.deepEqual(_.map(this.data.turtle.records, function(turtle) {
            return _.pick(turtle, 'id', 'turtle_foo', 'turtle_int');
        }), [
            {id: 1, turtle_foo: "yop", turtle_int: 1},
            {id: 2, turtle_foo: "blip", turtle_int:0},
            {id: 3, turtle_foo: "kawa", turtle_int:21}
        ], "should have save the changed sequence");

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
            "should still have the 3 rows in the new order");

        testUtils.unpatch(ListRenderer);

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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_data_cell').eq(1).click();
        var $cell = form.$('.o_selected_row .o_input[name=turtle_foo]');
        $cell.val("hop").trigger('change');
        form.$buttons.find('.o_form_button_save').click();

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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_data_cell').eq(1).click();
        var $cell = form.$('.o_selected_row .o_input[name=turtle_foo]');
        $cell.val("hop").trigger("change");
        form.$buttons.find('.o_form_button_save').click();

         assert.deepEqual(form.$('.o_many2many_tags_cell').text().trim().split(/\s+/),
              [ "second", "record", "aaa" ],
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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();

        // Drag and drop the second line in first position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(1),
            form.$('tbody tr').first(),
            {position: 'top'}
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
            arch:'<form string="Partners">' +
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
                    assert.deepEqual(args.args[1].turtles, [[4,2,false],[1,1,{"turtle_int":2}],[1,3,{"turtle_int":3}]],
                        "should change all lines that have changed (the first one doesn't change because it has the same sequence)");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();


        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
            "should have the 3 rows in the correct order");

        // Drag and drop the second line in first position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(1),
            form.$('tbody tr').first(),
            {position: 'top'}
        );

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipyopkawa",
            "should still have the 3 rows in the correct order");
        assert.strictEqual(turtleOnchange, 3, "should update all lines");

        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
    });

    QUnit.test('onchange (with command 5) for embedded one2many with handle widget', function (assert) {
        assert.expect(3);

        var ids = [];
        for (var i=10; i<50; i++) {
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
            arch:'<form string="Partners">' +
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

        form.$('.o_pager_next').click();
        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "yopblipkawa",
            "should have the 3 rows in the correct order");

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many .o_list_view tbody tr:first td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:first input:first').val('blurp').trigger('input');

        // Drag and drop the third line in second position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(2),
            form.$('.o_field_one2many tbody tr').eq(1),
            {position: 'top'}
        );

        assert.strictEqual(form.$('.o_data_cell').text(), "blurpkawablip", "should display to record in 'turtle_int' order");

        form.$buttons.find('.o_form_button_save').click();
        form.$('.o_pager_next').click();

        assert.strictEqual(form.$('.o_data_cell:not(.o_handle_cell)').text(), "blurpkawablip",
            "should display to record in 'turtle_int' order");

        form.destroy();
    });

    QUnit.test('onchange with modifiers for embedded one2many on the second page', function (assert) {
        assert.expect(7);

        var data = this.data;
        var ids = [];
        for (var i=10; i<60; i++) {
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
                    var record = _.findWhere(data.turtle.records, {id: change[1]});
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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
            "should display the records in order");

        form.$('.o_field_one2many .o_list_view tbody tr:first td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:first input:first').val('blurp').trigger('input');

        // the domain fail if the widget does not use the allready loaded data.
        form.$buttons.find('.o_form_button_cancel').click();

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "blurp#21#22#23#24#25#26#27#28#29",
            "should display the records in order with the changes");

        $('.modal .modal-footer button:first').click();

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
            "should cancel changes and display the records in order");

        form.$buttons.find('.o_form_button_edit').click();

        // Drag and drop the third line in second position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(2),
            form.$('.o_field_one2many tbody tr').eq(1),
            {position: 'top'}
        );

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#30#31#32#33#34#35#36#37#38",
            "should display the records in order after resequence (display record with turtle_int=0)");

        // Drag and drop the third line in second position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(2),
            form.$('.o_field_one2many tbody tr').eq(1),
            {position: 'top'}
        );

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#39#40#41#42#43#44#45#46#47",
            "should display the records in order after resequence (display record with turtle_int=0)");

        form.$buttons.find('.o_form_button_cancel').click();

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#39#40#41#42#43#44#45#46#47",
            "should display the records in order after resequence");

        $('.modal .modal-footer button:first').click();

        assert.equal(form.$('.o_field_one2many td[class="o_data_cell"]').text(), "#20#21#22#23#24#25#26#27#28#29",
            "should cancel changes and display the records in order");

        form.destroy();
    });

    QUnit.test('onchange followed by edition on the second page', function (assert) {
        assert.expect(12);

        var ids = [];
        for (var i=1; i<85; i++) {
            var id = 10 + i;
            ids.push(id);
            this.data.turtle.records.push({
                id: id,
                turtle_int: id/3|0,
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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_pager_next').click();

        form.$('.o_field_one2many .o_list_view tbody tr:eq(1) td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:eq(1) input:first').val('value 1').trigger('input');
        form.$('.o_field_one2many .o_list_view tbody tr:eq(2) td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:eq(2) input:first').val('value 2').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 40, "should display 40 records");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 0, "should display '#39' at the first line");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 40, "should display 39 records and the create line");
        assert.strictEqual(form.$('.o_data_row:first .o_field_char').length, 1, "should display the create line in first position");
        assert.strictEqual(form.$('.o_data_row:first .o_field_char').val(), "", "should an empty input");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 1, "should display '#39' at the second line");

        form.$('.o_data_row input:first').val('value 3').trigger('input');

        assert.strictEqual(form.$('.o_data_row:first .o_field_char').length, 1, "should display the create line in first position after onchange");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 1, "should display '#39' at the second line after onchange");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 40, "should display 39 records and the create line");
        assert.strictEqual(form.$('.o_data_row:first .o_field_char').length, 1, "should display the create line in first position");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(value 3))').index(), 1, "should display the created line at the second position");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#39))').index(), 2, "should display '#39' at the third line");

        form.destroy();
    });

    QUnit.test('onchange followed by edition on the second page (part 2)', function (assert) {
        assert.expect(8);

        var ids = [];
        for (var i=1; i<85; i++) {
            var id = 10 + i;
            ids.push(id);
            this.data.turtle.records.push({
                id: id,
                turtle_int: id/3|0,
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
            arch:'<form string="Partners">' +
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_pager_next').click();

        form.$('.o_field_one2many .o_list_view tbody tr:eq(1) td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:eq(1) input:first').val('value 1').trigger('input');
        form.$('.o_field_one2many .o_list_view tbody tr:eq(2) td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:eq(2) input:first').val('value 2').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 40, "should display 40 records");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#77))').index(), 39, "should display '#77' at the last line");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 41, "should display 41 records and the create line");
        assert.strictEqual(form.$('.o_data_row:has(.o_data_cell:contains(#76))').index(), 38, "should display '#76' at the penultimate line");
        assert.strictEqual(form.$('.o_data_row:has(.o_field_char)').index(), 40, "should display the create line at the last position");

        form.$('.o_data_row input:first').val('value 3').trigger('input');
        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_data_row').length, 42, "should display 42 records and the create line");
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
            arch:'<form>' +
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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "there should be one record in the relation");

        // change the value of foo to trigger the onchange
        form.$('.o_field_widget[name=foo]').val('some value').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 3,
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
            arch:'<form>' +
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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "there should be one record in the relation");
        assert.strictEqual(form.$('.o_data_row .o_field_widget[name=partner_ids]').text().replace(/\s/g, ''),
            'secondrecordaaa', "many2many_tags should be correctly displayed");

        // change the value of foo to trigger the onchange
        checkRPC = true; // enable flag to check read RPC for the m2m field
        form.$('.o_field_widget[name=foo]').val('some value').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 3,
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
            arch:'<form>' +
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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "there should be one record in the relation");
        assert.strictEqual(form.$('.ref_field').text().trim(), 'xpad',
            "reference field should be correctly displayed");

        // change the value of foo to trigger the onchange
        checkRPC = true; // enable flag to check read RPC for reference field
        form.$('.o_field_widget[name=foo]').val('some value').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 3,
            "there should be three records in the relation");
        assert.strictEqual(form.$('.ref_field').text().trim(), 'xpadxphone',
            "reference fields should be correctly displayed");

        form.destroy();
    });

    QUnit.test('onchange on one2many containing x2many in form view', function (assert) {
        assert.expect(16);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.turtles = [[0, false, {turtle_foo: 'new record'}]];
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form>' +
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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "the onchange should have created one record in the relation");

        // open the created o2m record in a form view, and add a m2m subrecord
        // in its relation
        form.$('.o_data_row').click();

        assert.strictEqual($('.modal').length, 1, "should have opened a dialog");
        assert.strictEqual($('.modal .o_data_row').length, 0,
            "there should be no record in the one2many in the dialog");

        // add a many2many subrecord
        $('.modal .o_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal').length, 2,
            "should have opened a second dialog");

        // select a many2many subrecord
        $('.modal:nth(1) .o_list_view .o_data_cell:first').click();

        assert.strictEqual($('.modal').length, 1,
            "second dialog should be closed");
        assert.strictEqual($('.modal .o_data_row').length, 1,
            "there should be one record in the one2many in the dialog");
        assert.notOk($('.modal .o_x2m_control_panel .o_cp_pager div').is(':visible'),
            'm2m pager should be hidden');

        // click on 'Save & Close'
        $('.modal .modal-footer .btn-primary:first').click();

        assert.strictEqual($('.modal').length, 0, "dialog should be closed");

        // reopen o2m record, and another m2m subrecord in its relation, but
        // discard the changes
        form.$('.o_data_row').click();

        assert.strictEqual($('.modal').length, 1, "should have opened a dialog");
        assert.strictEqual($('.modal .o_data_row').length, 1,
            "there should be one record in the one2many in the dialog");

        // add another m2m subrecord
        $('.modal .o_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal').length, 2,
            "should have opened a second dialog");

        $('.modal:nth(1) .o_list_view .o_data_cell:first').click();

        assert.strictEqual($('.modal').length, 1,
            "second dialog should be closed");
        assert.strictEqual($('.modal .o_data_row').length, 2,
            "there should be two records in the one2many in the dialog");

        // click on 'Discard'
        $('.modal .modal-footer .btn-default').click();

        assert.strictEqual($('.modal').length, 0, "dialog should be closed");

        // reopen o2m record to check that second changes have properly been discarded
        form.$('.o_data_row').click();

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
            arch:'<form string="Partners">' +
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

        testUtils.intercept(form, "field_changed", function (event) {
            assert.step(form.model.get(event.data.changes.turtles.id).res_id);
        }, true);

        form.$buttons.find('.o_form_button_edit').click();

        var steps = [];
        var positions = [
            [6, 0, 'top', [3, 6, 1, 2, 5, 7, 4]], // move the last to the first line
            [5, 1, 'top', [7, 6, 1, 2, 5]], // move the penultimate to the second line
            [2, 5, 'center', [1, 2, 5, 6]], // move the third to the penultimate line
        ];
        function dragAndDrop() {
            var pos = positions.shift();

            testUtils.dragAndDrop(
                form.$('.ui-sortable-handle').eq(pos[0]),
                form.$('tbody tr').eq(pos[1]),
                {position: pos[2]}
            );

            steps = steps.concat(pos[3]);
            assert.verifySteps(steps,
                "sequences values should be apply from the begin index to the drop index");

            if (positions.length) {

                setTimeout(dragAndDrop, 10);

            } else {

                assert.deepEqual(_.pluck(form.model.get(form.handle).data.turtles.data, 'data'), [
                    {  id: 3,  turtle_foo: "kawa",  turtle_int: 2 },
                    {  id: 7,  turtle_foo: "a4",  turtle_int: 3 },
                    {  id: 1,  turtle_foo: "yop",  turtle_int: 4 },
                    {  id: 2,  turtle_foo: "blip",  turtle_int: 5 },
                    {  id: 5,  turtle_foo: "a2",  turtle_int: 6 },
                    {  id: 6,  turtle_foo: "a3",  turtle_int: 7 },
                    {  id: 4,  turtle_foo: "a1",  turtle_int: 8 }
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
            arch:'<form string="Partners">' +
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

        testUtils.intercept(form, "field_changed", function (event) {
            assert.step(event.data.changes.p.data.int_field.toString());
        }, true);

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "My little Foo Valueblipyop",
            "should have the 3 rows in the correct order");

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "My little Foo Valueblipyop",
            "should still have the 3 rows in the correct order");

        // Drag and drop the second line in first position
        testUtils.dragAndDrop(
            form.$('.ui-sortable-handle').eq(1),
            form.$('tbody tr').first(),
            {position: 'top'}
        );

        assert.verifySteps(["0", "1"],
            "sequences values should be incremental starting from the previous minimum one");

        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipMy little Foo Valueyop",
            "should have the 3 rows in the new order");

        form.$('tbody tr:first td:first').click();

        assert.strictEqual(form.$('tbody tr:first td.o_data_cell:not(.o_handle_cell) input').val(), "blip",
            "should edit the correct row");

        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('td.o_data_cell:not(.o_handle_cell)').text(), "blipMy little Foo Valueyop",
            "should still have the 3 rows in the new order");

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
                                        '<a t-if="!read_only_mode" type="delete" class="fa fa-times pull-right delete_icon"/>' +
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
                    switch(saveCount) {
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
                                [0, args.args[1].p[43][1], {display_name: 'new record page 1'}],
                                "should sent correct CREATE command");
                            assert.deepEqual(args.args[1].p[44],
                                [0, args.args[1].p[44][1], {display_name: 'new record page 2'}],
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o-kanban-button-new').click();
        $('.modal input').val('new record').trigger('input');
        $('.modal .modal-footer .btn-primary:first').click(); // save and close
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
        form.$buttons.find('.o_form_button_save').click();

        // delete a record on page one
        checkRead = true;
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 10)').length,
            1, 'first record should be the one with id 10 (next checks rely on that)');
        form.$('.delete_icon:first').click();
        // checks
        assert.deepEqual(readIDs, [50],
            "should have read a record (to display 40 records on page 1)");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'there should be 40 records on page 1');
        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '1-40 / 45', "pager range should be correct");
        // save
        form.$buttons.find('.o_form_button_save').click();

        // add and delete records in both pages
        form.$buttons.find('.o_form_button_edit').click();
        checkRead = true;
        readIDs = undefined;
        // add and delete a record in page 1
        form.$('.o-kanban-button-new').click();
        $('.modal input').val('new record page 1').trigger('input');
        $('.modal .modal-footer .btn-primary:first').click(); // save and close
        assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 11)').length,
            1, 'first record should be the one with id 11 (next checks rely on that)');
        form.$('.delete_icon:first').click();
        assert.deepEqual(readIDs, [51],
            "should have read a record (to display 40 records on page 1)");
        // add and delete a record in page 2
        form.$('.o_x2m_control_panel .o_pager_next').click();
        assert.strictEqual(form.$('.o_kanban_record:first span:contains(relational record 52)').length,
            1, 'first record should be the one with id 52 (next checks rely on that)');
        checkRead = true;
        readIDs = undefined;
        form.$('.delete_icon:first').click();
        form.$('.o-kanban-button-new').click();
        $('.modal input').val('new record page 2').trigger('input');
        $('.modal .modal-footer .btn-primary:first').click(); // save and close
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
        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('edition of one2many field, with onchange and not inline sub view', function (assert) {
        assert.expect(2);

        this.data.turtle.onchanges.turtle_int = function (obj) {
            obj.turtle_foo = String(obj.turtle_int);
        };
        this.data.partner.onchanges.turtles = function () {};

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        $('input[name="turtle_int"]').val('5').trigger('input');
        $('.modal-footer button.btn-primary').first().click();
        assert.strictEqual(form.$('tbody tr:eq(1) td.o_data_cell').text(), '5',
            'should display 5 in the foo field');
        form.$('tbody tr:eq(1) td.o_data_cell').click();

        $('input[name="turtle_int"]').val('3').trigger('input');
        $('.modal-footer button.btn-primary').first().click();
        assert.strictEqual(form.$('tbody tr:eq(1) td.o_data_cell').text(), '3',
            'should now display 3 in the foo field');
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

    QUnit.test('one2many list: unlink one record', function (assert) {
        assert.expect(5);
        this.data.partner.records[0].p = [2, 4];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.strictEqual(commands.length, 2,
                        'should have generated two commands');
                    assert.ok(commands[0][0] === 4 && commands[0][1] === 4,
                        'should have generated the command 4 (LINK_TO) with id 4');
                    assert.ok(commands[1][0] === 3 && commands[1][1] === 2,
                        'should have generated the command 3 (UNLINK) with id 2');
                }
                return this._super.apply(this, arguments);
            },
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('td.o_list_record_delete button').length, 2,
            "should have 2 delete buttons");

        form.$('td.o_list_record_delete button').first().click();

        assert.strictEqual(form.$('td.o_list_record_delete button').length, 1,
            "should have 1 delete button (a record is supposed to have been unlinked)");

        // save and check that the correct command has been generated
        form.$buttons.find('.o_form_button_save').click();
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

        assert.strictEqual(form.$('td.o_list_record_delete button').length, 2,
            "should have 2 delete buttons");

        form.$('td.o_list_record_delete button').first().click();

        assert.strictEqual(form.$('td.o_list_record_delete button').length, 1,
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

    QUnit.test('editable one2many list, pager is updated', function (assert) {
        assert.expect(1);

        this.data.turtle.records.push({id:4, turtle_foo: 'stephen hawking'});
        this.data.partner.records[0].turtles = [1,2,3,4];

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$el.click();

        assert.strictEqual(form.$('.o_cp_pager').text().trim(), '1-3 / 5',
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

    QUnit.test('editable one2many list, adding line when only one page', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].turtles=[1,2,3];
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        // the record currently being added should not count in the pager
        assert.ok(!form.$('.o_cp_pager').is(':visible'),
            "pager should not be visible");
        form.destroy();
    });

    QUnit.test('editable one2many list, adding line, then discarding', function (assert) {
        assert.expect(1);

        this.data.turtle.records.push({id:4, turtle_foo: 'stephen hawking'});
        this.data.partner.records[0].turtles = [1,2,3,4];

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$buttons.find('.o_form_button_cancel').click();

        // confirm the discard operation
        $('.modal .modal-footer .btn-primary').click(); // click on confirm

        assert.strictEqual(form.$('.o_cp_pager').text().trim(), '1-3 / 4',
            "pager should still be visible");
        form.destroy();
    });

    QUnit.test('editable one2many list, required field and pager', function (assert) {
        assert.expect(1);

        this.data.turtle.records.push({id:4, turtle_foo: 'stephen hawking'});
        this.data.turtle.fields.turtle_foo.required = true;
        this.data.partner.records[0].turtles = [1,2,3,4];

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        // go on next page. The new record is not valid and should be discarded
        form.$('.o_pager_next').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "should have 1 data rows");

        form.destroy();
    });

    QUnit.test('editable one2many list, required field, pager and confirm discard', function (assert) {
        assert.expect(3);

        this.data.turtle.records.push({id:4, turtle_foo: 'stephen hawking'});
        this.data.turtle.fields.turtle_foo.required = true;
        this.data.partner.records[0].turtles = [1,2,3,4];

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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="turtle_int"]').val(4321).trigger('input');

        // go to next page. The new record is not valid, but dirty. we should
        // see a confirm dialog
        form.$('.o_pager_next').click();

        assert.strictEqual(form.$('.o_cp_pager').text().trim(), '1-3 / 4',
            "pager should still display the correct total");

        // click on cancel
        $('.modal .modal-footer .btn-default').click(); // click on cancel

        assert.strictEqual(form.$('.o_cp_pager').text().trim(), '1-3 / 4',
            "pager should again display the correct total");
        assert.strictEqual(form.$('.o_field_one2many input.o_field_invalid').length, 1,
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_x2many_list_row_add a').click();

        // go on next page
        form.$('.o_pager_next').click();

        // discard
        form.$buttons.find('.o_form_button_cancel').click();
        $('.modal .modal-footer .btn-primary').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "should have 1 data row");
        assert.ok(!form.$('.o_cp_pager').is(':visible'),
            "pager should not be visible");

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

    QUnit.test('pressing enter in a o2m with a required empty m2o', function (assert) {
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="turtle_foo"]').trigger($.Event('keydown', {
            which: $.ui.keyCode.ENTER,
            keyCode: $.ui.keyCode.ENTER,
        }));
        assert.ok(form.$('input[name="turtle_foo"]').hasClass('o_field_invalid'),
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "there should be one data row");

        form.$('input[name="turtle_foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 1,
            "there should be one data row");

        form.$('input[name="turtle_foo"]').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
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

        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal .o_field_x2many_list_row_add a').click();

        assert.strictEqual($('.modal .o_data_row.o_selected_row').length, 1,
            "there should be a row in edition in the dialog");

        // trigger keydown ESCAPE in the edited row
        $('.modal .o_data_cell input').trigger({type: 'keydown', which: $.ui.keyCode.ESCAPE});

        assert.strictEqual($('.modal').length, 1,
            "dialog should still be open");
        assert.strictEqual($('.modal .o_data_row').length, 0,
            "the row should have been removed");

        form.destroy();
    });

    QUnit.test('editable o2m with onchange and required field: delete an invalid line', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges = {
            turtles: function () {},
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

        form.$('.o_data_cell:first').click();
        form.$('.o_field_widget[name="product_id"] input').val('').trigger('keyup');
        assert.verifySteps(['read', 'read'], 'no onchange should be done as line is invalid');
        form.$('.o_list_record_delete').click();
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

    QUnit.test('one2many and default_get (with date)', function (assert) {
        assert.expect(1);

        this.data.partner.fields.p.default = [
            [0, false, {date: '2017-10-08'}],
        ];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        assert.expect(7);

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
        $('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Month selection
        $('.bootstrap-datetimepicker-widget .picker-switch').first().click();  // Year selection
        $('.bootstrap-datetimepicker-widget .year:contains(2017)').click();
        $('.bootstrap-datetimepicker-widget .month').eq(1).click();  // February
        $('.day:contains(22)').click(); // select the 22 February

        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps(['read', 'read', 'onchange', 'write', 'read', 'read']);
        form.destroy();
    });

    QUnit.test('one2many and onchange (with command DELETE_ALL)', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.p = [[5]];
            },
            p: function () {}, // dummy onchange on the o2m to execute _isX2ManyValid()
        };
        this.data.partner.records[0].p = [2];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                        [0, args.args[1].p[0][1], {display_name: 'z'}],
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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "o2m should contain one row");

        // empty o2m by triggering the onchange
        form.$('.o_field_widget[name=foo]').val('trigger onchange').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 0,
            "rows of the o2m should have been deleted");

        // add two new subrecords
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_widget[name=display_name]').val('x').trigger('input');
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_widget[name=display_name]').val('y').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 2,
            "o2m should contain two rows");

        // empty o2m by triggering the onchange
        form.$('.o_field_widget[name=foo]').val('trigger onchange again').trigger('input');

        assert.strictEqual(form.$('.o_data_row').length, 0,
            "rows of the o2m should have been deleted");

        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_widget[name=display_name]').val('z').trigger('input');

        form.$buttons.find('.o_form_button_save').click();
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
            arch:'<form string="Partners">' +
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
                        [1, 3, {display_name: 'coucou', turtle_foo: 'has changed', turtle_int: 42}],
                    ], "correct commands should be sent (only send changed values)");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "o2m should contain one row");

        form.$('.o_field_one2many .o_list_view tbody tr:first td:first').click();
        form.$('.o_field_one2many .o_list_view tbody tr:first input:first').val('blurp').trigger('input');

        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
    });

    QUnit.test('one2many with CREATE onchanges correctly refreshed', function (assert) {
        assert.expect(5);

        var delta = 0;
        testUtils.patch(AbstractField, {
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
            arch:'<form string="Partners">' +
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

        assert.strictEqual(form.$('.o_data_row').length, 0,
            "o2m shouldn't contain any row");

        form.$('.o_field_x2many_list_row_add a').click();
        // trigger the first onchange
        deactiveOnchange = false;
        form.$('input[name="turtle_int"]').val('10').trigger('input');
        // put the list back in non edit mode
        form.$('input[name="foo"]').click();
        assert.strictEqual(form.$('.o_data_row').text(), "first10second-10",
            "should correctly refresh the records");

        // trigger the second onchange
        form.$('.o_field_x2many_list tbody tr:first td:first').click();
        form.$('input[name="turtle_int"]').val('20').trigger('input');

        form.$('input[name="foo"]').click();
        assert.strictEqual(form.$('.o_data_row').text(), "first20second-20",
            "should correctly refresh the records");

        assert.strictEqual(form.$('.o_field_widget').length, delta,
            "all (non visible) field widgets should have been destroyed");

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_data_row').text(), "first20second-20",
            "should correctly refresh the records after save");

        form.destroy();
        testUtils.unpatch(AbstractField);
    });

    QUnit.test('editable one2many with sub widgets are rendered in readonly', function (assert) {
        assert.expect(2);

        var editableWidgets = 0;
        testUtils.patch(AbstractField, {
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
            arch:'<form string="Partners">' +
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
        form.$('tbody td.o_field_x2many_list_row_add a').click();

        assert.strictEqual(editableWidgets, 3,
            "3 widgets currently in edit mode");

        form.destroy();
        testUtils.unpatch(AbstractField);
    });

    QUnit.test('one2many editable list with onchange keeps the order', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].p = [1, 2, 4];
        this.data.partner.onchanges = {
            p: function () {},
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_data_row:first .o_data_cell').click();
        form.$('.o_selected_row .o_field_widget[name=display_name]').val('new').trigger('input');
        form.$el.click(); // click outside to validate the row

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
                    assert.deepEqual(args.args[1].p, [[4, 2, false], [0, args.args[1].p[1][1], {product_id: 41}]],
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
                    assert.deepEqual(args.args[1].p, [[0, args.args[1].p[0][1], {
                        foo: false, int_field: 123, product_id: 41,
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_widget[name=product_id] input').click();

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
                        [[4, 2, false], [0, args.kwargs.context.turtles[1][1], {turtle_foo: 'hammer'}]];
                    assert.deepEqual(args.kwargs.context.turtles, expected,
                        "should have properly evaluated turtles key in context");
                    counter++;
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="turtle_foo"]').val('hammer').trigger('input');
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
        assert.strictEqual(form.$('.o_data_row').text(), "blip1.59yop1.50tototo1.550xphone",
            "should display the record values in one2many list");

        $('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('one2many with many2many widget: edition', function (assert) {
        assert.expect(7);

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
        assert.strictEqual($('.modal .modal-title').first().text().trim(), 'Open: one2many turtle field',
            "modal should use the python field string as title");
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
        assert.expect(6);

        this.data.turtle.onchanges = {turtle_bar: function () {}};
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

        form.$buttons.find('.o_form_button_edit').click();
        form.$('tbody td.o_field_x2many_list_row_add a').click();
        assert.verifySteps(['default_get', 'onchange', 'default_get', 'onchange']);
        form.destroy();
    });

    QUnit.test('id in one2many obtained in onchange is properly set', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges.turtles = function (obj) {
            obj.turtles = [
                [5],
                [1, 3, {turtle_foo: "kawa"}]
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
                        [[0, virtualID, {turtle_foo: "cat"}]],
                        'should send proper commands');
                }
                return this._super.apply(this, arguments);
            },
        });
        form.$('td.o_field_x2many_list_row_add a').click();
        form.$('td input[name="turtle_foo"]').val('cat').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

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

        form.$('.oe_kanban_action_button').click();

        form.destroy();
    });

    QUnit.test('one2many kanban with edit type action and domain widget (widget using SpecialData)', function (assert) {
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

        form.$('.oe_kanban_action:eq(0)').click();
        assert.strictEqual($('.o_domain_selector').length, 1, "should add domain selector widget");
        form.destroy();
    });

    QUnit.test('one2many list with onchange and domain widget (widget using SpecialData)', function (assert) {
        assert.expect(3);

        this.data.turtle.fields.model_name = {string: "Domain Condition Model", type: "char"};
        this.data.turtle.fields.condition = {string: "Domain Condition", type: "char"};
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

        form.$('.o_field_one2many .o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal').length, 1, "form view dialog should be opened");
        $('.modal-body input[name="model_name"]').val('partner').trigger('input');
        $('.modal-footer button:first').click();

        assert.strictEqual(form.$('.o_field_one2many tbody tr:first').text(), "coucouhas changed[]",
            "the onchange should create one new record and remove the existing");

        form.$('.o_field_one2many .o_list_view tbody tr:eq(0) td:first').click();

        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(nbFetchSpecialDomain, 1,
            "should only fetch special domain once");
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

    QUnit.test('many2manytag in one2many, onchange, some modifiers, and more than one page', function (assert) {
        assert.expect(9);

        this.data.partner.records[0].turtles = [1,2,3];

        this.data.partner.onchanges.turtles = function () {};

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
            viewOptions: {mode: 'edit'},
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(form.$('.o_data_row').length, 2,
            'there should be only 2 rows displayed');
        form.$('.o_list_record_delete').click();
        form.$('.o_list_record_delete').click();

        assert.strictEqual(form.$('.o_data_row').length, 1,
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
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="display_name"]').val('first').trigger('input');
        form.$('div[name="product_id"] input').click();
        // the onchange won't be generated
        $('li.ui-menu-item a:contains(xpad)').trigger('mouseenter').click();

        assert.strictEqual(form.$('.o_field_many2manytags.o_input').length, 1,
            'should display the line in editable mode');
        assert.strictEqual(form.$('.o_field_many2one input').val(), "xpad",
            'should display the product xpad');
        assert.strictEqual(form.$('.o_field_many2manytags.o_input .o_badge_text').text(), "first record",
            'should display the tag from the onchange');

        form.$('input.o_field_integer[name="int_field"]').click();

        assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xpad",
            'should display the product xpad');
        assert.strictEqual(form.$('.o_field_many2manytags:not(.o_input) .o_badge_text').text(), "first record",
            'should display the tag in readonly');

        // enable the many2many onchange and generate it
        form.$('input.o_field_integer[name="int_field"]').val('10').trigger('input');

        assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xenomorphexphone",
            'should display the product xphone and xenomorphe');
        assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
            'should display the name, one2many and many2many value');

        // disable the many2many onchange
        form.$('input.o_field_integer[name="int_field"]').val('0').trigger('input');

        // delete and start over
        form.$('.o_list_record_delete:first button').click();
        form.$('.o_list_record_delete:first button').click();

        // enable the many2many onchange
        form.$('input.o_field_integer[name="int_field"]').val('10').trigger('input');

        // add new line (first, xenomorphe)
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="display_name"]').val('first').trigger('input');
        form.$('div[name="product_id"] input').click();
        // generate the onchange
        $('li.ui-menu-item a:contains(xenomorphe)').trigger('mouseenter').click();

        assert.strictEqual(form.$('.o_field_many2manytags.o_input').length, 1,
            'should display the line in editable mode');
        assert.strictEqual(form.$('.o_field_many2one input').val(), "xenomorphe",
            'should display the product xenomorphe');
        assert.strictEqual(form.$('.o_field_many2manytags.o_input .o_badge_text').text(), "second record",
            'should display the tag from the onchange');

        // put list in readonly mode
        form.$('input.o_field_integer[name="int_field"]').click();

        assert.strictEqual(form.$('.o_data_cell.o_required_modifier').text(), "xenomorphexphone",
            'should display the product xphone and xenomorphe');
        assert.strictEqual(form.$('.o_field_many2manytags:not(.o_input) .o_badge_text').text(), "second recordfirst record",
            'should display the tag in readonly (first record and second record)');

        form.$('input.o_field_integer[name="int_field"]').val('10').trigger('input');

        assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
            'should display the name, one2many and many2many value');

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_data_row').text().replace(/\s+/g, ' '), "firstxenomorphe second record new linexphone first record ",
            'should display the name, one2many and many2many value after save');

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

    QUnit.test('one2many with x2many in form view (but not in list view)', function (assert) {
        assert.expect(1);

        // avoid error when saving the edited related record (because the
        // related x2m field is unknown in the inline list view)
        // also ensure that the changes are correctly saved

        this.data.turtle.fields.o2m = {string: "o2m", type: "one2many", relation: 'user'};

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

        form.$('.o_data_row:first').click(); // edit first record

        var $input = $('.modal .o_field_many2manytags input');
        $input.click(); // opens the dropdown
        $input.autocomplete('widget').find('li').click(); // add 'first record'

        // add a many2many tag and save
        $('.modal .o_field_x2many_list_row_add a').click();
        $('.modal .o_field_widget[name=name]').val('test').trigger('input');
        $('.modal .modal-footer .btn-primary').click(); // save

        form.$buttons.find('.o_form_button_save').click();

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
                    assert.deepEqual(args.args[1].timmy, [[6,  false, [12]]],
                        'should properly write ids')
                }
                return this._super.apply(this, arguments);
            },
        });

        // edit the first partner in the one2many partner form view
        form.$('.o_data_row:first td.o_data_cell').click();
        // open form view for many2one
        form.$('.o_external_button').click();

        // click on add, to add a new partner in the m2m
        $('.modal .o_field_x2many_list_row_add a').click();

        // select the partner_type 'gold' (this closes the 2nd modal)
        $('.modal td:contains(gold)').click();

        // confirm the changes in the modal
        $('.modal .modal-footer .btn-primary').click();

        form.$buttons.find('.o_form_button_save').click();
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
                            [0, 0, {partner_ids: [[6, 0, [4]]]}],
                            [0, 0, {partner_ids: [[6, 0, [1]]]}],
                        ],
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_list_view .o_data_row').length, 2,
            "one2many list should contain 2 rows");
        assert.strictEqual(form.$('.o_list_view .o_field_many2manytags[name="partner_ids"] .badge').length, 2,
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
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
            "int_field should start with value 10");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
            "int_field should still be 10 (no onchange, because line is not valid)");

        // fill turtle_foo field
        form.$('.o_field_widget[name="turtle_foo"]').val("some text").trigger('input');

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
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
            "int_field should start with value 10");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_field_widget[name="int_field"]').val(), "10",
            "int_field should still be 10 (no onchange, because line is not valid)");

        // fill turtle_int field
        form.$('.o_field_widget[name="turtle_int"]').val("1").trigger('input');

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
            turtle_trululu: function () {},
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
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should have created the first row immediately");
        def = $.Deferred();
        form.$('.o_field_many2one input').click();
        form.$('.o_field_many2one input').autocomplete('widget').find('a').first().click();

        // try to add a second line and check that it is correctly waiting
        // for the onchange to return
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal').length, 0, "no modal should be displayed");
        assert.strictEqual($('.o_field_invalid').length, 0,
            "no field should be marked as invalid");
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should wait for the onchange to create the second row");
        assert.ok(form.$('.o_data_row').hasClass('o_selected_row'),
            "first row should still be in edition");

        // resolve the onchange def
        def.resolve();
        assert.strictEqual(form.$('.o_data_row').length, 2,
            "second row should now have been created");
        assert.notOk(form.$('.o_data_row:first').hasClass('o_selected_row'),
            "first row should no more be in edition");

        form.destroy();
    });

    QUnit.test('editable list: multiple clicks on Add an item do not create invalid rows', function (assert) {
        assert.expect(3);

        this.data.turtle.onchanges = {
            turtle_trululu: function () {},
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
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_data_row').length, 0,
            "no row should have been created yet (waiting for the onchange)");

        // resolve the onchange def
        def.resolve();
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "only one row should have been created");
        assert.ok(form.$('.o_data_row:first').hasClass('o_selected_row'),
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
                obj.turtles = [[5], [0, 0, {display_name: 'new'}]];
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
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_data_row .o_field_widget').val('a name').trigger('input');
        def = $.Deferred();
        form.$('.o_datepicker_input').click(); // focusout o2m and set value to today
        var dateTimeVal = fieldUtils.format.datetime(moment(), {timezone: false});
        form.$('.o_datepicker_input').val(dateTimeVal).trigger('change');

        // resolve the onchange def
        def.resolve();

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "should have one record in the o2m");
        assert.strictEqual(form.$('.o_data_row .o_data_cell').text(), 'new',
            "should be the record created by the onchange");

        form.destroy();
    });

    QUnit.test('editable list: onchange that returns a warning', function (assert) {
        assert.expect(5);

        this.data.turtle.onchanges = {
            display_name: function () {},
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
        form.$('.o_field_x2many_list_row_add a').click();

        // check if 'Add an item' still works (this should trigger an onchange
        // and a warning again)
        form.$('.o_field_x2many_list_row_add a').click();

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
                user_context: {someKey: 'some value'},
            },
            viewOptions: {
                mode: 'edit',
                context: {active_field: 2},
            },
            res_id: 1,
        });

        form.$('.o_data_cell:first').click();
        form.$('.o_field_widget[name=display_name]').val('abc').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

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

        form.$('input[name="foo"]').val('abcd').trigger('input');
        assert.verifySteps(['read', 'onchange']);

        form.destroy();
    });

    QUnit.test('one2many: onchange that returns unknow field in list, but not in form', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges = {
            name: function () {},
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
                            p: [[5], [0, 0, {display_name: 'new', timmy: [[5], [4, 12]]}]],
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "the one2many should contain one row");
        assert.strictEqual(form.$('.o_field_widget[name="timmy"]').length, 0,
            "timmy should not be displayed in the list view");

        form.$('.o_data_row td:first').click(); // open the record

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
            turtles: function (obj) {}
        };
        this.data.turtle.fields.turtle_foo.required = true;
        this.data.partner.records[0].turtles = [];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
        form.$buttons.find('.o_form_button_edit').click();

        // triggers an onchange on partner, because the new record is valid
        form.$('.o_field_x2many_list_row_add a').click();

        assert.verifySteps(['read', 'default_get', 'onchange']);
        form.destroy();
    });

    QUnit.test('onchange on a one2many containing a one2many', function (assert) {
        // the purpose of this test is to ensure that the onchange specs are
        // correctly and recursively computed
        assert.expect(1);

        this.data.partner.onchanges = {
            p: function () {}
        };
        var checkOnchange = false;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal .o_field_x2many_list_row_add a').click();
        $('.modal .o_data_cell input').val('new record').trigger('input');
        checkOnchange = true;
        $('.modal .modal-footer .btn-primary').click(); // save (should trigger the onchange)

        form.destroy();
    });

    QUnit.test('editing tabbed one2many (editable=bottom)', function (assert) {
        assert.expect(12);

        this.data.partner.records[0].turtles = [];
        for (var i = 0; i < 42; i++) {
            var id = 100 + i;
            this.data.turtle.records.push({id: id, turtle_foo: 'turtle' + (id-99)});
            this.data.partner.records[0].turtles.push(id);
        }

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.deepEqual(args.args[1].turtles[40][2], {turtle_foo: 'rainbow dash'});
                }
                return this._super.apply(this, arguments);
            },
        });


        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 41,
            "should have 41 data rows on the current page");
        assert.ok(form.$('tr.o_data_row').last().hasClass('o_selected_row'),
            "last row should be selected");

        form.$('.o_data_row input[name="turtle_foo"]').val('rainbow dash').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 40,
        "should have 40 data rows on the current page");

        assert.verifySteps(['read', 'read', 'default_get', 'write', 'read', 'read']);
        form.destroy();
    });

    QUnit.test('editing tabbed one2many (editable=bottom), again...', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].turtles = [];
        for (var i = 0; i < 9; i++) {
            var id = 100 + i;
            this.data.turtle.records.push({id: id, turtle_foo: 'turtle' + (id-99)});
            this.data.partner.records[0].turtles.push(id);
        }

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree editable="bottom" limit="3">' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });


        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_data_row input[name="turtle_foo"]').val('rainbow dash').trigger('input');
        form.$('.o_x2m_control_panel .o_pager_next').click();
        form.$('.o_x2m_control_panel .o_pager_next').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 3,
            "should have 3 data rows on the current page");
        form.destroy();
    });

    QUnit.test('editing tabbed one2many (editable=top)', function (assert) {
        assert.expect(15);

        this.data.partner.records[0].turtles = [];
        this.data.turtle.fields.turtle_foo.default = "default foo";
        for (var i = 0; i < 42; i++) {
            var id = 100 + i;
            this.data.turtle.records.push({id: id, turtle_foo: 'turtle' + (id-99)});
            this.data.partner.records[0].turtles.push(id);
        }

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    assert.deepEqual(args.args[1].turtles[40][2], {turtle_foo: 'rainbow dash'});
                }
                return this._super.apply(this, arguments);
            },
        });


        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_pager_next').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 2,
            "should have 2 data rows on the current page");

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 3,
            "should have 3 data rows on the current page (2 records and the created line)");

        assert.ok(form.$('tr.o_data_row').first().hasClass('o_selected_row'),
            "first row should be selected");

        assert.strictEqual(form.$('tr.o_data_row input').val(), 'default foo',
            "selected input should have correct string");

        form.$('.o_data_row input[name="turtle_foo"]').val('rainbow dash').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('tr.o_data_row').length, 40,
            "should have 40 data rows on the current page");

        assert.verifySteps(['read', 'read', 'read', 'default_get', 'write', 'read', 'read']);
        form.destroy();
    });

    QUnit.test('one2many field: change value before pending onchange returns', function (assert) {
        var done = assert.async();
        assert.expect(2);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        this.data.partner.onchanges = {
            int_field: function () {}
        };
        var def;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_field_x2many_list_row_add a').click();
        def = $.Deferred();
        form.$('.o_field_widget[name=int_field]')
            .val('44')
            .trigger('input');

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
            int_field: function () {}
        };
        var def;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_field_x2many_list_row_add a').click();
        def = $.Deferred();
        form.$('.o_field_widget[name=int_field]')
            .val('44')
            .trigger('input')
            .trigger({type: 'keydown', which: $.ui.keyCode.TAB});
        def.resolve();

        assert.strictEqual(document.activeElement, form.$('.o_field_widget[name=qux]')[0],
            "qux field should have the focus");

        form.$('.o_field_many2one input').click();
        form.$('.o_field_many2one input').autocomplete('widget').find('a').first().click();
        assert.strictEqual(form.$('.o_field_many2one input').val(), 'first record',
            "the one2many field should have the expected value");

        form.destroy();
    });

    QUnit.test('checkbox in an x2many that triggers an onchange', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges = {
            bar: function () {}
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

        form.$('.o_field_x2many_list_row_add a').click();

        form.$('.o_field_widget[name=bar] input').click();
        assert.notOk(form.$('.o_field_widget[name=bar] input').prop('checked'),
            "the checkbox should be unticked");

        form.destroy();
    });

    QUnit.test('one2many with default value: edit line to make it invalid', function (assert) {
        assert.expect(3);

        this.data.partner.fields.p.default = [
            [0, false, {foo: "coucou", int_field: 5}],
        ];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="foo"/>' +
                            '<field name="int_field"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        });

        // edit the line and enter an invalid value for int_field
        form.$('.o_data_row .o_data_cell:nth(1)').click();
        form.$('.o_field_widget[name=int_field]').val('e').trigger('input');
        form.$el.click(); // try to validate the line

        assert.strictEqual(form.$('.o_data_row.o_selected_row').length, 1,
            "line should not have been removed and should still be in edition");
        assert.strictEqual($('.modal').length, 1,
            "a confirmation dialog should be opened");
        assert.ok(form.$('.o_field_widget[name=int_field]').hasClass('o_field_invalid'),
            "should indicate that int_field is invalid");

        form.destroy();
    });

    QUnit.test('default value for nested one2manys (coming from onchange)', function (assert) {
        assert.expect(3);

        this.data.partner.onchanges.p = function (obj) {
            obj.p = [
                [5],
                [0, 0, {turtles: [[5], [4, 1]]}], // link record 1 by default
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
                    assert.deepEqual(args.args[0].p[0][2], {turtles: [[4, 1, false]]},
                        "should send the correct values");
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_data_cell').text(), '1 record',
            "should correctly display the value of the inner o2m");

        form.$buttons.find('.o_form_button_save').click();

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
                    assert.deepEqual(args.args[1].turtles[0], [1,2,{turtle_foo: 'foo'}],
                        'should send the "good" value');
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {mode: 'edit'},
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'blip',
            "initial text should be correct");

        // click and edit value to 'foo', which will trigger onchange
        form.$('.o_data_row .o_data_cell:nth(0)').click();
        form.$('.o_field_widget[name=turtle_foo]').val('foo').trigger('input');
        form.$el.click();
        assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'foo',
            "field should have been changed to foo");

        // click and edit value to 'pinky', which trigger a failed onchange
        form.$('.o_data_row .o_data_cell:nth(0)').click();
        form.$('.o_field_widget[name=turtle_foo]').val('pinky').trigger('input');
        form.$el.click();

        assert.strictEqual(form.$('.o_data_row .o_data_cell:nth(0)').text(), 'foo',
            "turtle_foo text should now be set back to foo");

        // we make sure here that when we save, the values are the current
        // values displayed in the field.
        form.$buttons.find('.o_form_button_save').click();

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
            viewOptions: {context: {flutter: 'shy'}},
        });
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input[name="turtle_foo"]').val('pinky pie').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

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
                        turtles: [[5], [0, 0, {display_name: 'test nested'}]],
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
                    assert.deepEqual(args.args[0].p[0][2].turtles[0][2], {display_name: 'test nested'},
                        "should send the correct values");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$('.o_field_widget[name=display_name]').val('trigger onchange').trigger('input');

        assert.strictEqual(form.$('.o_data_cell').text(), 'test',
            "should have added the new row to the one2many");

        // open the new subrecord to check the value of the nested o2m, and to
        // ensure that it will be saved
        form.$('.o_data_cell:first').click();
        assert.strictEqual($('.modal .o_data_cell').text(), 'test nested',
            "should have added the new row to the nested one2many");
        $('.modal .modal-footer .btn-primary').click();

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('one2many with multiple pages and sequence field', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].turtles = [3, 2, 1];
        this.data.partner.onchanges.turtles = function () {};

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    return $.when({value: { turtles: [
                        [5],
                        [1, 1, {turtle_foo: "from onchange", partner_ids: [[5]]}],
                    ]}});
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });
        form.$('button[name="delete"]').first().click();
        assert.strictEqual(form.$('.o_data_row').text(), 'from onchange',
            'onchange has been properly applied');
        form.destroy();
    });

    QUnit.test('one2many with multiple pages and sequence field, part2', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].turtles = [3, 2, 1];
        this.data.partner.onchanges.turtles = function () {};

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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
                    return $.when({value: { turtles: [
                        [5],
                        [1, 1, {turtle_foo: "from onchange id2", partner_ids: [[5]]}],
                        [1, 3, {turtle_foo: "from onchange id3", partner_ids: [[5]]}],
                    ]}});
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });
        form.$('button[name="delete"]').first().click();
        assert.strictEqual(form.$('.o_data_row').text(), 'from onchange id2from onchange id3',
            'onchange has been properly applied');
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
                    var record = _.findWhere(data.turtle.records, {id: id});
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
        form.$('.o_data_cell:first').click();
        form.$('.o_field_widget[name=turtle_int]').val(3).trigger('input');
        form.$el.click(); // leave edition

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
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree limit="2">' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            context: { default_turtles: [1,2,3]},
            viewOptions: {
                mode: 'edit',
            },
        });
        assert.strictEqual(form.$('.o_data_row').text(), 'yopblip',
            'data has been properly loaded');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_data_row').text(), 'yopblip',
            'data has been properly saved');
        form.destroy();
    });

    QUnit.test('add a new line after limit is reached should behave nicely', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].turtles = [1,2,3];

        this.data.partner.onchanges = {
            turtles: function (obj) {
                obj.turtles = [
                    [5],
                    [1, 1, {turtle_foo: "yop"}],
                    [1, 2, {turtle_foo: "blip"}],
                    [1, 3, {turtle_foo: "kawa"}],
                    [0, obj.turtles[3][2], {turtle_foo: "abc"}],
                ];
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
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

        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_data_row').length, 4, 'should have 4 data rows');
        form.$('.o_input[name="turtle_foo"]').val('a').trigger('input');
        assert.strictEqual(form.$('.o_data_row').length, 4,
            'should still have 4 data rows (the limit is increased to 4)');

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

        assert.strictEqual(form.$('.o_data_row').length, 0,
            "there should be no record in the relation");

        // add a new record
        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal .o_field_widget').val('new record').trigger('input');
        $('.modal .modal-footer .btn-primary:first').click(); // Save & Close

        assert.strictEqual(form.$('.o_data_row .o_data_cell').text(), 'new record',
            "should display the new record");

        // reopen freshly added record and edit it
        form.$('.o_data_row .o_data_cell').click();
        $('.modal .o_field_widget').val('new record edited').trigger('input');

        // save it, and choose to directly create another record
        $('.modal .modal-footer .btn-primary:nth(1)').click(); // Save & New

        assert.strictEqual($('.modal').length, 1,
            "the model should still be open");
        assert.strictEqual($('.modal .o_field_widget').text(), '',
            "should have cleared the input");

        $('.modal .o_field_widget').val('another new record').trigger('input');
        $('.modal .modal-footer .btn-primary:first').click(); // Save & Close

        assert.strictEqual(form.$('.o_data_row .o_data_cell').text(),
            'new record editedanother new record', "should display the two records");

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

        assert.strictEqual(form.$('.o_data_row').length, 1,
            "there should be one record in the one2many");
        assert.strictEqual(form.$('.o_data_cell').text(), 'second record',
            "initial display_name of o2m record should be correct");

        // open one2many record in form view
        form.$('.o_data_cell:first').click();
        assert.strictEqual($('.modal .o_form_view').length, 1,
            "should have opened the form view in a dialog");
        assert.strictEqual($('.modal .o_form_view .o_data_row').length, 0,
            "there should be no record in the many2many");

        // click on the action button
        $('.modal .o_form_view button').click();
        assert.strictEqual($('.modal .o_data_row').length, 1,
            "fields in the o2m form view should have been read");
        assert.strictEqual($('.modal .o_data_cell').text(), 'gold',
            "many2many subrecord should have been fetched");

        // save the dialog
        $('.modal .modal-footer .btn-primary').click();

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
                                [1, 2, {'display_name': 'donatello'}],
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
                          '<form>'+
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
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_data_row:eq(1)').click();
        $('.modal .o_field_x2many_list_row_add a').click();
        $('.modal input[name="display_name"]').val('michelangelo').change();
        $('.modal .btn-primary').click();
        // open first partner so changes from previous action are applied
        form.$('.o_data_row:eq(0)').click();
        $('.modal .btn-primary').click();
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(numUserOnchange, 2,
            'there should 2 and only 2 onchange from closing the partner modal');

        form.$('.o_data_row:eq(0)').click();
        assert.strictEqual($('.modal .o_data_row').length, 1,
            'only 1 turtle for first partner');
        assert.strictEqual($('.modal .o_data_row').text(), 'donatello',
            'first partner turtle is donatello');
        $('.modal .o_form_button_cancel').click();

        form.$('.o_data_row:eq(1)').click();
        assert.strictEqual($('.modal .o_data_row').length, 1,
            'only 1 turtle for second partner');
        assert.strictEqual($('.modal .o_data_row').text(), 'michelangelo',
            'second partner turtle is michelangelo');
        $('.modal .o_form_button_cancel').click();

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

    QUnit.test('many2many list: list of id as default value', function (assert) {
        assert.expect(1);

        this.data.partner.fields.turtles.default = [2, 3];
        this.data.partner.fields.turtles.type = "many2many";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree>' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        });

        assert.strictEqual(form.$('td.o_data_cell').text(), "blipkawa",
            "should have loaded default data");

        form.destroy();
    });

    QUnit.test('many2many checkboxes with default values', function (assert) {
        assert.expect(7);

        this.data.partner.fields.turtles.default = [3];
        this.data.partner.fields.turtles.type = "many2many";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles" widget="many2many_checkboxes">' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0].turtles, [[6, false, [1]]],
                        "correct values should have been sent to create");
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.notOk(form.$('.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should not be checked");
        assert.notOk(form.$('.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");
        assert.ok(form.$('.o_checkbox input').eq(2).prop('checked'),
            "third checkbox should be checked");

        form.$('.o_checkbox input:checked').click();  // Uncheck default record
        form.$('.o_checkbox input').first().click();  // Check first record
        form.$('.o_checkbox input').first().click();  // Uncheck first record
        form.$('.o_checkbox input').first().click();  // Recheck first record

        assert.ok(form.$('.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");
        assert.notOk(form.$('.o_checkbox input').eq(2).prop('checked'),
            "third checkbox should not be checked");

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('many2many checkboxes with default values', function (assert) {
        assert.expect(7);

        this.data.partner.fields.turtles.default = [3];
        this.data.partner.fields.turtles.type = "many2many";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles" widget="many2many_checkboxes">' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0].turtles, [[6, false, [1]]],
                        "correct values should have been sent to create");
                }
                return this._super.apply(this, arguments);
            }
        });

        assert.notOk(form.$('.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should not be checked");
        assert.notOk(form.$('.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");
        assert.ok(form.$('.o_checkbox input').eq(2).prop('checked'),
            "third checkbox should be checked");

        form.$('.o_checkbox input:checked').click();  // Uncheck default record
        form.$('.o_checkbox input').first().click();  // Check first record
        form.$('.o_checkbox input').first().click();  // Uncheck first record
        form.$('.o_checkbox input').first().click();  // Recheck first record

        assert.ok(form.$('.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.notOk(form.$('.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");
        assert.notOk(form.$('.o_checkbox input').eq(2).prop('checked'),
            "third checkbox should not be checked");

        form.$buttons.find('.o_form_button_save').click();

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

    QUnit.test('many2many with a domain', function (assert) {
        // The domain specified on the field should not be replaced by the potential
        // domain the user writes in the dialog, they should rather be concatenated
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" domain="[[\'display_name\', \'=\', \'gold\']]"/>' +
                '</form>',
            res_id: 1,
            archs: {
                'partner_type,false,list': '<tree>' +
                        '<field name="display_name"/>' +
                    '</tree>',
                'partner_type,false,search': '<search>' +
                        '<field name="display_name" string="Name"/>' +
                    '</search>',
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal .o_data_row').length, 1,
            "should contain only one row (gold)");

        $('.modal .o_searchview_input').trigger({type: 'keypress', which: 115}); // s
        $('.modal .o_searchview_input').trigger({type: 'keydown', which: 13}); // enter

        assert.strictEqual($('.modal .o_data_row').length, 0, "should contain no row");

        form.destroy();
    });

    QUnit.test('many2many list with onchange and edition of a record', function (assert) {
        assert.expect(7);

        this.data.partner.fields.turtles.type = "many2many";
        this.data.partner.onchanges.turtles = function () {};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="turtles">' +
                        '<tree>' +
                            '<field name="turtle_foo"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            archs: {
                'turtle,false,form': '<form string="Turtle Power"><field name="turtle_bar"/></form>',
            },
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('td.o_data_cell:first').click();

        $('.modal-body input[type="checkbox"]').click();
        $('.modal .modal-footer .btn-primary').first().click();

        // there is nothing left to save -> should not do a 'write' RPC
        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps([
            'read', // read initial record (on partner)
            'read', // read many2many turtles
            'read', // read missing field when opening record in modal form view
            'write', // when saving the modal
            'onchange', // onchange should be triggered on partner
            'read', // reload many2many
        ]);

        form.destroy();
    });

    QUnit.test('onchange with 40+ commands for a many2many', function (assert) {
        // this test ensures that the basic_model correctly handles more LINK_TO
        // commands than the limit of the dataPoint (40 for x2many kanban)
        assert.expect(23);

        // create a lot of partner_types that will be linked by the onchange
        var commands = [[5]];
        for (var i = 0; i < 45; i++) {
            var id = 100 + i;
            this.data.partner_type.records.push({id: id, display_name: "type " + id});
            commands.push([4, id]);
        }
        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.timmy = commands;
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="timmy">' +
                        '<kanban>' +
                            '<field name="display_name"/>' +
                            '<templates>' +
                                '<t t-name="kanban-box">' +
                                    '<div><t t-esc="record.display_name.value"/></div>' +
                                '</t>' +
                            '</templates>' +
                        '</kanban>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].timmy[0][0], 6,
                        "should send a command 6");
                    assert.strictEqual(args.args[1].timmy[0][2].length, 45,
                        "should replace with 45 ids");
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.verifySteps(['read']);

        form.$('.o_field_widget[name=foo]').val('trigger onchange').trigger('input');

        assert.verifySteps(['read', 'onchange', 'read']);
        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '1-40 / 45', "pager should be correct");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'there should be 40 records displayed on page 1');

        form.$('.o_pager_next').click();
        assert.verifySteps(['read', 'onchange', 'read', 'read']);
        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '41-45 / 45', "pager should be correct");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 5,
            'there should be 5 records displayed on page 2');

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '1-40 / 45', "pager should be correct");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'there should be 40 records displayed on page 1');

        form.$('.o_pager_next').click();
        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '41-45 / 45', "pager should be correct");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 5,
            'there should be 5 records displayed on page 2');

        form.$('.o_pager_next').click(); // back to page 1
        assert.strictEqual(form.$('.o_x2m_control_panel .o_pager_counter').text().trim(),
            '1-40 / 45', "pager should be correct");
        assert.strictEqual(form.$('.o_kanban_record:not(".o_kanban_ghost")').length, 40,
            'there should be 40 records displayed on page 1');

        form.destroy();
    });

    QUnit.test('default_get, onchange, onchange on m2m', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges.int_field = function (obj) {
            if (obj.int_field === 2) {
                assert.deepEqual(obj.timmy, [
                    [6, false, [12]],
                    [1, 12, {display_name: 'gold'}]
                ]);
            }
            obj.timmy = [
                [5],
                [1, 12, {display_name: 'gold'}]
            ];
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="timmy">' +
                            '<tree>' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                        '<field name="int_field"/>' +
                    '</sheet>' +
                '</form>',
        });

        form.$('.o_field_widget[name=int_field]').val(2).trigger('input');
        form.destroy();
    });

    QUnit.test('widget many2many_tags', function (assert) {
        assert.expect(1);
        this.data.turtle.records[0].partner_ids = [2];

        var form = createView({
            View: FormView,
            model: 'turtle',
            data: this.data,
            arch:'<form string="Turtles">' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                        '<field name="partner_ids" widget="many2many_tags"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.deepEqual(
            form.$('.o_field_many2manytags.o_field_widget .badge .o_badge_text').attr('title'),
            'second record', 'the title should be filled in'
        );

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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
            config: {device: {isMobile: false}},
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
        assert.expect(18);

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
        assert.strictEqual(form.$('.o_field_widget[name=product_id]').text(), 'xphone',
            "should have rendered the many2one field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=trululu]').text(), '',
            "should have rendered the unset many2one field correctly");
        assert.strictEqual(form.$('.o_field_widget[name=color]').text(), 'Red',
            "should have rendered the selection field correctly");

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

    QUnit.test('unset selection field with 0 as key', function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [[0, "Value O"], [1, "Value 1"]],
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="selection"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget').text(), 'Value O',
            "the displayed value should be 'Value O'");
        assert.notOk(form.$('.o_field_widget').hasClass('o_field_empty'),
            "should not have class o_field_empty");

        form.destroy();
    });

    QUnit.test('unset selection field with string keys', function (assert) {
        // The server doesn't make a distinction between false value (the field
        // is unset), and selection 0, as in that case the value it returns is
        // false. So the client must convert false to value 0 if it exists. In
        // this test, it doesn't exist as keys are strings.
        assert.expect(2);

        this.data.partner.fields.selection = {
            type: "selection",
            selection: [['0', "Value O"], ['1', "Value 1"]],
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="selection"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_widget').text(), '',
            "there should be no displayed value");
        assert.ok(form.$('.o_field_widget').hasClass('o_field_empty'),
            "should have class o_field_empty");

        form.destroy();
    });

    QUnit.test('unset selection on a many2one field', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="trululu" widget="selection"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].trululu, false,
                        "should send 'false' as trululu value");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('select').val("false").trigger('change');
        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('field selection with many2ones and special characters', function (assert) {
        assert.expect(1);

        // edit the partner with id=4
        this.data.partner.records[2].display_name = '<span>hey</span>';
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="trululu" widget="selection"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
        });
        assert.strictEqual(form.$('select option[value="4"]').text(), '<span>hey</span>');

        form.destroy();
    });

    QUnit.test('widget selection on a many2one: domain updated by an onchange', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="int_field"/>' +
                    '<field name="trululu" widget="selection"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    domain = [['id', 'in', [10]]];
                    return $.when({
                        domain: {
                            trululu: domain,
                        }
                    });
                }
                if (args.method === 'name_search') {
                    assert.deepEqual(args.args[1], domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=trululu] option').length, 4,
            "should be 4 options in the selection");

        // trigger an onchange that will update the domain
        form.$('.o_field_widget[name=int_field]').val(2).trigger('input');

        assert.strictEqual(form.$('.o_field_widget[name=trululu] option').length, 1,
            "should be 1 option in the selection");

        form.destroy();
    });

    QUnit.module('FieldMany2ManyTags');

    QUnit.test('fieldmany2many tags with and without color', function (assert) {
        assert.expect(5);

        this.data.partner.fields.partner_ids = {string: "Partner", type: "many2many", relation: 'partner'};
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="partner_ids" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method ==='read' && args.model === 'partner_type') {
                    assert.deepEqual(args.args , [[12], ['display_name']], "should not read any color field");
                } else if (args.method ==='read' && args.model === 'partner') {
                    assert.deepEqual(args.args , [[1], ['display_name', 'color']], "should read color field");
                }
                return this._super.apply(this, arguments);
            }
        });

        // add a tag on field partner_ids
        var $input = form.$('.o_field_many2manytags[name="partner_ids"] input');
        $input.click(); // opens the dropdown
        $input.autocomplete('widget').find('li:first()').click(); // adds a tag

        // add a tag on field timmy
        $input = form.$('.o_field_many2manytags[name="timmy"] input');
        $input.click(); // opens the dropdown
        assert.strictEqual($input.autocomplete('widget').find('li').length, 3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')");
        $input.autocomplete('widget').find('li:first()').click(); // adds a tag
        assert.strictEqual(form.$('.o_field_many2manytags[name="timmy"] > span').length, 1,
            "should contain 1 tag");
        assert.ok(form.$('.o_field_many2manytags[name="timmy"] > span:contains("gold")').length,
            "should contain newly added tag 'gold'");

        form.destroy();
    });

    QUnit.test('fieldmany2many tags with color: rendering and edition', function (assert) {
        assert.expect(20);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records.push({id: 13, display_name: "red", color: 8});
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\', \'no_create_edit\': True}"/>' +
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
                if (args.method ==='read' && args.model === 'partner_type') {
                    assert.deepEqual(args.args[1], ['display_name', 'color'], "should read the color field");
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
        assert.expect(3);

        this.data.partner.records[0].timmy = [12, 14];
        this.data.partner_type.records[0].color = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy" widget="many2many_tags" options="{\'color_field\': \'color\'}"/>' +
                '</form>',
            res_id: 1,
        });

        // First checks that default color 0 is rendered as 0 color
        assert.ok(form.$('span:first()').is('.o_tag_color_0'),
            'first tag color should be 0');

        // Update the color in readonly
        form.$('span:first()').click();
        $('.o_colorpicker a[data-color="1"]').trigger('mousedown'); // choose color 1
        assert.strictEqual(form.$('span:first()').data('color'), 1,
            'should have correctly updated the color (in readonly)');

        // Update the color in edit
        form.$buttons.find('.o_form_button_edit').click();
        form.$('span:first()').click();
        $('.o_colorpicker a[data-color="6"]').trigger('mousedown'); // choose color 6
        assert.strictEqual(form.$('span:first()').data('color'), 6,
            'should have correctly updated the color (in edit)');
        form.destroy();
    });

    QUnit.test('fieldmany2many tags in editable list', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            context: {take: 'five'},
            arch:'<tree editable="bottom">' +
                    '<field name="foo"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                '</tree>',
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.model === 'partner_type') {
                    assert.deepEqual(args.kwargs.context, {take: 'five'},
                        'The context should be passed to the RPC');
                }
            return this._super.apply(this, arguments);
            }
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

    QUnit.test('search more in many2one: group and use the pager', function (assert) {
        assert.expect(2);

        this.data.partner.records.push({
            id: 5,
            display_name: "Partner 4",
        }, {
            id: 6,
            display_name: "Partner 5",
        }, {
            id: 7,
            display_name: "Partner 6",
        }, {
            id: 8,
            display_name: "Partner 7",
        }, {
            id: 9,
            display_name: "Partner 8",
        }, {
            id: 10,
            display_name: "Partner 9",
        });

        this.data.partner.fields.datetime.searchable = true;
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
                'partner,false,list': '<tree limit="7"><field name="display_name"/></tree>',
                'partner,false,search': '<search><group>' +
                       '    <filter name="bar" string="Bar" context="{\'group_by\': \'bar\'}"/>' +
                        '</group></search>',
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('.o_m2o_dropdown_option:contains(Search)').mouseenter().click();  // Open Search More

        $('.modal .o_searchview_more').click();  // Magnifying class for more filters
        $('.modal .o_search_options .o_group_by_menu a:contains(Bar)').click(); // group by 'Bar'

        $('.modal .o_group_header:first').click();
        assert.strictEqual($('.modal tbody:nth(1) .o_data_row').length, 7,
            "should display 7 records in the first page");
        $('.modal .o_group_header:first .o_pager_next').click();
        assert.strictEqual($('.modal tbody:nth(1) .o_data_row').length, 1,
            "should display 1 record in the second page");

        form.destroy();
    });

    QUnit.test('many2many_tags can load more than 40 records', function (assert) {
        assert.expect(1);

        this.data.partner.fields.partner_ids = {string: "Partner", type: "many2many", relation: 'partner'};
        this.data.partner.records[0].partner_ids = [];
        for (var i = 15; i < 115; i++) {
            this.data.partner.records.push({id: i, display_name: 'walter' + i});
            this.data.partner.records[0].partner_ids.push(i);
        }
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="partner_ids" widget="many2many_tags"/>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('.o_field_widget[name="partner_ids"] > span').length, 100,
            'should have rendered 100 tags');
        form.destroy();
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

    QUnit.test('fieldradio widget has o_horizontal or o_vertical class', function (assert) {
        assert.expect(2);

        this.data.partner.fields.color2 = this.data.partner.fields.color;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                    '<field name="color" widget="radio"/>' +
                    '<field name="color2" widget="radio" options="{\'horizontal\': True}"/>' +
                    '</group>' +
                '</form>',
        });

        var btn1 = form.$('div.o_field_radio.o_vertical');
        var btn2 = form.$('div.o_field_radio.o_horizontal');

        assert.strictEqual(btn1.length, 1, "should have o_vertical class");
        assert.strictEqual(btn2.length, 1, "should have o_horizontal class");
        form.destroy();
    });

    QUnit.test('fieldradio widget with numerical keys encoded as strings', function (assert) {
        assert.expect(5);

        this.data.partner.fields.selection = {
            type: 'selection',
            selection: [['0', "Red"], ['1', "Black"]],
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="selection" widget="radio"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].selection, '1',
                        "should write correct value");
                }
                return this._super.apply(this, arguments);
            },
        });


        assert.strictEqual(form.$('.o_field_widget').text(), '',
            "field should be unset");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_radio_input:checked').length, 0,
            "no value should be checked");

        form.$("input.o_radio_input:nth(1)").click(); // click on 2nd option

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_field_widget').text(), 'Black',
            "value should be 'Black'");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_radio_input[data-index=1]:checked').length, 1,
            "'Black' should be checked");

        form.destroy();
    });

    QUnit.test('widget radio on a many2one: domain updated by an onchange', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            int_field: function () {},
        };

        var domain = [];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="int_field"/>' +
                    '<field name="trululu" widget="radio"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    domain = [['id', 'in', [10]]];
                    return $.when({
                        value: {
                            trululu: false,
                        },
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (args.method === 'search_read') {
                    assert.deepEqual(args.kwargs.domain, domain,
                        "sent domain should be correct");
                }
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=trululu] .o_radio_item').length, 3,
            "should be 3 radio buttons");

        // trigger an onchange that will update the domain
        form.$('.o_field_widget[name=int_field]').val(2).trigger('input');

        assert.strictEqual(form.$('.o_field_widget[name=trululu] .o_radio_item').length, 0,
            "should be no more radio button");

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

        // add a m2m value by clicking on input
        form.$('div.o_field_widget div.o_checkbox input').eq(1).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.deepEqual(this.data.partner.records[0].timmy, [12, 14],
            "should have added the second element to the many2many");
        assert.strictEqual(form.$('input:checked').length, 2,
            "both checkboxes should be checked");

        // remove a m2m value by clinking on label
        form.$buttons.find('.o_form_button_edit').click();
        form.$('div.o_field_widget div.o_checkbox + label').eq(0).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.deepEqual(this.data.partner.records[0].timmy, [14],
            "should have removed the first element to the many2many");
        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should be checked");
        assert.ok(form.$('div.o_field_widget div.o_checkbox input').eq(1).prop('checked'),
            "second checkbox should not be checked");

        form.destroy();
    });

    QUnit.test('widget many2many_checkboxes: start non empty, then remove twice', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].timmy = [12,14];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<group><field name="timmy" widget="many2many_checkboxes"/></group>' +
                '</form>',
            res_id: 1,
            viewOptions: {mode: 'edit'},
        });

        form.$('div.o_field_widget div.o_checkbox input').eq(0).click();
        form.$('div.o_field_widget div.o_checkbox input').eq(1).click();
        form.$buttons.find('.o_form_button_save').click();
        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').eq(0).prop('checked'),
            "first checkbox should not be checked");
        assert.notOk(form.$('div.o_field_widget div.o_checkbox input').eq(1).prop('checked'),
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

    QUnit.test('name_create in form dialog', function (assert) {
        var done = assert.async();
        assert.expect(2);

        var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
        relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="bar"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="product_id"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_create') {
                    assert.step('name_create');
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        var $dropdown = $('.modal .o_field_many2one input').autocomplete('widget');
        $('.modal input').val('new record').trigger('keydown');
        concurrency.delay(0).then(function () {
            $dropdown.find('li:first()').click(); // quick create 'new record'
            assert.verifySteps(['name_create']);

            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
            form.destroy();
            done();
        });
    });

    QUnit.module('FieldReference');

    QUnit.test('Reference field in modal readonly mode', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = 'product,41';

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="reference"/>' +
                    '<field name="p"/>' +
                '</form>',
            archs: {
                'partner,false,form': '<form><field name="reference"/></form>',
                'partner,false,list': '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // Cuurent Form
        assert.equal(form.$('.o_form_uri.o_field_widget[name=reference]').text(), 'xphone',
            'the field reference of the form should have the right value');

        var $cell_o2m = form.$('.o_data_cell');
        assert.equal($cell_o2m.text(), 'second record',
            'the list should have one record');

        $cell_o2m.click();

        // In modal
        var $modal = $('.modal-dialog.modal-lg');
        assert.equal($modal.length, 1,
            'there should be one modal opened');

        assert.equal($modal.find('.o_form_uri.o_field_widget[name=reference]').text(), 'xpad',
            'The field reference in the modal should have the right value');

        $modal.find('.o_form_button_cancel').click();

        form.destroy();
    });

    QUnit.test('Reference field in modal write mode', function (assert) {
        assert.expect(5);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].trululu = 1;
        this.data.partner.records[1].reference = 'product,41';

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="reference"/>' +
                    '<field name="p"/>' +
                '</form>',
            archs: {
                'partner,false,form': '<form><field name="reference"/></form>',
                'partner,false,list': '<tree><field name="display_name"/></tree>',
            },
            res_id: 1,
        });

        // current form
        form.$buttons.find('.o_form_button_edit').click();

        var $fieldRef = form.$('.o_field_widget.o_field_many2one[name=reference]');
        assert.equal($fieldRef.find('option:selected').text(), 'Product',
            'The reference field\'s model should be Product');
        assert.equal($fieldRef.find('.o_input.ui-autocomplete-input').val(), 'xphone',
            'The reference field\'s record should be xphone');

        form.$('.o_data_cell').click();

        // In modal
        var $modal = $('.modal-dialog.modal-lg');
        assert.equal($modal.length, 1,
            'there should be one modal opened');

        var $fieldRefModal = $modal.find('.o_field_widget.o_field_many2one[name=reference]');

        assert.equal($fieldRefModal.find('option:selected').text(), 'Product',
            'The reference field\'s model should be Product');
        assert.equal($fieldRefModal.find('.o_input.ui-autocomplete-input').val(), 'xpad',
            'The reference field\'s record should be xpad');

        form.destroy();
    });

    QUnit.test('reference in form view', function (assert) {
        assert.expect(15);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="reference" string="custom label"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form': '<form string="Product"><field name="display_name"/></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action') {
                    assert.deepEqual(args.args[0], [37], "should call get_formview_action with correct id");
                    return $.when({
                        res_id: 17,
                        type: 'ir.actions.act_window',
                        target: 'current',
                        res_model: 'res.partner'
                    });
                }
                if (args.method === 'get_formview_id') {
                    assert.deepEqual(args.args[0], [37], "should call get_formview_id with correct id");
                    return $.when(false);
                }
                if (args.method === 'name_search') {
                    assert.strictEqual(args.model, 'partner_type',
                        "the name_search should be done on the newly set model");
                }
                if (args.method === 'write') {
                    assert.strictEqual(args.model, 'partner',
                        "should write on the current model");
                    assert.deepEqual(args.args, [[1], {reference: 'partner_type,12'}],
                        "should write the correct value");
                }
                return this._super(route, args);
            },
        });

        testUtils.intercept(form, 'do_action', function (event) {
            assert.strictEqual(event.data.action.res_id, 17,
                "should do a do_action with correct parameters");
        });

        assert.strictEqual(form.$('a.o_form_uri:contains(xphone)').length, 1,
                        "should contain a link");
        form.$('a.o_form_uri').click(); // click on the link in readonly mode (should trigger do_action)

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget').length, 2,
            "should contain two field widgets (selection and many2one)");
        assert.strictEqual(form.$('.o_field_many2one').length, 1,
            "should contain one many2one");
        assert.strictEqual(form.$('.o_field_widget select').val(), "product",
            "widget should contain one select with the model");
        assert.strictEqual(form.$('.o_field_widget input').val(), "xphone",
            "widget should contain one input with the record");

        var options = _.map(form.$('.o_field_widget select > option'), function (el) {
            return $(el).val();
        });
        assert.deepEqual(options, ['', 'product', 'partner_type', 'partner'],
            "the options should be correctly set");

        form.$('.o_external_button').click(); // click on the external button (should do an RPC)

        assert.strictEqual($('.modal .modal-title').text().trim(), 'Open: custom label',
                        "dialog title should display the custom string label");
        $('.modal .o_form_button_cancel').click();

        form.$('.o_field_widget select').val('partner_type').trigger('change');
        assert.strictEqual(form.$('.o_field_widget input').val(), "",
            "many2one value should be reset after model change");

        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        // change the value of the m2o with a suggestion of the dropdown
        form.$('.o_field_many2one input').click(); // will trigger a name_search on partner_type model
        $dropdown.find('li:first()').click();

        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('a.o_form_uri:contains(gold)').length, 1,
                        "should contain a link with the new value");

        form.destroy();
    });

    QUnit.test('default_get and onchange with a reference field', function (assert) {
        assert.expect(8);

        this.data.partner.fields.reference.default = 'product,37';
        this.data.partner.onchanges = {
            int_field: function (obj) {
                if (obj.int_field !== 0) {
                    obj.reference = 'partner_type,' + obj.int_field;
                }
            },
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field"/>' +
                            '<field name="reference"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    assert.step(args.model);
                }
                return this._super(route, args);
            },
        });

        assert.verifySteps(['product'], "the first name_get should have been done");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] select').val(), "product",
            "reference field model should be correctly set");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] input').val(), "xphone",
            "reference field value should be correctly set");

        // trigger onchange
        form.$('.o_field_widget[name=int_field]').val(12).trigger('input');

        assert.verifySteps(['product', 'partner_type'], "the second name_get should have been done");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] select').val(), "partner_type",
            "reference field model should be correctly set");
        assert.strictEqual(form.$('.o_field_widget[name="reference"] input').val(), "gold",
            "reference field value should be correctly set");
        form.destroy();
    });

    QUnit.test('default_get a reference field in a x2m', function (assert) {
        assert.expect(1);

        this.data.partner.fields.turtles.default = [
            [0, false, {turtle_ref: 'product,37'}]
        ];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="turtles">' +
                            '<tree>' +
                                '<field name="turtle_ref"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            archs: {
                'turtle,false,form': '<form><field name="display_name"/><field name="turtle_ref"/></form>',
            },
        });
        assert.strictEqual(form.$('.o_field_one2many[name="turtles"] .o_data_row:first').text(), "xphone",
            "the default value should be correctly handled");
        form.destroy();
    });

    QUnit.test('widget reference on char field, reset by onchange', function (assert) {
        assert.expect(4);

        this.data.partner.records[0].foo = 'product,37';
        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = 'product,' + obj.int_field;
            },
        };

        var nbNameGet = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="int_field"/>' +
                            '<field name="foo" widget="reference" readonly="1"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.model === 'product' && args.method === 'name_get') {
                    nbNameGet++;
                }
                return this._super(route, args);
            },
        });

        assert.strictEqual(nbNameGet, 1,
            "the first name_get should have been done");
        assert.strictEqual(form.$('a[name="foo"]').text(), "xphone",
            "foo field should be correctly set");

        // trigger onchange
        form.$('.o_field_widget[name=int_field]').val(41).trigger('input');

        assert.strictEqual(nbNameGet, 2,
            "the second name_get should have been done");
        assert.strictEqual(form.$('a[name="foo"]').text(), "xpad",
            "foo field should have been updated");
        form.destroy();
    });

    QUnit.test('reference and list navigation', function (assert) {
        assert.expect(2);

        var list = createView({
            View: ListView,
            model: 'partner',
            data: this.data,
            arch: '<tree editable="bottom"><field name="reference"/></tree>',
        });

        // edit first row
        list.$('.o_data_row .o_data_cell').first().click();
        assert.strictEqual(list.$('.o_data_row:eq(0) .o_field_widget[name="reference"] input')[0], document.activeElement,
            'input of first data row should be selected');

        // press TAB to go to next line
        list.$('.o_data_row:eq(0) input').trigger($.Event('keydown', {
            which: $.ui.keyCode.TAB,
            keyCode: $.ui.keyCode.TAB,
        }));
        assert.strictEqual(list.$('.o_data_row:eq(1) .o_field_widget[name="reference"] select')[0], document.activeElement,
            'select of second data row should be selected');

        list.destroy();
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
                                    '</form>'},
            mockRPC: function(route, args) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    args.args[1].p[0][2].datetime = '2018-04-05 12:00:00';
                }
                return this._super.apply(this, arguments);
            }
        });

        form.$buttons.find('.o_form_button_edit').click();

        var x2mList = form.$('.o_field_x2many_list[name=p]');

        // Add a record in the list
        x2mList.find('.o_field_x2many_list_row_add a').click();

        var modal = $('.modal-dialog.modal-lg');

        var nameInput = modal.find('input.o_input[name=display_name]');
        nameInput.val('michelangelo').trigger('input');

        // Save the record in the modal (though it is still virtual)
        modal.find('.btn-primary').first().click();

        assert.equal(x2mList.find('.o_data_row').length, 1,
            'There should be 1 records in the x2m list');

        var newlyAdded = x2mList.find('.o_data_row').eq(0);

        assert.equal(newlyAdded.find('.o_data_cell').first().text(), '',
            'The create_date field should be empty');
        assert.equal(newlyAdded.find('.o_data_cell').eq(1).text(), 'michelangelo',
            'The display name field should have the right value');

        // Save the whole thing
        form.$buttons.find('.o_form_button_save').click();

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
            arch:'<form string="Partners">' +
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
        assert.strictEqual(form.$('th').length, 2,
            "should be 2 columns in the one2many");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_many2one[name="product_id"] input').click();
        $('li.ui-menu-item a:contains(xpad)').trigger('mouseenter').click();
        assert.strictEqual(form.$('th').length, 1,
            "should be 1 column when the product_id is set");
        form.$('.o_field_many2one[name="product_id"] input').val('').trigger('keyup');
        assert.strictEqual(form.$('th').length, 2,
            "should be 2 columns in the one2many when product_id is not set");
        form.$('.o_field_boolean[name="bar"] input').click();
        assert.strictEqual(form.$('th').length, 1,
            "should be 1 column after the value change");
        form.destroy();
    });

});
});
});
