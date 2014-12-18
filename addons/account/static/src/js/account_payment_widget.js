(function() {
    "use strict";
    var QWeb = openerp.web.qweb;
    var _t = openerp.web._t;

    /**
     * Create new payment widget method.
     * Used to show payments and outstanding credit/debit on invoice
     */
    openerp.web.form.ShowPaymentLineWidget = openerp.web.form.AbstractField.extend({
        render_value: function() {
            var self = this;
            var info = JSON.parse(this.get('value'));
            var invoice_id = info.invoice_id;
            if (info !== false){
                _.each(info.content, function(k,v){
                    k.amount = openerp.web.format_value(k.amount, {type: "float", digits: k.digits});
                });
                this.$el.html(QWeb.render('ShowPaymentInfo', {
                    'lines': info.content, 
                    'outstanding': info.outstanding, 
                    'title': info.title
                }));
                this.$('.outstanding_credit_assign').click(function(){
                    var id = $(this).data('id') || false;
                    new openerp.web.Model("account.invoice")
                        .call("assign_outstanding_credit", [invoice_id, id])
                        .then(function (result) {
                            self.view.reload();
                        });
                });
            }
        },
    });

/**
 * Registry of form fields
 */
openerp.web.form.widgets.add('payment', 'openerp.web.form.ShowPaymentLineWidget');

})();
