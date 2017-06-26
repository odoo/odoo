odoo.define('barcodes.tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var FormView = require('web.FormView');

var createView = testUtils.createView;
var triggerKeypressEvent = testUtils.triggerKeypressEvent;

QUnit.module('Barcodes', {
    beforeEach: function () {
        this.data = {
            product: {
                fields: {
                    name: {string : "Product name", type: "char"},
                },
                records: [
                    {id: 1, name: "iPad Mini"},
                    {id: 2, name: "Mouse, Optical"},
                ],
            },
        };
    }
});

QUnit.test('Button with barcode_trigger', function (assert) {
    assert.expect(1);

    var form = createView({
        View: FormView,
        model: 'product',
        data: this.data,
        arch: '<form>' +
                '<header>' +
                    '<button name="do_something" string="Validate" type="object" barcode_trigger="doit"/>' +
                '</header>' +
            '</form>',
        res_id: 2,
        intercepts: {
            execute_action: function (event) {
                assert.strictEqual(event.data.action_data.name, 'do_something',
                    "do_something method call verified");
            },
        },
    });

    // O-BTN.doit
    _.each(['O','-','B','T','N','.','d','o','i','t','Enter'], triggerKeypressEvent);

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
    _.each(["O","-","C","M","D",".","C","A","N","C","E","L","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$(".o_form_readonly").length, 1,
        "should have switched to 'readonly' mode");
    assert.verifySteps(['save'], 'should not have saved');

    form.destroy();
});

QUnit.test('pager buttons', function (assert) {
    assert.expect(3);

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
    _.each(["O","-","C","M","D",".","P","A","G","E","R","-","N","E","X","T","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'Mouse, Optical');
    // O-CMD.PAGER-PREV
    _.each(["O","-","C","M","D",".","P","A","G","E","R","-","P","R","E","V","Enter"], triggerKeypressEvent);
    assert.strictEqual(form.$('.o_field_widget').text(), 'iPad Mini');

    form.destroy();
});

});
