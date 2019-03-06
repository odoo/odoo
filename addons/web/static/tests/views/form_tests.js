odoo.define('web.form_tests', function (require) {
"use strict";

var BasicModel = require('web.BasicModel');
var concurrency = require('web.concurrency');
var config = require('web.config');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');
var FormView = require('web.FormView');
var mixins = require('web.mixins');
var NotificationService = require('web.NotificationService');
var pyUtils = require('web.py_utils');
var testUtils = require('web.test_utils');
var widgetRegistry = require('web.widget_registry');
var Widget = require('web.Widget');

var _t = core._t;
var createView = testUtils.createView;
var createAsyncView = testUtils.createAsyncView;
var createActionManager = testUtils.createActionManager;

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
                    product_ids: {string: "one2many product", type: "one2many", relation: "product"},
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
                }, {
                    id: 5,
                    display_name: "aaa",
                    foo:'',
                    bar:false,
                    state: "ef",
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"},
                    partner_type_id: {string: "Partner type", type: "many2one", relation: "partner_type"},
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
        };

        this.actions = [{
            id: 1,
            name: 'Partners Action 1',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'kanban'], [false, 'form']],
        }];
    }
}, function () {

    QUnit.module('FormView');

    QUnit.test('simple form rendering', function (assert) {
        assert.expect(12);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<div class="test" style="opacity: 0.5;">some html<span>aa</span></div>' +
                    '<sheet>' +
                        '<group>' +
                            '<group style="background-color: red">' +
                                '<field name="foo" style="color: blue"/>' +
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

        assert.strictEqual(form.$('.o_group .o_group:first').attr('style'), 'background-color: red',
                        "should apply style attribute on groups");
        assert.strictEqual(form.$('.o_field_widget[name=foo]').attr('style'), 'color: blue',
                        "should apply style attribute on fields");

        assert.strictEqual(form.$('label:contains(something_id)').length, 0,
                        "should not contain f3 string description");
        assert.strictEqual(form.$('label:contains(f3_description)').length, 1,
                        "should contain custom f3 string description");
        assert.strictEqual(form.$('div.o_field_one2many table').length, 1,
                        "should render a one2many relation");

        assert.strictEqual(form.$('tbody td:not(.o_list_record_selector) .custom-checkbox input:checked').length, 1,
                        "1 checkboxes should be checked");

        assert.strictEqual(form.get('title'), "second record",
                        "title should be display_name of record");
        assert.strictEqual(form.$('label.o_form_label_empty:contains(timmy)').length, 0,
                        "the many2many label shouldn't be marked as empty");
        form.destroy();
    });

    QUnit.test('attributes are transferred on async widgets', function (assert) {
        assert.expect(1);

        var def = $.Deferred();

        var FieldChar = fieldRegistry.get('char');
        fieldRegistry.add('asyncwidget', FieldChar.extend({
            willStart: function () {
                return def;
            },
        }));

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group>' +
                        '<field name="foo" style="color: blue" widget="asyncwidget"/>' +
                    '</group>' +
                '</form>',
            res_id: 2,
        }).then(function (form) {
            assert.strictEqual(form.$('.o_field_widget[name=foo]').attr('style'), 'color: blue',
                "should apply style attribute on fields");
            form.destroy();
            delete fieldRegistry.map.asyncwidget;
        });
        def.resolve();
    });

    QUnit.test('decoration works on widgets', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="display_name" decoration-danger="int_field &lt; 5"/>' +
                    '<field name="foo" decoration-danger="int_field &gt; 5"/>' +
                '</form>',
            res_id: 2,
        });
        assert.ok(!form.$('span[name="display_name"]').hasClass('text-danger'),
            'field display name should not have decoration');
        assert.ok(form.$('span[name="foo"]').hasClass('text-danger'),
            'field foo should have decoration');
        form.destroy();
    });

    QUnit.test('decoration on widgets are reevaluated if necessary', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field"/>' +
                    '<field name="display_name" decoration-danger="int_field &lt; 5"/>' +
                '</form>',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });
        assert.ok(!form.$('input[name="display_name"]').hasClass('text-danger'),
            'field display name should not have decoration');
        form.$('input[name="int_field"]').val(3).trigger('input');
        assert.ok(form.$('input[name="display_name"]').hasClass('text-danger'),
            'field display name should now have decoration');
        form.destroy();
    });

    QUnit.test('decoration on widgets works on same widget', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="int_field" decoration-danger="int_field &lt; 5"/>' +
                '</form>',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });
        assert.ok(!form.$('input[name="int_field"]').hasClass('text-danger'),
            'field should not have decoration');
        form.$('input[name="int_field"]').val(3).trigger('input');
        assert.ok(form.$('input[name="int_field"]').hasClass('text-danger'),
            'field should now have decoration');
        form.destroy();
    });

    QUnit.test('only necessary fields are fetched with correct context', function (assert) {
        assert.expect(2);

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
                assert.deepEqual(args.kwargs.context, {bin_size: true},
                    "bin_size should always be in the context");
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
    QUnit.test('Form and subview with _view_ref contexts', function (assert) {
        assert.expect(2);

        this.data.product.fields.partner_type_ids = {string: "one2many field", type: "one2many", relation: "partner_type"},
        this.data.product.records = [{id: 1, name: 'Tromblon', partner_type_ids: [12,14]}];
        this.data.partner.records[0].product_id = 1;

        var actionManager = createActionManager({
            data: this.data,
            archs: {
                'product,false,form': '<form>'+
                                            '<field name="name"/>'+
                                            '<field name="partner_type_ids" context="{\'tree_view_ref\': \'some_other_tree_view\'}"/>' +
                                        '</form>',

                'partner_type,false,list': '<tree>'+
                                                '<field name="color"/>'+
                                            '</tree>',
                'product,false,search': '<search></search>',
            },
            mockRPC: function (route, args) {
                if (args.method === 'load_views') {
                    var context = args.kwargs.context;
                    if (args.model === 'product') {
                        assert.deepEqual(context, {tree_view_ref: 'some_tree_view'},
                            'The correct _view_ref should have been sent to the server, first time');
                    }
                    if (args.model === 'partner_type') {
                        assert.deepEqual(context, {tree_view_ref: 'some_other_tree_view'},
                            'The correct _view_ref should have been sent to the server for the subview');
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                     '<field name="name"/>' +
                     '<field name="product_id" context="{\'tree_view_ref\': \'some_tree_view\'}"/>' +
                  '</form>',
            res_id: 1,

            mockRPC: function(route, args) {
                if (args.method === 'get_formview_action') {
                    return $.when({
                        res_id: 1,
                        type: 'ir.actions.act_window',
                        target: 'current',
                        res_model: args.model,
                        context: args.kwargs.context,
                        'view_type': 'form',
                        'view_mode': 'form',
                        'views': [[false, 'form']],
                    });
                }
                return this._super(route, args);
            },

            interceptsPropagate: {
                do_action: function (ev) {
                    actionManager.doAction(ev.data.action);
                },
            },
        });
        form.$('.o_field_widget[name="product_id"]').click();
        form.destroy();
        actionManager.destroy();
    });
    QUnit.test('invisible fields are properly hidden', function (assert) {
        assert.expect(4);

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
                        // x2many field without inline view: as it is always invisible, the view
                        // should not be fetched. we don't specify any view in this test, so if it
                        // ever tries to fetch it, it will crash, indicating that this is wrong.
                        '<field name="p" invisible="True"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('label.o_invisible_modifier:contains(Foo)').length, 1,
                        "should not contain label Foo");
        assert.strictEqual(form.$('span.o_invisible_modifier:contains(yop)').length, 1,
                        "should not contain span with field value");
        assert.strictEqual(form.$('.o_field_widget.o_invisible_modifier:contains(0.4)').length, 1,
                        "field qux should be invisible");
        assert.ok(form.$('.o_field_widget[name=p]').hasClass('o_invisible_modifier'),
                        "field p should be invisible");
        form.destroy();
    });

    QUnit.test('invisible elements are properly hidden', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header invisible="1">' +
                        '<button name="myaction" string="coucou"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<group string="invgroup" invisible="1">' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</group>' +
                        '<notebook>' +
                            '<page string="visible"/>' +
                            '<page string="invisible" invisible="1"/>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('.o_form_statusbar.o_invisible_modifier button:contains(coucou)').length, 1,
                        "should not display invisible header");
        assert.strictEqual(form.$('.o_notebook li.o_invisible_modifier a:contains(invisible)').length, 1,
                        "should not display tab invisible");
        assert.strictEqual(form.$('table.o_inner_group.o_invisible_modifier td:contains(invgroup)').length, 1,
                        "should not display invisible groups");
        form.destroy();
    });

    QUnit.test('invisible attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(3);

        // we set the value bar to simulate a falsy boolean value.
        this.data.partner.records[0].bar = false;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="product_id"/>' +
                        '<field name="timmy" invisible="1"/>' +
                        '<field name="foo" class="foo_field" attrs=\'{"invisible": [["product_id", "=", false]]}\'/>' +
                        '<field name="bar" class="bar_field" attrs=\'{"invisible":[("bar","=",False),("timmy","=",[])]}\'/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });


        form.$buttons.find('.o_form_button_edit').click();
        assert.ok(form.$('.foo_field').hasClass('o_invisible_modifier'), 'should not display foo field');
        assert.ok(form.$('.bar_field').hasClass('o_invisible_modifier'), 'should not display bar field');

        // set a value on the m2o
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!form.$('.foo_field').hasClass('o_invisible_modifier'), 'should display foo field');
        form.destroy();
    });

    QUnit.test('asynchronous fields can be set invisible', function (assert) {
        assert.expect(1);

        var def = $.Deferred();

        // we choose this widget because it is a quite simple widget with a non
        // empty qweb template
        var PercentPieWidget = fieldRegistry.get('percentpie');
        fieldRegistry.add('asyncwidget', PercentPieWidget.extend({
            willStart: function () {
                return def;
            },
        }));

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="foo"/>' +
                        '<field name="int_field" invisible="1" widget="asyncwidget"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        }).then(function (form) {
            assert.ok(form.$('.o_field_widget[name="int_field"]').hasClass('o_invisible_modifier'),
                'int_field is invisible');
            form.destroy();
            delete fieldRegistry.map.asyncwidget;
        });
        def.resolve();
    });


    QUnit.test('properly handle modifiers and attributes on notebook tags', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<notebook class="new_class" attrs=\'{"invisible": [["product_id", "=", false]]}\'>' +
                            '<page string="Foo">' +
                                '<field name="foo"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.ok(form.$('.o_notebook').hasClass('o_invisible_modifier'),
            'the notebook should handle modifiers (invisible)');
        assert.ok(form.$('.o_notebook').hasClass('new_class'),
            'the notebook should handle attributes');
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
        assert.ok(form.$('.o_notebook .nav .nav-link:first()').hasClass('active'),
            'first tab should be active');
        assert.ok(!form.$('.o_notebook .nav .nav-item:first()').hasClass('o_invisible_modifier'),
            'first tab should be visible');

        // set a value on the m2o
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('li:first()').click();
        assert.ok(!form.$('.o_notebook .nav .nav-link:first()').hasClass('active'),
            'first tab should not be active');
        assert.ok(form.$('.o_notebook .nav .nav-item:first()').hasClass('o_invisible_modifier'),
            'first tab should be invisible');
        assert.ok(form.$('.o_notebook .nav .nav-link:nth(1)').hasClass('active'),
            'second tab should be active');
        assert.ok(form.$('.o_notebook .tab-content .tab-pane:nth(1)').hasClass('active'),
            'second page should be active');
        form.destroy();
    });

    QUnit.test('first notebook page invisible', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<notebook>' +
                            '<page string="Foo" invisible="1">' +
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

        assert.notOk(form.$('.o_notebook .nav .nav-item:first()').is(':visible'),
            'first tab should be invisible');
        assert.ok(form.$('.o_notebook .nav .nav-link:nth(1)').hasClass('active'),
            'second tab should be active');

        form.destroy();
    });

    QUnit.test('autofocus on second notebook page', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<notebook>' +
                            '<page string="Choucroute">' +
                                '<field name="foo"/>' +
                            '</page>' +
                            '<page string="Cassoulet" autofocus="autofocus">' +
                                '<field name="bar"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        assert.notOk(form.$('.o_notebook .nav .nav-link:first()').hasClass('active'),
            'first tab should not active');
        assert.ok(form.$('.o_notebook .nav .nav-link:nth(1)').hasClass('active'),
            'second tab should be active');

        form.destroy();
    });

    QUnit.test('invisible attrs on group are re-evaluated on field change', function (assert) {
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

    QUnit.test('invisible attrs with zero value in domain and unset value in data', function (assert) {
        assert.expect(1);

        this.data.partner.fields.int_field.type = 'monetary';

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="foo"/>' +
                        '<group attrs=\'{"invisible": [["int_field", "=", 0.0]]}\'>' +
                            '<div class="hello">this should be invisible</div>' +
                            '<field name="int_field"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        assert.notOk(form.$('div.hello').is(':visible'),
            "attrs invisible should have been computed and applied");
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
        assert.strictEqual(form.$('button.oe_stat_button.o_invisible_modifier').length, 1,
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

    QUnit.test('readonly attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(4);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" attrs="{\'readonly\': [[\'bar\', \'=\', True]]}"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('span[name="foo"]').length, 1,
            "the foo field widget should be readonly");
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered to now be editable");
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('span[name="foo"]').length, 1,
            "the foo field widget should have been rerendered to now be readonly again");
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('input[name="foo"]').length, 1,
            "the foo field widget should have been rerendered to now be editable again");

        form.destroy();
    });

    QUnit.test('empty fields have o_form_empty class in readonly mode', function (assert) {
        assert.expect(8);

        this.data.partner.fields.foo.default = false; // no default value for this test
        this.data.partner.records[1].foo = false;  // 1 is record with id=2
        this.data.partner.records[1].trululu = false;  // 1 is record with id=2
        this.data.partner.fields.int_field.readonly = true;
        this.data.partner.onchanges.foo = function (obj) {
            if (obj.foo === "hello") {
                obj.int_field = false;
            }
        };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="trululu" attrs="{\'readonly\': [[\'foo\', \'=\', False]]}"/>' +
                            '<field name="int_field"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_field_widget.o_field_empty').length, 2,
            "should have 2 empty fields with correct class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 2,
            "should have 2 muted labels (for the empty fieds) in readonly");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_empty').length, 1,
            "in edit mode, only empty readonly fields should have the o_field_empty class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 1,
            "in edit mode, only labels associated to empty readonly fields should have the o_form_label_empty class");

        form.$('input[name="foo"]').val("test").trigger("input");

        assert.strictEqual(form.$('.o_field_empty').length, 0,
            "after readonly modifier change, the o_field_empty class should have been removed");
        assert.strictEqual(form.$('.o_form_label_empty').length, 0,
            "after readonly modifier change, the o_form_label_empty class should have been removed");

        form.$('input[name="foo"]').val("hello").trigger("input");

        assert.strictEqual(form.$('.o_field_empty').length, 1,
            "after value changed to false for a readonly field, the o_field_empty class should have been added");
        assert.strictEqual(form.$('.o_form_label_empty').length, 1,
            "after value changed to false for a readonly field, the o_form_label_empty class should have been added");

        form.destroy();
    });

    QUnit.test('empty fields\' labels still get the empty class after widget rerender', function (assert) {
        assert.expect(6);

        this.data.partner.fields.foo.default = false; // no default value for this test
        this.data.partner.records[1].foo = false;  // 1 is record with id=2
        this.data.partner.records[1].display_name = false;  // 1 is record with id=2

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="display_name" attrs="{\'readonly\': [[\'foo\', \'=\', \'readonly\']]}"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_field_widget.o_field_empty').length, 2,
            "should have 1 empty field with correct class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 2,
            "should have 1 muted label (for the empty fied) in readonly");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_empty').length, 0,
            "in edit mode, only empty readonly fields should have the o_field_empty class");
        assert.strictEqual(form.$('.o_form_label_empty').length, 0,
            "in edit mode, only labels associated to empty readonly fields should have the o_form_label_empty class");

        form.$('input[name="foo"]').val("readonly").trigger("input"); // display_name is now rerendered as readonly
        form.$('input[name="foo"]').val("edit").trigger("input"); // display_name is now rerendered as editable
        form.$('input[name="display_name"]').val('1').trigger("input"); // display_name is now set
        form.$('input[name="foo"]').val("readonly").trigger("input"); // display_name is now rerendered as readonly

        assert.strictEqual(form.$('.o_field_empty').length, 0,
            "there still should not be any empty class on fields as the readonly one is now set");
        assert.strictEqual(form.$('.o_form_label_empty').length, 0,
            "there still should not be any empty class on labels as the associated readonly field is now set");

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
        assert.strictEqual(form.$('.o_field_empty').length, 0,
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
            'form view should be .o_form_readonly');
        assert.ok(form.$buttons.find('.o_form_buttons_view').is(':visible'),
            'readonly buttons should be visible');
        assert.ok(!form.$buttons.find('.o_form_buttons_edit').is(':visible'),
            'edit buttons should not be visible');
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.mode, 'edit', 'form view should be in edit mode');
        assert.ok(form.$('.o_form_view').hasClass('o_form_editable'),
            'form view should be .o_form_editable');
        assert.ok(!form.$('.o_form_view').hasClass('o_form_readonly'),
            'form view should not be .o_form_readonly');
        assert.ok(!form.$buttons.find('.o_form_buttons_view').is(':visible'),
            'readonly buttons should not be visible');
        assert.ok(form.$buttons.find('.o_form_buttons_edit').is(':visible'),
            'edit buttons should be visible');
        form.destroy();
    });

    QUnit.test('required attrs on fields are re-evaluated on field change', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should be required");
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('input[name="foo"]:not(.o_required_modifier)').length, 1,
            "the foo field widget should now have been marked as non-required");
        form.$('.o_field_boolean input').click();
        assert.strictEqual(form.$('input[name="foo"].o_required_modifier').length, 1,
            "the foo field widget should now have been marked as required again");

        form.destroy();
    });

    QUnit.test('required fields should have o_required_modifier in readonly mode', function (assert) {
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

        assert.strictEqual(form.$('span.o_required_modifier').length, 1,
                            "should have 1 span with o_required_modifier class");

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input.o_required_modifier').length, 1,
                            "in edit mode, should have 1 input with o_required_modifier");
        form.destroy();
    });

    QUnit.test('required float fields works as expected', function (assert) {
        assert.expect(10);

        this.data.partner.fields.qux.required = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        assert.ok(form.$('input[name="qux"]').hasClass('o_required_modifier'),
            "qux input is flagged as required");
        assert.strictEqual(form.$('input[name="qux"]').val(), "0.0",
            "qux input is 0 by default (float field)");

        form.$buttons.find('.o_form_button_save').click();

        assert.notOk(form.$('input[name="qux"]').hasClass('o_field_invalid'),
            "qux input is not displayed as invalid");

        form.$buttons.find('.o_form_button_edit').click();

        form.$('input[name="qux"]').val("1").trigger('input');

        form.$buttons.find('.o_form_button_save').click();

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('input[name="qux"]').val(), "1.0",
            "qux input is properly formatted");

        assert.verifySteps(['default_get', 'create', 'read', 'write', 'read']);
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

    QUnit.test('invisible attrs on separators', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<separator string="Geolocation" attrs=\'{"invisible": [["bar", "=", True]]}\'/>'+
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        assert.strictEqual(form.$('div.o_horizontal_separator').hasClass('o_invisible_modifier'), true,
                "separator div should be hidden");
        form.destroy();
    });

    QUnit.test('buttons in form view', function (assert) {
        assert.expect(8);

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
        assert.strictEqual(form.$('button.btn i.fa.fa-check').length, 1,
                        "should contain a button with correct content");

        assert.strictEqual(form.$('.o_form_statusbar button').length, 2,
            "should have 2 buttons in the statusbar");
        assert.strictEqual(form.$('button[name="post"]').length, 1,
            "'name' attribute of buttons is transmitted to the rendered html element");

        assert.strictEqual(form.$('.o_form_statusbar button:visible').length, 1,
            "should have only 1 visible button in the statusbar");

        testUtils.intercept(form, 'execute_action', function (event) {
            assert.strictEqual(event.data.action_data.name, "post",
                "should trigger execute_action with correct method name");
            assert.deepEqual(event.data.env.currentID, 2, "should have correct id in event data");
            event.data.on_success();
            event.data.on_closed();
        });
        rpcCount = 0;
        form.$('.o_form_statusbar button.p').click();

        assert.strictEqual(rpcCount, 1, "should have done 1 rpcs to reload");

        testUtils.intercept(form, 'execute_action', function (event) {
            event.data.on_fail();
        });
        form.$('.o_form_statusbar button.s').click();

        assert.strictEqual(rpcCount, 1, "should have done 1 rpc, because we do not reload anymore if the server action fails");
        form.destroy();
    });

    QUnit.test('buttons classes in form view', function (assert) {
        assert.expect(16);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<header>' +
                        '<button name="0"/>' +
                        '<button name="1" class="btn-primary"/>' +
                        '<button name="2" class="oe_highlight"/>' +
                        '<button name="3" class="btn-secondary"/>' +
                        '<button name="4" class="btn-link"/>' +
                        '<button name="5" class="oe_link"/>' +
                        '<button name="6" class="btn-success"/>' +
                        '<button name="7" class="o_this_is_a_button"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<button name="8"/>' +
                        '<button name="9" class="btn-primary"/>' +
                        '<button name="10" class="oe_highlight"/>' +
                        '<button name="11" class="btn-secondary"/>' +
                        '<button name="12" class="btn-link"/>' +
                        '<button name="13" class="oe_link"/>' +
                        '<button name="14" class="btn-success"/>' +
                        '<button name="15" class="o_this_is_a_button"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('button[name="0"]').attr('class'), 'btn btn-secondary',
            "header buttons without any class should receive the correct classes");
        assert.strictEqual(form.$('button[name="1"]').attr('class'), 'btn btn-primary',
            "header buttons with bootstrap primary class should receive the correct classes");
        assert.strictEqual(form.$('button[name="2"]').attr('class'), 'btn btn-primary',
            "header buttons with oe_highlight class should receive the correct classes");
        assert.strictEqual(form.$('button[name="3"]').attr('class'), 'btn btn-secondary',
            "header buttons with bootstrap default class should receive the correct classes");
        assert.strictEqual(form.$('button[name="4"]').attr('class'), 'btn btn-link',
            "header buttons with bootstrap link class should receive the correct classes");
        assert.strictEqual(form.$('button[name="5"]').attr('class'), 'btn btn-link',
            "header buttons with oe_link class should receive the correct classes");
        assert.strictEqual(form.$('button[name="6"]').attr('class'), 'btn btn-success',
            "header buttons with bootstrap state class should receive the correct classes");
        assert.strictEqual(form.$('button[name="7"]').attr('class'), 'btn o_this_is_a_button btn-secondary',
            "header buttons with custom classes should receive the correct classes");
        assert.strictEqual(form.$('button[name="8"]').attr('class'), 'btn btn-secondary',
            "sheet header buttons without any class should receive the correct classes");
        assert.strictEqual(form.$('button[name="9"]').attr('class'), 'btn btn-primary',
            "sheet buttons with bootstrap primary class should receive the correct classes");
        assert.strictEqual(form.$('button[name="10"]').attr('class'), 'btn btn-primary',
            "sheet buttons with oe_highlight class should receive the correct classes");
        assert.strictEqual(form.$('button[name="11"]').attr('class'), 'btn btn-secondary',
            "sheet buttons with bootstrap default class should receive the correct classes");
        assert.strictEqual(form.$('button[name="12"]').attr('class'), 'btn btn-link',
            "sheet buttons with bootstrap link class should receive the correct classes");
        assert.strictEqual(form.$('button[name="13"]').attr('class'), 'btn btn-link',
            "sheet buttons with oe_link class should receive the correct classes");
        assert.strictEqual(form.$('button[name="14"]').attr('class'), 'btn btn-success',
            "sheet buttons with bootstrap state class should receive the correct classes");
        assert.strictEqual(form.$('button[name="15"]').attr('class'), 'btn o_this_is_a_button',
            "sheet buttons with custom classes should receive the correct classes");

        form.destroy();
    });

    QUnit.test('buttons in form view, new record', function (assert) {
        // this simulates a situation similar to the settings forms.
        assert.expect(7);

        var resID;

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
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'create') {
                    return this._super.apply(this, arguments).then(function (result) {
                        resID = result;
                        return resID;
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        testUtils.intercept(form, 'execute_action', function (event) {
            assert.step('execute_action');
            assert.deepEqual(event.data.env.currentID, resID,
                "execute action should be done on correct record id");
            event.data.on_success();
            event.data.on_closed();
        });
        form.$('.o_form_statusbar button.p').click();

        assert.verifySteps(['default_get', 'create', 'read', 'execute_action', 'read']);
        form.destroy();
    });

    QUnit.test('buttons in form view, new record, with field id in view', function (assert) {
        assert.expect(7);
        // buttons in form view are one of the rare example of situation when we
        // save a record without reloading it immediately, because we only care
        // about its id for the next step.  But at some point, if the field id
        // is in the view, it was registered in the changes, and caused invalid
        // values in the record (data.id was set to null)

        var resID;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button name="post" class="p" string="Confirm" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="id" invisible="1"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'create') {
                    return this._super.apply(this, arguments).then(function (result) {
                        resID = result;
                        return resID;
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        testUtils.intercept(form, 'execute_action', function (event) {
            assert.step('execute_action');
            assert.deepEqual(event.data.env.currentID, resID,
                "execute action should be done on correct record id");
            event.data.on_success();
            event.data.on_closed();
        });
        form.$('.o_form_statusbar button.p').click();

        assert.verifySteps(['default_get', 'create', 'read', 'execute_action', 'read']);
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

    QUnit.test('disable buttons until reload data from server', function (assert) {
        assert.expect(2);
        var def;

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
                } else if (args.method === 'read') {
                    // Block the 'read' call
                    var result = this._super.apply(this, arguments);
                    return $.when(def).then(_.constant(result));
                }
                return this._super(route, args);
            },
            res_id: 2,
        });

        var def = $.Deferred();
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        // Save button should be disabled
        assert.strictEqual(
            form.$buttons.find('.o_form_button_save').attr('disabled'),
            'disabled', 'buttons should be disabled')

        // Release the 'read' call
        def.resolve();

        // Edit button should be enabled after the reload
        assert.strictEqual(
            form.$buttons.find('.o_form_button_edit').attr('disabled'),
            undefined, 'buttons should be enabled')

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

    QUnit.test('properly apply onchange when changed field is active field', function (assert) {
        assert.expect(3);

        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.int_field = 14;
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="int_field"/></group>' +
                '</form>',
            res_id: 2,
            viewOptions: {mode: 'edit'},
        });


        assert.strictEqual(form.$('input').val(), "9",
                        "should contain input with initial value");

        form.$('input').val("666").trigger('input');

        assert.strictEqual(form.$('input').val(), "14",
                "value should have been set to 14 by onchange");

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_field_widget[name=int_field]').text(), "14",
            "value should still be 14");

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
                        {"foo": "1", "p": "", "p.bar": "", "p.product_id": "", "timmy": "", "timmy.name": ""},
                        "should send only the fields used in the views");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input:first').val("tralala").trigger('input');

        form.destroy();
    });

    QUnit.test('onchange only send present fields value', function (assert) {
        assert.expect(1);
        this.data.partner.onchanges.foo = function (obj) {};

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                        '<tree editable="top">' +
                            '<field name="display_name"/>' +
                            '<field name="qux"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === "onchange") {
                    assert.deepEqual(args.args[1], {
                        display_name: "first record",
                        foo: "tralala",
                        id: 1,
                        p: [[0, args.args[1].p[0][1], {"display_name": "valid line", "qux": 12.4}]]
                    }, "should send the values for the present fields");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        // add a o2m row
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_one2many input:first').focus();
        form.$('.o_field_one2many input:first').val('valid line').trigger('input');
        form.$('.o_field_one2many input:last').focus();
        form.$('.o_field_one2many input:last').val('12.4').trigger('input');

        // trigger an onchange by modifying foo
        form.$('input[name="foo"]:first').val("tralala").trigger('input');

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
        assert.expect(5);

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
            viewOptions: {
                context: {active_field: 2},
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.strictEqual(args.kwargs.context.active_field, 2,
                        "should have send the correct context");
                }
                return this._super.apply(this, arguments);
            },
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

    QUnit.test('default record with a one2many and an onchange on sub field', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges.foo = function () {};

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
                assert.step(args.method);
                if (args.method === 'onchange') {
                    assert.deepEqual(args.args[3], {
                        p: '',
                        'p.foo': '1'
                    }, "onchangeSpec should be correct (with sub fields)");
                }
                return this._super.apply(this, arguments);
            },
        });
        assert.verifySteps(['default_get', 'onchange']);
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
            viewOptions: {hasSidebar: true},
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
            assert.ok(form.$('input').val(), 'aaa',
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
            viewOptions: {hasSidebar: true},
        });

        assert.strictEqual(form.get('title'), 'first record',
            "should have the display name of the record as  title");
        form.sidebar.$('a:contains(Duplicate)').click();

        assert.strictEqual(form.get('title'), 'first record (copy)',
            "should have duplicated the record");

        assert.strictEqual(form.mode, "edit", 'should be in edit mode');
        form.destroy();
    });

    QUnit.test('duplicating a record preserve the context', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {hasSidebar: true, context: {hey: 'hoy'}},
            mockRPC: function (route, args) {
                if (args.method === 'read') {
                    // should have 2 read, one for initial load, second for
                    // read after duplicating
                    assert.strictEqual(args.kwargs.context.hey, 'hoy',
                        "should have send the correct context");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.sidebar.$('a:contains(Duplicate)').click();

        form.destroy();
    });

    QUnit.test('cannot duplicate a record', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners" duplicate="false">' +
                        '<field name="foo"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {hasSidebar: true},
        });

        assert.strictEqual(form.get('title'), 'first record',
            "should have the display name of the record as  title");
        assert.ok(form.sidebar.$('a:contains(Duplicate)').length === 0,
            "should not contains a 'Duplicate' action");
        form.destroy();
    });

    QUnit.test('buttons in footer are moved to $buttons if necessary', function (assert) {
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
            viewOptions: {footerToButtons: true},
        });

        assert.ok(form.$buttons.find('button.infooter').length, "footer button should be in footer");
        assert.ok(!form.$('button.infooter').length, "footer button should not be in form");
        form.destroy();
    });

    QUnit.test('clicking on stat buttons in edit mode', function (assert) {
        assert.expect(9);

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
                assert.step(args.method);
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
        assert.strictEqual(form.mode, "edit", "form view should be in edit mode");


        form.$('input').val("tralala").trigger('input');
        form.$('.oe_stat_button').first().click();

        assert.strictEqual(form.mode, "edit", "form view should be in edit mode");
        assert.strictEqual(count, 2, "should have triggered a execute action");
        assert.verifySteps(['read', 'write', 'read']);
        form.destroy();
    });

    QUnit.test('clicking on stat buttons save and reload in edit mode', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<div name="button_box">' +
                            '<button class="oe_stat_button" type="action">' +
                                '<field name="int_field" widget="statinfo" string="Some number"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="name"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    // simulate an override of the model...
                    args.args[1].display_name = "GOLDORAK";
                    args.args[1].name = "GOLDORAK";
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.getTitle(), 'second record',
            "should have correct display_name");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="name"]').val('some other name').trigger('input');

        form.$('.oe_stat_button').first().click();
        assert.strictEqual(form.getTitle(), 'GOLDORAK',
            "should have correct display_name");

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
                        '<button string="Discard" class="btn-secondary" special="cancel"/>' +
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

    QUnit.test('buttons with attr "special=save" save', function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                        '<button string="Save" class="btn-primary" special="save"/>' +
                '</form>',
            res_id: 1,
            intercepts: {
                execute_action: function () {
                    assert.step('execute_action');
                },
            },
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super(route, args);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('input').val("tralala").trigger('input'); // make the record dirty
        form.$('button').click(); // click on Save
        assert.verifySteps(['read', 'write', 'read', 'execute_action']);

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

        assert.strictEqual(form.$("label.o_form_label").length, 2, "should have rendered only two label");
        assert.strictEqual(form.$("label.o_form_label").first().text(), "Product",
            "one should be the one for the product field");
        assert.strictEqual(form.$("label.o_form_label").eq(1).text(), "Bar",
            "one should be the one for the bar field");

        assert.strictEqual(form.$('.firstgroup td').first().attr('colspan'), undefined,
            "foo td should have a default colspan (1)");
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

    QUnit.test('circular many2many\'s', function (assert) {
        assert.expect(4);
        this.data.partner_type.fields.partner_ids = {string: "partners", type: "many2many", relation: 'partner'}
        this.data.partner.records[0].timmy = [12];
        this.data.partner_type.records[0].partner_ids = [1];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="timmy">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                        '<form>' +
                            '<field name="partner_ids">' +
                                '<tree>' +
                                    '<field name="display_name"/>' +
                                '</tree>' +
                                '<form>' +
                                    '<field name="display_name"/>' +
                                '</form>' +
                            '</field>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('td:contains(gold)').length, 1,
            "should display the name of the many2many on the original form");
        form.$('td:contains(gold)').click();

        assert.strictEqual($('.modal').length, 1,
            'The partner_type modal should have opened');
        assert.strictEqual($('.modal').find('td:contains(first record)').length, 1,
            "should display the name of the many2many on the modal form");

        $('.modal').find('td:contains(first record)').click();
        assert.strictEqual($('.modal').length, 2,
            'There should be 2 modals (partner on top of partner_type) opened');

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
        assert.strictEqual(form.$('input').val(), 'yop', 'input should contain yop');

        // click on discard
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok(!$('.modal:visible').length, 'no confirm modal should be displayed');
        assert.strictEqual(form.$('.o_field_widget').text(), 'yop', 'field in readonly should display yop');

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
        assert.strictEqual(form.$('input').val(), 'yop', 'input should contain yop');
        form.$('input').val('new value').trigger('input');
        assert.strictEqual(form.$('input').val(), 'new value', 'input should contain new value');

        // click on discard and cancel the confirm request
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal-footer .btn-secondary').click(); // click on cancel
        assert.strictEqual(form.$('input').val(), 'new value', 'input should still contain new value');

        // click on discard and confirm
        form.$buttons.find('.o_form_button_cancel').click();
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('.o_field_widget').text(), 'yop', 'field in readonly should display yop');

        assert.strictEqual(nbWrite, 0, 'no write RPC should have been done');
        form.destroy();
    });

    QUnit.test('discard changes on a dirty form view (for date field)', function (assert) {
        assert.expect(1);

        // this test checks that the basic model properly handles date object
        // when they are discarded and saved.  This may be an issue because
        // dates are saved as moment object, and were at one point stringified,
        // then parsed into string, which is wrong.

        this.data.partner.fields.date.default = "2017-01-25";
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="date"></field></form>',
            intercepts: {
                history_back: function () {
                    form.update({}, {reload: false});
                }
            },
        });

        // focus the buttons before clicking on them to precisely reproduce what
        // really happens (mostly because the datepicker lib need that focus
        // event to properly focusout the input, otherwise it crashes later on
        // when the 'blur' event is triggered by the re-rendering)
        form.$buttons.find('.o_form_button_cancel').focus().click();
        form.$buttons.find('.o_form_button_save').focus().click();
        assert.strictEqual(form.$('span:contains(2017)').length, 1,
            "should have a span with the year somewhere");

        form.destroy();
    });

    QUnit.test('discard changes on relational data on new record', function (assert) {
        assert.expect(3);

        var nbWrite = 0;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><sheet><group>' +
                    '<field name="p">' +
                        '<tree editable="top">' +
                            '<field name="product_id"/>' +
                        '</tree>' +
                    '</field>' +
                '</group></sheet></form>',
            mockRPC: function (route) {
                if (route === '/web/dataset/call_kw/partner/write') {
                    nbWrite++;
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                history_back: function () {
                    assert.ok(true, "should have sent correct event");
                    // simulate the response from the action manager, in the case
                    // where we have only one active view (the form).  If there
                    // was another view, we would have switched to that view
                    // instead
                    form.update({}, {reload: false});
                }
            },
        });

        // switch to edit mode and edit the p field
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_field_many2one input').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        $dropdown.find('li:first()').click();

        assert.strictEqual(form.$('input').val(), 'xphone', 'input should contain xphone');

        // click on discard and confirm
        form.$buttons.find('.o_form_button_cancel').click();
        $('.modal-footer .btn-primary').click(); // click on confirm

        assert.notOk(form.$el.prop('outerHTML').match('xphone'),
            "the string xphone should not be present after discarding");
        form.destroy();
    });

    QUnit.test('discard changes on a new (non dirty, except for defaults) form view', function (assert) {
        assert.expect(3);

        this.data.partner.fields.foo.default = "ABC";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            intercepts: {
                history_back: function () {
                    assert.ok(true, "should have sent correct event");
                }
            }
        });

        // switch to edit mode and edit the foo field
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input').val(), 'ABC', 'input should contain ABC');

        form.$buttons.find('.o_form_button_cancel').click();

        assert.strictEqual($('.modal').length, 0,
            'there should not be a confirm modal');

        form.destroy();
    });

    QUnit.test('discard changes on a new (dirty) form view', function (assert) {
        assert.expect(8);

        this.data.partner.fields.foo.default = "ABC";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            intercepts: {
                history_back: function () {
                    assert.ok(true, "should have sent correct event");
                    // simulate the response from the action manager, in the case
                    // where we have only one active view (the form).  If there
                    // was another view, we would have switched to that view
                    // instead
                    form.update({}, {reload: false});
                }
            },
        });

        // edit the foo field
        assert.strictEqual(form.$('input').val(), 'ABC', 'input should contain ABC');
        form.$('input').val('DEF').trigger('input');

        // discard the changes and check it has properly been discarded
        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual($('.modal').length, 1,
            'there should be a confirm modal');
        assert.strictEqual(form.$('input').val(), 'DEF', 'input should be DEF');
        $('.modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('input').val(), 'ABC', 'input should now be ABC');

        // redirty and discard the field foo (to make sure initial changes haven't been lost)
        form.$('input').val('GHI').trigger('input');
        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual(form.$('input').val(), 'GHI', 'input should be GHI');
        $('.modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('input').val(), 'ABC', 'input should now be ABC');

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
            viewOptions: {hasSidebar: true},
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val("tralala").trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        form.sidebar.$('a:contains(Duplicate)').click();

        assert.strictEqual(form.$('input').val(), 'tralala', 'input should contain ABC');

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
        assert.strictEqual(form.$('input').val(), 'yop', 'input should contain yop');

        // edit the foo field
        form.$('input').val('new value').trigger('input');
        assert.strictEqual(form.$('input').val(), 'new value', 'input should contain new value');

        // click on the pager to switch to the next record and cancel the confirm request
        form.pager.$('.o_pager_next').click(); // click on next
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal-footer .btn-secondary').click(); // click on cancel
        assert.strictEqual(form.$('input').val(), 'new value', 'input should still contain new value');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should still be 1');

        // click on the pager to switch to the next record and confirm
        form.pager.$('.o_pager_next').click(); // click on next
        assert.ok($('.modal').length, 'a confirm modal should be displayed');
        $('.modal-footer .btn-primary').click(); // click on confirm
        assert.strictEqual(form.$('input').val(), 'blip', 'input should contain blip');
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
        assert.strictEqual(form.$('input').val(), 'yop', 'input should contain yop');

        // edit the foo field
        form.$('input').val('new value').trigger('input');
        assert.strictEqual(form.$('input').val(), 'new value', 'input should contain new value');

        form.$buttons.find('.o_form_button_save').click();

        // click on the pager to switch to the next record and cancel the confirm request
        form.pager.$('.o_pager_next').click(); // click on next
        assert.strictEqual($('.modal:visible').length, 0, 'no confirm modal should be displayed');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "2", 'pager value should be 2');

        assert.strictEqual(form.$('.o_priority .fa-star-o').length, 2,
            'priority widget should have been rendered with correct value');

        // edit the value in readonly
        form.$('.o_priority .fa-star-o:first').click(); // click on the first star
        assert.strictEqual(form.$('.o_priority .fa-star').length, 1,
            'priority widget should have been updated');

        form.pager.$('.o_pager_next').click(); // click on next
        assert.strictEqual($('.modal:visible').length, 0, 'no confirm modal should be displayed');
        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input').val(), 'new value', 'input should contain yop');

        // edit the foo field
        form.$('input').val('wrong value').trigger('input');

        form.$buttons.find('.o_form_button_cancel').click();
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        $('.modal-footer .btn-primary').click(); // click on confirm
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
        form.$('.o_notebook .nav-link:eq(1)').click();

        assert.notOk(form.$('.o_notebook .nav-link:eq(0)').hasClass('active'),
            "first tab should not be active");
        assert.ok(form.$('.o_notebook .nav-link:eq(1)').hasClass('active'),
            "second tab should be active");

        // click on the pager to switch to the next record
        form.pager.$('.o_pager_next').click();

        assert.notOk(form.$('.o_notebook .nav-link:eq(0)').hasClass('active'),
            "first tab should not be active");
        assert.ok(form.$('.o_notebook .nav-link:eq(1)').hasClass('active'),
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

        assert.strictEqual(form.$('.o_field_empty').length, 1,
            'readonly field should be invisible on an existing record');

        form.$buttons.find('.o_form_button_create').click();

        assert.strictEqual(form.$('.o_field_empty').length, 0,
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
                hasSidebar: true,
            },
            res_id: 1,
        });

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "3", 'pager limit should be 3');
        assert.strictEqual(form.$('span:contains(yop)').length, 1,
            'should have a field with foo value for record 1');
        assert.ok(!$('.modal:visible').length, 'no confirm modal should be displayed');

        // open sidebar
        form.sidebar.$('button.o_dropdown_toggler_btn').click();
        form.sidebar.$('a:contains(Delete)').click();

        assert.ok($('.modal').length, 'a confirm modal should be displayed');

        // confirm the delete
        $('.modal-footer button.btn-primary').click();

        assert.strictEqual(form.pager.$('.o_pager_value').text(), "1", 'pager value should be 1');
        assert.strictEqual(form.pager.$('.o_pager_limit').text(), "2", 'pager limit should be 2');
        assert.strictEqual(form.$('span:contains(blip)').length, 1,
            'should have a field with foo value for record 2');
        form.destroy();
    });

    QUnit.test('deleting the last record', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners"><field name="foo"></field></form>',
            viewOptions: {
                ids: [1],
                index: 0,
                hasSidebar: true,
            },
            res_id: 1,
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            }
        });

        // open sidebar, click on delete and confirm
        form.sidebar.$('button.o_dropdown_toggler_btn').click();
        form.sidebar.$('a:contains(Delete)').click();

        testUtils.intercept(form, 'history_back', function () {
            assert.step('history_back');
        });
        assert.strictEqual($('.modal').length, 1, 'a confirm modal should be displayed');
        $('.modal-footer button.btn-primary').click();
        assert.strictEqual($('.modal').length, 0, 'no confirm modal should be displayed');

        assert.verifySteps(['read', 'unlink', 'history_back']);
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
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        if (params.type !== 'warning') {
                            return;
                        }
                        assert.strictEqual(params.title, 'The following fields are invalid:',
                            "should have a warning with correct title");
                        assert.strictEqual(params.message, '<ul><li>Foo</li></ul>',
                            "should have a warning with correct message");
                    }
                }),
            },
        });

        form.$buttons.find('.o_form_button_save').click();
        assert.ok(form.$('label').hasClass('o_field_invalid'),
            "label should be tagged as invalid");
        assert.ok(form.$('input').hasClass('o_field_invalid'),
            "input should be tagged as invalid");

        form.$('input').val("tralala").trigger('input');

        assert.strictEqual(form.$('.o_field_invalid').length, 0,
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

        assert.strictEqual(form.$('input[name=int_field]').val(), '9',
            "'int_field' value should be 9 before the change");

        form.$('input').first().val("tralala").trigger('input');

        assert.strictEqual(form.$('input[name=int_field]').val(), '10',
            "the onchange should have been correctly applied");

        form.destroy();
    });

    QUnit.test('can create record even if onchange returns a warning', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = { foo: true };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/><field name="int_field"/></group>' +
                '</form>',
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
                    assert.step('warning');
                },
            },
        });
        assert.strictEqual(form.$('input[name="int_field"]').val(), "10",
            "record should have been created and rendered");

        form.destroy();
    });

    QUnit.test('do nothing if add a line in one2many result in a onchange with a warning', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = { foo: true };

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
                        value: {},
                        warning: {
                            title: "Warning",
                            message: "You must first select a partner"
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                warning: function () {
                    assert.step("should have triggered a warning");
                },
            },
        });

        // go to edit mode, click to add a record in the o2m
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('tr.o_data_row').length, 0,
            "should not have added a line");
        form.destroy();
    });

    QUnit.test('default_get, onchange which fails, should still work', function (assert) {
        assert.expect(1);

        this.data.partner.onchanges.foo = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="foo"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    // we simulate a validation error.  In the 'real' web client,
                    // the server error will be used by the session to display
                    // an error dialog.  From the point of view of the basic
                    // model, the deferred is just rejected.
                    return $.Deferred().reject();
                }
                return this._super.apply(this, arguments);
            },
        });

        // this test checks that a form view is still rendered when the server
        // onchange fails (for example, because of a validation error, or, more
        // likely, a bug in the onchange code).  This is quite rare, but if the
        // onchange fails, we still want to display the form view (with the error
        // dialog from the session/crashmanager).  Otherwise, we could be in the
        // situation where a user clicks on a button, it should open a wizard,
        // but something fails and the wizard is not even rendered.  In that
        // case, there is nothing that the user could do.
        assert.strictEqual(form.$('.o_field_widget[name="foo"]').val(), 'My little Foo Value',
            "should display proper default value");

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

    QUnit.test('button box is rendered in create mode', function (assert) {
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

        // create mode (leave edition first!)
        form.$buttons.find('.o_form_button_cancel').click();
        form.$buttons.find('.o_form_button_create').click();
        assert.strictEqual(form.$('.oe_stat_button').length, 1,
            "button box should be displayed when creating a new record as well");

        form.destroy();
    });

    QUnit.test('properly apply onchange on one2many fields', function (assert) {
        assert.expect(5);

        this.data.partner.records[0].p = [4];
        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.p = [
                    [5],
                    [1, 4, {display_name: "updated record"}],
                    [0, null, {display_name: "created record"}],
                ];
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="foo"/></group>' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_field_one2many .o_data_row').length, 1,
            "there should be one one2many record linked at first");
        assert.strictEqual(form.$('.o_field_one2many .o_data_row td:first').text(), 'aaa',
            "the 'display_name' of the one2many record should be correct");

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val('let us trigger an onchange').trigger('input');
        var $o2m = form.$('.o_field_one2many');
        assert.strictEqual($o2m.find('.o_data_row').length, 2,
            "there should be two linked record");
        assert.strictEqual($o2m.find('.o_data_row:first td:first').text(), 'updated record',
            "the 'display_name' of the first one2many record should have been updated");
        assert.strictEqual($o2m.find('.o_data_row:nth(1) td:first').text(), 'created record',
            "the 'display_name' of the second one2many record should be correct");

        form.destroy();
    });

    QUnit.test('update many2many value in one2many after onchange', function (assert) {
        assert.expect(2);

        this.data.partner.records[1].p = [4];
        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.p = [
                    [5],
                    [1, 4, {
                        display_name: "gold",
                        timmy: [5]
                    }],
                ];
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="foo"/>' +
                    '<field name="p">' +
                        '<tree editable="top">' +
                            '<field name="display_name" attrs="{\'readonly\': [(\'timmy\', \'=\', false)]}"/>' +
                            '<field name="timmy"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 2,
        });
        assert.strictEqual($('div[name="p"] .o_data_row td').text().trim(), "aaaNo records",
            "should have proper initial content");
        form.$buttons.find('.o_form_button_edit').click();

        form.$('input').val("tralala").trigger('input');

        assert.strictEqual($('div[name="p"] .o_data_row td').text().trim(), "goldNo records",
            "should have proper initial content");
        form.destroy();
    });

    QUnit.test('delete a line in a one2many while editing another line triggers a warning', function (assert) {
        assert.expect(3);

        this.data.partner.records[0].p = [1, 2];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="p">' +
                        '<tree editable="bottom">' +
                            '<field name="display_name" required="True"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_data_cell').first().click(); // edit first row
        form.$('input').val('').trigger('input');
        form.$('.fa-trash-o').eq(1).click(); // delete second row

        assert.strictEqual($('.modal').find('.modal-title').first().text(), "Warning",
            "Clicking out of a dirty line while editing should trigger a warning modal.");

        $('.modal').find('.btn-primary').click(); // discard changes

        assert.strictEqual(form.$('.o_data_cell').first().text(), "first record",
            "Value should have been reset to what it was before editing began.");
        assert.strictEqual(form.$('.o_data_row').length, 1,
            "The other line should have been deleted.");
        form.destroy();
    });

    QUnit.test('properly apply onchange on many2many fields', function (assert) {
        assert.expect(14);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.timmy = [
                    [5],
                    [4, 12],
                    [4, 14],
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
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'read' && args.model === 'partner_type') {
                    assert.deepEqual(args.args[0], [12, 14],
                        "should read both m2m with one RPC");
                }
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1].timmy, [[6, false, [12, 14]]],
                        "should correctly save the changed m2m values");

                }
                return this._super.apply(this, arguments);
            },
            res_id: 2,
        });

        assert.strictEqual(form.$('.o_field_many2many .o_data_row').length, 0,
            "there should be no many2many record linked at first");

        // switch to edit mode
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input').val('let us trigger an onchange').trigger('input');
        var $m2m = form.$('.o_field_many2many');
        assert.strictEqual($m2m.find('.o_data_row').length, 2,
            "there should be two linked records");
        assert.strictEqual($m2m.find('.o_data_row:first td:first').text(), 'gold',
            "the 'display_name' of the first m2m record should be correctly displayed");
        assert.strictEqual($m2m.find('.o_data_row:nth(1) td:first').text(), 'silver',
            "the 'display_name' of the second m2m record should be correctly displayed");

        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps(['read', 'onchange', 'read', 'write', 'read', 'read']);

        form.destroy();
    });

    QUnit.test('display_name not sent for onchanges if not in view', function (assert) {
        assert.expect(7);

        this.data.partner.records[0].timmy = [12];
        this.data.partner.onchanges = {
            foo: function () {},
        };
        this.data.partner_type.onchanges = {
            name: function () {},
        };
        var readInModal = false;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="timmy">' +
                            '<tree>' +
                                '<field name="name"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="name"/>' +
                                '<field name="color"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'read' && args.model === 'partner') {
                    assert.deepEqual(args.args[1], ['foo', 'timmy', 'display_name'],
                        "should read display_name even if not in the view");
                }
                if (args.method === 'read' && args.model === 'partner_type') {
                    if (!readInModal) {
                        assert.deepEqual(args.args[1], ['name'],
                            "should not read display_name for records in the list");
                    } else {
                        assert.deepEqual(args.args[1], ['name', 'color', 'display_name'],
                            "should read display_name when opening the subrecord");
                    }
                }
                if (args.method === 'onchange' && args.model === 'partner') {
                    assert.deepEqual(args.args[1], {
                        id: 1,
                        foo: 'coucou',
                        timmy: [[6, false, [12]]],
                    }, "should only send the value of fields in the view (+ id)");
                    assert.deepEqual(args.args[3], {
                        foo: '1',
                        timmy: '',
                        'timmy.name': '1',
                        'timmy.color': '',
                    }, "only the fields in the view should be in the onchange spec");
                }
                if (args.method === 'onchange' && args.model === 'partner_type') {
                    assert.deepEqual(args.args[1], {
                        id: 12,
                        name: 'new name',
                        color: 2,
                    }, "should only send the value of fields in the view (+ id)");
                    assert.deepEqual(args.args[3], {
                        name: '1',
                        color: '',
                    }, "only the fields in the view should be in the onchange spec");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
        });

        // trigger the onchange
        form.$('.o_field_widget[name=foo]').val("coucou").trigger('input');

        // open a subrecord and trigger an onchange
        readInModal = true;
        form.$('.o_data_row .o_data_cell:first').click();
        $('.modal .o_field_widget[name=name]').val("new name").trigger('input');

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
            session: {
                getTZOffset: function () {
                    return 120;
                },
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name=date]').text(),
            '01/25/2017', "the initial date should be correct");
        assert.strictEqual(form.$('.o_field_widget[name=datetime]').text(),
            '12/12/2016 12:55:05', "the initial datetime should be correct");

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_field_widget[name=date] input').val(),
            '01/25/2017', "the initial date should be correct in edit");
        assert.strictEqual(form.$('.o_field_widget[name=datetime] input').val(),
            '12/12/2016 12:55:05', "the initial datetime should be correct in edit");

        // trigger the onchange
        form.$('.o_field_widget[name="foo"]').val("coucou").trigger('input');

        assert.strictEqual(form.$('.o_field_widget[name=date] input').val(),
            '12/12/2021', "the initial date should be correct in edit");
        assert.strictEqual(form.$('.o_field_widget[name=datetime] input').val(),
            '12/12/2021 12:55:05', "the initial datetime should be correct in edit");

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
        var def = $.Deferred();
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
                        def.resolve();
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

        return waitForFinishedOnChange().then(function () {
            assert.strictEqual(onchangeNbr, 1, "one onchange has been called");

            // add something in the input, then focus another input
            form.$('input').first().val("123").trigger('input');
            form.$('input').first().change();
            assert.strictEqual(onchangeNbr, 2,
                "one onchange has been called immediately");

            return waitForFinishedOnChange();
        }).then(function () {
            assert.strictEqual(onchangeNbr, 2,
                "no extra onchange should have been called");

            form.destroy();
            done();
        });

        function waitForFinishedOnChange() {
            return def.then(function () {
                def = $.Deferred();
                return concurrency.delay(0);
            });
        }
    });

    QUnit.test('onchanges are not sent for invalid values', function (assert) {
        assert.expect(6);

        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = String(obj.int_field);
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
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        // edit int_field, and check that an onchange has been applied
        form.$('input[name="int_field"]').val("123").trigger('input');
        assert.strictEqual(form.$('input[name="foo"]').val(), "123",
            "the onchange has been applied");

        // enter an invalid value in a float, and check that no onchange has
        // been applied
        form.$('input[name="int_field"]').val("123a").trigger('input');
        assert.strictEqual(form.$('input[name="foo"]').val(), "123",
            "the onchange has not been applied");

        // save, and check that the int_field input is marked as invalid
        form.$buttons.find('.o_form_button_save').click();
        assert.ok(form.$('input[name="int_field"]').hasClass('o_field_invalid'),
            "input int_field is marked as invalid");

        assert.verifySteps(['read', 'onchange']);
        form.destroy();
    });

    QUnit.test('rpc complete after destroying parent', function (assert) {
        // We just test that there is no crash in this situation
        assert.expect(0);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<button name="update_module" type="object" class="o_form_button_update"/>' +
                '</form>',
            res_id: 2,
            intercepts: {
                execute_action: function (event) {
                    form.destroy();
                    event.data.on_success();
                }
            }
        });
        form.$('.o_form_button_update').click();
    });

    QUnit.test('onchanges that complete after discarding', function (assert) {
        assert.expect(4);

        var def1 = $.Deferred();

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
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    assert.step('onchange is done');
                    return def1.then(function () {
                        return result;
                    });
                }
                return result;
            },
        });

        // go into edit mode
        assert.strictEqual(form.$('span[name="foo"]').text(), "blip",
            "field foo should be displayed to initial value");
        form.$buttons.find('.o_form_button_edit').click();

        // edit a value
        form.$('input').first().val("1234").trigger('input');

        // discard changes
        form.$buttons.find('.o_form_button_cancel').click();
        $('.modal-footer .btn-primary').click();
        assert.strictEqual(form.$('span[name="foo"]').text(), "blip",
            "field foo should still be displayed to initial value");

        // complete the onchange
        def1.resolve();
        assert.strictEqual(form.$('span[name="foo"]').text(), "blip",
            "field foo should still be displayed to initial value");

        form.destroy();
    });

    QUnit.test('discarding before save returns', function (assert) {
        assert.expect(4);

        var def = $.Deferred();

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group><field name="foo"/></group>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'write') {
                    return def.then(_.constant(result));
                }
                return result;
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('input').val("1234").trigger('input');

        // save the value and discard directly
        form.$buttons.find('.o_form_button_save').click();
        form.discardChanges(); // Simulate click on breadcrumb

        assert.strictEqual(form.$('.o_field_widget[name="foo"]').val(), "1234",
            "field foo should still contain new value");
        assert.strictEqual($('.modal').length, 0,
            "Confirm dialog should not be displayed");

        // complete the write
        def.resolve();

        assert.strictEqual($('.modal').length, 0,
            "Confirm dialog should not be displayed");
        assert.strictEqual(form.$('.o_field_widget[name="foo"]').text(), "1234",
            "value should have been saved and rerendered in readonly");

        form.destroy();
    });

    QUnit.test('unchanged relational data is sent for onchanges', function (assert) {
        assert.expect(1);

        this.data.partner.records[1].p = [4];
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
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="foo"/>' +
                                '<field name="bar"/>' +
                            '</tree>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.deepEqual(args.args[1].p, [[4, 4, false]],
                        "should send a command for field p even if it hasn't changed");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input:first').val('trigger an onchange').trigger('input');

        form.destroy();
    });

    QUnit.test('onchanges on unknown fields of o2m are ignored', function (assert) {
        // many2one fields need to be postprocessed (the onchange returns [id,
        // display_name]), but if we don't know the field, we can't know it's a
        // many2one, so it isn't ignored, its value is an array instead of a
        // dataPoint id, which may cause errors later (e.g. when saving).
        assert.expect(2);

        this.data.partner.records[1].p = [4];
        this.data.partner.onchanges = {
            foo: function () {},
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="foo"/>' +
                                '<field name="bar"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="foo"/>' +
                                '<field name="product_id"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({
                        value: {
                            p: [
                                [5],
                                [1, 4, {
                                    foo: 'foo changed',
                                    product_id: [37, "xphone"],
                                }]
                            ],
                        },
                    });
                }
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1].p, [[1, 4, {
                        foo: 'foo changed',
                    }]], "should only write value of known fields");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input:first').val('trigger an onchange').trigger('input');

        assert.strictEqual(form.$('.o_data_row td:first').text(), 'foo changed',
            "onchange should have been correctly applied on field in o2m list");

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('onchange value are not discarded on o2m edition', function (assert) {
        assert.expect(4);

        this.data.partner.records[1].p = [4];
        this.data.partner.onchanges = {
            foo: function () {},
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="int_field"/>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="foo"/>' +
                                '<field name="bar"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="foo"/>' +
                                '<field name="product_id"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    return $.when({
                        value: {
                            p: [[5], [1, 4, {foo: 'foo changed'}]],
                        },
                    });
                }
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1].p, [[1, 4, {
                        foo: 'foo changed',
                    }]], "should only write value of known fields");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_data_row td:first').text(), 'My little Foo Value',
            "the initial value should be the default one");

        form.$('input:first').val('trigger an onchange').trigger('input');

        assert.strictEqual(form.$('.o_data_row td:first').text(), 'foo changed',
            "onchange should have been correctly applied on field in o2m list");

        form.$('.o_data_row').click(); // edit the o2m in the dialog
        assert.strictEqual($('.modal .modal-title').text().trim(), 'Open: one2many field',
            "the field string is displayed in the modal title");
        assert.strictEqual($('.modal .o_field_widget').val(), 'foo changed',
            "the onchange value hasn't been discarded when opening the o2m");

        form.destroy();
    });

    QUnit.test('args of onchanges in o2m fields are correct (inline edition)', function (assert) {
        assert.expect(3);

        this.data.partner.records[1].p = [4];
        this.data.partner.fields.p.relation_field = 'rel_field';
        this.data.partner.fields.int_field.default = 14;
        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = '[' + obj.rel_field.foo + '] ' + obj.int_field;
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="p">' +
                            '<tree editable="top">' +
                                '<field name="foo"/>' +
                                '<field name="int_field"/>' +
                            '</tree>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 2,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_data_row td:first').text(), 'My little Foo Value',
            "the initial value should be the default one");

        form.$('.o_data_row td:nth(1)').click(); // edit the o2m inline
        form.$('.o_data_row input:nth(1)').val(77).trigger('input');

        assert.strictEqual(form.$('.o_data_row input:first').val(), '[blip] 77',
            "onchange should have been correctly applied");

        // create a new o2m record
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual(form.$('.o_data_row input:first').val(), '[blip] 14',
            "onchange should have been correctly applied after default get");

        form.destroy();
    });

    QUnit.test('args of onchanges in o2m fields are correct (dialog edition)', function (assert) {
        assert.expect(6);

        this.data.partner.records[1].p = [4];
        this.data.partner.fields.p.relation_field = 'rel_field';
        this.data.partner.fields.int_field.default = 14;
        this.data.partner.onchanges = {
            int_field: function (obj) {
                obj.foo = '[' + obj.rel_field.foo + '] ' + obj.int_field;
            },
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="foo"/>' +
                        '<field name="p" string="custom label">' +
                            '<tree>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="foo"/>' +
                                '<field name="int_field"/>' +
                            '</form>' +
                        '</field>' +
                    '</group>' +
                '</form>',
            res_id: 2,
        });

        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('.o_data_row td:first').text(), 'My little Foo Value',
            "the initial value should be the default one");

        form.$('.o_data_row td:first').click(); // edit the o2m in a dialog
        $('.modal input:nth(1)').val(77).trigger('input');
        assert.strictEqual($('.modal input:first').val(), '[blip] 77',
            "onchange should have been correctly applied");
        $('.modal-footer .btn-primary').click(); // save the dialog
        assert.strictEqual(form.$('.o_data_row td:first').text(), '[blip] 77',
            "onchange should have been correctly applied");

        // create a new o2m record
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal .modal-title').text().trim(), 'Create custom label',
            "the custom field label is applied in the modal title");
        assert.strictEqual($('.modal input:first').val(), '[blip] 14',
            "onchange should have been correctly applied after default get");
        $('.modal-footer .btn-primary').click(); // save the dialog
        assert.strictEqual(form.$('.o_data_row:nth(1) td:first').text(), '[blip] 14',
            "onchange should have been correctly applied after default get");

        form.destroy();
    });

    QUnit.test('context of onchanges contains the context of changed fields', function (assert) {
        assert.expect(2);

        this.data.partner.onchanges = {
            foo: function () {},
        };
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="foo" context="{\'test\': 1}"/>' +
                        '<field name="int_field" context="{\'int_ctx\': 1}"/>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'onchange') {
                    assert.strictEqual(args.args[4].test, 1,
                        "the context of the field triggering the onchange should be given");
                    assert.strictEqual(args.args[4].int_ctx, undefined,
                        "the context of other fields should not be given");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 2,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input:first').val('coucou').trigger('input');

        form.destroy();
    });

    QUnit.test('navigation with tab key in form view', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" widget="email"/>' +
                            '<field name="bar"/>' +
                            '<field name="display_name" widget="url"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        // go to edit mode
        form.$buttons.find('.o_form_button_edit').click();

        // focus first input, trigger tab
        form.$('input[name="foo"]').focus();

        form.$('input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.ok($.contains(form.$('div[name="bar"]')[0], document.activeElement),
            "bar checkbox should be focused");

        form.$('div[name="bar"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('input[name="display_name"]')[0], document.activeElement,
            "display_name should be focused");

        // simulate shift+tab on active element
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "first input should be focused");

        form.destroy();
    });

    QUnit.test('navigation with tab key in readonly form view', function (assert) {
        assert.expect(3);

        this.data.partner.records[1].product_id = 37;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="trululu"/>' +
                            '<field name="foo"/>' +
                            '<field name="product_id"/>' +
                            '<field name="foo" widget="phone"/>' +
                            '<field name="display_name" widget="url"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        // focus first field, trigger tab
        form.$('[name="trululu"]').focus();
        form.$('[name="trululu"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        form.$('[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('[name="product_id"]')[0], document.activeElement,
            "product_id should be focused");
        form.$('[name="product_id"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        form.$('[name="foo"]:eq(1)').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('[name="display_name"]')[0], document.activeElement,
            "display_name should be focused");

        // simulate shift+tab on active element
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB, shiftKey: true}));
        assert.strictEqual(document.activeElement, form.$('[name="trululu"]')[0],
            "first many2one should be focused");

        form.destroy();
    });

    QUnit.test('skip invisible fields when navigating with TAB', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].bar = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="foo"/>' +
                        '<field name="bar" invisible="1"/>' +
                        '<field name="product_id" attrs=\'{"invisible": [["bar", "=", true]]}\'/>' +
                        '<field name="int_field"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').focus();
        form.$('input[name="foo"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('input[name="int_field"]')[0], document.activeElement,
            "int_field should be focused");

        form.destroy();
    });

    QUnit.test('clicking on a stat button with a context', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" type="action" name="1" context="{\'test\': active_id}">' +
                                '<field name="qux" widget="statinfo"/>' +
                            '</button>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            viewOptions: {
                context: {some_context: true},
            },
            intercepts: {
                execute_action: function (e) {
                    assert.deepEqual(e.data.action_data.context, {
                        'test': 2
                    }, "button context should have been evaluated and given to the action, with magicc without previous context");
                },
            },
        });

        form.$('.oe_stat_button').click();

        form.destroy();
    });

    QUnit.test('clicking on a stat button with no context', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button class="oe_stat_button" type="action" name="1">' +
                                '<field name="qux" widget="statinfo"/>' +
                            '</button>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            viewOptions: {
                context: {some_context: true},
            },
            intercepts: {
                execute_action: function (e) {
                    assert.deepEqual(e.data.action_data.context, {
                    }, "button context should have been evaluated and given to the action, with magic keys but without previous context");
                },
            },
        });

        form.$('.oe_stat_button').click();

        form.destroy();
    });

    QUnit.test('diplay a stat button outside a buttonbox', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form string="Partners">' +
                    '<sheet>' +
                        '<button class="oe_stat_button" type="action" name="1">' +
                            '<field name="int_field" widget="statinfo"/>' +
                        '</button>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('button .o_field_widget').length, 1,
            "a field widget should be display inside the button");
        assert.strictEqual(form.$('button .o_field_widget').children().length, 2,
            "the field widget should have 2 children, the text and the value");
        assert.strictEqual(parseInt(form.$('button .o_field_widget .o_stat_value').text()), 9,
            "the value rendered should be the same than the field value");
        form.destroy();
    });

    QUnit.test('diplay something else than a button in a buttonbox', function (assert) {
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
                        '<label/>' +
                    '</div>' +
                '</form>',
            res_id: 2,
        });

        assert.strictEqual(form.$('.oe_button_box').children().length, 2,
            "button box should contain two children");
        assert.strictEqual(form.$('.oe_button_box > .oe_stat_button').length, 1,
            "button box should only contain one button");
        assert.strictEqual(form.$('.oe_button_box > label').length, 1,
            "button box should only contain one label");

        form.destroy();
    });

    QUnit.test('display correctly buttonbox, in large size class', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<div name="button_box" class="oe_button_box">' +
                        '<button type="object" class="oe_stat_button" icon="fa-check-square">' +
                            '<field name="bar"/>' +
                        '</button>' +
                        '<button type="object" class="oe_stat_button" icon="fa-check-square">' +
                            '<field name="foo"/>' +
                        '</button>' +
                    '</div>' +
                '</form>',
            res_id: 2,
            config: {
                device: {size_class: 5},
            },
        });

        assert.strictEqual(form.$('.oe_button_box').children().length, 2,
            "button box should contain two children");

        form.destroy();
    });

    QUnit.test('one2many default value creation', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].product_ids = [37];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_ids" nolabel="1">' +
                                '<tree editable="top" create="0">' +
                                    '<field name="name" readonly="1"/>' +
                                '</tree>' +
                            '</field>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    return $.when({
                        product_ids: [[0, 0, {
                            name: 'xdroid',
                            partner_type_id: 12,
                        }]]
                    });
                }
                if (args.method === 'create') {
                    var command = args.args[0].product_ids[0];
                    assert.strictEqual(command[2].partner_type_id, 12,
                        "the default partner_type_id should be equal to 12");
                }
                return this._super.apply(this, arguments);
            },
        });
        form.$buttons.find('.o_form_button_save').click();
        form.destroy();
    });

    QUnit.test('many2manys inside one2manys are saved correctly', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree editable="top">' +
                                '<field name="timmy" widget="many2many_tags"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    var command = args.args[0].p;
                    assert.deepEqual(command, [[0, command[0][1], {
                        timmy: [[6, false, [12]]],
                    }]], "the default partner_type_id should be equal to 12");
                }
                return this._super.apply(this, arguments);
            },
        });

        // add a o2m subrecord with a m2m tag
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('.o_many2many_tags_cell').click();
        form.$('.o_field_many2one input').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        $dropdown.find('li:first()').click(); // select the first tag

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('one2manys (list editable) inside one2manys are saved correctly', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="p"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            archs: {
                "partner,false,form": '<form>' +
                        '<field name="p">' +
                            '<tree editable="top">' +
                                '<field name="display_name"/>' +
                            '</tree>' +
                        '</field>' +
                    '</form>'
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0].p,
                        [[0, args.args[0].p[0][1], {
                            p: [[0, args.args[0].p[0][2].p[0][1], {display_name: "xtv"}]],
                        }]],
                        "create should be called with the correct arguments");
                }
                return this._super.apply(this, arguments);
            },
        });

        // add a o2m subrecord
        form.$('.o_field_x2many_list_row_add a').click();
        $('.modal-body .o_field_one2many .o_field_x2many_list_row_add a').click();
        $('.modal-body input').val('xtv').trigger('input');
        $('.modal-footer button:first').click(); // save & close
        assert.strictEqual($('.modal').length, 0,
            "dialog should be closed");

        var row = form.$('.o_field_one2many .o_list_view .o_data_row');
        assert.strictEqual(row.children()[0].textContent, '1 record',
            "the cell should contains the number of record: 1");

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('*_view_ref in context are passed correctly', function (assert) {
        var done = assert.async();
        assert.expect(3);

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p" context="{\'tree_view_ref\':\'module.tree_view_ref\'}"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            intercepts: {
                load_views: function (event) {
                    var context = event.data.context;
                    assert.strictEqual(context.tree_view_ref, 'module.tree_view_ref',
                        "context should contain tree_view_ref");
                    event.data.on_success();
                }
            },
            viewOptions: {
                context: {some_context: false},
            },
            mockRPC: function (route, args) {
                if (args.method === 'read') {
                    assert.strictEqual('some_context' in args.kwargs.context && !args.kwargs.context.some_context, true,
                        "the context should have been set");
                }
                return this._super.apply(this, arguments);
            },
        }).then(function (form) {
            // reload to check that the record's context hasn't been modified
            form.reload();
            form.destroy();
            done();
        });
    });

    QUnit.test('readonly fields with modifiers may be saved', function (assert) {
        // the readonly property on the field description only applies on view,
        // this is not a DB constraint. It should be seen as a default value,
        // that may be overriden in views, for example with modifiers. So
        // basically, a field defined as readonly may be edited.
        assert.expect(3);

        this.data.partner.fields.foo.readonly = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="foo" attrs="{\'readonly\': [(\'bar\',\'=\',False)]}"/>' +
                        '<field name="bar"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1], {foo: 'New foo value'},
                        "the new value should be saved");
                }
                return this._super.apply(this, arguments);
            },
        });

        // bar being set to true, foo shouldn't be readonly and thus its value
        // could be saved, even if in its field description it is readonly
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(form.$('input[name="foo"]').length, 1,
            "foo field should be editable");
        form.$('input[name="foo"]').val('New foo value').trigger('input');

        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_field_widget[name=foo]').text(), 'New foo value',
            "new value for foo field should have been saved");

        form.destroy();
    });

    QUnit.test('check if id and active_id are defined', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p" context="{\'default_trululu\':active_id, \'current_id\':id}">' +
                            '<tree>' +
                                '<field name="trululu"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            archs: {
                "partner,false,form": '<form><field name="trululu"/></form>'
            },
            mockRPC: function (route, args) {
                if (args.method === 'default_get' && args.args[0][0] === 'trululu') {
                  assert.strictEqual(args.kwargs.context.current_id, false,
                      "current_id should be false");
                    assert.strictEqual(args.kwargs.context.default_trululu, false,
                        "default_trululu should be false");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        form.destroy();
    });

    QUnit.test('modifiers are considered on multiple <footer/> tags', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="bar"/>' +
                    '<footer attrs="{\'invisible\': [(\'bar\',\'=\',False)]}">' +
                        '<button>Hello</button>' +
                        '<button>World</button>' +
                    '</footer>' +
                    '<footer attrs="{\'invisible\': [(\'bar\',\'!=\',False)]}">' +
                        '<button>Foo</button>' +
                    '</footer>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                footerToButtons: true,
                mode: 'edit',
            },
        });

        assert.deepEqual(getVisibleButtonTexts(), ["Hello", "World"],
            "only the first button section should be visible");

        form.$(".o_field_boolean input").click();

        assert.deepEqual(getVisibleButtonTexts(), ["Foo"],
            "only the second button section should be visible");

        form.destroy();

        function getVisibleButtonTexts() {
            var $visibleButtons = form.$buttons.find('button:visible');
            return _.map($visibleButtons, function (el) {
                return el.innerHTML.trim();
            });
        }
    });

    QUnit.test('footers are not duplicated on rerender', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<field name="foo"/>' +
                    '<footer>' +
                        '<button>Hello</button>' +
                    '</footer>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                footerToButtons: true,
            },
        });

        assert.strictEqual(form.$('footer').length, 0,
            "footer should have been moved outside of the form view");
        form.reload();
        assert.strictEqual(form.$('footer').length, 0,
            "footer should still have been moved outside of the form view");
        form.destroy();
    });

    QUnit.test('render stat button with string inline', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Manufacturing Orders">' +
                    '<sheet>' +
                        '<div class="oe_button_box" name="button_box">' +
                            '<button string="Inventory Moves" class="oe_stat_button" icon="fa-arrows-v"/>' +
                        '</div>' +
                    '</sheet>' +
                '</form>',
        });
        var $button = form.$('.o_form_view .o_form_sheet .oe_button_box .oe_stat_button span');
        assert.strictEqual($button.text(), "Inventory Moves",
            "the stat button should contain a span with the string attribute value");
        form.destroy();
    });

    QUnit.test('renderer waits for asynchronous fields rendering', function (assert) {
        assert.expect(1);
        var done = assert.async();

        testUtils.createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="bar"/>' +
                    '<field name="foo" widget="ace"/>' +
                    '<field name="int_field"/>' +
                '</form>',
            res_id: 1,
        }).then(function (form) {
            assert.strictEqual(form.$('.ace_editor').length, 1,
                "should have waited for ace to load its dependencies");
            form.destroy();
            done();
        });
    });

    QUnit.test('open one2many form containing one2many', function (assert) {
        assert.expect(9);

        this.data.partner.records[0].product_ids = [37];
        this.data.product.fields.partner_type_ids = {
            string: "one2many partner", type: "one2many", relation: "partner_type",
        };
        this.data.product.records[0].partner_type_ids = [12];

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_ids">' +
                                '<tree create="0">' +
                                    '<field name="display_name"/>' +
                                    '<field name="partner_type_ids"/>' +
                                '</tree>' +
                            '</field>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form':
                    '<form string="Products">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="partner_type_ids">' +
                                    '<tree create="0">' +
                                        '<field name="display_name"/>' +
                                        '<field name="color"/>' +
                                    '</tree>' +
                                '</field>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });
        var row = form.$('.o_field_one2many .o_list_view .o_data_row');
        assert.strictEqual(row.children()[1].textContent, '1 record',
            "the cell should contains the number of record: 1");
        row.click();
        var modal_row = $('.modal-body .o_form_sheet .o_field_one2many .o_list_view .o_data_row');
        assert.strictEqual(modal_row.children().length, 2,
            "the row should contains the 2 fields defined in the form view");
        assert.strictEqual($(modal_row).text(), "gold2",
            "the value of the fields should be fetched and displayed");
        assert.verifySteps(['read', 'read', 'load_views', 'read', 'read'],
            "there should be 4 read rpcs");
        form.destroy();
    });

    QUnit.test('in edit mode, first field is focused', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo"/>' +
                        '<field name="bar"/>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();

        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "foo field should have focus");
        assert.strictEqual(form.$('input[name="foo"]')[0].selectionStart, 3,
            "cursor should be at the end");

        form.destroy();
    });

    QUnit.test('autofocus fields are focused', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="bar"/>' +
                        '<field name="foo" default_focus="1"/>' +
                '</form>',
            res_id: 1,
        });
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "foo field should have focus");

        form.destroy();
    });

    QUnit.test('in create mode, autofocus fields are focused', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="int_field"/>' +
                        '<field name="foo" default_focus="1"/>' +
                '</form>',
        });
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "foo field should have focus");

        form.destroy();
    });

    QUnit.test('create with false values', function (assert) {
        assert.expect(1);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group><field name="bar"/></group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.strictEqual(args.args[0].bar, false,
                        "the false value should be given as parameter");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('autofocus first visible field', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="int_field" invisible="1"/>' +
                        '<field name="foo"/>' +
                '</form>',
        });
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0],
            "foo field should have focus");

        form.destroy();
    });

    QUnit.test('no autofocus with disable_autofocus option [REQUIRE FOCUS]', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="int_field"/>' +
                        '<field name="foo"/>' +
                '</form>',
            viewOptions: {
                disable_autofocus: true,
            },
        });
        assert.notStrictEqual(document.activeElement, form.$('input[name="int_field"]')[0],
            "int_field field should not have focus");

        form.update({});

        assert.notStrictEqual(document.activeElement, form.$('input[name="int_field"]')[0],
            "int_field field should not have focus");

        form.destroy();
    });

    QUnit.test('open one2many form containing many2many_tags', function (assert) {
            assert.expect(4);

            this.data.partner.records[0].product_ids = [37];
            this.data.product.fields.partner_type_ids = {
                string: "many2many partner_type", type: "many2many", relation: "partner_type",
            };
            this.data.product.records[0].partner_type_ids = [12, 14];

            var form = createView({
                View: FormView,
                model: 'partner',
                res_id: 1,
                data: this.data,
                arch: '<form string="Partners">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="product_ids">' +
                                    '<tree create="0">' +
                                        '<field name="display_name"/>' +
                                        '<field name="partner_type_ids" widget="many2many_tags"/>' +
                                    '</tree>' +
                                    '<form string="Products">' +
                                        '<sheet>' +
                                            '<group>' +
                                                '<label for="partner_type_ids"/>' +
                                                '<div>' +
                                                    '<field name="partner_type_ids" widget="many2many_tags"/>' +
                                                '</div>' +
                                            '</group>' +
                                        '</sheet>' +
                                    '</form>' +
                                '</field>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
                mockRPC: function (route, args) {
                    assert.step(args.method);
                    return this._super.apply(this, arguments);
                },
            });
            var row = form.$('.o_field_one2many .o_list_view .o_data_row');
            row.click();
            assert.verifySteps(['read', 'read', 'read'],
                "there should be 3 read rpcs");
            form.destroy();
        });

    QUnit.test('onchanges are applied before checking if it can be saved', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges.foo = function (obj) {};
        this.data.partner.fields.foo.required = true;

        var def = $.Deferred();

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet><group>' +
                        '<field name="foo"/>' +
                    '</group></sheet>' +
                '</form>',
            res_id: 2,
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method);
                if (args.method === 'onchange') {
                    return def.then(function () {
                        return result;
                    });
                }
                return result;
            },
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        assert.step(params.type);
                    }
                }),
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').val('').trigger("input");
        form.$buttons.find('.o_form_button_save').click();

        def.resolve();

        assert.verifySteps(['read', 'onchange', 'warning']);
        form.destroy();
    });

    QUnit.test('display toolbar', function (assert) {
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            res_id: 1,
            arch: '<form string="Partners">' +
                    '<group><field name="bar"/></group>' +
                '</form>',
            toolbar: {
                action: [{
                    model_name: 'partner',
                    name: 'Action partner',
                    type: 'ir.actions.server',
                    usage: 'ir_actions_server',
                }],
                print: [],
            },
            viewOptions: {
                hasSidebar: true,
            },
            mockRPC: function (route, args) {
                if (route === '/web/action/load') {
                    assert.strictEqual(args.context.active_id, 1,
                        "the active_id shoud be 1.");
                    assert.deepEqual(args.context.active_ids, [1],
                        "the active_ids should be an array with 1 inside.");
                    return $.when({});
                }
                return this._super.apply(this, arguments);
            },
        });
        // The toolbar displayed changes if the module 'document' is installed.
        // So if the module is installed, the assertion checks for 3 dropdowns
        // if not only 2 dropdowns are displayed.
        var $dropdowns = $('.o_web_client .o_control_panel .btn-group .o_dropdown_toggler_btn');
        var $actions = $('.o_web_client .o_control_panel .btn-group .dropdown-menu')[1].children;
        assert.strictEqual($dropdowns.length, 2,
            "there should be 2 dropdowns (print, action) in the toolbar.");
        assert.strictEqual($actions.length, 3,
            "there should be 3 actions");
        var $customAction = $('.o_web_client .o_control_panel .btn-group .dropdown-menu:last .dropdown-item:nth(2)');
        assert.strictEqual($customAction.text().trim(), 'Action partner',
            "the custom action should have 'Action partner' as name");
        testUtils.intercept(form, 'do_action', function (event) {
            var context = event.data.action.context.__contexts[1];
            assert.strictEqual(context.active_id, 1,
                "the active_id shoud be 1.");
            assert.deepEqual(context.active_ids, [1],
                "the active_ids should be an array with 1 inside.");
        });
        $customAction.click();

        form.destroy();
    });

    QUnit.test('check interactions between multiple FormViewDialogs', function (assert) {
        assert.expect(8);

        this.data.product.fields.product_ids = {
            string: "one2many product", type: "one2many", relation: "product",
        };

        this.data.partner.records[0].product_id = 37;

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form':
                    '<form string="Products">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="display_name"/>' +
                                '<field name="product_ids"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
                'product,false,list': '<tree><field name="display_name"/></tree>'
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/get_formview_id') {
                    return $.when(false);
                } else if (args.method === 'write') {
                    assert.strictEqual(args.model, 'product',
                        "should write on product model");
                    assert.strictEqual(args.args[1].product_ids[0][2].display_name, 'xtv',
                        "display_name of the new object should be xtv");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        // Open first dialog
        form.$('.o_external_button').click();
        assert.strictEqual($('.modal').length, 1,
            "One FormViewDialog should be opened");
        var $firstModal = $('.modal');
        assert.strictEqual($('.modal .modal-title').first().text().trim(), 'Open: Product',
            "dialog title should display the python field string as label");
        assert.strictEqual($firstModal.find('input').val(), 'xphone',
            "display_name should be correctly displayed");

        // Open second dialog
        $firstModal.find('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal').length, 2,
            "two FormViewDialogs should be opened");
        var $secondModal = $('.modal:nth(1)');
        // Add new value
        $secondModal.find('input').val('xtv').trigger('input');
        $secondModal.find('.modal-footer button:first').click(); // Save & close
        assert.strictEqual($('.modal').length, 1,
            "last opened dialog should be closed");

        // Check that data in first dialog is correctly updated
        assert.strictEqual($firstModal.find('tr.o_data_row td').text(), 'xtv',
            "should have added a line with xtv as new record");
        $firstModal.find('.modal-footer button:first').click(); // Save & close
        form.destroy();
    });

    QUnit.test('fields and record contexts are not mixed', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<group>' +
                        '<field name="trululu" context="{\'test\': 1}"/>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.strictEqual(args.kwargs.context.test, 1,
                        "field's context should be sent");
                    assert.notOk('mainContext' in args.kwargs.context,
                        "record's context should not be sent");
                }
                return this._super.apply(this, arguments);
            },
            res_id: 2,
            viewOptions: {
                mode: 'edit',
                context: {mainContext: 3},
            },
        });

        form.$('input:first').click(); // trigger the name_search

        form.destroy();
    });

    QUnit.test('do not activate an hidden tab when switching between records', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<notebook>' +
                            '<page string="Foo" attrs=\'{"invisible": [["id", "=", 2]]}\'>' +
                                '<field name="foo"/>' +
                            '</page>' +
                            '<page string="Bar">' +
                                '<field name="bar"/>' +
                            '</page>' +
                        '</notebook>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
        });

        assert.strictEqual(form.$('.o_notebook .nav-item:not(.o_invisible_modifier)').length, 2,
            "both tabs should be visible");
        assert.ok(form.$('.o_notebook .nav-link:first').hasClass('active'),
            "first tab should be active");

        // click on the pager to switch to the next record
        form.pager.$('.o_pager_next').click();
        assert.strictEqual(form.$('.o_notebook .nav-item:not(.o_invisible_modifier)').length, 1,
            "only the second tab should be visible");
        assert.ok(form.$('.o_notebook .nav-item:not(.o_invisible_modifier) .nav-link').hasClass('active'),
            "the visible tab should be active");

        // click on the pager to switch back to the previous record
        form.pager.$('.o_pager_previous').click();
        assert.strictEqual(form.$('.o_notebook .nav-item:not(.o_invisible_modifier)').length, 2,
            "both tabs should be visible again");
        assert.ok(form.$('.o_notebook .nav-link:nth(1)').hasClass('active'),
            "second tab should be active");

        form.destroy();
    });

    QUnit.test('support anchor tags with action type', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                            '<a type="action" name="42"><i class="fa fa-arrow-right"/> Click me !</a>' +
                  '</form>',
            res_id: 1,
            intercepts: {
                do_action: function (event) {
                    assert.strictEqual(event.data.action, "42",
                        "should trigger do_action with correct action parameter");
                }
            }
        });
        form.$('a[type="action"]').click();

        form.destroy();
    });

    QUnit.test('do not perform extra RPC to read invisible many2one fields', function (assert) {
        assert.expect(2);

        this.data.partner.fields.trululu.default = 2;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="trululu" invisible="1"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
        });

        assert.verifySteps(['default_get'], "only one RPC should have been done");

        form.destroy();
    });

    QUnit.test('do not perform extra RPC to read invisible x2many fields', function (assert) {
        assert.expect(2);

        this.data.partner.records[0].p = [2]; // one2many
        this.data.partner.records[0].product_ids = [37]; // one2many
        this.data.partner.records[0].timmy = [12]; // many2many

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p" invisible="1"/>' + // no inline view
                        '<field name="product_ids" invisible="1">' + // inline view
                            '<tree><field name="display_name"/></tree>' +
                        '</field>' +
                        '<field name="timmy" invisible="1" widget="many2many_tags"/>' + // no view
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
            res_id: 1,
        });

        assert.verifySteps(['read'], "only one read should have been done");

        form.destroy();
    });

    QUnit.test('default_order on x2many embedded view', function (assert) {
        assert.expect(11);

        this.data.partner.fields.display_name.sortable = true;
        this.data.partner.records[0].p = [1, 4];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc">' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                                '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
            res_id: 1,
        });

        assert.ok(form.$('.o_field_one2many tbody tr:first td:contains(yop)').length,
            "record 1 should be first");
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal').length, 1,
            "FormViewDialog should be opened");
        $('.modal input[name="foo"]').val('xop').trigger("input");
        $('.modal-footer button:eq(1)').click(); // Save & new
        $('.modal input[name="foo"]').val('zop').trigger("input");
        $('.modal-footer button:first').click(); // Save & close

        // client-side sort
        assert.ok(form.$('.o_field_one2many tbody tr:eq(0) td:contains(zop)').length,
            "record zop should be first");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(1) td:contains(yop)').length,
            "record yop should be second");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(2) td:contains(xop)').length,
            "record xop should be third");

        // server-side sort
        form.$buttons.find('.o_form_button_save').click();
        assert.ok(form.$('.o_field_one2many tbody tr:eq(0) td:contains(zop)').length,
            "record zop should be first");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(1) td:contains(yop)').length,
            "record yop should be second");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(2) td:contains(xop)').length,
            "record xop should be third");

        // client-side sort on edit
        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_one2many tbody tr:eq(1) td:contains(yop)').click();
        $('.modal input[name="foo"]').val('zzz').trigger("input");
        $('.modal-footer button:first').click(); // Save
        assert.ok(form.$('.o_field_one2many tbody tr:eq(0) td:contains(zzz)').length,
            "record zzz should be first");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(1) td:contains(zop)').length,
            "record zop should be second");
        assert.ok(form.$('.o_field_one2many tbody tr:eq(2) td:contains(xop)').length,
            "record xop should be third");

        form.destroy();
    });

    QUnit.test('action context is used when evaluating domains', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="trululu" domain="[(\'id\', \'in\', context.get(\'product_ids\', []))]"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                context: {product_ids: [45,46,47]}
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args[0], ['id', 'in', [45,46,47]],
                        "domain should be properly evaluated");
                }
                return this._super.apply(this, arguments);
            },
        });
        form.$buttons.find('.o_form_button_edit').click();
        form.$('div[name="trululu"] input').click();

        form.destroy();
    });

    QUnit.test('form rendering with groups with col/colspan', function (assert) {
        assert.expect(46);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group col="6" class="parent_group">' +
                            '<group col="4" colspan="3" class="group_4">' +
                                '<div colspan="3"/>' +
                                '<div colspan="2"/><div/>' +
                                '<div colspan="4"/>' +
                            '</group>' +
                            '<group col="3" colspan="4" class="group_3">' +
                                '<group col="1" class="group_1">' +
                                    '<div/><div/><div/>' +
                                '</group>' +
                                '<div/>' +
                                '<group col="3" class="field_group">' +
                                    '<field name="foo" colspan="3"/>' +
                                    '<div/><field name="bar" nolabel="1"/>' +
                                    '<field name="qux"/>' +
                                    '<field name="int_field" colspan="3" nolabel="1"/>' +
                                    '<span/><field name="product_id"/>' +
                                '</group>' +
                            '</group>' +
                        '</group>' +
                        '<group>' +
                            '<field name="p">' +
                                '<tree>' +
                                    '<field name="display_name"/>' +
                                    '<field name="foo"/>' +
                                    '<field name="int_field"/>' +
                                '</tree>' +
                            '</field>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        var $parentGroup = form.$('.parent_group');
        var $group4 = form.$('.group_4');
        var $group3 = form.$('.group_3');
        var $group1 = form.$('.group_1');
        var $fieldGroup = form.$('.field_group');

        // Verify outergroup/innergroup
        assert.strictEqual($parentGroup[0].tagName, 'DIV', ".parent_group should be an outergroup");
        assert.strictEqual($group4[0].tagName, 'TABLE', ".group_4 should be an innergroup");
        assert.strictEqual($group3[0].tagName, 'DIV', ".group_3 should be an outergroup");
        assert.strictEqual($group1[0].tagName, 'TABLE', ".group_1 should be an innergroup");
        assert.strictEqual($fieldGroup[0].tagName, 'TABLE', ".field_group should be an innergroup");

        // Verify .parent_group content
        var $parentGroupChildren = $parentGroup.children();
        assert.strictEqual($parentGroupChildren.length, 2, "there should be 2 groups in .parent_group");
        assert.ok($parentGroupChildren.eq(0).is('.o_group_col_6'), "first .parent_group group should be 1/2 parent width");
        assert.ok($parentGroupChildren.eq(1).is('.o_group_col_8'), "second .parent_group group should be 2/3 parent width");

        // Verify .group_4 content
        var $group4rows = $group4.find('> tbody > tr');
        assert.strictEqual($group4rows.length, 3, "there should be 3 rows in .group_4");
        var $group4firstRowTd = $group4rows.eq(0).children('td');
        assert.strictEqual($group4firstRowTd.length, 1, "there should be 1 td in first row");
        assert.strictEqual($group4firstRowTd.attr('colspan'), "3", "the first td colspan should be 3");
        assert.strictEqual($group4firstRowTd.attr('style').substr(0, 9), "width: 75", "the first td should be 75% width");
        assert.strictEqual($group4firstRowTd.children()[0].tagName, "DIV", "the first td should contain a div");
        var $group4secondRowTds = $group4rows.eq(1).children('td');
        assert.strictEqual($group4secondRowTds.length, 2, "there should be 2 tds in second row");
        assert.strictEqual($group4secondRowTds.eq(0).attr('colspan'), "2", "the first td colspan should be 2");
        assert.strictEqual($group4secondRowTds.eq(0).attr('style').substr(0, 9), "width: 50", "the first td be 50% width");
        assert.strictEqual($group4secondRowTds.eq(1).attr('colspan'), undefined, "the second td colspan should be default one (1)");
        assert.strictEqual($group4secondRowTds.eq(1).attr('style').substr(0, 9), "width: 25", "the second td be 75% width");
        var $group4thirdRowTd = $group4rows.eq(2).children('td');
        assert.strictEqual($group4thirdRowTd.length, 1, "there should be 1 td in third row");
        assert.strictEqual($group4thirdRowTd.attr('colspan'), "4", "the first td colspan should be 4");
        assert.strictEqual($group4thirdRowTd.attr('style').substr(0, 10), "width: 100", "the first td should be 100% width");

        // Verify .group_3 content
        assert.strictEqual($group3.children().length, 3, ".group_3 should have 3 children");
        assert.strictEqual($group3.children('.o_group_col_4').length, 3, ".group_3 should have 3 children of 1/3 width");

        // Verify .group_1 content
        assert.strictEqual($group1.find('> tbody > tr').length, 3, "there should be 3 rows in .group_1");

        // Verify .field_group content
        var $fieldGroupRows = $fieldGroup.find('> tbody > tr');
        assert.strictEqual($fieldGroupRows.length, 5, "there should be 5 rows in .field_group");
        var $fieldGroupFirstRowTds = $fieldGroupRows.eq(0).children('td');
        assert.strictEqual($fieldGroupFirstRowTds.length, 2, "there should be 2 tds in first row");
        assert.ok($fieldGroupFirstRowTds.eq(0).hasClass('o_td_label'), "first td should be a label td");
        assert.strictEqual($fieldGroupFirstRowTds.eq(1).attr('colspan'), "2", "second td colspan should be given colspan (3) - 1 (label)");
        assert.strictEqual($fieldGroupFirstRowTds.eq(1).attr('style').substr(0, 10), "width: 100", "second td width should be 100%");
        var $fieldGroupSecondRowTds = $fieldGroupRows.eq(1).children('td');
        assert.strictEqual($fieldGroupSecondRowTds.length, 2, "there should be 2 tds in second row");
        assert.strictEqual($fieldGroupSecondRowTds.eq(0).attr('colspan'), undefined, "first td colspan should be default one (1)");
        assert.strictEqual($fieldGroupSecondRowTds.eq(0).attr('style').substr(0, 9), "width: 33", "first td width should be 33.3333%");
        assert.strictEqual($fieldGroupSecondRowTds.eq(1).attr('colspan'), undefined, "second td colspan should be default one (1)");
        assert.strictEqual($fieldGroupSecondRowTds.eq(1).attr('style').substr(0, 9), "width: 33", "second td width should be 33.3333%");
        var $fieldGroupThirdRowTds = $fieldGroupRows.eq(2).children('td'); // new row as label/field pair colspan is greater than remaining space
        assert.strictEqual($fieldGroupThirdRowTds.length, 2, "there should be 2 tds in third row");
        assert.ok($fieldGroupThirdRowTds.eq(0).hasClass('o_td_label'), "first td should be a label td");
        assert.strictEqual($fieldGroupThirdRowTds.eq(1).attr('colspan'), undefined, "second td colspan should be default one (1)");
        assert.strictEqual($fieldGroupThirdRowTds.eq(1).attr('style').substr(0, 9), "width: 50", "second td should be 50% width");
        var $fieldGroupFourthRowTds = $fieldGroupRows.eq(3).children('td');
        assert.strictEqual($fieldGroupFourthRowTds.length, 1, "there should be 1 td in fourth row");
        assert.strictEqual($fieldGroupFourthRowTds.attr('colspan'), "3", "the td should have a colspan equal to 3");
        assert.strictEqual($fieldGroupFourthRowTds.attr('style').substr(0, 10), "width: 100", "the td should have 100% width");
        var $fieldGroupFifthRowTds = $fieldGroupRows.eq(4).children('td'); // label/field pair can be put after the 1-colspan span
        assert.strictEqual($fieldGroupFifthRowTds.length, 3, "there should be 3 tds in fourth row");
        assert.strictEqual($fieldGroupFifthRowTds.eq(0).attr('style').substr(0, 9), "width: 50", "the first td should 50% width");
        assert.ok($fieldGroupFifthRowTds.eq(1).hasClass('o_td_label'), "the second td should be a label td");
        assert.strictEqual($fieldGroupFifthRowTds.eq(2).attr('style').substr(0, 9), "width: 50", "the third td should 50% width");

        // Verify that one2many list table hasn't been impacted
        assert.strictEqual(form.$('.o_field_one2many th:first').attr('style'), undefined,
            "o2m list columns should have no width harcoded");

        form.destroy();
    });

    QUnit.test('outer and inner groups string attribute', function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group string="parent group" class="parent_group">' +
                            '<group string="child group 1" class="group_1">' +
                                '<field name="bar"/>' +
                            '</group>' +
                            '<group string="child group 2" class="group_2">' +
                                '<field name="bar"/>' +
                            '</group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        var $parentGroup = form.$('.parent_group');
        var $group1 = form.$('.group_1');
        var $group2 = form.$('.group_2');

        assert.strictEqual(form.$('table.o_inner_group').length, 2,
            "should contain two inner groups");
        assert.strictEqual($group1.find('.o_horizontal_separator').length, 1,
            "inner group should contain one string separator");
        assert.strictEqual($group1.find('.o_horizontal_separator:contains(child group 1)').length, 1,
            "first inner group should contain 'child group 1' string");
        assert.strictEqual($group2.find('.o_horizontal_separator:contains(child group 2)').length, 1,
            "second inner group should contain 'child group 2' string");
        assert.strictEqual($parentGroup.find('> div.o_horizontal_separator:contains(parent group)').length, 1,
            "outer group should contain 'parent group' string");

        form.destroy();
    });

    QUnit.test('form group with newline tag inside', function (assert) {
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:
                '<form>' +
                    '<sheet>' +
                        '<group col="5" class="main_inner_group">' +
                            // col=5 otherwise the test is ok even without the
                            // newline code as this will render a <newline/> DOM
                            // element in the third column, leaving no place for
                            // the next field and its label on the same line.
                            '<field name="foo"/>' +
                            '<newline/>' +
                            '<field name="bar"/>' +
                            '<field name="qux"/>' +
                        '</group>' +
                        '<group col="3">' +
                            // col=3 otherwise the test is ok even without the
                            // newline code as this will render a <newline/> DOM
                            // element with the o_group_col_6 class, leaving no
                            // place for the next group on the same line.
                            '<group class="top_group">' +
                                '<div style="height: 200px;"/>' +
                            '</group>' +
                            '<newline/>' +
                            '<group class="bottom_group">' +
                                '<div/>' +
                            '</group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // Inner group
        assert.strictEqual(form.$('.main_inner_group > tbody > tr').length, 2,
            "there should be 2 rows in the group");
        assert.strictEqual(form.$('.main_inner_group > tbody > tr:first > .o_td_label').length, 1,
            "there should be only one label in the first row");
        assert.strictEqual(form.$('.main_inner_group > tbody > tr:first .o_field_widget').length, 1,
            "there should be only one widget in the first row");
        assert.strictEqual(form.$('.main_inner_group > tbody > tr:last > .o_td_label').length, 2,
            "there should be two labels in the second row");
        assert.strictEqual(form.$('.main_inner_group > tbody > tr:last .o_field_widget').length, 2,
            "there should be two widgets in the second row");

        // Outer group
        assert.ok((form.$('.bottom_group').position().top - form.$('.top_group').position().top) >= 200,
            "outergroup children should not be on the same line");

        form.destroy();
    });

    QUnit.test('custom open record dialog title', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].p = [2];
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<field name="p" widget="many2many" string="custom label">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                        '<form>' +
                            '<field name="display_name"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            session: {},
            res_id: 1,
        });

        form.$('.o_data_row:first').click();
        assert.strictEqual($('.modal .modal-title').first().text().trim(), 'Open: custom label',
            "modal should use the python field string as title");

        form.destroy();
    });

    QUnit.test('display translation alert', function (assert) {
        assert.expect(2);

        this.data.partner.fields.foo.translate = true;
        this.data.partner.fields.display_name.translate = true;

        var multi_lang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="display_name"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').val("test").trigger("input");
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_view > .alert > div .oe_field_translate').length, 1,
            "should have single translation alert");

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="display_name"]').val("test2").trigger("input");
        form.$buttons.find('.o_form_button_save').click();
        assert.strictEqual(form.$('.o_form_view > .alert > div .oe_field_translate').length, 2,
            "should have two translate fields in translation alert");

        form.destroy();

        _t.database.multi_lang = multi_lang;
    });

    QUnit.test('translation alerts are preserved on pager change', function (assert) {
        assert.expect(5);

        this.data.partner.fields.foo.translate = true;

        var multi_lang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="foo"/>' +
                    '</sheet>' +
                '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').val("test").trigger("input");
        form.$buttons.find('.o_form_button_save').click();

        assert.strictEqual(form.$('.o_form_view > .alert > div').length, 1,
            "should have a translation alert");

        // click on the pager to switch to the next record
        form.pager.$('.o_pager_next').click();
        assert.strictEqual(form.$('.o_form_view > .alert > div').length, 0,
            "should not have a translation alert");

        // click on the pager to switch back to the previous record
        form.pager.$('.o_pager_previous').click();
        assert.strictEqual(form.$('.o_form_view > .alert > div').length, 1,
            "should have a translation alert");

        // remove translation alert by click X and check alert even after form reload
        form.$('.o_form_view > .alert > .close').click();
        assert.strictEqual(form.$('.o_form_view > .alert > div').length, 0,
            "should not have a translation alert");
        form.reload();
        assert.strictEqual(form.$('.o_form_view > .alert > div').length, 0,
            "should not have a translation alert after reload");

        form.destroy();
        _t.database.multi_lang = multi_lang;
    });

    QUnit.test('translation alerts preseved on reverse breadcrumb', function (assert) {
        assert.expect(2);

        this.data['ir.translation'] = {
            fields: {
                name: { string: "name", type: "char" },
                source: {string: "Source", type: "char"},
                value: {string: "Value", type: "char"},
            },
            records: [],
        };

        this.data.partner.fields.foo.translate = true;

        var multi_lang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var archs = {
            'partner,false,form': '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="foo"/>' +
                    '</sheet>' +
                '</form>',
            'partner,false,search': '<search></search>',
            'ir.translation,false,list': '<tree>' +
                        '<field name="name"/>' +
                        '<field name="source"/>' +
                        '<field name="value"/>' +
                    '</tree>',
            'ir.translation,false,search': '<search></search>',
        };

        var actions = [{
            id: 1,
            name: 'Partner',
            res_model: 'partner',
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
        }, {
            id: 2,
            name: 'Translate',
            res_model: 'ir.translation',
            type: 'ir.actions.act_window',
            views: [[false, 'list']],
            target: 'current',
            flags: {'search_view': true, 'action_buttons': true},
        }];

        var actionManager = createActionManager({
            actions: actions,
            archs: archs,
            data: this.data,
        });

        actionManager.doAction(1);

        actionManager.controlPanel.$el.find('.o_form_button_edit').click();
        actionManager.$('input[name="foo"]').val("test").trigger("input");
        actionManager.controlPanel.$el.find('.o_form_button_save').click();

        assert.strictEqual(actionManager.$('.o_form_view > .alert > div').length, 1,
            "should have a translation alert");

        var currentController = actionManager.getCurrentController().widget;
        actionManager.doAction(2, {
            on_reverse_breadcrumb: function () {
                if (!_.isEmpty(currentController.renderer.alertFields)) {
                    currentController.renderer.displayTranslationAlert();
                }
                return false;
            },
        });

        $('.o_control_panel .breadcrumb a:first').click();
        assert.strictEqual(actionManager.$('.o_form_view > .alert > div').length, 1,
            "should have a translation alert");

        actionManager.destroy();
        _t.database.multi_lang = multi_lang;
    });

    QUnit.test('translate event correctly handled with multiple controllers', function (assert) {
        assert.expect(3);

        this.data.product.fields.name.translate = true;
        this.data.partner.records[0].product_id = 37;
        var nbTranslateCalls = 0;

        var multi_lang = _t.database.multi_lang;
        _t.database.multi_lang = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form': '<form>' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="name"/>' +
                                '<field name="partner_type_id"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/product/get_formview_id') {
                    return $.when(false);
                } else if (route === "/web/dataset/call_button" && args.method === 'translate_fields') {
                    assert.deepEqual(args.args, ["product",37,"name",{}], 'should call "call_button" route');
                    nbTranslateCalls++;
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('[name="product_id"] .o_external_button').click();

        assert.strictEqual($('.modal-body .o_field_translate').length, 1,
            "there should be a translate button in the modal");

        $('.modal-body .o_field_translate').click();

        assert.strictEqual(nbTranslateCalls, 1, "should call_button translate once");

        form.destroy();
        _t.database.multi_lang = multi_lang;
    });

    QUnit.test('buttons are disabled until status bar action is resolved', function (assert) {
        assert.expect(9);

        var def = $.Deferred();

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
                        '<div name="button_box" class="oe_button_box">' +
                            '<button class="oe_stat_button">' +
                                '<field name="bar"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            intercepts: {
                execute_action: function (event) {
                    return def.then(function() {
                        event.data.on_success();
                    });
                }
            },
        });

        assert.strictEqual(form.$buttons.find('button:not(:disabled)').length, 4,
            "control panel buttons should be enabled");
        assert.strictEqual(form.$('.o_form_statusbar button:not(:disabled)').length, 2,
            "status bar buttons should be enabled");
        assert.strictEqual(form.$('.oe_button_box button:not(:disabled)').length, 1,
            "stat buttons should be enabled");

        form.$('.o_form_statusbar button').click();

        // The unresolved deferred lets us check the state of the buttons
        assert.strictEqual(form.$buttons.find('button:disabled').length, 4,
            "control panel buttons should be disabled");
        assert.strictEqual(form.$('.o_form_statusbar button:disabled').length, 2,
            "status bar buttons should be disabled");
        assert.strictEqual(form.$('.oe_button_box button:disabled').length, 1,
            "stat buttons should be disabled");

        def.resolve();

        assert.strictEqual(form.$buttons.find('button:not(:disabled)').length, 4,
            "control panel buttons should be enabled");
        assert.strictEqual(form.$('.o_form_statusbar button:not(:disabled)').length, 2,
            "status bar buttons should be enabled");
        assert.strictEqual(form.$('.oe_button_box button:not(:disabled)').length, 1,
            "stat buttons should be enabled");

        form.destroy();
    });

    QUnit.test('buttons are disabled until button box action is resolved', function (assert) {
        assert.expect(9);

        var def = $.Deferred();

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
                        '<div name="button_box" class="oe_button_box">' +
                            '<button class="oe_stat_button">' +
                                '<field name="bar"/>' +
                            '</button>' +
                        '</div>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            intercepts: {
                execute_action: function (event) {
                    return def.then(function() {
                        event.data.on_success();
                    });
                }
            },
        });

        assert.strictEqual(form.$buttons.find('button:not(:disabled)').length, 4,
            "control panel buttons should be enabled");
        assert.strictEqual(form.$('.o_form_statusbar button:not(:disabled)').length, 2,
            "status bar buttons should be enabled");
        assert.strictEqual(form.$('.oe_button_box button:not(:disabled)').length, 1,
            "stat buttons should be enabled");

        form.$('.oe_button_box button').click();

        // The unresolved deferred lets us check the state of the buttons
        assert.strictEqual(form.$buttons.find('button:disabled').length, 4,
            "control panel buttons should be disabled");
        assert.strictEqual(form.$('.o_form_statusbar button:disabled').length, 2,
            "status bar buttons should be disabled");
        assert.strictEqual(form.$('.oe_button_box button:disabled').length, 1,
            "stat buttons should be disabled");

        def.resolve();

        assert.strictEqual(form.$buttons.find('button:not(:disabled)').length, 4,
            "control panel buttons should be enabled");
        assert.strictEqual(form.$('.o_form_statusbar button:not(:disabled)').length, 2,
            "status bar buttons should be enabled");
        assert.strictEqual(form.$('.oe_button_box button:not(:disabled)').length, 1,
            "stat buttons should be enabled");

        form.destroy();
    });

    QUnit.test('buttons with "confirm" attribute save before calling the method', function (assert) {
        assert.expect(9);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button name="post" class="p" string="Confirm" type="object" ' +
                            'confirm="Very dangerous. U sure?"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<field name="foo"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
            intercepts: {
                execute_action: function (event) {
                    assert.step('execute_action');
                },
            },
        });

        // click on button, and cancel in confirm dialog
        form.$('.o_statusbar_buttons button').click();
        assert.ok(form.$('.o_statusbar_buttons button').prop('disabled'),
            'button should be disabled');
        $('.modal-footer button.btn-secondary').click();
        assert.ok(!form.$('.o_statusbar_buttons button').prop('disabled'),
            'button should no longer be disabled');

        assert.verifySteps(['default_get']);

        // click on button, and click on ok in confirm dialog
        form.$('.o_statusbar_buttons button').click();
        assert.verifySteps(['default_get']);
        $('.modal-footer button.btn-primary').click();

        assert.verifySteps(['default_get', 'create', 'read', 'execute_action']);

        form.destroy();
    });

    QUnit.test('buttons are disabled until action is resolved (in dialogs)', function (assert) {
        assert.expect(3);

        var def = $.Deferred();

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="trululu"/>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form': '<form>' +
                        '<sheet>' +
                            '<div name="button_box" class="oe_button_box">' +
                                '<button class="oe_stat_button">' +
                                    '<field name="bar"/>' +
                                '</button>' +
                            '</div>' +
                            '<group>' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
            },
            res_id: 1,
            intercepts: {
                execute_action: function (event) {
                    return def.then(function() {
                        event.data.on_success();
                    });
                }
            },
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_id') {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('.o_external_button').click();

        assert.notOk($('.modal .oe_button_box button').attr('disabled'),
            "stat buttons should be enabled");

        $('.modal .oe_button_box button').click();

        assert.ok($('.modal .oe_button_box button').attr('disabled'),
            "stat buttons should be disabled");

        def.resolve();

        assert.notOk($('.modal .oe_button_box button').attr('disabled'),
            "stat buttons should be enabled");

        form.destroy();
    });

    QUnit.test('multiple clicks on save should reload only once', function (assert) {
        assert.expect(4);

        var def = $.Deferred();

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
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                assert.step(args.method);
                if (args.method === "write") {
                    return def.then(function () {
                        return result;
                    });
                } else {
                    return result;
                }
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').val("test").trigger("input");
        form.$buttons.find('.o_form_button_save').click();
        form.$buttons.find('.o_form_button_save').click();

        def.resolve();

        assert.verifySteps([
            'read', // initial read to render the view
            'write', // write on save
            'read' // read on reload
        ]);

        form.destroy();
    });

    QUnit.test('form view is not broken if save operation fails', function (assert) {
        assert.expect(5);

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
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'write' && args.args[1].foo === 'incorrect value') {
                    return $.Deferred().reject();
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="foo"]').val("incorrect value").trigger("input");
        form.$buttons.find('.o_form_button_save').click();

        form.$('input[name="foo"]').val("correct value").trigger("input");

        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps([
            'read', // initial read to render the view
            'write', // write on save (it fails, does not trigger a read)
            'write', // write on save (it works)
            'read' // read on reload
        ]);

        form.destroy();
    });

    QUnit.test('support password attribute', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="foo" password="True"/>' +
                '</form>',
            res_id: 1,
        });

        assert.strictEqual(form.$('span[name="foo"]').text(), '***',
            "password should be displayed with stars");
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[name="foo"]').val(), 'yop',
            "input value should be the password");
        assert.strictEqual(form.$('input[name="foo"]').prop('type'), 'password',
            "input should be of type password");
        form.destroy();
    });

    QUnit.test('support autocomplete attribute', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="display_name" autocomplete="coucou"/>' +
                '</form>',
            res_id: 1,
        });

        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('input[name="display_name"]').attr('autocomplete'), 'coucou',
            "attribute autocomplete should be set");
        form.destroy();
    });

    QUnit.test('context is correctly passed after save & new in FormViewDialog', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 4,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_ids"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'product,false,form':
                    '<form string="Products">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="partner_type_id" ' +
                                    'context="{\'color\': parent.id}"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
                'product,false,list': '<tree><field name="display_name"/></tree>'
            },
            mockRPC: function (route, args) {
                if (args.method === 'name_search') {
                    assert.strictEqual(args.kwargs.context.color, 4,
                        "should use the correct context");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$buttons.find('.o_form_button_edit').click();
        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal').length, 1,
            "One FormViewDialog should be opened");
        // set a value on the m2o
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        $('.modal .o_field_many2one input').click();
        $dropdown.find('li:first()').click();

        $('.modal-footer button:eq(1)').click(); // Save & new
        $('.modal .o_field_many2one input').click();
        $('.modal-footer button:first').click(); // Save & close
        form.destroy();
    });

    QUnit.test('render domain field widget without model', function (assert) {
        assert.expect(3);

        this.data.partner.fields.model_name = { string: "Model name", type: "char" };

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<group>' +
                        '<field name="model_name"/>' +
                        '<field name="display_name" widget="domain" options="{\'model\': \'model_name\'}"/>' +
                    '</group>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'search_count') {
                    assert.strictEqual(args.model, 'test',
                        "should search_count on test");
                    if (!args.kwargs.domain) {
                        return $.Deferred().reject({
                            code: 200,
                            data: {},
                            message: "MockServer._getRecords: given domain has to be an array.",
                        }, $.Event());
                    }
                }
                return this._super.apply(this, arguments);
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name="display_name"]').text(), "Select a model to add a filter.",
            "should contain an error message saying the model is missing");
        form.$('input[name="model_name"]').val("test").trigger("input");
        assert.notStrictEqual(form.$('.o_field_widget[name="display_name"]').text(), "Select a model to add a filter.",
            "should not contain an error message anymore");
        form.destroy();
    });

    QUnit.test('readonly fields are not sent when saving', function (assert) {
        assert.expect(6);

        // define an onchange on display_name to check that the value of readonly
        // fields is correctly sent for onchanges
        this.data.partner.onchanges = {
            display_name: function () {},
            p: function () {},
        };
        var checkOnchange = false;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="display_name"/>' +
                        '</tree>' +
                        '<form string="Partners">' +
                            '<field name="display_name"/>' +
                            '<field name="foo" attrs="{\'readonly\': [[\'display_name\', \'=\', \'readonly\']]}"/>' +
                        '</form>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                if (checkOnchange && args.method === 'onchange') {
                    if (args.args[2] === 'display_name') { // onchange on field display_name
                        assert.strictEqual(args.args[1].foo, 'foo value',
                            "readonly fields value should be sent for onchanges");
                    } else { // onchange on field p
                        assert.deepEqual(args.args[1].p, [
                            [0, args.args[1].p[0][1], {display_name: 'readonly', foo: 'foo value'}]
                        ], "readonly fields value should be sent for onchanges");
                    }
                }
                if (args.method === 'create') {
                    assert.deepEqual(args.args[0], {
                        p: [[0, args.args[0].p[0][1], {display_name: 'readonly'}]]
                    }, "should not have sent the value of the readonly field");
                }
                return this._super.apply(this, arguments);
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();
        assert.strictEqual($('.modal input.o_field_widget[name=foo]').length, 1,
            'foo should be editable');
        checkOnchange = true;
        $('.modal .o_field_widget[name=foo]').val('foo value').trigger('input');
        $('.modal .o_field_widget[name=display_name]').val('readonly').trigger('input');
        assert.strictEqual($('.modal span.o_field_widget[name=foo]').length, 1,
            'foo should be readonly');
        $('.modal-footer .btn-primary').click(); // close the modal
        checkOnchange = false;

        form.$('.o_data_row').click(); // re-open previous record
        assert.strictEqual($('.modal .o_field_widget[name=foo]').text(), 'foo value',
            "the edited value should have been kept");
        $('.modal-footer .btn-primary').click(); // close the modal

        form.$buttons.find('.o_form_button_save').click(); // save the record

        form.destroy();
    });

    QUnit.test('id is False in evalContext for new records', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="id"/>' +
                        '<field name="foo" attrs="{\'readonly\': [[\'id\', \'=\', False]]}"/>' +
                '</form>',
        });

        assert.ok(form.$('.o_field_widget[name=foo]').hasClass('o_readonly_modifier'),
            "foo should be readonly in 'Create' mode");

        form.$buttons.find('.o_form_button_save').click();
        form.$buttons.find('.o_form_button_edit').click();

        assert.notOk(form.$('.o_field_widget[name=foo]').hasClass('o_readonly_modifier'),
            "foo should not be readonly anymore");

        form.destroy();
    });

    QUnit.test('delete a duplicated record', function (assert) {
        assert.expect(5);

        var newRecordID;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                        '<field name="display_name"/>' +
                '</form>',
            res_id: 1,
            viewOptions: {hasSidebar: true},
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'copy') {
                    return result.then(function (id) {
                        newRecordID = id;
                        return id;
                    });
                }
                if (args.method === 'unlink') {
                    assert.deepEqual(args.args[0], [newRecordID],
                        "should delete the newly created record");
                }
                return result;
            },
        });

        form.sidebar.$('a:contains(Duplicate)').click(); // duplicate record 1
        assert.strictEqual(form.$('.o_form_editable').length, 1,
            "form should be in edit mode");
        assert.strictEqual(form.$('.o_field_widget').val(), 'first record (copy)',
            "duplicated record should have correct name");
        form.$buttons.find('.o_form_button_save').click(); // save duplicated record

        form.sidebar.$('a:contains(Delete)').click(); // delete duplicated record
        assert.strictEqual($('.modal').length, 1, "should have opened a confirm dialog");
        $('.modal-footer .btn-primary').click(); // confirm

        assert.strictEqual(form.$('.o_field_widget').text(), 'first record',
            "should have come back to previous record");

        form.destroy();
    });

    QUnit.test('display tooltips for buttons', function (assert) {
        assert.expect(2);

        var initialDebugMode = config.debug;
        config.debug = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button name="some_method" class="oe_highlight" string="Button" type="object"/>' +
                    '</header>' +
                    '<button name="other_method" class="oe_highlight" string="Button2" type="object"/>' +
                '</form>',
        });

        var $button = form.$('.o_form_statusbar button');
        $button.tooltip('show', false);
        $button.trigger($.Event('mouseenter'));

        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1,
            "should have rendered a tooltip");
        $button.trigger($.Event('mouseleave'));

        var $secondButton = form.$('button[name="other_method"]');
        $secondButton.tooltip('show', false);
        $secondButton.trigger($.Event('mouseenter'));

        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1,
            "should have rendered a tooltip");
        $secondButton.trigger($.Event('mouseleave'));

        config.debug = initialDebugMode;
        form.destroy();
    });

    QUnit.test('reload event is handled only once', function (assert) {
        // In this test, several form controllers are nested (two of them are
        // opened in dialogs). When the users clicks on save in the last
        // opened dialog, a 'reload' event is triggered up to reload the (direct)
        // parent view. If this event isn't stopPropagated by the first controller
        // catching it, it will crash when the other one will try to handle it,
        // as this one doesn't know at all the dataPointID to reload.
        assert.expect(11);

        var arch = '<form>' +
                        '<field name="display_name"/>' +
                        '<field name="trululu"/>' +
                    '</form>';
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: arch,
            archs: {
                'partner,false,form': arch,
            },
            res_id: 2,
            mockRPC: function (route, args) {
                assert.step(args.method);
                if (args.method === 'get_formview_id') {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('.o_external_button').click(); // open the many2one record in a modal
        $('.modal .o_external_button').click(); // in the modal, open the many2one record in another modal

        $('.modal:nth(1) .o_field_widget[name=display_name]').val('new name').trigger('input');
        $('.modal:nth(1) footer .btn-primary').first().click(); // save changes

        assert.strictEqual($('.modal .o_field_widget[name=trululu] input').val(), 'new name',
            "record should have been reloaded");
        assert.verifySteps([
            "read", // main record
            "get_formview_id", // id of first form view opened in a dialog
            "load_views", // arch of first form view opened in a dialog
            "read", // first dialog
            "get_formview_id", // id of second form view opened in a dialog
            "load_views", // arch of second form view opened in a dialog
            "read", // second dialog
            "write", // save second dialog
            "read", // reload first dialog
        ]);

        form.destroy();
    });

    QUnit.test('process the context for inline subview', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].p = [2];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p">' +
                        '<tree>' +
                            '<field name="foo"/>' +
                            '<field name="bar" invisible="context.get(\'hide_bar\', False)"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                context: {hide_bar: true},
            },
        });
        assert.strictEqual(form.$('.o_list_view thead tr th').length, 1,
            "there should be only one column");
        form.destroy();
    });

    QUnit.test('process the context for subview not inline', function (assert) {
        assert.expect(1);

        this.data.partner.records[0].p = [2];

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="p"/>' +
                '</form>',
            archs: {
                "partner,false,list": '<tree>' +
                    '<field name="foo"/>' +
                    '<field name="bar" invisible="context.get(\'hide_bar\', False)"/>' +
                '</tree>',
            },
            res_id: 1,
            viewOptions: {
                context: {hide_bar: true},
            },
        });
        assert.strictEqual(form.$('.o_list_view thead tr th').length, 1,
            "there should be only one column");
        form.destroy();
    });

    QUnit.test('can toggle column in x2many in sub form view', function (assert) {
        assert.expect(2);

        this.data.partner.records[2].p = [1,2];
        this.data.partner.fields.foo.sortable = true;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="trululu"/>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/partner/get_formview_id') {
                    return $.when(false);
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                'partner,false,form': '<form string="Partners">' +
                        '<field name="p">' +
                            '<tree>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                        '</field>' +
                    '</form>',
            },
            viewOptions: {mode: 'edit'},
        });
        form.$('.o_external_button').click();
        assert.strictEqual($('.modal-body .o_form_view .o_list_view .o_data_cell').text(), "yopblip",
            "table has some initial order");

        $('.modal-body .o_form_view .o_list_view th').click();
        assert.strictEqual($('.modal-body .o_form_view .o_list_view .o_data_cell').text(), "blipyop",
            "table is now sorted");
        form.destroy();
    });

    QUnit.test('rainbowman attributes correctly passed on button click', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<button name="action_won" string="Won" type="object" effect="{\'message\': \'Congrats!\'}"/>' +
                    '</header>' +
                '</form>',
            intercepts: {
                execute_action: function (event) {
                    var effectDescription = pyUtils.py_eval(event.data.action_data.effect);
                    assert.deepEqual(effectDescription, {message: 'Congrats!'}, "should have correct effect description");
                }
            }
        });

        form.$('.o_form_statusbar .btn-secondary').click();
        form.destroy();
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

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<field name="bar"/>' +
                    '<widget name="test"/>' +
                '</form>',
        });

        assert.strictEqual(form.$('.o_widget').text(), '{"foo":"My little Foo Value","bar":false}',
            "widget should have been instantiated");

        form.destroy();
        delete widgetRegistry.map.test;
    });

    QUnit.test('support header button as widgets on form statusbar', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<header>' +
                        '<widget name="attach_document" string="Attach document"/>' +
                    '</header>' +
                '</form>',
        });

        assert.strictEqual(form.$('button.o_attachment_button').length, 1,
            "should have 1 attach_document widget in the statusbar");
        assert.strictEqual(form.$('span.o_attach_document').text().trim(), 'Attach document',
            "widget should have been instantiated");

        form.destroy();
    });

    QUnit.test('basic support for widgets', function (assert) {
        assert.expect(1);

        var MyWidget = Widget.extend({
            init: function (parent, dataPoint) {
                this.data = dataPoint.data;
            },
            start: function () {
                this.$el.text(this.data.foo + "!");
            },
            updateState: function (dataPoint) {
                this.$el.text(dataPoint.data.foo + "!");
            },
        });
        widgetRegistry.add('test', MyWidget);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                    '<widget name="test"/>' +
                '</form>',
        });

        form.$('input[name="foo"]').val("I am alive").trigger('input');
        assert.strictEqual(form.$('.o_widget').text(), 'I am alive!',
            "widget should have been updated");

        form.destroy();
        delete widgetRegistry.map.test;
    });


    QUnit.test('bounce edit button in readonly mode', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<div class="oe_title">' +
                        '<field name="display_name"/>' +
                    '</div>' +
                '</form>',
            res_id: 1,
            intercepts: {
                bounce_edit: function() {
                    assert.step('bounce');
                },
            },
        });

        // in readonly
        form.$('[name="display_name"]').click();
        assert.verifySteps(['bounce']);

        // in edit
        form.$buttons.find('.o_form_button_edit').click();
        form.$('[name="display_name"]').click();
        assert.verifySteps(['bounce']);

        form.destroy();
    });

    QUnit.test('proper stringification in debug mode tooltip', function (assert) {
        assert.expect(4);

        var initialDebugMode = config.debug;
        config.debug = true;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id" context="{\'lang\': \'en_US\'}" ' +
                            'attrs=\'{"invisible": [["product_id", "=", 33]]}\'/>' +
                    '</sheet>' +
                '</form>',
        });

        var $field = form.$('[name="product_id"]');
        $field.tooltip('show', true);
        $field.trigger($.Event('mouseenter'));
        assert.strictEqual($('.oe_tooltip_technical>li[data-item="context"]').length,
            1, 'context should be present for this field');
        assert.strictEqual($('.oe_tooltip_technical>li[data-item="context"]')[0].lastChild.wholeText.trim(),
            "{'lang': 'en_US'}", "context should be properly stringified");

        assert.strictEqual($('.oe_tooltip_technical>li[data-item="modifiers"]').length,
            1, 'modifiers should be present for this field');
        assert.strictEqual($('.oe_tooltip_technical>li[data-item="modifiers"]')[0].lastChild.wholeText.trim(),
            '{"invisible":[["product_id","=",33]]}', "modifiers should be properly stringified");

        config.debug = initialDebugMode;
        form.destroy();
    });

    QUnit.test('autoresize of text fields is done when switching to edit mode', function (assert) {
        assert.expect(4);

        this.data.partner.fields.text_field = { string: 'Text field', type: 'text' };
        this.data.partner.fields.text_field.default = "some\n\nmulti\n\nline\n\ntext\n";
        this.data.partner.records[0].text_field = "a\nb\nc\nd\ne\nf";

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                        '<field name="text_field"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // switch to edit mode to ensure that autoresize is correctly done
        form.$buttons.find('.o_form_button_edit').click();
        var height = form.$('.o_field_widget[name=text_field]').height();
        // focus the field to manually trigger autoresize
        form.$('.o_field_widget[name=text_field]').trigger('focus');
        assert.strictEqual(form.$('.o_field_widget[name=text_field]').height(), height,
            "autoresize should have been done automatically at rendering");
        // next assert simply tries to ensure that the textarea isn't stucked to
        // its minimal size, even after being focused
        assert.ok(height > 80, "textarea should have an height of at least 80px");

        // save and create a new record to ensure that autoresize is correctly done
        form.$buttons.find('.o_form_button_save').click();
        form.$buttons.find('.o_form_button_create').click();
        height = form.$('.o_field_widget[name=text_field]').height();
        // focus the field to manually trigger autoresize
        form.$('.o_field_widget[name=text_field]').trigger('focus');
        assert.strictEqual(form.$('.o_field_widget[name=text_field]').height(), height,
            "autoresize should have been done automatically at rendering");
        assert.ok(height > 80, "textarea should have an height of at least 80px");

        form.destroy();
    });

    QUnit.test('check if the view destroys all widgets and instances', function (assert) {
        assert.expect(1);

        var instanceNumber = 0;
        testUtils.patch(mixins.ParentedMixin, {
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
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                        '<field name="foo"/>' +
                        '<field name="bar"/>' +
                        '<field name="int_field"/>' +
                        '<field name="qux"/>' +
                        '<field name="trululu"/>' +
                        '<field name="timmy"/>' +
                        '<field name="product_id"/>' +
                        '<field name="priority"/>' +
                        '<field name="state"/>' +
                        '<field name="date"/>' +
                        '<field name="datetime"/>' +
                        '<field name="product_ids"/>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc">' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                        '</field>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group>' +
                                '<field name="foo"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>',
                "partner_type,false,list": '<tree><field name="name"/></tree>',
                'product,false,list': '<tree><field name="display_name"/></tree>',

            },
            res_id: 1,
        };

        var form = createView(params);
        form.destroy();

        var initialInstanceNumber = instanceNumber;
        instanceNumber = 0;

        form = createView(params);

        // call destroy function of controller to ensure that it correctly destroys everything
        form.__destroy();

        assert.strictEqual(instanceNumber, initialInstanceNumber + 3, "every widget must be destroyed exept the parent");

        form.destroy();

        testUtils.unpatch(mixins.ParentedMixin);
    });

    QUnit.test('do not change pager when discarding current record', function (assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo"/>' +
                '</form>',
            viewOptions: {
                ids: [1, 2],
                index: 0,
            },
            res_id: 2,
        });

        assert.strictEqual(form.pager.$('.o_pager_counter').text().trim(), '2 / 2',
            'pager should indicate that we are on second record');

        form.$buttons.find('.o_form_button_edit').click();
        form.$buttons.find('.o_form_button_cancel').click();

        assert.strictEqual(form.pager.$('.o_pager_counter').text().trim(), '2 / 2',
            'pager should not have changed');

        form.destroy();
    });

    QUnit.test('edition in form view on a "noCache" model', function (assert) {
        assert.expect(4);

        testUtils.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['partner']),
        });

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.step('write');
                }
                return this._super.apply(this, arguments);
            },
        });
        core.bus.on('clear_cache', form, assert.step.bind(assert, 'clear_cache'));

        form.$('.o_field_widget[name=display_name]').val('new value').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps(['write', 'clear_cache']);

        form.destroy();
        testUtils.unpatch(BasicModel);
    });

    QUnit.test('creation in form view on a "noCache" model', function (assert) {
        assert.expect(4);

        testUtils.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['partner']),
        });

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.step('create');
                }
                return this._super.apply(this, arguments);
            },
        });
        core.bus.on('clear_cache', form, assert.step.bind(assert, 'clear_cache'));

        form.$('.o_field_widget[name=display_name]').val('value').trigger('input');
        form.$buttons.find('.o_form_button_save').click();

        assert.verifySteps(['create', 'clear_cache']);

        form.destroy();
        testUtils.unpatch(BasicModel);
    });

    QUnit.test('deletion in form view on a "noCache" model', function (assert) {
        assert.expect(4);

        testUtils.patch(BasicModel, {
            noCacheModels: BasicModel.prototype.noCacheModels.concat(['partner']),
        });

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<field name="display_name"/>' +
                    '</sheet>' +
                '</form>',
            mockRPC: function (route, args) {
                if (args.method === 'unlink') {
                    assert.step('unlink');
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                hasSidebar: true,
            },
        });
        core.bus.on('clear_cache', form, assert.step.bind(assert, 'clear_cache'));

        form.sidebar.$('a:contains(Delete)').click();
        $('.modal-footer .btn-primary').click(); // confirm

        assert.verifySteps(['unlink', 'clear_cache']);

        form.destroy();
        testUtils.unpatch(BasicModel);
    });

    QUnit.test('a popup window should automatically close after a do_action event', function (assert) {

        // Having clicked on a one2many in a form view and clicked on a many2one
        // field in the resulting popup window that popup window should automatically close.

        assert.expect(2);

        this.data.partner.records[0].product_ids = [37];
        this.data.product.records[0].partner_type_id = 12;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form>' +
                    '<field name="product_ids">' +
                        '<tree><field name="partner_type_id"/></tree>' +
                        '<form><field name="partner_type_id"/></form>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action' && args.model === 'partner_type') {
                    return $.when();
                }
                return this._super(route, args);
            },
            intercepts: {
                do_action: function (event) {
                    event.data.on_success();
                }
            },
        });
        // Open one2many
        form.$('.o_data_row').click();
        assert.strictEqual($('.modal-content').length, 1, "a popup window should have opened");
        // Click on many2one and trigger do_action
        $('.modal-content a[name="partner_type_id"]').click();
        assert.strictEqual($('.modal-content').length, 0, "the popup window should have closed");

        form.destroy();
    });

    QUnit.test('all popup windows should automatically close after a do_action event', function (assert) {

        // Having clicked successively on two different one2many in form views
        // and clicked on a many2one in the last popup window all popup
        // windows should automatically close.

        assert.expect(2);

        this.data.partner.records[0].p = [2];
        this.data.partner.records[1].product_ids = [37];
        this.data.product.records[0].partner_type_id = 12;

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form>' +
                        '<field name="p">' +
                            '<tree><field name="display_name"/></tree>' +
                        '</field>' +
                '</form>',
            archs: {
                'partner,false,form': '<form><field name="product_ids">' +
                                            '<tree><field name="partner_type_id"/></tree>' +
                                            '<form><field name="partner_type_id"/></form>' +
                                        '</field></form>',
            },
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'get_formview_action' && args.model === 'partner_type') {
                    return $.when();
                }
                return this._super(route, args);
            },
            intercepts: {
                do_action: function (event) {
                    event.data.on_success();
                }
            },
        });
        // Open two one2manys
        form.$('.o_data_row').click();
        $('.modal-content .o_data_row').click();
        assert.strictEqual($('.modal-content').length, 2, "Two popup windows should have opened.");
        // Click on many2one and trigger do_action
        $('.modal-content a[name="partner_type_id"]').click();
        assert.strictEqual($('.modal-content').length, 0, "All popup windows should have closed.");

        form.destroy();
    });

    QUnit.test('keep editing after call_button fail', function (assert) {
        assert.expect(4);

        var values;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form>' +
                    '<button name="post" class="p" string="Raise Error" type="object"/>' +
                    '<field name="p">' +
                        '<tree editable="top">' +
                            '<field name="display_name"/>' +
                            '<field name="product_id"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            res_id: 1,
            intercepts: {
                execute_action: function (ev) {
                    assert.ok(true, 'the action is correctly executed');
                    ev.data.on_fail();
                },
            },
            mockRPC: function (route, args) {
                if (args.method === 'write') {
                    assert.deepEqual(args.args[1].p[0][2], values);
                }
                return this._super.apply(this, arguments);
            },
            viewOptions: {
                mode: 'edit',
            },
        });

        // add a row and partially fill it
        form.$('.o_field_x2many_list_row_add a').click();
        form.$('input:nth(0)').val('abc').trigger('input');

        // click button which will trigger_up 'execute_action' (this will save)
        values = {
            display_name: 'abc',
            product_id: false,
        };
        form.$('button.p').click();

        // edit the new row again and set a many2one value
        form.$('.o_form_view .o_field_one2many .o_data_row .o_data_cell').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.find('li:first()').click();

        assert.strictEqual(form.$('.o_field_many2one input').val(), 'xphone',
            "value of the m2o should have been correctly updated");

        values = {
            product_id: 37,
        };
        form.$buttons.find('.o_form_button_save').click();

        form.destroy();
    });

    QUnit.test('asynchronous rendering of a widget tag', function (assert) {
        assert.expect(1);

        var def1 = $.Deferred();

        var MyWidget = Widget.extend({
            willStart: function() {
                return def1;
            },
        });

        widgetRegistry.add('test', MyWidget);

        createAsyncView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                        '<widget name="test"/>' +
                    '</form>',
        }).then(function(form) {
            assert.strictEqual(form.$('div.o_widget').length, 1,
                "there should be a div with widget class");
            form.destroy();
            delete widgetRegistry.map.test;
        });

        def1.resolve();
    });

    QUnit.test('no deadlock when saving with uncommitted changes', function (assert) {
        // Before saving a record, all field widgets are asked to commit their changes (new values
        // that they wouldn't have sent to the model yet). This test is added alongside a bug fix
        // ensuring that we don't end up in a deadlock when a widget actually has some changes to
        // commit at that moment. By chance, this situation isn't reached when the user clicks on
        // 'Save' (which is the natural way to save a record), because by clicking outside the
        // widget, the 'change' event (this is mainly for InputFields) is triggered, and the widget
        // notifies the model of its new value on its own initiative, before being requested to.
        // In this test, we try to reproduce the deadlock situation by forcing the field widget to
        // commit changes before the save. We thus manually call 'saveRecord', instead of clicking
        // on 'Save'.
        assert.expect(6);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="foo"/></form>',
            mockRPC: function (route, args) {
                assert.step(args.method);
                return this._super.apply(this, arguments);
            },
             // we set a fieldDebounce to precisely mock the behavior of the webclient: changes are
             // not sent to the model at keystrokes, but when the input is left
            fieldDebounce: 5000,
        });

        form.$('input').val('some foo value').trigger('input');
        // manually save the record, to prevent the field widget to notify the model of its new
        // value before being requested to
        form.saveRecord();

        assert.strictEqual(form.$('.o_form_readonly').length, 1,
            "form view should be in readonly");
        assert.strictEqual(form.$el.text().trim(), 'some foo value',
            "foo field should have correct value");
        assert.verifySteps(['default_get', 'create', 'read']);

        form.destroy();
    });

    QUnit.test('save record with onchange on one2many with required field', function (assert) {
        // in this test, we have a one2many with a required field, whose value is
        // set by an onchange on another field ; we manually set the value of that
        // first field, and directly click on Save (before the onchange RPC returns
        // and sets the value of the required field)
        assert.expect(6);

        this.data.partner.fields.foo.default = undefined;
        this.data.partner.onchanges = {
            display_name: function (obj) {
                obj.foo = obj.display_name ? 'foo value' : undefined;
            },
        };

        var onchangeDef;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<field name="p">' +
                        '<tree editable="top">' +
                            '<field name="display_name"/>' +
                            '<field name="foo" required="1"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return $.when(onchangeDef).then(_.constant(result));
                }
                if (args.method === 'create') {
                    assert.step('create');
                    assert.strictEqual(args.args[0].p[0][2].foo, 'foo value',
                        "should have wait for the onchange to return before saving");
                }
                return result;
            },
        });

        form.$('.o_field_x2many_list_row_add a').click();

        assert.strictEqual(form.$('.o_field_widget[name=display_name]').val(), '',
            "display_name should be the empty string by default");
        assert.strictEqual(form.$('.o_field_widget[name=foo]').val(), '',
            "foo should be the empty string by default");

        onchangeDef = $.Deferred(); // delay the onchange

        form.$('.o_field_widget[name=display_name]').val('some value').trigger('input');

        form.$buttons.find('.o_form_button_save').click();

        assert.step('resolve');
        onchangeDef.resolve();

        assert.verifySteps(['resolve', 'create']);

        form.destroy();
    });

    QUnit.test('call canBeRemoved while saving', function (assert) {
        assert.expect(10);

        this.data.partner.onchanges = {
            foo: function (obj) {
                obj.display_name = obj.foo === 'trigger onchange' ? 'changed' : 'default';
            },
        };

        var onchangeDef;
        var createDef = $.Deferred();
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="display_name"/><field name="foo"/></form>',
            mockRPC: function (route, args) {
                var result = this._super.apply(this, arguments);
                if (args.method === 'onchange') {
                    return $.when(onchangeDef).then(_.constant(result));
                }
                if (args.method === 'create') {
                    return $.when(createDef).then(_.constant(result));
                }
                return result;
            },
        });

        // edit foo to trigger a delayed onchange
        onchangeDef = $.Deferred();
        testUtils.fields.editInput(form.$('.o_field_widget[name=foo]'), 'trigger onchange');

        assert.strictEqual(form.$('.o_field_widget[name=display_name]').val(), 'default');

        // save (will wait for the onchange to return), and will be delayed as well
        testUtils.dom.click(form.$buttons.find('.o_form_button_save'));

        assert.hasClass(form.$('.o_form_view'), 'o_form_editable');
        assert.strictEqual(form.$('.o_field_widget[name=display_name]').val(), 'default');

        // simulate a click on the breadcrumbs to leave the form view
        form.canBeRemoved();

        assert.hasClass(form.$('.o_form_view'), 'o_form_editable');
        assert.strictEqual(form.$('.o_field_widget[name=display_name]').val(), 'default');

        // unlock the onchange
        onchangeDef.resolve();

        assert.hasClass(form.$('.o_form_view'), 'o_form_editable');
        assert.strictEqual(form.$('.o_field_widget[name=display_name]').val(), 'changed');

        // unlock the create
        createDef.resolve();

        assert.hasClass(form.$('.o_form_view'), 'o_form_readonly');
        assert.strictEqual(form.$('.o_field_widget[name=display_name]').text(), 'changed');
        assert.containsNone(document.body, '.modal',
            "should not display the 'Changes will be discarded' dialog");

        form.destroy();
    });

    QUnit.test('domain returned by onchange is cleared on discard', function (assert) {
        assert.expect(4);

        this.data.partner.onchanges = {
            foo: function () {},
        };

        var domain = ['id', '=', 1];
        var expectedDomain = domain;
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form><field name="foo"/><field name="trululu"/></form>',
            mockRPC: function (route, args) {
                if (args.method === 'onchange' && args.args[0][0] === 1) {
                    // onchange returns a domain only on record 1
                    return $.when({
                        domain: {
                            trululu: domain,
                        },
                    });
                }
                if (args.method === 'name_search') {
                    assert.deepEqual(args.kwargs.args, expectedDomain);
                }
                return this._super.apply(this, arguments);
            },
            res_id: 1,
            viewOptions: {
                ids: [1, 2],
                mode: 'edit',
            },
        });

        assert.strictEqual(form.$('input[name=foo]').val(), 'yop', "should be on record 1");

        // change foo to trigger the onchange
        testUtils.fields.editInput(form.$('input[name=foo]'), 'new value');

        // open many2one dropdown to check if the domain is applied
        testUtils.fields.many2one.clickOpenDropdown('trululu');

        // switch to another record (should ask to discard changes, and reset the domain)
        testUtils.dom.click(form.pager.$('.o_pager_next'));

        // discard changes by clicking on confirm in the dialog
        testUtils.dom.click($('.modal .modal-footer .btn-primary:first'));

        assert.strictEqual(form.$('input[name=foo]').val(), 'blip', "should be on record 2");

        // open many2one dropdown to check if the domain is applied
        expectedDomain = [];
        testUtils.fields.many2one.clickOpenDropdown('trululu');

        form.destroy();
    });

    QUnit.test('discard after a failed save', function (assert) {
        assert.expect(2);

        var actionManager = createActionManager({
            data: this.data,
            archs: {
                'partner,false,form': '<form>' +
                                        '<field name="date" required="true"/>' +
                                        '<field name="foo" required="true"/>' +
                                    '</form>',
                'partner,false,kanban': '<kanban><templates><t t-name="kanban-box">' +
                                        '</t></templates></kanban>',
                'partner,false,search': '<search></search>',
            },
            actions: this.actions,
        });

        actionManager.doAction(1);

        testUtils.dom.click('.o_control_panel .o-kanban-button-new');

        //cannot save because there is a required field
        testUtils.dom.click('.o_control_panel .o_form_button_save');
        testUtils.dom.click('.o_control_panel .o_form_button_cancel');

        assert.containsNone(actionManager, '.o_form_view');
        assert.containsOnce(actionManager, '.o_kanban_view');

        actionManager.destroy();
    });

    QUnit.module('FormViewTABMainButtons');

    QUnit.test('using tab in an empty required string field should not move to the next field',function(assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name" required="1" />' +
                            '<field name="foo" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        form.$('input[name=display_name]').click();
        assert.strictEqual(form.$('input[name="display_name"]')[0], document.activeElement,
            "display_name should be focused");
        form.$('input[name="display_name"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('input[name="display_name"]')[0], document.activeElement,
            "display_name should still be focused because it is empty and required");
        assert.strictEqual(form.$('input[name="display_name"]').hasClass("o_field_invalid"), true,
            "display_name should have the o_field_invalid class");
        form.destroy();
    });

    QUnit.test('using tab in an empty required date field should not move to the next field',function(assert) {
        assert.expect(2);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch:'<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="date" required="1" />' +
                            '<field name="foo" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        form.$('input[name=date]').click();
        assert.strictEqual(form.$('input[name="date"]')[0], document.activeElement,
            "display_name should be focused");
        form.$('input[name="date"]').trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$('input[name="date"]')[0], document.activeElement,
            "date should still be focused because it is empty and required");

        form.destroy();
    });

    QUnit.test('Edit button get the focus when pressing TAB from form', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form>' +
                    '<div class="oe_title">' +
                        '<field name="display_name"/>' +
                    '</div>' +
                '</form>',
            res_id: 1,
        });

        // in edit
        form.$buttons.find('.o_form_button_edit').click();
        form.$('input[name="display_name"]').focus().trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$buttons.find('.btn-primary:visible')[0], document.activeElement,
            "the first primary button (save) should be focused");
        form.destroy();
    });

    QUnit.module('FormViewTABFormButtons');

    QUnit.test('In Edition mode, after navigating to the last field, the default button when pressing TAB is SAVE', function (assert) {
        assert.expect(1);
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="post" class="btn-primary firstButton" string="Confirm" type="object"/>' +
                        '<button name="post" class="btn-primary secondButton" string="Confirm2" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<div class="oe_title">' +
                                '<field name="display_name"/>' +
                            '</div>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('input[name="display_name"]').focus().trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));
        assert.strictEqual(form.$buttons.find('.o_form_button_save:visible')[0], document.activeElement,
            "the save should be focused");
        form.destroy();
    });

    QUnit.test('In READ mode, the default button with focus is the first primary button of the form', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="post" class="btn-primary firstButton" string="Confirm" type="object"/>' +
                        '<button name="post" class="btn-primary secondButton" string="Confirm2" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<div class="oe_title">' +
                                '<field name="display_name"/>' +
                            '</div>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });
        assert.strictEqual(form.$('button.firstButton')[0], document.activeElement,
                        "by default the focus in edit mode should go to the first primary button of the form (not edit)");
        form.destroy();
    });

    QUnit.test('In READ mode, the default button when pressing TAB is EDIT when there is no primary button on the form', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="post" class="not-primary" string="Confirm" type="object"/>' +
                        '<button name="post" class="not-primary" string="Confirm2" type="object"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<div class="oe_title">' +
                                '<field name="display_name"/>' +
                            '</div>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 2,
        });
        assert.strictEqual(form.$buttons.find('.o_form_button_edit')[0],document.activeElement,
                        "in read mode, when there are no primary buttons on the form, the default button with the focus should be edit");
        form.destroy();
    });

    QUnit.test('In Edition mode, when an attribute is dynamically required (and not required), TAB should navigate to the next field', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('input[name="foo"]').focus();
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));

        assert.strictEqual(form.$('div[name="bar"]>input')[0], document.activeElement, "foo is not required, so hitting TAB on foo should have moved the focus to BAR");
        form.destroy();
    });

    QUnit.test('In Edition mode, when an attribute is dynamically required, TAB should stop on the field if it is required', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" attrs="{\'required\': [[\'bar\', \'=\', True]]}"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 5,
            viewOptions: {
                mode: 'edit',
            },
        });

        form.$('div[name="bar"]>input').click();
        form.$('input[name="foo"]').focus();
        $(document.activeElement).trigger($.Event('keydown', {which: $.ui.keyCode.TAB}));

        assert.strictEqual(form.$('input[name="foo"]')[0], document.activeElement, "foo is required, so hitting TAB on foo should keep the focus on foo");
        form.destroy();
    });

    QUnit.test('display tooltips for save and discard buttons', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />'+
                '</form>',
        });

        form.$buttons.find('.o_form_buttons_edit').tooltip('show',false);
        assert.strictEqual($('.tooltip .oe_tooltip_string').length, 1,
            "should have rendered a tooltip");
        form.destroy();
    });
    QUnit.test('if the focus is on the save button, hitting ENTER should save', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />'+
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.ok(true, "should call the /create route");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_save')
                     .focus()
                     .trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
        form.destroy();
    });
    QUnit.test('if the focus is on the discard button, hitting ENTER should save', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />'+
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'create') {
                    assert.ok(true, "should call the /create route");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_cancel')
                     .focus()
                     .trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
        form.destroy();
    });
    QUnit.test('if the focus is on the save button, hitting ESCAPE should discard', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />'+
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    assert.ok(true, "should call the /create route");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_save')
                     .focus()
                     .trigger($.Event('keydown', {which: $.ui.keyCode.ESCAPE}));
        form.destroy();
    });
    QUnit.test('if the focus is on the discard button, hitting ESCAPE should discard', function (assert) {
        assert.expect(1);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />'+
                '</form>',
            viewOptions: {
                mode: 'edit',
            },
            mockRPC: function (route, args) {
                if (args.method === 'default_get') {
                    assert.ok(true, "should call the /create route");
                }
                return this._super(route, args);
            },
        });

        form.$buttons.find('.o_form_button_cancel')
                     .focus()
                     .trigger($.Event('keydown', {which: $.ui.keyCode.ESCAPE}));
        form.destroy();
    });

    QUnit.test('if the focus is on the save button, hitting TAB should not move to the next button', function (assert) {
        assert.expect(1);
        /*
        this test has only one purpose: to say that it is normal that the focus stays within a button primary even after the TAB key has been pressed.
        It is not possible here to execute the default action of the TAB on a button : https://stackoverflow.com/questions/32428993/why-doesnt-simulating-a-tab-keypress-move-focus-to-the-next-input-field
        so writing a test that will always succeed is not useful.
         */
        assert.ok("Behavior can't be tested");
    });
});

});
