odoo.define('barcodes.tests', function (require) {
"use strict";

var barcodeEvents = require('barcodes.BarcodeEvents');

var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
var triggerKeypressEvent = testUtils.triggerKeypressEvent;

QUnit.module('Barcodes', {
    beforeEach: function () {
        this.data = {
            order: {
                fields: {
                    _barcode_scanned: {string: 'Barcode scanned', type: 'char'},
                    line_ids: {string: 'Order lines', type: 'one2many', relation: 'order_line'},
                },
                records: [
                    {id: 1, line_ids: [1, 2]},
                ],
            },
            order_line: {
                fields: {
                    product_id: {string: 'Product', type: 'many2one', relation: 'product'},
                    product_barcode: {string: 'Product Barcode', type: 'char'},
                    quantity: {string: 'Quantity', type: 'integer'},
                },
                records: [
                    {id: 1, product_id: 1, quantity: 0, product_barcode: '1234567890'},
                    {id: 2, product_id: 2, quantity: 0, product_barcode: '0987654321'},
                ],
            },
            product: {
                fields: {
                    name: {string : "Product name", type: "char"},
                    int_field: {string : "Integer", type: "integer"},
                    barcode: {string: "Barcode", type: "char"},
                },
                records: [
                    {id: 1, name: "iPad Mini", barcode: '1234567890'},
                    {id: 2, name: "Mouse, Optical", barcode: '0987654321'},
                ],
            },
        };
    }
});

QUnit.test('Button with barcode_trigger', function (assert) {
    assert.expect(2);

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                '<header>' +
                    '<button name="do_something" string="Validate" type="object" barcode_trigger="doit"/>' +
                    '<button name="do_something_else" string="Validate" type="object" invisible="1" barcode_trigger="dothat"/>' +
                '</header>' +
            '</form>',
        res_id: 2,
        intercepts: {
            execute_action: function (event) {
                assert.strictEqual(event.data.action_data.name, 'do_something',
                    "do_something method call verified");
            },
            warning: function () {
                assert.step('warn');
            },
        },
    });

    // O-BTN.doit
    _.each(['O','-','B','T','N','.','d','o','i','t','Enter'], triggerKeypressEvent);
    // O-BTN.dothat (should not call execute_action as the button isn't visible)
    _.each(['O','-','B','T','N','.','d','o','t','h','a','t','Enter'], triggerKeypressEvent);

    assert.verifySteps([], "no warning should be displayed");

    form.destroy();
});

QUnit.test('edit, save and cancel buttons', function (assert) {
    assert.expect(6);

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form><field name="display_name"/></form>',
        mockRPC: function (route, args) {
            if (args.method === 'write') {
                assert.step('save');
            }
            return this._super.apply(this, arguments);
        },
        res_id: 1,
    });

    // O-CMD.EDIT
    _.each(["O","-","C","M","D",".","E","D","I","T","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$(".o_form_editable").length, 1,
        "should have switched to 'edit' mode");
    // dummy change to check that it actually saves
    form.$('.o_field_widget').val('test').trigger('input');
    // O-CMD.SAVE
    _.each(["O","-","C","M","D",".","S","A","V","E","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$(".o_form_readonly").length, 1,
        "should have switched to 'readonly' mode");
    assert.verifySteps(['save'], 'should have saved');

    // O-CMD.EDIT
    _.each(["O","-","C","M","D",".","E","D","I","T","Enter"], triggerKeypressEvent);
    // dummy change to check that it correctly discards
    form.$('.o_field_widget').val('test').trigger('input');
    // O-CMD.CANCEL
    _.each(["O","-","C","M","D",".","D","I","S","C","A","R","D","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$(".o_form_readonly").length, 1,
        "should have switched to 'readonly' mode");
    assert.verifySteps(['save'], 'should not have saved');

    form.destroy();
});

QUnit.test('pager buttons', function (assert) {
    assert.expect(5);

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form><field name="display_name"/></form>',
        res_id: 1,
        viewOptions: {
            ids: [1, 2],
            index: 0,
        },
    });

    assert.strictEqual(form.$('.o_field_widget').text(), 'iPad Mini');
    // O-CMD.PAGER-NEXT
    _.each(["O","-","C","M","D",".","N","E","X","T","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'Mouse, Optical');
    // O-CMD.PAGER-PREV
    _.each(["O","-","C","M","D",".","P","R","E","V","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'iPad Mini');
    // O-CMD.PAGER-LAST
    _.each(["O","-","C","M","D",".","P","A","G","E","R","-","L","A","S","T","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'Mouse, Optical');
    // O-CMD.PAGER-FIRST
    _.each(["O","-","C","M","D",".","P","A","G","E","R","-","F","I","R","S","T","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'iPad Mini');

    form.destroy();
});

QUnit.test('do no update form twice after a command barcode scanned', function (assert) {
    assert.expect(7);

    var delay = barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms;
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = 0;
    testUtils.patch(FormController, {
        update: function () {
            assert.step('update');
            return this._super.apply(this, arguments);
        },
    });

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="int_field" widget="field_float_scannable"/>' +
                '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'read') {
                assert.step('read');
            }
            return this._super.apply(this, arguments);
        },
        res_id: 1,
        viewOptions: {
            ids: [1, 2],
            index: 0,
        },
    });

    assert.verifySteps(['read'], "update should not have been called yet");

    // switch to next record
    _.each(["O","-","C","M","D",".","N","E","X","T","Enter"], triggerKeypressEvent);
    // a first update is done to reload the data (thus followed by a read), but
    // update shouldn't be called afterwards
    assert.verifySteps(['read', 'update', 'read']);

    _.each(['5','4','3','9','8','2','6','7','1','2','5','2','Enter'], triggerKeypressEvent);
    // a real barcode has been scanned -> an update should be requested (with
    // option reload='false', so it isn't followed by a read)
    assert.verifySteps(['read', 'update', 'read', 'update']);

    form.destroy();
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = delay;
    testUtils.unpatch(FormController);
});

QUnit.test('widget field_float_scannable', function (assert) {
    var done = assert.async();
    assert.expect(11);

    var delay = barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms;
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = 0;

    this.data.product.records[0].int_field = 4;
    this.data.product.onchanges = {
        int_field: function () {},
    };

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="int_field" widget="field_float_scannable"/>' +
                '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'onchange') {
                assert.step('onchange');
                assert.strictEqual(args.args[1].int_field, 426,
                    "should send correct value for int_field");
            }
            return this._super.apply(this, arguments);
        },
        fieldDebounce: 1000,
        res_id: 1,
    });

    assert.strictEqual(form.$('.o_field_widget[name=int_field]').text(), '4',
        "should display the correct value in readonly");

    form.$buttons.find('.o_form_button_edit').click();

    assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '4',
        "should display the correct value in edit");

    // simulates keypress events in the input to replace 0.00 by 26 (should not trigger onchanges)
    form.$('.o_field_widget[name=int_field]').focus();
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').get(0), document.activeElement,
        "int field should be focused");
    form.$('.o_field_widget[name=int_field]').trigger({type: 'keypress', which: 50, keyCode: 50}); // 2
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').get(0), document.activeElement,
        "int field should still be focused");
    form.$('.o_field_widget[name=int_field]').trigger({type: 'keypress', which: 54, keyCode: 54}); // 6
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').get(0), document.activeElement,
        "int field should still be focused");

    setTimeout(function () {
        assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '426',
            "should display the correct value in edit");
        assert.strictEqual(form.$('.o_field_widget[name=int_field]').get(0), document.activeElement,
        "int field should still be focused");

        assert.verifySteps([], 'should not have done any onchange RPC');

        form.$('.o_field_widget[name=int_field]').trigger('change'); // should trigger the onchange

        assert.verifySteps(['onchange'], 'should have done the onchange RPC');

        form.destroy();
        barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = delay;
        done();
    });
});

