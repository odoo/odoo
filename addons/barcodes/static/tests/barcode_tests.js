odoo.define('barcodes.tests', function (require) {
"use strict";

const {barcodeService} = require("@barcodes/barcode_service");
const {barcodeAutoClick} = require("@barcodes/barcode_handlers");
const {barcodeRemapperService} = require("@barcodes/js/barcode_events");
const { makeTestEnv } = require("@web/../tests/helpers/mock_env");
const { registry } = require("@web/core/registry");

var AbstractField = require('web.AbstractField');
var fieldRegistry = require('web.field_registry');
var FormController = require('web.FormController');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;
var triggerEvent = testUtils.dom.triggerEvent;
var core = require('web.core');

const maxTimeBetweenKeysInMs = barcodeService.maxTimeBetweenKeysInMs;

function simulateBarCode(chars, target = document.body) {
    for (let char of chars) {
        let keycode;
        if (char === 'Enter') {
            keycode = $.ui.keyCode.ENTER;
        } else if (char === "Tab") {
            keycode = $.ui.keyCode.TAB;
        } else {
            keycode = char.charCodeAt(0);
        }
        triggerEvent(target, 'keydown', {
            key: char,
            keyCode: keycode,
        });
    }
}

QUnit.module('Barcodes', {
    before() {
        barcodeService.maxTimeBetweenKeysInMs = 0;
        registry.category("services").add("barcode", barcodeService, { force: true});
        registry.category("services").add("barcode_autoclick", barcodeAutoClick, { force: true});
        // remove this one later
        registry.category("services").add("barcode_remapper", barcodeRemapperService);
        this.env = makeTestEnv();
    },
    after() {
        barcodeService.maxTimeBetweenKeysInMs = maxTimeBetweenKeysInMs;
    },
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
                    int_field_2: {string : "Integer", type: "integer"},
                    barcode: {string: "Barcode", type: "char"},
                },
                records: [
                    {id: 1, name: "Large Cabinet", barcode: '1234567890'},
                    {id: 2, name: "Cabinet with Doors", barcode: '0987654321'},
                ],
            },
        };
    }
});

QUnit.test('Button with barcode_trigger', async function (assert) {
    assert.expect(2);

    var form = await createView({
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
        services: {
            notification: {
                notify: function (params) {
                    assert.step(params.type);
                }
            },
        },
        intercepts: {
            execute_action: function (event) {
                assert.strictEqual(event.data.action_data.name, 'do_something',
                    "do_something method call verified");
            },
        },
    });

    // O-BTN.doit
    simulateBarCode(['O','-','B','T','N','.','d','o','i','t','Enter']);
    // O-BTN.dothat (should not call execute_action as the button isn't visible)
    simulateBarCode(['O','-','B','T','N','.','d','o','t','h','a','t','Enter']);
    await testUtils.nextTick();
    assert.verifySteps([], "no warning should be displayed");

    form.destroy();
});

