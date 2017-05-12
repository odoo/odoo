odoo.define('web.form_keyboard_tests', function (require) {
"use strict";

var concurrency = require('web.concurrency');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

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
                    htmldata : {string: "HTML Field" , type: "html"},
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
                    id: 3,
                    display_name: "Third record",
                    foo: "",
                    bar: true,
                    trululu: 2,

                }, {
                    id: 4,
                    display_name: "aaa",
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
                }, {
                    id: 42,
                    display_name: "xtab",
                },{
                    id: 43,
                    display_name: "xelec",
                },{
                    id: 44,
                    display_name: "xtrimemer",
                },{
                    id: 45,
                    display_name: "xipad",
                },{
                    id: 46,
                    display_name: "xphone1",
                },{
                    id: 47,
                    display_name: "xphone2",
                },{
                    id: 48,
                    display_name: "xphone3",
                },{
                    id: 59,
                    display_name: "xphone4",
                },{
                    id: 62,
                    display_name: "xphone5",
                },{
                    id: 69,
                    display_name: "xphone6",
                }]
            },
            partner_type: {
                fields: {
                    name: {string: "Partner Type", type: "char"},
                    color: {string: "Color index", type: "integer"},
                },
                records: [
                    {id: 12, display_name: "iron", color: 2},
                    {id: 14, display_name: "silver", color: 5},
                    {id: 16, display_name: "gold", color: 6},
                    {id: 18, display_name: "platinum", color: 7}
                ]
            },
        };
    }
}, function () {

    QUnit.module('FormView Keyboard');

    QUnit.test('keyboard navigation on form view', function(assert) {
        assert.expect(12);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo" required="1"/>' +
                            '<field name="qux"/>' +
                            '<field name="bar" />' +
                            '<field name="trululu" />' +
                            '<field name="int_field" />' +
                            '<field name="priority" />' +
                            '<field name="date" />' +
                            '<field name="datetime" />' +
                            '<field name="state" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 3,
        });

        // edit record and navigate using TAB key
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual($(document.activeElement).attr('name'), 'foo', "foo field should be focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        // test required field, qux is required and we try to press TAB, it should not move user to next widget
        assert.strictEqual(document.activeElement, form.$('input[name="foo"]')[0], "required field is empty and after pressing the TAB it should't leave the focus from current field");
        $(document.activeElement).val("qux");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'qux', "qux field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('type'), 'checkbox', "bar field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).closest('.o_field_widget').attr('name'), 'trululu', "trululu field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'int_field', "int field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'priority', "selection field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'date', "date field should be focused");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'datetime', "datetime field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement).attr('name'), 'state', "selection field should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.ok($(document.activeElement).hasClass('o_form_button_save'), "Save button should have focus");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey: true}));
        assert.strictEqual($(document.activeElement).attr('name'), 'state', "Last field widget should have focus");
        form.destroy();
    });

    QUnit.test('ESCAPE key on all widget should show discard warning or call history_back', function(assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                            '<field name="foo"/>' +
                            '<field name="trululu"/>' +
                            '<field name="timmy" widget="many2many_tags"/>' +
                            '<field name="state"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // edit record and without modifying press Escape, it should set record again in readonly mode
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($(document.activeElement).hasClass('o_form_button_edit'), "Record should be discarded on escape key");

        // edit record again and press escape after making form dirty, it should display discard warning
        $(document.activeElement).trigger('click');
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).val("Hello").trigger('input');
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($('.modal').length, 'discard warning given on escape key');
        $('.modal .modal-footer .btn-primary').click();

        // edit record again and set focus on state selection field and press escape
        $(document.activeElement).trigger('click');
        form.$('[name="state"]').focus();
        form.$('[name="state"] option:eq(2)').prop('selected', true).trigger('change');
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($('.modal').length, 'discard message show in selection field');
        $('.modal .modal-footer .btn-primary').click();
        assert.ok($(document.activeElement).hasClass('o_form_button_edit'), "Record changes should be discarded when escape key pressed on selection field");

        // edit record again and set focus on many2many field and press escape key
        $(document.activeElement).trigger('click');
        form.$('[name="timmy"]').focus();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE }));
        assert.ok($(document.activeElement).hasClass('o_form_button_edit'), "Record changes should be discarded when escape key pressed on many2many field");

        form.destroy();
    });

    QUnit.test('save form view using shift enter', function(assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="qux"/>' +
                            '<field name="foo"/>' +
                            '<field name="state"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // edit record and test SHIFT + ENTER on different widgets
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual(form.mode, 'readonly', "SHIFT + ENTER should save the record on Float field");

        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual(form.mode, 'readonly',"SHIFT + ENTER should save the record on Char field");

        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ENTER , shiftKey : true}));
        assert.strictEqual(form.mode, 'readonly', "SHIFT + ENTER should save the record on Selection field");

        form.destroy();
    });

    QUnit.test('M2O autocomplete open and press escape should not discard record', function (assert) {
        assert.expect(3);

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
            res_id: 1,
        });

        // go to edit mode and test SHIFT + ENTER
        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        assert.ok($dropdown.find('li').length, 'the click on m2o widget should open a dropdown');
        form.$('.o_field_many2one input').trigger($.Event('keydown', { which: $.ui.keyCode.ESCAPE}));
        assert.strictEqual(form.mode, 'edit', 'm2o autocomplete when open and press escape it should not discard form changes');
        assert.strictEqual($(document.activeElement).closest('.o_field_widget').attr('name'), 'product_id',
            "Focus should be set on input field");
        form.destroy();
    });

    QUnit.test('Test m2o selectCreatePopup and select record', function (assert) {
        assert.expect(4);

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
                'product,false,search':
                    '<search string="Products">' +
                        '<field name="name"/>' +
                    '</search>',
                'product,false,list': '<tree><field name="display_name"/></tree>'
            },
        });

        // go to edit mode and open selectCreatePopup, test first focus on search input
        form.$buttons.find('.o_form_button_edit').click();
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        form.$('.o_field_many2one input').click();
        $dropdown.trigger($.Event("keydown", { keyCode: $.ui.keyCode.UP }));
        $dropdown.trigger($.Event("keydown", { keyCode: $.ui.keyCode.UP }));
        $dropdown.trigger($.Event("keydown", { keyCode: $.ui.keyCode.ENTER }));
        var selectCreatePopup = $('.modal');
        assert.strictEqual(selectCreatePopup.find(".o_list_view").length, 1,
            "Should open listview");
        assert.ok($(document.activeElement).hasClass('o_searchview_input'),
            "Focus should be set on search view");

        // Press down key and and select first record
        $(selectCreatePopup).find('input[class="o_searchview_input"]').trigger($.Event("keydown", { which: $.ui.keyCode.DOWN }));
        assert.strictEqual($(document.activeElement).find('.o_row_selected')[0], selectCreatePopup.find(".o_list_view tr.o_data_row:first")[0], 'First row should be selected');
        var value = $(document.activeElement).find('.o_row_selected').text();
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.ENTER })));
        assert.strictEqual(form.$('.o_field_many2one input').val(), value, "the value should equal to the value that is selected from dialog");
        form.destroy();
    });

    QUnit.test('when press enter on Create and Edit in m2o, it should open FormViewDialog', function (assert) {
        var done = assert.async();
        assert.expect(4);
        this.data.product.fields.product_ids = {
            string: "one2many product", type: "one2many", relation: "product",
        };

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
                                '<field name="name"/>' +
                            '</group>' +
                        '</sheet>' +
                    '</form>'
            }
        });
        // go to edit mode, open m2o and press Create and Edit option and test FormViewDialog
        form.$buttons.find('.o_form_button_edit').click();
        var upKey = $.Event("keydown", { keyCode: $.ui.keyCode.UP });
        form.$el.find('.o_input_dropdown input').trigger(upKey);
        var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
        $dropdown.trigger(upKey);
        $dropdown.trigger($.Event("keydown", { keyCode: $.ui.keyCode.ENTER }));
        var $firstModel = $('.modal-dialog');
        assert.strictEqual($(document.activeElement)[0], $firstModel.find('input[name="name"]')[0],
        "focus should be on first input field in FormViewDialog");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.ok($(document.activeElement).hasClass("o_form_button_save"), "Focus should be on Save button of FormViewDialog");
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual($(document.activeElement)[0], $firstModel.find('input[name="name"]')[0],
        "again focus should be on first input field");
        $firstModel.trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
        concurrency.delay(200).then(function() {
            assert.ok($(document.activeElement).hasClass('o_input'), "Focus should be on Product field after pressing the ESCAPE on FormViewDialog");
            form.destroy();
            done();
        });
    });

    QUnit.test('keyboard navigation on html field', function(assert) {
        assert.expect(4);

        var done = assert.async();

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="htmldata"/>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // edit record and test focus on html field by using TAB and SHIFT+TAB
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual($(document.activeElement).attr('name'), "display_name", "Focus should be on Displayed name field");
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        concurrency.delay(0).then(function() { // content area of html field having timeout in summernote itself
            assert.ok($(document.activeElement).hasClass('note-editable'), "Active element should be html field");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.strictEqual($(document.activeElement).attr('name'), "foo", "Focus should be on Foo field");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey : true }));
            return concurrency.delay(0);
        }).then(function() {
            assert.ok($(document.activeElement).hasClass('note-editable'), "Active element should be html field again on SHIFT+TAB");
            form.destroy();
            done();
        });
    });

    QUnit.test('navigation on header buttons in edit mode and readonly mode', function(assert) {
        assert.expect(15);

        this.data.partner.records[0].product_id = 37;

        var done = assert.async();
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<field name="state" invisible="1"/>' +
                    '<header>' +
                        '<button name="confirm" states="ab" type="object" class="btn-primary confirm" string="Confirm"/>' +
                        '<button name="doit" states="cd,ef" type="object" class="btn-primary doit" string="Do it"/>' +
                        '<button name="done" states="cd,ef" type="object" class="btn-primary done" string="Done"/>' +
                    '</header>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name"/>' +
                            '<field name="foo"/>' +
                            '<field name="product_id"/>' +
                            '<field name="state" invisible="1"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // edit record and test focus on html field and test navigation on header buttons
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual(form.$('.o_form_statusbar button').length, 3,
            "should have 3 buttons in the statusbar");
        assert.strictEqual(form.$('.o_form_statusbar button:visible').length, 1,
            "should have only 1 visible button in the statusbar");

        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));

        // Focus should come to save button when TAB pressed from last field widget
        assert.ok($(document.activeElement).hasClass('o_form_button_save'), "Focus must be on Save button");
        // When TAB pressed from Save button focus should go to first statubar button
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
        assert.ok($(document.activeElement).hasClass('confirm'), "Confirm button must have focus");

        // Intercept execute_action i.e. when button is clicked we will check whether confirm button is clicked?
        testUtils.intercept(form, 'execute_action', _.bind(function (event) {
            assert.strictEqual(event.data.action_data.name, "confirm",
                "should trigger execute_action with correct method name");
            assert.deepEqual(event.data.env.resIDs, [1], "should have correct id in event data");
            this.data.partner.records[0].state = "cd"; // Change state value to show next states based buttons
            event.data.on_success();
            event.data.on_closed();
        }, this));

        // Need to trigger ENTER as well as click forcefully(enter doesn't call execute_action I don't know why)
        // Also ENTER in our case preserve last tabindex widget index so that when record reloaded right next widget get focus
        $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ENTER }));
        $(document.activeElement).click();

        concurrency.delay(100).then(function() {
            assert.strictEqual(form.$('.o_form_statusbar button:visible').length, 2,
            "should have 2 visible button in the statusbar");

            assert.ok($(document.activeElement).hasClass('doit'), "Do It button must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.ok($(document.activeElement).hasClass('done'), "Done button must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey: true }));
            assert.ok($(document.activeElement).hasClass('doit'), "Do It button must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.strictEqual($(document.activeElement).attr('name'),'display_name',"Display name field must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.ENTER ,shiftKey: true}));
            return concurrency.delay(100);
        }).then(function() {
            assert.ok($(document.activeElement).hasClass('doit'), "Do it button must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.ok($(document.activeElement).hasClass('done'), "Done button must have focus");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.strictEqual($(document.activeElement).closest(".o_field_widget").attr('name'), 'product_id', "Product field must have focus in readonly mode");
            $(document.activeElement).trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.ok($(document.activeElement).hasClass('o_form_button_edit'), "Edit button must have focus");
            form.destroy();
            done();
        });
    });

    QUnit.test('ESCAPE key with editable listview: it should discard editable listview record only', function (assert) {
        assert.expect(3);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id"/>' +
                        '</group>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc" editable="bottom" >' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                        '</field>' +
                        '<group>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });
        // go to edit mode and create editable row in o2m and test ESCAPE key, Escape key should discard o2m editable record
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.strictEqual($(document.activeElement).attr('name'), 'display_name', "Focus should be on Display name field of o2m");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE })));
        assert.strictEqual($(document.activeElement).attr('name'), "p", "Focus must be on o2m element when editable o2m record is cancelled");
        assert.strictEqual(form.mode, 'edit', 'When escape pressed on o2m it should discard editable record only');
        form.destroy();
    });

    QUnit.test('Test key up event on m2o when autocomplete is open inside editable list', function(assert) {
        assert.expect(2);

        var done = assert.async();
        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="bar" />' +
                            '<field name="p">' +
                                '<tree default_order="foo" editable="bottom" >' +
                                    '<field name="product_id"/>' +
                                    '<field name="foo"/>' +
                                '</tree>' +
                            '</field>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            res_id: 1,
        });

        // go to edit mode and create editable record and open m2o autocomplete dropdown and test UP/DOWN keys,
        // it should not go to next/previous record instead it should select next previous m2o dropdown option
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.DOWN }));

        concurrency.delay(500).then(function() {
            var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
            assert.strictEqual($dropdown.find('.ui-state-focus a').html(), "xphone", "First element focused in autocomplete");
            $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.UP }));
            assert.ok($(document.activeElement).hasClass('ui-autocomplete-input'),"focus is in many2one field on key up pressed");
            form.destroy();
            done();
        });
    });

    QUnit.test('Test o2m widget with form popup and escape key', function (assert) {
        var done = assert.async();
        assert.expect(7);

        var form = createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<field name="product_id"/>' +
                        '<field name="p">' +
                            '<tree default_order="foo desc">' +
                                '<field name="display_name"/>' +
                                '<field name="foo"/>' +
                            '</tree>' +
                            '<form>' +
                                '<field name="foo"/>' +
                            '</form>' +
                        '</field>' +
                        '<group>' +
                        '</group>' +
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
        // go to edit mode and open o2m form popup and test Escape key, Escape key should discard o2m record,
        // close form popup and set focus on o2m element
        form.$buttons.find('.o_form_button_edit').click();
        assert.strictEqual($(document.activeElement).closest('.o_field_widget').attr('name'), 'product_id', "Focus should be on Product field");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.strictEqual(document.activeElement, $("div[name='p'] .o_field_x2many_list_row_add a")[0],
            "Focus should be on Add an Item link of one2many field");
        $(document.activeElement).click();
        assert.strictEqual($('.modal').length, 1,
            "O2M FormViewDialog should be opened");
        assert.strictEqual($(document.activeElement).attr("name"), 'foo',
            "Focus should be on Foo field of FormViewDialog");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        assert.ok($(document.activeElement).hasClass('o_form_button_save'),
            "Focus should be on save button of FormViewDialog");
        $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.TAB })));
        $('.modal').trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE})));
        concurrency.delay(100).then(function() {
            assert.ok($(document.activeElement).hasClass('o_field_one2many'), "focus should be on o2m widget after pressing the ESCAPE on o2m form popup");
            $(document.activeElement).trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE })));
            assert.strictEqual(form.mode, 'readonly', 'o2m when focus and press escape it should discard form changes');
            form.destroy();
            done();
        });
    });

    QUnit.test('move to previous view after pressing ESCAPE in create record', function (assert) {
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
            intercepts: {
                switch_to_previous_view: function (event) {
                    assert.ok(true, "should have sent correct event");
                },
            }
        });

        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
        form.destroy();
    });

    QUnit.test('move to previous view after pressing ESCAPE on edit', function (assert) {
        assert.expect(2);
        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            intercepts: {
                history_back: function (event) {
                    assert.ok(true, "should have sent correct event");
                },
            }
        });

        form.$buttons.find('.o_form_button_edit').focus();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));

        form.$buttons.find('.o_form_button_create').focus();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
        form.destroy();
    });

    QUnit.test('When form is dirty and press escape should show warning dialog and set focus back to form', function (assert) {
        assert.expect(2);
        var done = assert.async();

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="product_id" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
        });

        // go to edit mode and select m2o value and test escape, pressing escape should show discard warning
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.DOWN }));

        concurrency.delay(500).then(function() {
            var $dropdown = form.$('.o_field_many2one input').autocomplete('widget');
            $dropdown.trigger($.Event("keydown", { keyCode: $.ui.keyCode.ENTER }));
            $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
            return concurrency.delay(100);
        }).then(function() {
            assert.strictEqual(document.activeElement, $('.modal-footer .btn-primary')[0], 'Focus should be on OK button of discard warning');
            $('.modal-footer').trigger($.Event("keydown", { which: $.ui.keyCode.ESCAPE }));
            return concurrency.delay(100);
        }).then(function() {
            assert.strictEqual($(document.activeElement).closest('.o_field_widget').attr('name'), "product_id", "focus should be on form or form's field")
            form.destroy();
            done();
        });
    });

    QUnit.test('Test many2many field and many2many SelectCreatePopup with TAB navigation and ESCAPE key', function (assert) {
        assert.expect(12);
        var done = assert.async();

        var form = createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form string="Partners">' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="display_name" />' +
                            '<field name="timmy" />' +
                        '</group>' +
                    '</sheet>' +
                '</form>',
            archs: {
                'partner_type,false,search': '<search><field name="name"/></search>',
                'partner_type,false,list': '<tree><field name="display_name"/><field name="name"/></tree>'
            },
        });

        // go to edit mode and open many2many SelectCreatePopup and test TAB and ESCAPE key
        form.$buttons.find('.o_form_button_edit').click();
        $(document.activeElement).trigger($.Event("keydown", { which: $.ui.keyCode.TAB }));
        assert.strictEqual(document.activeElement, $("div[name='timmy'] .o_field_x2many_list_row_add a")[0],
            "Focus should be on Add an Item link of one2many field");
        $(document.activeElement).click();

        var selectCreatePopup = $('.modal');
        var $listview = selectCreatePopup.find(".o_list_view");
        assert.ok(selectCreatePopup.length, 'Many2Many SelectCreatePopup should open');
        assert.strictEqual(selectCreatePopup.find(".o_list_view").length, 1,
            "Should open listview");
        assert.ok($(document.activeElement).hasClass('o_searchview_input'),
            "Focus should be set on search view input by default");

        // Press down key and and select first record and then DOWN key should select second record
        selectCreatePopup.find('input[class="o_searchview_input"]').trigger($.Event("keydown", { which: $.ui.keyCode.DOWN }));

        assert.strictEqual($listview.find('.o_row_selected')[0], $listview.find("tr.o_data_row:first")[0], 'First row should be selected');
        $listview.trigger($.Event('keydown', { which: $.ui.keyCode.DOWN }));
        assert.strictEqual($listview.find('.o_row_selected')[0], $listview.find("tr.o_data_row:eq(1)")[0], 'Second row should be selected');
        // Test navigation on row with shift key
        $listview.trigger($.Event("keydown", { which: 40, shiftKey: true }));
        assert.ok($listview.find("tr.o_data_row:eq(1)").hasClass('o_row_selected') && $listview.find("tr.o_data_row:eq(2)").hasClass('o_row_selected'), "Second and Third row should be selected");
        // Test navigation on row with control key
        $listview.trigger($.Event("keydown", { which: 40, ctrlKey: true }));
        assert.ok($listview.find("tr.o_data_row:eq(3)").hasClass('o_row_focused'), "Fourth row should have focus");

        // Press TAB and press ENTER key to select selected records
        selectCreatePopup.find('.o_select_button').focus();
        assert.ok($(document.activeElement).hasClass("o_select_button"), "Select button of Many2Many field should have focus");
        $(document.activeElement).click();
        concurrency.delay(200).then(function() {
            assert.ok($(document.activeElement).hasClass('o_field_many2many'), "focus should be on m2m widget after selecting records from SelectCreatePopup");
            // Again go to previous widget and press TAB again so that m2m SelectCreatePopup is opened again
            $listview.trigger($.Event('keydown', { which: $.ui.keyCode.TAB, shiftKey: true }));
            $listview.trigger($.Event('keydown', { which: $.ui.keyCode.TAB }));
            assert.ok(selectCreatePopup.length, 'Many2Many SelectCreatePopup should open');
            // Press escape without selecting records, it should set focus on m2m widget
            $('.modal').trigger(($.Event("keydown", { which: $.ui.keyCode.ESCAPE})));
            return concurrency.delay(100);
        }).then(function() {
            assert.ok($(document.activeElement).hasClass('o_field_many2many'), "focus should be on m2m widget after selecting records from SelectCreatePopup");
            form.destroy();
            done();
        });
    });

});

});