QUnit.test('widget barcode_handler', function (assert) {
    assert.expect(4);

    var delay = barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms;
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = 0;

    this.data.product.fields.barcode_scanned = {string : "Scanned barcode", type: "char"};
    this.data.product.onchanges = {
        barcode_scanned: function (obj) {
            // simulate an onchange that increment the int_field value
            // at each barcode scanned
            obj.int_field = obj.int_field + 1;
        },
    };

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="int_field"/>' +
                    '<field name="barcode_scanned" widget="barcode_handler" invisible="1"/>' +
                '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'onchange') {
                assert.step('onchange');
            }
            return this._super.apply(this, arguments);
        },
        res_id: 1,
        viewOptions: {
            mode: 'edit',
        },
    });

    assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '0',
        "initial value should be correct");

    _.each(['5','4','3','9','8','2','6','7','1','2','5','2','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '1',
        "value should have been incremented");

    assert.verifySteps(['onchange'], "an onchange should have been done");

    form.destroy();
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = delay;
});

QUnit.test('specification of widget barcode_handler', function (assert) {
    assert.expect(5);

    var delay = barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms;
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = 0;

    // Define a specific barcode_handler widget for this test case
    var TestBarcodeHandler = AbstractField.extend({
        init: function () {
            this._super.apply(this, arguments);

            this.trigger_up('activeBarcode', {
                name: 'test',
                fieldName: 'line_ids',
                quantity: 'quantity',
                commands: {
                    barcode: '_barcodeAddX2MQuantity',
                }
            });
        },
    });
    fieldRegistry.add('test_barcode_handler', TestBarcodeHandler);

    var form = createView({
        View: FormView,
        model: 'order',
        data: this.data,
        arch: '<form>' +
                    '<field name="_barcode_scanned" widget="test_barcode_handler"/>' +
                    '<field name="line_ids">' +
                        '<tree>' +
                            '<field name="product_id"/>' +
                            '<field name="product_barcode" invisible="1"/>' +
                            '<field name="quantity"/>' +
                        '</tree>' +
                    '</field>' +
                '</form>',
        mockRPC: function (route, args) {
            if (args.method === 'onchange') {
                assert.notOK(true, "should not do any onchange RPC");
            }
            if (args.method === 'write') {
                assert.deepEqual(args.args[1].line_ids, [
                    [1, 1, {quantity: 2}], [1, 2, {quantity: 1}],
                ], "should have generated the correct commands");
            }
            return this._super.apply(this, arguments);
        },
        res_id: 1,
        viewOptions: {
            mode: 'edit',
        },
    });

    assert.strictEqual(form.$('.o_data_row').length, 2,
        "one2many should contain 2 rows");

    // scan twice product 1
    _.each(['1','2','3','4','5','6','7','8','9','0','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_data_row:first .o_data_cell:nth(1)').text(), '1',
        "quantity of line one should have been incremented");
    _.each(['1','2','3','4','5','6','7','8','9','0','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_data_row:first .o_data_cell:nth(1)').text(), '2',
        "quantity of line one should have been incremented");

    // scan once product 2
    _.each(['0','9','8','7','6','5','4','3','2','1','Enter'], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_data_row:nth(1) .o_data_cell:nth(1)').text(), '1',
        "quantity of line one should have been incremented");

    form.$buttons.find('.o_form_button_save').click();

    form.destroy();
    barcodeEvents.BarcodeEvents.max_time_between_keys_in_ms = delay;
    delete fieldRegistry.map.test_barcode_handler;
});
});
