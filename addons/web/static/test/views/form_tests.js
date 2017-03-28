odoo.define('web.form_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var core = require('web.core');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var _t = core._t;
var createView = testUtils.createView;
var createAsyncView = testUtils.createAsyncView;

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: { string: "Displayed name", type: "char" },
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                    bar: {string: "Bar", type: "boolean"},
                    int_field: {string: "int_field", type: "integer", sortable: true},
                    qux: {string: "Qux", type: "float", digits: [16,1] },
                    p: {string: "one2many field", type: "one2many", relation: 'partner'},
                    trululu: {string: "Trululu", type: "many2one", relation: 'partner'},
                    timmy: { string: "pokemon", type: "many2many", relation: 'partner_type'},
                    product_id: {string: "Product", type: "many2one", relation: 'product'},
                    priority: {
                        string: "Priority",
                        type: "selection",
                        selection: [[1, "Low"], [2, "Medium"], [3, "High"]],
                        default: 1,
                    },
                    state: {string: "State", type: "selection", selection: [["ab", "AB"], ["cd", "CD"], ["ef", "EF"]]},
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
                    timmy: [],
                    trululu: 4,
                    state: "ab",
                    date: "2017-01-25",
                    datetime: "2016-12-12 10:55:05",
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
                    state: "cd",
                }, {
                    id: 4,
                    display_name: "aaa",
                    state: "ef",
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
        };
    }
}, function () {

    QUnit.module('FormView');

    QUnit.test('simple form rendering', function (assert) {
        assert.expect(10);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<div class="test" style="opacity: 0.5;">some html<span>aa</span></div>' +
                    '<sheet>' +
                        '<group>' +
                            '<group>' +
                                '<field name="foo"/>' +
                                '<field name="bar"/>' +
                                '<field name="int_field" string="f3_description"/>' +
                                '<field name="qux"/>' +
                            '</group>' +
                            '<group>' +
                                '<div class="hello"></div>' +
                            '</group>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="Partner Yo">' +
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
            res_id: 2,
        });
        assert.strictEqual(form.$('div.test').length, 1,
                        "should contain a div with some html");
        assert.strictEqual(form.$('div.test').css('opacity'), "0.5",
                        "should keep the inline style on html elements");
        assert.strictEqual(form.$('label:contains(Foo)').length, 1,
                        "should contain label Foo");
        assert.strictEqual(form.$('span:contains(blip)').length, 1,
                        "should contain span with field value");

        assert.strictEqual(form.$('label:contains(something_id)').length, 0,
                        "should not contain f3 string description");
        assert.strictEqual(form.$('label:contains(f3_description)').length, 1,
                        "should contain custom f3 string description");
        assert.strictEqual(form.$('div.o_field_one2many table').length, 1,
                        "should render a one2many relation");

        assert.strictEqual(form.$('tbody td:not(.o_list_record_selector) .o_checkbox input:checked').length, 1,
                        "1 checkboxes should be checked");

        assert.strictEqual(form.get('title'), "second record",
                        "title should be display_name of record");
        assert.strictEqual(form.$('label.o_form_label_empty:contains(timmy)').length, 0,
                        "the many2many label shouldn't be marked as empty");
        form.destroy();
    });

    QUnit.test('only necessary fields are fetched', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                // NOTE: actually, the current web client always request the __last_update
                // field, not sure why.  Maybe this test should be modified.
                assert.deepEqual(args.args[1], ["foo", "display_name"],
                    "should only fetch requested fields");
                return this._super(route, args);
            }
        });
        form.destroy();
    });

    QUnit.test('group rendering', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('table.o_inner_group').length, 1,
                        "should contain an inner group");
        form.destroy();
    });

    QUnit.test('invisible fields are not rendered', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" invisible="1"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                        '<field name="qux" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('label.o_form_invisible:contains(Foo)').length, 1,
                        "should not contain label Foo");
        assert.strictEqual(form.$('span.o_form_invisible:contains(yop)').length, 1,
                        "should not contain span with field value");
        assert.strictEqual(form.$('.o_form_field.o_form_invisible:contains(0.4)').length, 1,
                        "field qux should be invisible");
        form.destroy();
    });

    QUnit.test('invisible elements are properly hidden', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<group string="invgroup" invisible="1">' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="visible">' +
                            '</page>' +
                            '<page string="invisible" invisible="1">' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_notebook li.o_form_invisible a:contains(invisible)').length, 1,
                        "should not display tab invisible");
        assert.strictEqual(form.$('table.o_inner_group.o_form_invisible td:contains(invgroup)').length, 1,
                        "should not display invisible groups");
        form.destroy();
    });

    QUnit.test('invisible attrs are re-evaluated on field changed', function (assert) {
        assert.expect(3);

        // we set the value bar to simulate a falsy boolean value.
        this.data.partner.records[0].bar = false;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="product_id" invisible="1"/>' +
                        '<field name="timmy" invisible="1"/>' +
                        '<field name="foo" class="foo_field" attrs=\'{"invisible": [["product_id", "=", false]]}\'/>' +
                        '<field name="bar" class="bar_field" attrs=\'{"invisible":[("bar","=",False),("timmy","=",[])]}\'/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });


        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('.foo_field').hasClass('o_form_invisible'), 'should not display foo field');
        assert.ok(form.$('.bar_field').hasClass('o_form_invisible'), 'should not display bar field');

        // set a value on the m2o
        var $dropdown = form.$('.o_form_field_many2one input').autocomplete('widget');
        form.$('.o_form_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!form.$('.foo_field').hasClass('o_form_invisible'), 'should not display foo field');
        form.destroy();
    });

    QUnit.test('invisible attrs on first notebook page', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<notebook>' +
                            '<page string="Foo" attrs=\'{"invisible": [["product_id", "!=", false]]}\'>' +
                                '<field name="foo"/>' +
                            '</page>' +
                            '<page string="Bar">' +
                                '<field name="bar"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('.o_notebook .nav li:first()').hasClass('active'),
            'first tab should be active');
        assert.ok(!form.$('.o_notebook .nav li:first()').hasClass('o_form_invisible'),
            'first tab should be visible');

        // set a value on the m2o
        var $dropdown = form.$('.o_form_field_many2one input').autocomplete('widget');
        form.$('.o_form_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!form.$('.o_notebook .nav li:first()').hasClass('active'),
            'first tab should not be active');
        assert.ok(form.$('.o_notebook .nav li:first()').hasClass('o_form_invisible'),
            'first tab should be invisible');
        assert.ok(form.$('.o_notebook .nav li:nth(1)').hasClass('active'),
            'second tab should be active');
        assert.ok(form.$('.o_notebook .tab-content .tab-pane:nth(1)').hasClass('active'),
            'second page should be active');
        form.destroy();
    });

    QUnit.test('invisible attrs on group', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="bar"/>' +
                        '<group attrs=\'{"invisible": [["bar", "!=", true]]}\'>' +
                            '<group>' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1
        });

        assert.strictEqual(form.$('div.o_group:visible').length, 1, "should display the group");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('div.o_group:hidden').length, 1, "should not display the group");
        form.destroy();
    });

    QUnit.test('rendering stat buttons', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<div name="button_box">' +
                            '<button class="oe_stat_button">' +
                                '<field name="int_field"/>' +
                            '</button>' +
                            '<button class="oe_stat_button" attrs=\'{"invisible": [["bar", "=", true]]}\'>' +
                                '<field name="bar"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('button.oe_stat_button').length, 2,
                        "should have 2 stat buttons");
        assert.strictEqual(form.$('button.oe_stat_button.o_form_invisible').length, 1,
                        "should have 1 invisible stat buttons");

        var count = 0;
        testUtils.intercept(form, "execute_action", function () {
            count++;
        });
        form.$('.oe_stat_button').first().click();
        assert.strictEqual(count, 1, "should have triggered a execute action");
        form.destroy();
    });


    QUnit.test('label uses the string attribute', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<label for="bar" string="customstring"/>' +
                            '<div><field name="bar"/></div>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('label.o_form_label:contains(customstring)').length, 1,
                        "should have 1 label with correct string");
        form.destroy();
    });


    QUnit.test('empty fields have o_form_empty class in readonly mode', function (assert) {
        assert.expect(4);

        this.data.partner.fields.foo.default = false; // no default value for this test
        this.data.partner.records[1].foo = false;  // 1 is record with id=2
        this.data.partner.records[1].trululu = false;  // 1 is record with id=2
        this.data.partner.fields.trululu.readonly = true;
        this.data.partner.fields.int_field.readonly = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="trululu"/>' +
                            '<field name="int_field"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_form_field.o_form_field_empty').length, 2,
                            "should have 2 empty fields with correct class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 2,
                "should have 2 muted labels (for the empty fieds) in readonly");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_form_field_empty').length, 1,
                "in edit mode, only readonly fields should have .o_form_field_empty class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 1,
                "in edit mode, only readonly fields should have .o_form_label_empty class");
        form.destroy();
    });

    QUnit.test('empty inner readonly fields don\'t have o_form_empty class in "create" mode', function (assert) {
        assert.expect(2);

        this.data.partner.fields.product_id.readonly = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<group>' +
                                '<field name="product_id"/>' +
                            '</group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });
        assert.strictEqual(form.$('.o_form_label_empty').length, 0,
                "no empty class on label");
        assert.strictEqual(form.$('.o_form_field_empty').length, 0,
                "no empty class on field");
        form.destroy();
    });

    QUnit.test('form view can switch to edit mode', function (assert) {
        assert.expect(9);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');
        assert.ok(form.$('.o_form_view').hasClass('o_form_readonly'),
                    'form view should have .o_form_readonly');
        assert.ok(form.$buttons.find('.o_form_buttons_view').is(':visible'),
            'readonly buttons should be visible');
        assert.ok(!form.$buttons.find('.o_form_buttons_edit').is(':visible'),
            'edit buttons should not be visible');
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.mode, 'edit', 'form view should be in edit mode');
        assert.ok(form.$el.hasClass('o_form_editable'),
                    'form view should have .o_form_editable');
        assert.ok(!form.$el.hasClass('o_form_readonly'),
                    'form view should not have .o_form_readonly');
        assert.ok(!form.$buttons.find('.o_form_buttons_view').is(':visible'),
            'readonly buttons should not be visible');
        assert.ok(form.$buttons.find('.o_form_buttons_edit').is(':visible'),
            'edit buttons should be visible');
        form.destroy();
    });

    QUnit.test('required fields should have o_form_required in readonly mode', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.required = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('span.o_form_required').length, 1,
                            "should have 1 span with o_form_required class");

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_form_required').length, 1,
                            "in edit mode, should have 1 input with o_form_required");
        form.destroy();
    });

    QUnit.test('separators', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<separator string="Geolocation"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('div.o_horizontal_separator').length, 1,
                        "should contain a separator div");
        form.destroy();
    });

    QUnit.test('buttons in form view', function (assert) {
        assert.expect(7);

        var rpcCount = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="post" class="p" states="ab,ef" string="Confirm" type="object"/>' +
                        '<button name="some_method" class="s" string="Do it" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });
        assert.strictEqual(form.$('button.btn.btn-sm div.fa.fa-check').length, 1,
                        "should contain a button with correct content");

        assert.strictEqual(form.$('.o_form_statusbar button').length, 2,
            "should have 2 buttons in the statusbar");

        assert.strictEqual(form.$('.o_form_statusbar button:visible').length, 1,
            "should have only 1 visible button in the statusbar");

        testUtils.intercept(form, 'execute_action', function (event) {
            assert.strictEqual(event.data.action_data.name, "post",
                "should trigger execute_action with correct method name");
            assert.strictEqual(event.data.record_id, 2, "should have correct id in event data");
            event.data.on_success();
        });
        rpcCount = 0;
        form.$('.o_form_statusbar button.p').click();

        assert.strictEqual(rpcCount, 1, "should have done 1 rpcs to reload");

        testUtils.intercept(form, 'execute_action', function (event) {
            event.data.on_fail();
        });
        form.$('.o_form_statusbar button.s').click();

        assert.strictEqual(rpcCount, 2, "should have done 1 rpcs to reload");
        form.destroy();
    });


    QUnit.test('buttons in form view, new record', function (assert) {
        // this simulates a situation similar to the settings forms.
        assert.expect(1);

        var rpcCount = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button name="post" class="p" string="Confirm" type="object"/>' +
                        '<button name="some_method" class="s" string="Do it" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<button string="Geolocate" name="geo_localize" icon="fa-check" type="object"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function () {
                rpcCount++;
                return this._super.apply(this, arguments);
            },
        });

        testUtils.intercept(form, 'execute_action', function (event) {
            event.data.on_success();
        });
        rpcCount = 0;
        form.$('.o_form_statusbar button.p').click();

        assert.strictEqual(rpcCount, 3,
            "should have done 3 rpcs: 1 create, 1 read (before _callButtonAction, and 1 read (after)");
        form.destroy();
    });

    QUnit.test('change and save char', function (assert) {
        assert.expect(6);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/></group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.ok(true, "should call the /write route");
                }
                return this._super(route, args);
            },
            res_id: 2,
        });

        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');
        assert.strictEqual(form.$('span:contains(blip)').length, 1,
                        "should contain span with field value");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.mode, 'edit', 'form view should be in edit mode');
        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');
        assert.strictEqual(form.$('span:contains(tralala)').length, 1,
                        "should contain span with field value");
        form.destroy();
    });

    QUnit.test('properly reload data from server', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/></group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    args.args[1].foo = "apple";
                }
                return this._super(route, args);
            },
            res_id: 2,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('span:contains(apple)').length, 1,
                        "should contain span with field value");
        form.destroy();
    });

    QUnit.test('properly apply onchange in simple case', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/><field name="int_field"/></group>' +
                '</form>',
            res_id: 2,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('input').eq(1).val(), "9",
                        "should contain input with initial value");

        form.$('input').first().val("tralala").trigger('input');

        assert.strictEqual(form.$('input').eq(1).val(), "1007",
                        "should contain input with onchange applied");
        form.destroy();
    });

    QUnit.test('onchange send only the present fields to the server', function (assert) {
        assert.expect(1);
        this.data.partner.records[0].product_id = false;
        this.data.partner.onchanges.foo = function (obj) {
            obj.foo = obj.foo + " alligator";
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="bar"/>' +
                            '<field name="product_id"/>' +
                        '</tree>' +
                    '</field>' +
                    '<field name="timmy"/>' +
                '</form>',
            archs: {
                "partner_type,false,list": '<tree><field name="name"/></tree>'
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(args.args[3], 
                        {"foo": "1", "p": "", "p.bar": "", "p.display_name": "", "p.product_id": "", "timmy": "", "timmy.name": ""},
                        "should send only the fields used in the views");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input:first').val("tralala").trigger('input');

        form.destroy();
    });

    QUnit.test('evaluate in python field options', function (assert) {
        assert.expect(1);

        var isOk = false;
        var tmp = py.eval;
        py.eval = function (expr) {
            if (expr === "{'horizontal': true}") {
                isOk = true;
            }
            return tmp.apply(tmp, arguments);
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" options="{\'horizontal\': true}"/>' +
                '</form>',
            res_id: 2,
        });

        py.eval = tmp;

        assert.ok(isOk, "should have evaluated the field options");
        form.destroy();
    });

    QUnit.test('can create a record with default values', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        var n = this.data.partner.records.length;

        form.$buttons.find('.o_form_button_create').click();
        assert.strictEqual(form.mode, 'edit', 'form view should be in edit mode');

        assert.strictEqual(form.$('input:first').val(), "My little Foo Value",
                "should have correct default_get value");
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');
        assert.strictEqual(this.data.partner.records.length, n + 1, "should have created a record");
        form.destroy();
    });

    QUnit.test('sidebar is hidden when switching to edit mode', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="foo"/>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {sidebar: true},
            res_id: 1,
        });

        assert.ok(!form.sidebar.$el.hasClass('o_hidden'), 'sidebar should be visible');
        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.sidebar.$el.hasClass('o_hidden'), 'sidebar should be invisible');
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok(!form.sidebar.$el.hasClass('o_hidden'), 'sidebar should be visible');
        form.destroy();
    });

    QUnit.test('basic default record', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.default = "default foo value";

        var count = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            mockRPC: function (route, args) {
                count++;
                return this._super(route, args);
            },
        });

        assert.strictEqual(form.$('input').val(), "default foo value", "should have correct default");
        assert.strictEqual(count, 1, "should do only one rpc");
        form.destroy();
    });


    QUnit.test('make default record with non empty one2many', function (assert) {
        assert.expect(4);

        this.data.partner.fields.p.default = [
            [6, 0, []],                  // replace with zero ids
            [0, 0, {foo: "new foo1", product_id: 41}],   // create a new value
            [0, 0, {foo: "new foo2", product_id: 37}],   // create a new value
        ];

        var nameGetCount = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="foo"/>' +
                            '<field name="product_id"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    nameGetCount++;
                }
                return this._super(route, args);
            },
        });
        assert.ok(form.$('td:contains(new foo1)').length,
            "should have new foo1 value in one2many");
        assert.ok(form.$('td:contains(new foo2)').length,
            "should have new foo2 value in one2many");
        assert.ok(form.$('td:contains(xphone)').length,
            "should have a cell with the name field 'product_id', set to xphone");
        assert.strictEqual(nameGetCount, 1, "should have done only 1 nameget");
        form.destroy();
    });

    QUnit.test('make default record with non empty many2one', function (assert) {
        var done = assert.async();
        assert.expect(2);

        this.data.partner.fields.trululu.default = 4;

        var nameGetCount = 0;

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners"><field name="trululu"/></form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_get') {
                    nameGetCount++;
                    var result = this._super.apply(this, arguments);
                    return concurrency.delay(1).then(function () {
                        return result;
                    });
                }
                return this._super.apply(this, arguments);
            },
        }).then(function (form) {
            assert.ok(form.$('.o_form_input').val(), 'aaa',
            'default value should be correctly displayed');
            assert.strictEqual(nameGetCount, 1, 'should have done one name_get');
            form.destroy();
            done();
        });
    });

    QUnit.test('form view properly change its title', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.get('title'), 'first record',
            "should have the display name of the record as  title");
        form.$buttons.find('.o_form_button_create').click();
        assert.strictEqual(form.get('title'), _t("New"),
            "should have the display name of the record as  title");
        form.destroy();
    });

    QUnit.test('can duplicate a record', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {sidebar: true},
        });

        assert.strictEqual(form.get('title'), 'first record',
            "should have the display name of the record as  title");
        form.sidebar.$('a:contains(Duplicate)').click();

        assert.strictEqual(form.get('title'), 'first record (copy)',
            "should have duplicated the record");

        assert.strictEqual(form.mode, "edit", 'should be in edit mode');
        form.destroy();
    });

    QUnit.test('buttons in footer are moved to $buttons if required', function (assert) {
        // not sure about this test...
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                        '<footer>' +
                            '<button string="Create" type="object" class="infooter"/>' +
                        '</footer>' +
                '</form>',
            res_id: 1,
            viewOptions: {footer_to_buttons: true},
        });

        assert.ok(form.$buttons.find('button.infooter').length, "footer button should be in footer");
        assert.ok(!form.$('button.infooter').length, "footer button should not be in form");
        form.destroy();
    });

    QUnit.test('clicking on stat buttons in edit mode', function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<div name="button_box">' +
                            '<button class="oe_stat_button">' +
                                '<field name="bar"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.strictEqual(args.args[1].foo, "tralala", "should have saved the changes");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        var count = 0;
        testUtils.intercept(form, "execute_action", function (event) {
            event.stopPropagation();
            count++;
        });
        form.$('.oe_stat_button').first().click();
        assert.strictEqual(count, 1, "should have triggered a execute action");
        assert.strictEqual(form.mode, "readonly", "form view should be in readonly mode");


        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("tralala").trigger('input');
        form.$('.oe_stat_button').first().click();

        assert.strictEqual(form.mode, "readonly", "form view should be in readonly mode");
        assert.strictEqual(count, 2, "should have triggered a execute action");
        form.destroy();
    });

    QUnit.test('buttons with attr "special" do not trigger a save', function (assert) {
        assert.expect(4);

        var executeActionCount = 0;
        var writeCount = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                        '<button string="Do something" class="btn-primary" name="abc" type="object"/>' +
                        '<button string="Discard" class="btn-default" special="cancel"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    writeCount++;
                }
                return this._super(route, args);
            }
        });
        testUtils.intercept(form, "execute_action", function () {
            executeActionCount++;
        });

        form.$buttons.find('.o_form_button_edit').click();

        // make the record dirty
        form.$('input').val("tralala").trigger('input');


        form.$('button').eq(0).click();
        assert.strictEqual(writeCount, 1, "should have triggered a write");
        assert.strictEqual(executeActionCount, 1, "should have triggered a execute action");

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("abcdef").trigger('input');

        form.$('button').eq(1).click();
        assert.strictEqual(writeCount, 1, "should not have triggered a write");
        assert.strictEqual(executeActionCount, 2, "should have triggered a execute action");
        form.destroy();
    });

    QUnit.test('missing widgets do not crash', function (assert) {
        assert.expect(1);

        this.data.partner.fields.foo.type = 'new field type without widget';
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('.o_field_widget').length, 1, "should have rendered an abstract field");
        form.destroy();
    });

    QUnit.test('nolabel', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<group class="firstgroup"><field name="foo" nolabel="1"/></group>' +
                            '<group class="secondgroup">'+
                                '<field name="product_id"/>' +
                                '<field name="int_field" nolabel="1"/><field name="qux" nolabel="1"/>' +
                            '</group>' +
                            '<group><field name="bar"/></group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$("label").length, 2, "should have rendered only two label");
        assert.strictEqual(form.$("label").first().text(), "Product",
            "one should be the one for the product field");
        assert.strictEqual(form.$("label").eq(1).text(), "Bar",
            "one should be the one for the bar field");

        assert.strictEqual(form.$('.firstgroup td').first().attr('colspan'), "1",
            "foo td should have a colspan of 1");
        assert.strictEqual(form.$('.secondgroup tr').length, 2,
            "int_field and qux should have same tr");

        assert.strictEqual(form.$('.secondgroup tr:first td').length, 2,
            "product_id field should be on its own tr");
        form.destroy();
    });

    QUnit.test('many2one in a one2many', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].product_id = 37;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="product_id"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('td:contains(xphone)').length, 1,
            "should display the name of the many2one");
        form.destroy();
    });

    QUnit.test('discard changes on a non dirty form view', function (assert) {
        assert.expect(4);

        var nbWrite = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            res_id: 1,
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    nbWrite++;
                }
                return this._super.apply(this, arguments);
            },
        });

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'yop', 'input should contain yop');

        // click on discard
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok(!$('.modal').length, 'no confirm modal should be displayed');
        assert.strictEqual(form.$('.o_form_field').text(), 'yop', 'field in readonly should display yop');

        assert.strictEqual(nbWrite, 0, 'no write RPC should have been done');
        form.destroy();
    });

    QUnit.test('discard changes on a dirty form view', function (assert) {
        assert.expect(7);

        var nbWrite = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            res_id: 1,
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    nbWrite++;
                }
                return this._super.apply(this, arguments);
            },
        });

        // switch to edit mode and edit the foo field
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'yop', 'input should contain yop');
        form.$('.o_form_input').val('new value').trigger('input');
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should contain new value');

        // click on discard and cancel the confirm request
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-default').click(); // click on cancel
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should still contain new value');

        // click on discard and confirm
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('.o_form_field').text(), 'yop', 'field in readonly should display yop');

        assert.strictEqual(nbWrite, 0, 'no write RPC should have been done');
        form.destroy();
    });

    QUnit.test('discard changes on a new (non dirty, except for defaults) form view', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.default = "ABC";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
        });

        // switch to edit mode and edit the foo field
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'ABC', 'input should contain ABC');

        form.$buttons.find('.o_form_button_cancel').click();

        assert.strictEqual($('.modal').length, 0,
            'there should not be a confirm modal');

        form.destroy();
    });

    QUnit.test('discard changes on a duplicated record', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            res_id: 1,
            viewOptions: {sidebar: true},
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        form.sidebar.$('a:contains(Duplicate)').click();

        assert.strictEqual(form.$('.o_form_input').val(), 'tralala', 'input should contain ABC');

        form.$buttons.find('.o_form_button_cancel').click();

        assert.strictEqual($('.modal').length, 0,
            'there should not be a confirm modal');

        form.destroy();
    });

    QUnit.test('switching to another record from a dirty one', function (assert) {
        assert.expect(11);

        var nbWrite = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    nbWrite++;
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "2", 'pager limit should be 2');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'yop', 'input should contain yop');

        // edit the foo field
        form.$('.o_form_input').val('new value').trigger('input');
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should contain new value');

        // click on the pager to switch to the next record and cancel the confirm request
        form.pager.$('.o_pager_next').click(); // click on next
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-default').click(); // click on cancel
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should still contain new value');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should still be 1');

        // click on the pager to switch to the next record and confirm
        form.pager.$('.o_pager_next').click(); // click on next
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('.o_form_input').val(), 'blip', 'input should contain blip');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "2", 'pager value should be 2');

        assert.strictEqual(nbWrite, 0, 'no write RPC should have been done');
        form.destroy();
    });

    QUnit.test('handling dirty state: switching to another record', function (assert) {
        assert.expect(12);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"></field>' +
                    '<field name="priority" widget="priority"></field>' +
                '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
        });
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'yop', 'input should contain yop');

        // edit the foo field
        form.$('.o_form_input').val('new value').trigger('input');
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should contain new value');

        form.$buttons.find('.o_form_button_save').click();

        // click on the pager to switch to the next record and cancel the confirm request
        form.pager.$('.o_pager_next').click(); // click on next
        assert.strictEqual($('.modal').length, 0, 'no confirm modal should be displayed');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "2", 'pager value should be 2');

        assert.strictEqual(form.$('.o_priority .fa-star-o').length, 2,
            'priority widget should have been rendered with correct value');

        // edit the value in readonly
        form.$('.o_priority .fa-star-o:first').click(); // click on the first star
        assert.strictEqual(form.$('.o_priority .fa-star').length, 1,
            'priority widget should have been updated');

        form.pager.$('.o_pager_next').click(); // click on next
        assert.strictEqual($('.modal').length, 0, 'no confirm modal should be displayed');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_input').val(), 'new value', 'input should contain yop');

        // edit the foo field
        form.$('.o_form_input').val('wrong value').trigger('input');

        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        $('.modal .modal-footer .btn-primary').click(); // click on confirm
        form.pager.$('.o_pager_next').click(); // click on next
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "2", 'pager value should be 2');
        form.destroy();
    });

    QUnit.test('restore local state when switching to another record', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<notebook>' +
                            '<page string="First Page" name="first">' +
                                '<field name="foo"/>' +
                            '</page>' +
                            '<page string="Second page" name="second">' +
                                '<field name="bar"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
        });

        // click on second page tab
        form.$('.o_notebook li:eq(1) a').click();

        assert.notOk(form.$('.o_notebook li:eq(0)').hasClass('active'),
            "first tab should not be active");
        assert.ok(form.$('.o_notebook li:eq(1)').hasClass('active'),
            "second tab should be active");

        // click on the pager to switch to the next record
        form.pager.$('.o_pager_next').click();

        assert.notOk(form.$('.o_notebook li:eq(0)').hasClass('active'),
            "first tab should not be active");
        assert.ok(form.$('.o_notebook li:eq(1)').hasClass('active'),
            "second tab should be active");
        form.destroy();
    });

    QUnit.test('pager is hidden in create mode', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
        });

        assert.ok(form.pager.$el.is(':visible'), "pager should be visible");
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1",
            "current pager value should be 1");
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "2",
            "current pager limit should be 1");
        form.$buttons.find('.o_form_button_create').click();

        assert.notOk(form.pager.$el.is(':visible'), "pager should not be visible");
        form.$buttons.find('.o_form_button_save').click();

        assert.ok(form.pager.$el.is(':visible'), "pager should be visible");
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "3",
            "current pager value should be 3");
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "3",
            "current pager limit should be 3");
        form.destroy();
    });

    QUnit.test('switching to another record, in readonly mode', function (assert) {
        assert.expect(5);

        var pushStateCount = 0;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
            intercepts: {
                push_state: function (event) {
                    pushStateCount++;
                }
            }
        });

        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        form.pager.$('.o_pager_next').click(); // click on next

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "2", 'pager value should be 2');
        assert.strictEqual(form.mode, 'readonly', 'form view should be in readonly mode');

        assert.strictEqual(pushStateCount, 2, "should have triggered 2 push_state");
        form.destroy();
    });

    QUnit.test('modifiers are reevaluated when creating new record', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="foo" class="foo_field" attrs=\'{"invisible": [["bar", "=", True]]}\'/>' +
                        '<field name="bar"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('span.foo_field').length, 1, "should have a span foo field");

        assert.ok(!form.$('span.foo_field').is(':visible'),
                        "foo field should not be visible");

        form.$buttons.find('.o_form_button_create').click();

        assert.strictEqual(form.$('input.foo_field').length, 1,
            "should have a visible input for foo field");

        assert.ok(form.$('input.foo_field').is(':visible'),
                        "foo field should be visible");
        form.destroy();
    });

    QUnit.test('empty readonly fields are visible on new records', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.readonly = true;
        this.data.partner.fields.foo.default = undefined;
        this.data.partner.records[0].foo = undefined;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="foo"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_form_field_empty').length, 1,
            'readonly field should be invisible on an existing record');

        form.$buttons.find('.o_form_button_create').click();

        assert.strictEqual(form.$('.o_form_field_empty').length, 0,
            'readonly field should be visible on a new record');
        form.destroy();
    });


    QUnit.test('all group children have correct layout classname', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<group class="inner_group">' +
                            '<field name="name"/>' +
                        '</group>' +
                        '<div class="inner_div">' +
                            '<field name="foo"/>' +
                        '</div>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('.inner_group').hasClass('o_group_col_6'),
            "inner groups should have classname 'o_group_col_6'");
        assert.ok(form.$('.inner_div').hasClass('o_group_col_6'),
            "divs inside groups should have classname 'o_group_col_6'");
        form.destroy();
    });

    QUnit.test('deleting a record', function (assert) {
        assert.expect(8);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            viewOptions: {
                ids: [1, 2, 4],
                index: 0,
                sidebar: true,
            },
            res_id: 1,
        });

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "3", 'pager limit should be 3');
        assert.strictEqual(form.$('span:contains(yop)').length, 1,
            'should have a field with foo value for record 1');
        assert.ok(!$('.modal').length, 'no confirm modal should be displayed');

        // open sidebar
        form.sidebar.$('button.o_dropdown_toggler_btn').click();
        form.sidebar.$('a:contains(Delete)').click();

        assert.ok($('.modal').length, 'a confirm modal should be displayed');

        // confirm the delete
        $('.modal .modal-footer button.btn-primary').click();

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "2", 'pager limit should be 2');
        assert.strictEqual(form.$('span:contains(blip)').length, 1,
            'should have a field with foo value for record 2');
        form.destroy();
    });

    QUnit.test('empty required fields cannot be saved', function (assert) {
        assert.expect(5);

        this.data.partner.fields.foo.required = true;
        delete this.data.partner.fields.foo.default;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<group><field name="foo"/></group>' +
                '</form>',
        });

        testUtils.intercept(form, 'warning', function (event) {
            assert.strictEqual(event.data.title, 'The following fields are invalid:',
                "should have a warning with correct title");
            assert.strictEqual(event.data.message, '<ul><li>Foo</li></ul>',
                "should have a warning with correct message");
        });

        form.$buttons.find('.o_form_button_save').click();
        assert.ok(form.$('label').hasClass('o_form_invalid'),
            "label should be tagged as invalid");
        assert.ok(form.$('input').hasClass('o_form_invalid'),
            "input should be tagged as invalid");

        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_form_invalid').length, 0,
            "nothing should be marked as invalid");
        form.destroy();
    });

    QUnit.test('changes in a readonly form view are saved directly', function (assert) {
        assert.expect(10);

        var nbWrite = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="priority" widget="priority"/>' +
                        '</group>' +
                '</form>',
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    nbWrite++;
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_priority .o_priority_star').length, 2,
            'priority widget should have been rendered');
        assert.strictEqual(form.$('.o_priority .fa-star-o').length, 2,
            'priority widget should have been rendered with correct value');

        // edit the value in readonly
        form.$('.o_priority .fa-star-o:first').click(); // click on the first star
        assert.strictEqual(nbWrite, 1, 'should have saved directly');
        assert.strictEqual(form.$('.o_priority .fa-star').length, 1,
            'priority widget should have been updated');

        // switch to edit mode and edit the value again
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_priority .o_priority_star').length, 2,
            'priority widget should have been correctly rendered');
        assert.strictEqual(form.$('.o_priority .fa-star').length, 1,
            'priority widget should have correct value');
        form.$('.o_priority .fa-star-o:first').click(); // click on the second star
        assert.strictEqual(nbWrite, 1, 'should not have saved directly');
        assert.strictEqual(form.$('.o_priority .fa-star').length, 2,
            'priority widget should have been updated');

        // save
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(nbWrite, 2, 'should not have saved directly');
        assert.strictEqual(form.$('.o_priority .fa-star').length, 2,
            'priority widget should have correct value');
        form.destroy();
    });

    QUnit.test('display a dialog if onchange result is a warning', function (assert) {
        assert.expect(5);

        this.data.partner.onchanges = { foo: true };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/><field name="int_field"/></group>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({
                        value: { int_field: 10 },
                        warning: {
                            title: "Warning",
                            message: "You must first select a partner"
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                warning: function (event) {
                    assert.strictEqual(event.data.type, 'dialog',
                        "should have triggered an event with the correct data");
                    assert.strictEqual(event.data.title, "Warning",
                        "should have triggered an event with the correct data");
                    assert.strictEqual(event.data.message, "You must first select a partner",
                        "should have triggered an event with the correct data");
                },
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_form_input[name=int_field]').val(), '9',
            "'int_field' value should be 9 before the change");

        form.$('input').first().val("tralala").trigger('input');

        assert.strictEqual(form.$('.o_form_input[name=int_field]').val(), '10',
            "the onchange should have been correctly applied");

        form.destroy();
    });

    QUnit.test('attrs are properly transmitted to new records', function (assert) {
        assert.expect(2);

        // this test checks that the fieldsInfo have been transmitted to the
        // load function when creating a new record

        var terminology = {
            string_true: "Production Environment",
            hover_true: "Switch to test environment",
            string_false: "Test Environment",
            hover_false: "Switch to production environment"
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="bar" widget="boolean_button" options=\'{"terminology": ' +
                            JSON.stringify(terminology) + '}\'/>' +
                    '</group>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_stat_text.o_not_hover:contains(Production Environment)').length, 1,
            "button should contain correct string");

        form.$buttons.find('.o_form_button_create').click();

        assert.strictEqual(form.$('.o_stat_text.o_not_hover:contains(Test Environment)').length, 1,
            "button should contain correct string");

        form.destroy();
    });

    QUnit.test('button box is not rendered in create mode', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<div name="button_box" class="oe_button_box">' +
                        '<button type="object" class="oe_stat_button" icon="fa-check-square">' +
                            '<field name="bar"/>' +
                        '</button>' +
                    '</div>' +
                '</form>',
            res_id: 2,
        });

        // readonly mode
        assert.strictEqual(form.$('.oe_stat_button').length, 1,
            "button box should be displayed in readonly");

        // edit mode
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.oe_stat_button').length, 1,
            "button box should be displayed in edit on an existing record");

        // create mode
        form.$buttons.find('.o_form_button_create').click();
        assert.strictEqual(form.$('.oe_stat_button').length, 0,
            "button box should not be displayed when creating a new record");

        form.destroy();
    });

    QUnit.test('properly apply onchange on many2many fields', function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.timmy = [
                    [5],
                    [1, 12, {display_name: "gold"}],
                ];
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/></group>' +
                    '<field name="timmy">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_form_field_many2many .o_data_row').length, 0,
            "there should be no many2many record linked at first");

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_form_input').val('let us trigger an onchange').trigger('input');
        assert.strictEqual(form.$('.o_form_field_many2many .o_data_row').length, 1,
            "there should be one linked record");
        assert.strictEqual(form.$('.o_form_field_many2many .o_data_row td:first').text(), 'gold',
            "the 'display_name' of the many2many record should be correctly displayed");

        form.destroy();
    });

    QUnit.test('onchanges on date(time) fields', function (assert) {
        assert.expect(6);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.date = '2021-12-12';
                obj.datetime = '2021-12-12 10:55:05';
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="date"/>' +
                        '<field name="datetime"/>' +
                    '</group>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_form_field[name=date]').text(),
            '01/25/2017', "the initial date should be correct");
        assert.strictEqual(form.$('.o_form_field[name=datetime]').text(),
            '12/12/2016 10:55:05', "the initial datetime should be correct");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_form_field[name=date] input').val(),
            '01/25/2017', "the initial date should be correct in edit");
        assert.strictEqual(form.$('.o_form_field[name=datetime] input').val(),
            '12/12/2016 10:55:05', "the initial datetime should be correct in edit");

        // trigger the onchange
        form.$('.o_form_field[name="foo"]').val("coucou").trigger('input');

        assert.strictEqual(form.$('.o_form_field[name=date] input').val(),
            '12/12/2021', "the initial date should be correct in edit");
        assert.strictEqual(form.$('.o_form_field[name=datetime] input').val(),
            '12/12/2021 10:55:05', "the initial datetime should be correct in edit");

        form.destroy();
    });

    QUnit.test('onchanges are not sent for each keystrokes', function (assert) {
        var done = assert.async();
        assert.expect(5);

        var onchangeNbr = 0;

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.int_field = obj.foo.length + 1000;
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group><field name="foo"/><field name="int_field"/></group>' +
                '</form>',
            res_id: 2,
            fieldDebounce: 3,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    onchangeNbr++;
                    return concurrency.delay(3).then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        form.$('input').first().val("1").trigger('input');
        assert.strictEqual(onchangeNbr, 0, "no onchange has been called yet");
        form.$('input').first().val("12").trigger('input');
        assert.strictEqual(onchangeNbr, 0, "no onchange has been called yet");

        return concurrency.delay(75).then(function () {
            assert.strictEqual(onchangeNbr, 1, "one onchange has been called");

            // add something in the input, then focus another input
            form.$('input').first().val("123").trigger('input');
            form.$('input').first().focusout();
            assert.strictEqual(onchangeNbr, 2,
                "one onchange has been called immediately");

            return concurrency.delay(75);
        }).then(function () {
            assert.strictEqual(onchangeNbr, 2,
                "no extra onchange should have been called");

            form.destroy();
            done();
        });
    });

});
});
