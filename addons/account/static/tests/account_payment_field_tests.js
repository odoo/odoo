odoo.define('account.reconciliation_field_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('account', {
    beforeEach: function () {
        this.data = {
            'account.invoice': {
                fields: {
                    payments_widget: {string: "payments_widget data", type: "char"},
                    outstanding_credits_debits_widget: {string: "outstanding_credits_debits_widget data", type: "char"},
                },
                records: [{
                    id: 1,
                    payments_widget: '{"content": [{"digits": [69, 2], "currency": "$", "amount": 555.0, "name": "Customer Payment: INV/2017/0004", "date": "2017-04-25", "position": "before", "ref": "BNK1/2017/0003 (INV/2017/0004)", "payment_id": 22, "move_id": 10, "journal_name": "Bank"}], "outstanding": false, "title": "Less Payment"}',
                    outstanding_credits_debits_widget: '{"content": [{"digits": [69, 2], "currency": "$", "amount": 100.0, "journal_name": "INV/2017/0004", "position": "before", "id": 20}], "invoice_id": 4, "outstanding": true, "title": "Outstanding credits"}',
                }]
            },
        };
    }
}, function () {
    QUnit.module('Reconciliation');

    QUnit.test('Reconciliation form field', function (assert) {
        assert.expect(5);

        var form = createView({
            View: FormView,
            model: 'account.invoice',
            data: this.data,
            arch: '<form>'+
                '<field name="outstanding_credits_debits_widget" widget="payment"/>'+
                '<field name="payments_widget" widget="payment"/>'+
            '</form>',
            res_id: 1,
            mockRPC: function (route, args) {
                if (args.method === 'remove_move_reconcile') {
                    assert.deepEqual(args.args, [22,{"invoice_id":1}], "should call remove_move_reconcile {warning: required focus}");
                    return $.when();
                }
                if (args.method === 'assign_outstanding_credit') {
                    assert.deepEqual(args.args, [4, 20], "should call assign_outstanding_credit {warning: required focus}");
                    return $.when();
                }
                return this._super.apply(this, arguments);
            },
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, {
                            'type': 'ir.actions.act_window',
                            'res_model': 'account.move',
                            'res_id': 10,
                            'views': [[false, 'form']],
                            'target': 'current'
                        },
                        "should open the form view");
                },
            },
        });

        assert.strictEqual(form.$('.o_field_widget[name="payments_widget"]').text().replace(/[\s\n\r]+/g, ' '),
            " Paid on 04/25/2017 $ 555.00 ",
            "should display payment information");

        form.$('.o_field_widget[name="outstanding_credits_debits_widget"] .outstanding_credit_assign').trigger('click');

        assert.strictEqual(form.$('.o_field_widget[name="outstanding_credits_debits_widget"]').text().replace(/[\s\n\r]+/g, ' '),
            " Outstanding credits Add INV/2017/0004 $ 100.00 ",
            "should display outstanding information");

        form.$('.o_field_widget[name="payments_widget"] .js_payment_info').trigger('focus');
        form.$('.popover .js_open_payment').trigger('click');

        form.$('.o_field_widget[name="payments_widget"] .js_payment_info').trigger('focus');
        form.$('.popover .js_unreconcile_payment').trigger('click');

        form.destroy();
    });
});
});
