odoo.define('account.payment', function (require) {
"use strict";

var AbstractField = require('web.AbstractField');
var core = require('web.core');
var formats = require('web.formats');
var field_registry = require('web.field_registry');

var QWeb = core.qweb;


var ShowPaymentLineWidget = AbstractField.extend({
    supportedFieldTypes: ['text'],
    render: function() {
        var self = this;
        var info = JSON.parse(this.value);
        var invoice_id = info.invoice_id;
        if (info !== false) {
            _.each(info.content, function(k,v){
                k.index = v;
                k.amount = formats.format_value(k.amount, {type: "float", digits: k.digits});
                if (k.date){
                    k.date = formats.format_value(k.date, {type: "date"});
                }
            });
            this.$el.html(QWeb.render('ShowPaymentInfo', {
                'lines': info.content,
                'outstanding': info.outstanding,
                'title': info.title
            }));
            this.$('.outstanding_credit_assign').click(function(){
                var id = $(this).data('id') || false;
                self.trigger_up('perform_model_rpc', {
                    model: 'account.invoice',
                    method: 'assign_outstanding_credit',
                    args: [invoice_id, id],
                    on_success: function () {
                        self.trigger_up('reload');
                    }
                });
            });
            _.each(this.$('.js_payment_info'), function(k, v){
                var options = {
                    'content': QWeb.render('PaymentPopOver', {
                            'name': info.content[v].name,
                            'journal_name': info.content[v].journal_name,
                            'date': info.content[v].date,
                            'amount': info.content[v].amount,
                            'currency': info.content[v].currency,
                            'position': info.content[v].position,
                            'payment_id': info.content[v].payment_id,
                            'move_id': info.content[v].move_id,
                            'ref': info.content[v].ref,
                            }),
                    'html': true,
                    'placement': 'left',
                    'title': 'Payment Information',
                    'trigger': 'focus',
                    'delay': { "show": 0, "hide": 100 },
                };
                $(k).popover(options);
                $(k).on('shown.bs.popover', function(){
                    $(this).parent().find('.js_unreconcile_payment').click(function(){
                        var payment_id = parseInt($(this).attr('payment-id'));
                        if (payment_id !== undefined && !isNaN(payment_id)){
                            self.trigger_up('perform_model_rpc', {
                                model: 'account.move.line',
                                method: 'remove_move_reconcile',
                                args: [payment_id, {'invoice_id': self.res_id}],
                                on_success: function () {
                                    self.trigger_up('reload');
                                }
                            });
                        }
                    });
                    $(this).parent().find('.js_open_payment').click(function(){
                        var move_id = parseInt($(this).attr('move-id'));
                        if (move_id !== undefined && !isNaN(move_id)){
                            //Open form view of account.move with id = move_id
                            self.do_action({
                                type: 'ir.actions.act_window',
                                res_model: 'account.move',
                                res_id: move_id,
                                views: [[false, 'form']],
                                target: 'current'
                            });
                        }
                    });
                });
            });
        }
        else {
            this.$el.html('');
        }
    },
    has_no_value: function() {
        return false;
    }
});

field_registry.add('payment', ShowPaymentLineWidget);

});
