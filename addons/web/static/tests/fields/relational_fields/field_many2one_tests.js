odoo.define('web.field_many_to_one_tests', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var ListView = require('web.ListView');
var relationalFields = require('web.relational_fields');
var StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

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

            testUtils.mock.intercept(form, 'do_action', function (event) {
                assert.strictEqual(event.data.action.res_id, 17,
                    "should do a do_action with correct parameters");
            });

            assert.strictEqual(form.$('a.o_form_uri:contains(aaa)').length, 1,
                "should contain a link");
            testUtils.dom.click(form.$('a.o_form_uri'));

            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('.o_external_button'));

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

            testUtils.form.clickEdit(form);

            // click on the external button (should do an RPC)
            testUtils.dom.click(form.$('.o_external_button'));
            // save and close modal
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            // save form
            testUtils.form.clickSave(form);
            // click next on pager
            testUtils.dom.click(form.pager.$('.o_pager_next'));

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

            testUtils.form.clickEdit(form);

            // click on the external button (should do an RPC)
            testUtils.dom.click(form.$('.o_external_button'));

            testUtils.fields.editInput($('.modal input[name="foo"]'), 'brandon');

            // save and close modal
            testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));
            // save form
            testUtils.form.clickSave(form);
            // click next on pager
            testUtils.dom.click(form.pager.$('.o_pager_next'));

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
            testUtils.form.clickEdit(form);
            assert.containsOnce(form, 'button.o_external_button:visible',
                "should have an open record button");

            testUtils.dom.click(form.$('input.o_input'));

            assert.containsOnce(form, 'button.o_external_button:visible',
                "should still have an open record button");
            form.$('input.o_input').trigger('focusout');
            assert.strictEqual($('.modal button:contains(Create and edit)').length, 0,
                "there should not be a quick create modal");

            form.destroy();
        });

        QUnit.test('show_address works in a view embedded in a view of another type', function (assert) {
            assert.expect(1);

            this.data.turtle.records[1].turtle_trululu = 2;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="turtles"/>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,form": '<form string="T">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu" context="{\'show_address\': 1}" options="{\'always_reload\': True}"/>' +
                        '</form>',
                    "turtle,false,list": '<tree editable="bottom">' +
                        '<field name="display_name"/>' +
                        '</tree>',
                },
                mockRPC: function (route, args) {
                    if (args.method === 'name_get') {
                        return this._super(route, args).then(function (result) {
                            if (args.model === 'partner' && args.kwargs.context.show_address) {
                                result[0][1] += '\nrue morgue\nparis 75013';
                            }
                            return result;
                        });
                    }
                    return this._super(route, args);
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            testUtils.dom.click(form.$('.o_data_row:first td.o_data_cell'));

            assert.strictEqual($('[name="turtle_trululu"]').text(), "second recordrue morgueparis 75013",
                "The partner's address should be displayed");
            form.destroy();
        });

        QUnit.test('many2one data is reloaded if there is a context to take into account', function (assert) {
            assert.expect(1);

            this.data.turtle.records[1].turtle_trululu = 2;

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="turtles"/>' +
                    '</form>',
                res_id: 1,
                archs: {
                    "turtle,false,form": '<form string="T">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu" context="{\'show_address\': 1}" options="{\'always_reload\': True}"/>' +
                        '</form>',
                    "turtle,false,list": '<tree editable="bottom">' +
                        '<field name="display_name"/>' +
                        '<field name="turtle_trululu"/>' +
                        '</tree>',
                },
                mockRPC: function (route, args) {
                    if (args.method === 'name_get') {
                        return this._super(route, args).then(function (result) {
                            if (args.model === 'partner' && args.kwargs.context.show_address) {
                                result[0][1] += '\nrue morgue\nparis 75013';
                            }
                            return result;
                        });
                    }
                    return this._super(route, args);
                },
            });
            // click the turtle field, opens a modal with the turtle form view
            testUtils.dom.click(form.$('.o_data_row:first'));

            assert.strictEqual($('.modal [name=turtle_trululu]').text(), "second recordrue morgueparis 75013",
                "The partner's address should be displayed");
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

            testUtils.form.clickEdit(form);

            testUtils.fields.many2one.clickOpenDropdown('trululu');
            testUtils.fields.many2one.clickItem('trululu', 'Search');

            assert.strictEqual($('tr.o_data_row').length, 9, "should display 9 records");

            testUtils.dom.click($('button:contains(Filters)'));
            testUtils.dom.click($('.o_add_custom_filter:visible'));
            assert.strictEqual($('.o_filter_condition select.o_searchview_extended_prop_field').val(), 'datetime',
                "datetime field should be selected");
            testUtils.dom.click($('.o_apply_filter'));

            assert.strictEqual($('tr.o_data_row').length, 0, "should display 0 records");
            form.destroy();
        });

        QUnit.test('onchanges on many2ones trigger when editing record in form view', function (assert) {
            assert.expect(10);

            this.data.partner.onchanges.user_id = function () { };
            this.data.user.fields.other_field = { string: "Other Field", type: "char" };
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
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_external_button'));
            testUtils.fields.editInput($('.modal-body input[name="other_field"]'), 'wood');

            // save the modal and make sure an onchange is triggered
            testUtils.dom.click($('.modal .modal-footer .btn-primary').first());
            assert.verifySteps(['read', 'get_formview_id', 'load_views', 'read', 'write', 'onchange', 'read']);

            // save the main record, and check that no extra rpcs are done (record
            // is not dirty, only a related record was modified)
            testUtils.form.clickSave(form);
            assert.verifySteps(['read', 'get_formview_id', 'load_views', 'read', 'write', 'onchange', 'read']);
            form.destroy();
        });

        QUnit.test('many2one fields with option "no_open"', function (assert) {
            assert.expect(3);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                    '<sheet>' +
                    '<group>' +
                    '<field name="trululu" options="{&quot;no_open&quot;: True}" />' +
                    '</group>' +
                    '</sheet>' +
                    '</form>',
                res_id: 1,
            });

            assert.containsOnce(form, 'span.o_field_widget[name=trululu]',
                "should be displayed inside a span (sanity check)");
            assert.containsNone(form, 'span.o_form_uri', "should not have an anchor");

            testUtils.form.clickEdit(form);
            assert.containsNone(form, '.o_field_widget[name=trululu] .o_external_button', "should not have the button to open the record");

            form.destroy();
        });

        QUnit.test('many2one in edit mode', function (assert) {
            assert.expect(16);

            // create 10 partners to have the 'Search More' option in the autocomplete dropdown
            for (var i = 0; i < 10; i++) {
                var id = 20 + i;
                this.data.partner.records.push({ id: id, display_name: "Partner " + id });
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
            testUtils.mock.intercept(form, 'get_session', function (event) {
                event.data.callback({ user_context: {} });
            });

            testUtils.form.clickEdit(form);

            var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');

            testUtils.fields.many2one.clickOpenDropdown('trululu');
            assert.ok($dropdown.is(':visible'),
                'clicking on the m2o input should open the dropdown if it is not open yet');
            assert.strictEqual($dropdown.find('li:not(.o_m2o_dropdown_option)').length, 7,
                'autocomplete should contains 7 suggestions');
            assert.strictEqual($dropdown.find('li.o_m2o_dropdown_option').length, 2,
                'autocomplete should contain "Search More" and Create and Edit..."');

            testUtils.fields.many2one.clickOpenDropdown('trululu');
            assert.ok(!$dropdown.is(':visible'),
                'clicking on the m2o input should close the dropdown if it is open');

            // change the value of the m2o with a suggestion of the dropdown
            testUtils.fields.many2one.clickOpenDropdown('trululu');
            testUtils.fields.many2one.clickHighlightedItem('trululu');
            assert.ok(!$dropdown.is(':visible'), 'clicking on a value should close the dropdown');
            assert.strictEqual(form.$('.o_field_many2one input').val(), 'first record',
                'value of the m2o should have been correctly updated');

            // change the value of the m2o with a record in the 'Search More' modal
            testUtils.fields.many2one.clickOpenDropdown('trululu');
            // click on 'Search More' (mouseenter required by ui-autocomplete)
            testUtils.fields.many2one.clickItem('trululu', 'Search');
            assert.ok($('.modal .o_list_view').length, "should have opened a list view in a modal");
            assert.ok(!$('.modal .o_list_view .o_list_record_selector').length,
                "there should be no record selector in the list view");
            assert.ok(!$('.modal .modal-footer .o_select_button').length,
                "there should be no 'Select' button in the footer");
            assert.ok($('.modal tbody tr').length > 10, "list should contain more than 10 records");
            // filter the list using the searchview
            $('.modal .o_searchview_input').trigger({ type: 'keypress', which: 80 }); // P
            $('.modal .o_searchview_input').trigger({ type: 'keydown', which: 13 }); // enter
            assert.strictEqual($('.modal tbody tr').length, 10,
                "list should be restricted to records containing a P (10 records)");
            // choose a record
            testUtils.dom.click($('.modal tbody tr:contains(Partner 20)'));
            assert.ok(!$('.modal').length, "should have closed the modal");
            assert.ok(!$dropdown.is(':visible'), 'should have closed the dropdown');
            assert.strictEqual(form.$('.o_field_many2one input').val(), 'Partner 20',
                'value of the m2o should have been correctly updated');

            // save
            testUtils.form.clickSave(form);
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

            assert.containsOnce(form, 'a.o_form_uri',
                "should display 1 m2o link in form");
            assert.hasAttrValue(form.$('a.o_form_uri'), 'href', "#id=4&model=partner",
                "href should contain id and model");

            // Remove value from many2one and then save, there should not have href with id and model on m2o anchor
            testUtils.form.clickEdit(form);
            form.$('.o_field_many2one input').val('').trigger('keyup').trigger('focusout');
            testUtils.form.clickSave(form);

            assert.hasAttrValue(form.$('a.o_form_uri'), 'href', "#",
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

            testUtils.dom.click(form.$('.o_field_many2one input'));
            // unset the many2one -> should search again with ''
            form.$('.o_field_many2one input').val('').trigger('keydown');
            concurrency.delay(0).then(function () {
                // write 'p' -> should search with 'p'
                form.$('.o_field_many2one input').val('p').trigger('keydown').trigger('keyup');

                return concurrency.delay(0);
            }).then(function () {
                // close and re-open the dropdown -> should search with 'p' again
                testUtils.dom.click(form.$('.o_field_many2one input'));
                testUtils.dom.click(form.$('.o_field_many2one input'));

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

            testUtils.form.clickEdit(form);

            assert.strictEqual(form.$('.o_field_widget[name=trululu] input').val(), "first record",
                "actual field value should be displayed to be edited");

            testUtils.form.clickSave(form);

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
            testUtils.dom.click(list.$('.o_data_row .o_data_cell').first());
            testUtils.fields.editInput(list.$('.o_data_cell input'), '');

            // press keydown, to select first choice
            list.$('.o_data_cell input').focus().trigger($.Event('keydown', {
                which: $.ui.keyCode.DOWN,
                keyCode: $.ui.keyCode.DOWN,
            }));

            // we now check that the dropdown is open (and that the focus did not go
            // to the next line)
            var $dropdown = list.$('.o_field_many2one input').autocomplete('widget');
            assert.ok($dropdown.is(':visible'), "dropdown should be visible");
            assert.hasClass(list.$('.o_data_row:eq(0)'),'o_selected_row',
                'first data row should still be selected');
            assert.doesNotHaveClass(list.$('.o_data_row:eq(1)'), 'o_selected_row',
                'second data row should not be selected');

            list.destroy();
        });

        QUnit.test('standalone many2one field', async function (assert) {
            assert.expect(4);
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
            }]).then(function (recordID) {
                var record = model.get(recordID);
                // create a new widget that uses the StandaloneFieldManagerMixin
                var StandaloneWidget = Widget.extend(StandaloneFieldManagerMixin, {
                    init: function (parent) {
                        this._super.apply(this, arguments);
                        StandaloneFieldManagerMixin.init.call(this, parent);
                    },
                });
                var parent = new StandaloneWidget(model);
                testUtils.mock.addMockEnvironment(parent, {
                    data: self.data,
                    mockRPC: function (route, args) {
                        assert.step(args.method);
                        return this._super.apply(this, arguments);
                    },
                });

                var relField = new relationalFields.FieldMany2One(parent, 'partner_id', record, {
                    mode: 'edit',
                    noOpen: true,
                });

                relField.appendTo(fixture);
                testUtils.fields.editInput($('input.o_input'), 'xyzzrot');

                concurrency.delay(0).then(function () {
                    testUtils.fields.many2one.clickItem('partner_id', 'Create');

                    assert.containsNone(relField, '.o_external_button',
                        "should not have the button to open the record");
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
        //     testUtils.form.clickEdit(form);
        //     assert.strictEqual(form.$('input').eq(1).val(), 'xpad', "initial product_id val should be xpad");

        //     testUtils.fields.editInput(form.$('input').eq(0), "let us trigger an onchange");

        //     assert.strictEqual(form.$('input').eq(1).val(), 'xphone', "onchange should have been applied");
        // });

        QUnit.test('form: quick create then save directly', async function (assert) {
            assert.expect(5);

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
            await testUtils.fields.many2one.searchAndClickItem('trululu', 'b');
            testUtils.form.clickSave(form);

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);
            form.destroy();
        });

        QUnit.test('list: quick create then save directly', async function (assert) {
            assert.expect(8);

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

            testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

            await testUtils.fields.many2one.searchAndClickItem('trululu', {search:'b'});
            list.$buttons.find('.o_list_button_add').show();
            testUtils.dom.click(list.$buttons.find('.o_list_button_add'));

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");
            assert.containsN(list, '.o_data_row', 4,
                "should wait for the name_create before adding the new row");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);
            assert.strictEqual(list.$('.o_data_row:nth(1) .o_data_cell').text(), 'b',
                "created row should have the correct m2o value");
            assert.containsN(list, '.o_data_row', 5, "should have added the fifth row");

            list.destroy();
        });

        QUnit.test('list in form: quick create then save directly', async function (assert) {
            assert.expect(6);

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

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            await testUtils.fields.many2one.searchAndClickItem('trululu', {search: 'b'});
            testUtils.form.clickSave(form);

            assert.verifySteps(['name_create'],
                "should wait for the name_create before creating the record");

            def.resolve();

            assert.verifySteps(['name_create', 'create']);
            assert.strictEqual(form.$('.o_data_row:first .o_data_cell').text(), 'b',
                "first row should have the correct m2o value");
            form.destroy();
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
                trululu: function () { },
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

            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            form.$('.o_field_many2one input').val('b').trigger('keydown');
            concurrency.delay(0).then(function () {
                testUtils.fields.many2one.clickHighlightedItem('trululu');
                testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));

                assert.containsOnce(form, '.o_data_row',
                    "there should still be only one row");
                assert.hasClass(form.$('.o_data_row'),'o_selected_row',
                    "the row should still be in edition");

                def.resolve();

                assert.strictEqual(form.$('.o_data_row:first .o_data_cell').text(), 'b',
                    "first row should have the correct m2o value");
                assert.containsN(form, '.o_data_row', 2,
                    "there should now be 2 rows");
                assert.hasClass(form.$('.o_data_row:nth(1)'),'o_selected_row',
                    "the second row should be in edition");

                testUtils.form.clickSave(form);

                assert.containsOnce(form, '.o_data_row',
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
                        return $.when({ p: [[0, 0, { display_name: 'new record' }]] });
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
                        return $.when({ p: [[0, 0, { display_name: 'new record', trululu: false }]] });
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

            testUtils.dom.click(requiredElement);
            // discard by clicking on body
            testUtils.dom.click($('body'));

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

            testUtils.dom.click(form.$('button.o_pager_next'));

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
            assert.containsOnce(form, '.o_data_row',
                "should have a row in the editable list");
            assert.strictEqual($('td.o_data_cell').first().text(), "entry",
                "should have the correct displayed name");
            var requiredField = $('td.o_data_cell.o_required_modifier');
            assert.strictEqual(requiredField.length, 1,
                "should have a required field on this record");
            assert.strictEqual(requiredField.text(), "",
                "should have empty string in the required field on this record");

            // click on empty required field in editable list record
            testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            testUtils.dom.click($('body'));

            // record should not be dropped
            assert.containsOnce(form, '.o_data_row',
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
            assert.containsNone(form, '.o_data_row',
                "should have no row in the editable list");

            // select product_id to force on_change in editable list
            testUtils.dom.click(form.$('.o_field_widget[name="product_id"] .o_input'));
            testUtils.dom.click($('.ui-menu-item').first());

            // check that there is a record in the editable list with empty string as required field
            assert.containsOnce(form, '.o_data_row',
                "should have a row in the editable list");
            assert.strictEqual($('td.o_data_cell').first().text(), "entry",
                "should have the correct displayed name");
            var requiredField = $('td.o_data_cell.o_required_modifier');
            assert.strictEqual(requiredField.length, 1,
                "should have a required field on this record");
            assert.strictEqual(requiredField.text(), "",
                "should have empty string in the required field on this record");

            // click on empty required field in editable list record
            testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            testUtils.dom.click($('body'));

            // record should not be dropped
            assert.containsOnce(form, '.o_data_row',
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
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            var charField = form.$('.o_field_widget.o_field_char[name="display_name"]');
            var requiredField = form.$('.o_field_widget.o_required_modifier[name="trululu"]');
            charField.val("some text");
            assert.strictEqual(charField.length, 1,
                "should have a char field 'display_name' on this record");
            assert.doesNotHaveClass(charField, 'o_required_modifier',
                "the char field should not be required on this record");
            assert.strictEqual(charField.val(), "some text",
                "should have entered text in the char field on this record");
            assert.strictEqual(requiredField.length, 1,
                "should have a required field 'trululu' on this record");
            assert.strictEqual(requiredField.val().trim(), "",
                "should have empty string in the required field on this record");

            // click on empty required field in editable list record
            testUtils.dom.click(requiredField);
            // click off so that the required field still stay empty
            testUtils.dom.click($('body'));

            // record should be dropped
            assert.containsNone(form, '.o_data_row',
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

            assert.containsNone(form, '.o_data_row',
                "should initially not have any record in the list");

            // Click on "Add an item"
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            assert.containsOnce(form, '.o_data_row',
                "should have a temporary record in the list");

            var $inputEditMode = form.$('.o_field_widget.o_required_modifier[name="trululu"] input');
            assert.strictEqual($inputEditMode.length, 1,
                "should have a required field 'trululu' on this record");
            assert.strictEqual($inputEditMode.val(), "",
                "should have empty string in the required field on this record");

            // add something to required field and leave edit mode of the record
            testUtils.dom.click($inputEditMode);
            testUtils.dom.click($('li.ui-menu-item').first());
            testUtils.dom.click($('body'));

            var $inputReadonlyMode = form.$('.o_data_cell.o_required_modifier');
            assert.containsOnce(form, '.o_data_row',
                "should not have dropped valid record when leaving edit mode");
            assert.strictEqual($inputReadonlyMode.text(), "first record",
                "should have put some content in the required field on this record");

            // remove the required field and leave edit mode of the record
            testUtils.dom.click($('.o_data_row'));
            assert.containsOnce(form, '.o_data_row',
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
                        [0, obj.timmy[1][1], { display_name: displayName, name: 'brandon' }]
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
                        return $.when({ timmy: [[0, 0, { display_name: 'brandon is the new timmy', name: 'brandon' }]] });
                    }
                    if (args.method === 'create') {
                        assert.deepEqual(args.args[0], {
                            int_field: 2,
                            timmy: [
                                [6, false, []],
                                [0, args.args[0].timmy[1][1], { display_name: displayName, name: 'brandon' }],
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
            testUtils.dom.click(form.$('.o_data_cell'));
            testUtils.fields.editInput(form.$('.o_data_cell input'), displayName);
            testUtils.form.clickSave(form);

            form.destroy();
        });

        QUnit.test('list in form: default_get with x2many create and onchange', function (assert) {
            assert.expect(2);

            this.data.partner.onchanges.turtles = function (obj) {
                assert.deepEqual(
                    obj.turtles,
                    [
                        [4, 2, false],
                        [1, 2, { turtle_foo: 'blip' }],
                        [4, 3, false],
                        [1, 3, { turtle_foo: 'kawa' }]
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
                        return $.when({ turtles: [[6, 0, [2, 3]]] });
                    }
                    if (args.method === 'create') {
                        // it would be even better if we did not send the current
                        // unchanged state with the command 1, but this seems more
                        // difficult.
                        assert.deepEqual(args.args[0].turtles, [
                            [4, 2, false],
                            [1, 2, { turtle_foo: 'blip' }],
                            [4, 3, false],
                            [1, 3, { turtle_foo: 'kawa' }]
                        ], 'should send proper commands to create method');
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickSave(form);

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

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('td.o_data_cell:first'));
            testUtils.dom.click(form.$('.o_external_button'));
            testUtils.dom.click($('button:contains("Just do it !")'));
            testUtils.dom.click($('button:contains("Just don\'t do it !")'));

            form.destroy();
        });

        QUnit.test('X2Many sequence list in modal', function (assert) {
            assert.expect(5);

            this.data.partner.fields.sequence = { string: 'Sequence', type: 'integer' };
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

            this.data.product.fields.turtle_ids = { string: 'Turtles', type: 'one2many', relation: 'turtle' };
            this.data.product.records[0].turtle_ids = [1];

            this.data.turtle.fields.partner_types_ids = { string: "Partner", type: "one2many", relation: 'partner' };
            this.data.turtle.fields.type_id = { string: "Partner Type", type: "many2one", relation: 'partner_type' };

            this.data.partner_type.fields.partner_ids = { string: "Partner", type: "one2many", relation: 'partner' };
            this.data.partner_type.records[0].partner_ids = [1, 2];

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
                        return $.when([{ id: 37, name: 'xphone', display_name: 'leonardo', turtle_ids: [1] }]);
                    }
                    if (route === '/web/dataset/call_kw/turtle/read') {
                        return $.when([{ id: 1, type_id: [12, 'gold'] }]);
                    }
                    if (route === '/web/dataset/call_kw/partner_type/get_formview_id') {
                        return $.when(false);
                    }
                    if (route === '/web/dataset/call_kw/partner_type/read') {
                        return $.when([{ id: 12, partner_ids: [1, 2], display_name: 'gold' }]);
                    }
                    if (route === '/web/dataset/call_kw/partner_type/write') {
                        assert.step('partner_type write');
                    }
                    return this._super.apply(this, arguments);
                },
            }).then(function (form) {
                testUtils.form.clickEdit(form);
                testUtils.dom.click(form.$('.o_data_cell'));
                testUtils.dom.click(form.$('.o_external_button'));

                var $modal = $('.modal');
                assert.equal($modal.length, 1,
                    'There should be 1 modal opened');

                var $handles = $modal.find('.ui-sortable-handle');
                assert.equal($handles.length, 2,
                    'There should be 2 sequence handlers');

                testUtils.dom.dragAndDrop($handles.eq(1), $modal.find('tbody tr').first(),
                    { position: 'top' });

                // Saving the modal and then the original model
                testUtils.dom.click($modal.find('.modal-footer .btn-primary'));
                testUtils.form.clickSave(form);

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
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('.o_field_widget[name=product_id] input'));
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
            testUtils.form.clickEdit(form);

            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));
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
            assert.strictEqual(form.$('.o_field_widget[name=trululu] input').val(), 'hello world',
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
            assert.strictEqual(form.$('a[name=product_id]').text(), '', 'the tag a should be empty');
            testUtils.form.clickEdit(form);

            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickItem('product_id','xphone');
            assert.strictEqual(form.$('.o_field_widget[name=product_id] input').val(), "xphone", "should have selected xphone");

            testUtils.form.clickDiscard(form);
            assert.strictEqual(form.$('a[name=product_id]').text(), '', 'the tag a should be empty');
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
                session: { user_context: { hey: "ho" } },
                mockRPC: function (route, args) {
                    if (args.method === 'name_search' && args.model === 'product') {
                        assert.deepEqual(
                            args.kwargs.args,
                            [['foo', '=', 'bar'], ['foo', '=', 'yop']],
                            'the field attr domain should have been used for the RPC (and evaluated)');
                        assert.deepEqual(
                            args.kwargs.context,
                            { hey: "ho", hello: "world", test: "yop" },
                            'the field attr context should have been used for the ' +
                            'RPC (evaluated and merged with the session one)');
                        return $.when([]);
                    }
                    if (args.method === 'name_search' && args.model === 'partner') {
                        assert.deepEqual(args.kwargs.args, [['id', 'in', [12]]],
                            'the field attr domain should have been used for the RPC (and evaluated)');
                        assert.deepEqual(args.kwargs.context, { hey: 'ho', timmy: [[6, false, [12]]] },
                            'the field attr context should have been used for the RPC (and evaluated)');
                        return $.when([]);
                    }
                    return this._super.apply(this, arguments);
                },
            });

            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_field_widget[name=product_id] input'));

            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));

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

            testUtils.dom.click($('.modal .modal-footer .btn-primary').first());

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
            testUtils.dom.click($('.modal .modal-footer .btn:contains(Cancel)'));
            assert.strictEqual(form.$('.o_field_many2one input').val(), "",
                'the many2one should not set a value as its creation has been cancelled (with Cancel button)');

            // cancel the many2one creation with Close button
            form.$('.o_field_many2one input').focus().val('new product').trigger('keyup').trigger('blur');
            testUtils.dom.click($('.modal .modal-header button'));
            assert.strictEqual(form.$('.o_field_many2one input').val(), "",
                'the many2one should not set a value as its creation has been cancelled (with Close button)');

            // select a new value then cancel the creation of the new one --> restore the previous
            testUtils.fields.many2one.clickOpenDropdown('product_id');
            testUtils.fields.many2one.clickItem('product_id','o');
            assert.strictEqual(form.$('.o_field_many2one input').val(), "xphone", "should have selected xphone");
            form.$('.o_field_many2one input').focus().val('new product').trigger('keyup').trigger('blur');
            assert.strictEqual($('.modal').length, 1, "there should be one opened modal");
            testUtils.dom.click($('.modal .modal-footer .btn:contains(Cancel)'));
            assert.strictEqual(form.$('.o_field_many2one input').val(), "xphone",
                'should have restored the many2one with its previous selected value (xphone)');

            // confirm the many2one creation
            form.$('.o_field_many2one input').focus();
            form.$('.o_field_many2one input').val('new partner').trigger('keyup').trigger('blur');
            testUtils.dom.clickFirst($('.modal .modal-footer .btn-primary'));
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

            testUtils.dom.click(form.$('.o_field_many2one input'));
            assert.strictEqual($('.ui-autocomplete .o_m2o_dropdown_option:contains(Create)').length, 0,
                "there shouldn't be any option to search and create");

            testUtils.dom.click($('.ui-autocomplete li:contains(xpad)').mouseenter());
            assert.strictEqual(form.$('.o_field_many2one input').val(), "xpad",
                "the correct record should be selected");
            assert.containsOnce(form, '.o_field_many2one .o_external_button',
                "there should be an external button displayed");

            testUtils.dom.click(form.$('.o_field_many2one .o_external_button'));
            assert.strictEqual($('.modal .o_form_view.o_form_readonly').length, 1,
                "there should be a readonly form view opened");

            testUtils.dom.click($('.modal .o_form_button_cancel'));

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

            testUtils.dom.click(list.$('td.o_data_cell:first'));
            assert.containsOnce(list, '.o_selected_row',
                "should have a row in edit mode");

            // we now write 'a' and press enter to check that the selection is
            // working, and prevent the navigation
            testUtils.fields.editInput(list.$('td.o_data_cell input:first'), 'a');
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
                assert.hasClass(list.$('tr.o_data_row:eq(1)'),'o_selected_row',
                    "second row should now be selected");

                // we now write again 'a' in the cell to select xpad. We will now
                // test with the tab key
                testUtils.fields.editInput(list.$('td.o_data_cell input:first'), 'a');
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
                assert.hasClass(list.$('tr.o_data_row:eq(2)'),'o_selected_row',
                    "third row should now be selected");
                list.destroy();
                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                done();
            });
        });

        QUnit.test('pressing ENTER on a \'no_quick_create\' many2one should open a M2ODialog', function (assert) {
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
            testUtils.fields.editInput($input, "Something that does not exist");
            $('.ui-autocomplete .ui-menu-item a:contains(Create and)').trigger('mouseenter');
            concurrency.delay(0).then(function () {
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
                concurrency.delay(0).then(function () {
                    $input.blur();
                    assert.strictEqual($('.modal').length, 1,
                        "should have one modal in body");
                    // Check that discarding clears $input
                    testUtils.dom.click($('.modal .o_form_button_cancel'));
                    assert.strictEqual($input.val(), '',
                        "the field should be empty");
                    form.destroy();
                    relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                    done();
                });
            });
        });

        QUnit.test('select a value by pressing TAB on a many2one with onchange', function (assert) {
            var done = assert.async();
            assert.expect(3);

            this.data.partner.onchanges.trululu = function () { };

            var M2O_DELAY = relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY;
            relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = 0;
            var def = $.Deferred();

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form>' +
                    '<field name="trululu"/>' +
                    '<field name="display_name"/>' +
                    '</form>',
                mockRPC: function (route, args) {
                    var result = this._super.apply(this, arguments);
                    if (args.method === 'onchange') {
                        return $.when(def).then(_.constant(result));
                    }
                    return result;
                },
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            var $input = form.$('.o_field_many2one input');
            testUtils.fields.editInput($input, "first");
            concurrency.delay(0).then(function () {
                var evOptions = {
                    which: $.ui.keyCode.TAB,
                    keyCode: $.ui.keyCode.TAB,
                };
                $input.trigger($.Event('keydown', evOptions));
                $input.trigger($.Event('keypress', evOptions));
                $input.trigger($.Event('keyup', evOptions));

                // simulate a focusout (e.g. because the user clicks outside)
                // before the onchange returns
                form.$('.o_field_char').focus();

                assert.strictEqual($('.modal').length, 0,
                    "there shouldn't be any modal in body");

                // unlock the onchange
                def.resolve();

                assert.strictEqual($input.val(), 'first record',
                    "first record should have been selected");
                assert.strictEqual($('.modal').length, 0,
                    "there shouldn't be any modal in body");
                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                form.destroy();
                done();
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

            testUtils.dom.click(list.$('td.o_data_cell:first'));
            testUtils.fields.editInput(list.$('td.o_data_cell input:first'), 'a');
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
                assert.strictEqual($('.modal').length, 0, "should not have any modal in DOM");
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

            testUtils.dom.click(list.$('td.o_data_cell:first'));
            testUtils.fields.editInput(list.$('td.o_data_cell input:first'), 'a');
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
                assert.strictEqual($('.modal').length, 0, "should not have any modal in DOM");
                assert.verifySteps(['name_search', 'onchange', 'write', 'read']);
                list.destroy();
                relationalFields.FieldMany2One.prototype.AUTOCOMPLETE_DELAY = M2O_DELAY;
                done();
            });
        });

        QUnit.test('many2one: domain updated by an onchange', function (assert) {
            assert.expect(2);

            this.data.partner.onchanges = {
                int_field: function () { },
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
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));
            // close the dropdown
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));
            // trigger an onchange that will update the domain
            testUtils.fields.editInput(form.$('.o_field_widget[name=int_field]'), 2);
            // trigger a name_search (domain should be [['id', 'in', [10]]])
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));

            form.destroy();
        });

        QUnit.test('many2one in one2many: domain updated by an onchange', function (assert) {
            assert.expect(3);

            this.data.partner.onchanges = {
                trululu: function () { },
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
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));

            // add a second row with another domain for the m2o
            domain = [['id', 'in', [5]]]; // domain for subrecord 2
            testUtils.dom.click(form.$('.o_field_x2many_list_row_add a'));
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));

            // check again the first row to ensure that the domain hasn't change
            domain = [['id', 'in', [10]]]; // domain for subrecord 1 should have been kept
            testUtils.dom.click(form.$('.o_data_row:first .o_data_cell'));
            testUtils.dom.click(form.$('.o_field_widget[name=trululu] input'));

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
            testUtils.form.clickEdit(form);
            testUtils.dom.click(form.$('.o_data_row td:contains(first record)'));
            testUtils.dom.click(form.$('.o_external_button'));
            assert.strictEqual($('.modal').length, 1,
                "should have one modal in body");

            // Changing the 'trululu' value
            testUtils.fields.editInput($('.modal input[name="display_name"]'), 'test');
            testUtils.dom.click($('.modal button.btn-primary'));

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

            testUtils.dom.click(form.$('.o_list_view thead th:nth(1)'));

            assert.strictEqual(form.$('.o_data_row .o_list_number').text(), '412',
                "should have correct order (ASC)");

            testUtils.dom.click(form.$('.o_list_view thead th:nth(1)'));

            assert.strictEqual(form.$('.o_data_row .o_list_number').text(), '214',
                "should have correct order (DESC)");

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
                                        '</form>'},
                mockRPC: function(route, args) {
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

        QUnit.test('one2many with extra field from server not in (inline) form', function (assert) {
            assert.expect(1);

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
                            '<form>' +
                                '<field name="display_name"/>' +
                            '</form>' +
                        '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

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

            form.destroy();
        });

        QUnit.test('one2many with extra X2many field from server not in inline form', function (assert) {
            assert.expect(1);

            var form = createView({
                View: FormView,
                model: 'partner',
                data: this.data,
                arch: '<form string="Partners">' +
                        '<field name="p" >' +
                            '<tree>' +
                                '<field name="turtles"/>' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="display_name"/>' +
                            '</form>' +
                        '</field>' +
                    '</form>',
                res_id: 1,
                viewOptions: {
                    mode: 'edit',
                },
            });

            var x2mList = form.$('.o_field_x2many_list[name=p]');

            // Add a first record in the list
            testUtils.dom.click(x2mList.find('.o_field_x2many_list_row_add a'));

            // Save & New
            testUtils.dom.click($('.modal-lg').find('.btn-primary').eq(1));

            // Save & Close
            testUtils.dom.click($('.modal-lg').find('.btn-primary').eq(0));

            assert.equal(x2mList.find('.o_data_row').length, 2,
                'There should be 2 records in the x2m list');

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
                arch:'<form>' +
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
                arch:'<form string="Partners">' +
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
