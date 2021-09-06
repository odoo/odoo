odoo.define('aumet_pos_ticket_qrcode.models', function (require) {
    "use strict";

    var models = require('point_of_sale.models');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var _super_Order = models.Order.prototype;

    models.Order = models.Order.extend({
        initialize: function (attributes, options) {
            var self= this;
            var res = _super_Order.initialize.apply(this, arguments);
            var rpc_qr = rpc.query({model: 'pos.order', method: 'action_receipt_qrcode', args: [[], this.get_name()]})
                .then(function (data) {
                    self.qr_code = data
                    console.log(">>>>>>>>>>>>>>>>>>>>>>>",data)
                })
            return this
        },

        // send detail in report
        export_for_printing: function () {
            var orders = _super_Order.export_for_printing.call(this);
            orders.order_qr_code = 'data:image/png;base64, ' + this.qr_code
            console.log(">>>>>>>>>orders",orders)
            return orders;
        },
    });

});
