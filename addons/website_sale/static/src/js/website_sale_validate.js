odoo.define('website_sale.validate', function (require) {
'use strict';

var publicWidget = require('web.public.widget');
var core = require('web.core');
var _t = core._t;

publicWidget.registry.websiteSaleValidate = publicWidget.Widget.extend({
    selector: 'div.oe_website_sale_tx_status[data-order-id]',

    /**
     * @override
     */
    start: function () {
        var def = this._super.apply(this, arguments);
        this._poll_nbr = 0;
        this._paymentTransationPollStatus();
        return def;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _paymentTransationPollStatus: function () {
        var self = this;
        this._rpc({
            route: '/shop/payment/get_status/' + parseInt(this.$el.data('order-id')),
        }).then(function (result) {
            self._poll_nbr += 1;
            if (result.recall) {
                if (self._poll_nbr < 20) {
                    setTimeout(function () {
                        self._paymentTransationPollStatus();
                    }, Math.ceil(self._poll_nbr / 3) * 1000);
                } else {
                    var $message = $(result.message);
                    var $warning =  $("<i class='fa fa-warning' style='margin-right:10px;'>");
                    $warning.attr("title", _t("We are waiting for confirmation from the bank or the payment provider"));
                    $message.find('span:first').prepend($warning);
                    result.message = $message.html();
                }
            }
            self.$el.html(result.message);
        });
    },
});
});