QUnit.test('edit, save and cancel buttons', async function (assert) {
    assert.expect(6);

    var form = await createView({
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
    simulateBarCode(["O","-","C","M","D",".","E","D","I","T","Enter"], document.body);
    await testUtils.nextTick();
    assert.containsOnce(form, ".o_form_editable",
        "should have switched to 'edit' mode");
    // dummy change to check that it actually saves
    await testUtils.fields.editInput(form.$('.o_field_widget'), 'test');
    // O-CMD.SAVE
    simulateBarCode(["O","-","C","M","D",".","S","A","V","E","Enter"], document.body);
    await testUtils.nextTick();
    assert.containsOnce(form, ".o_form_readonly",
        "should have switched to 'readonly' mode");
    assert.verifySteps(['save'], 'should have saved');

    // O-CMD.EDIT
    simulateBarCode(["O","-","C","M","D",".","E","D","I","T","Enter"], document.body);
    await testUtils.nextTick();
    // dummy change to check that it correctly discards
    await testUtils.fields.editInput(form.$('.o_field_widget'), 'test');
    // O-CMD.CANCEL
    simulateBarCode(["O","-","C","M","D",".","D","I","S","C","A","R","D","Enter"], document.body);
    await testUtils.nextTick();
    assert.containsOnce(form, ".o_form_readonly",
        "should have switched to 'readonly' mode");
    assert.verifySteps([], 'should not have saved');

    form.destroy();
});

QUnit.test('pager buttons', async function (assert) {
    assert.expect(5);

    var form = await createView({
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

    assert.strictEqual(form.$('.o_field_widget').text(), 'Large Cabinet');
    // O-CMD.PAGER-NEXT
    simulateBarCode(["O","-","C","M","D",".","N","E","X","T","Enter"]);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_field_widget').text(), 'Cabinet with Doors');
    // O-CMD.PAGER-PREV
    simulateBarCode(["O","-","C","M","D",".","P","R","E","V","Enter"]);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_field_widget').text(), 'Large Cabinet');
    // O-CMD.PAGER-LAST
    simulateBarCode(["O","-","C","M","D",".","P","A","G","E","R","-","L","A","S","T","Enter"]);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_field_widget').text(), 'Cabinet with Doors');
    // O-CMD.PAGER-FIRST
    simulateBarCode(["O","-","C","M","D",".","P","A","G","E","R","-","F","I","R","S","T","Enter"]);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_field_widget').text(), 'Large Cabinet');

    form.destroy();
});

QUnit.test('do no update form twice after a command barcode scanned', async function (assert) {
    assert.expect(7);

    testUtils.mock.patch(FormController, {
        update: function () {
            assert.step('update');
            return this._super.apply(this, arguments);
        },
    });

    var form = await createView({
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
    simulateBarCode(["O","-","C","M","D",".","N","E","X","T","Enter"]);
    await testUtils.nextTick();
    // a first update is done to reload the data (thus followed by a read), but
    // update shouldn't be called afterwards
    assert.verifySteps(['update', 'read']);

    simulateBarCode(['5','4','3','9','8','2','6','7','1','2','5','2','Enter']);
    await testUtils.nextTick();
    // a real barcode has been scanned -> an update should be requested (with
    // option reload='false', so it isn't followed by a read)
    assert.verifySteps(['update']);

    form.destroy();
    testUtils.mock.unpatch(FormController);
});

QUnit.test('widget field_float_scannable', async function (assert) {
    this.data.product.records[0].int_field = 4;

    function _onBarcodeScanned (code) {
        assert.step(`barcode scanned ${code}`)
    }
    core.bus.on('barcode_scanned', null, _onBarcodeScanned);

    var form = await createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="int_field" widget="field_float_scannable"/>' +
                    '<field name="int_field_2"/>' +
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

    await testUtils.form.clickEdit(form);

    assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '4',
        "should display the correct value in edit");

    // simulates keypress events in the input to replace 0.00 by 26 (should not trigger onchanges)
    form.$('.o_field_widget[name=int_field]').focus();

    // we check here that a scan on the fieldflotscannable widget triggers a
    // barcode event
    simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"], document.activeElement)
    await testUtils.nextTick();
    assert.verifySteps(['barcode scanned 60164785']);
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').get(0), document.activeElement,
        "int field should be focused");

    // we check here that a scan on the field without widget does not trigger a
    // barcode event
    form.$('.o_field_widget[name=int_field_2]').focus();
    simulateBarCode(["6", "0", "1", "6", "4", "7", "8", "5"], document.activeElement)
    await testUtils.nextTick();
    assert.verifySteps([]);

    form.destroy();
    core.bus.off('barcode_scanned', null, _onBarcodeScanned)
});

QUnit.test('widget barcode_handler', async function (assert) {
    assert.expect(4);

    this.data.product.fields.barcode_scanned = {string : "Scanned barcode", type: "char"};
    this.data.product.onchanges = {
        barcode_scanned: function (obj) {
            // simulate an onchange that increment the int_field value
            // at each barcode scanned
            obj.int_field = obj.int_field + 1;
        },
    };

    var form = await createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="int_field"/>' +
                    '<field name="barcode_scanned" widget="barcode_handler"/>' +
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

    simulateBarCode(['5','4','3','9','8','2','6','7','1','2','5','2','Enter']);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_field_widget[name=int_field]').val(), '1',
        "value should have been incremented");

    assert.verifySteps(['onchange'], "an onchange should have been done");

    form.destroy();
});

QUnit.test('specification of widget barcode_handler', async function (assert) {
    assert.expect(5);

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

    var form = await createView({
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

    assert.containsN(form, '.o_data_row', 2,
        "one2many should contain 2 rows");

    // scan twice product 1
    simulateBarCode(['1','2','3','4','5','6','7','8','9','0','Enter']);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_data_row:first .o_data_cell:nth(1)').text(), '1',
        "quantity of line one should have been incremented");
    simulateBarCode(['1','2','3','4','5','6','7','8','9','0','Enter']);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_data_row:first .o_data_cell:nth(1)').text(), '2',
        "quantity of line one should have been incremented");

    // scan once product 2
    simulateBarCode(['0','9','8','7','6','5','4','3','2','1','Enter']);
    await testUtils.nextTick();
    assert.strictEqual(form.$('.o_data_row:nth(1) .o_data_cell:nth(1)').text(), '1',
        "quantity of line one should have been incremented");

    await testUtils.form.clickSave(form);

    form.destroy();
    delete fieldRegistry.map.test_barcode_handler;
});

});
