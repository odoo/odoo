odoo.define('account.payment', function (require) {
"use strict";

var core = require('web.core');
var form_common = require('web.form_common');
var formats = require('web.formats');
var Model = require('web.Model');

var QWeb = core.qweb;

var ShowPaymentLineWidget = form_common.AbstractField.extend({
    render_value: function() {
        var self = this;
        var info = JSON.parse(this.get('value'));
        var invoice_id = info.invoice_id;
        if (info !== false) {
            _.each(info.content, function(k,v){
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
                new Model("account.invoice")
                    .call("assign_outstanding_credit", [invoice_id, id])
                    .then(function (result) {
                        self.view.reload();
                    });
            });
        }
        else {
            this.$el.html('');
        }
    },
});

core.form_widget_registry.add('payment', ShowPaymentLineWidget);

});