openerp.account_voucher = function(instance) {

    instance.web.form.Many2OneButton = instance.web.form.Many2OneButton.extend({
        on_click: function() {
            this._super.apply(this, arguments);
            this.popup.on('create_completed', self, function(r) {
                var voucher = new instance.web.Model('account.voucher');
                voucher.call('write', [[r], {'active':false}]);
            });
        },
    });
}