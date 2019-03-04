odoo.define('web.PrintTicket', function (require) {
"use static";

var core = require('web.core');
var AbstractAction = require('web.AbstractAction');

var QWeb = core.qweb;

var PrintTicket = AbstractAction.extend({
    /**
     * @override
     * @param {Object} parent
     * @param {Object} records
     *
     */
    init: function (parent, records) {
        this._super.apply(this, arguments);
        this.receipt_data = records.params.receipt_data;
        this.iot_box_url = records.params.iot_box_url;
    },
    /**
     * @override
     *
     */
    start: function () {
        var $receipt = QWeb.render('OrderXmlReceipt', this.receipt_data);
        var def = this._rpc({
                route: this.iot_box_url+'/hw_proxy/print_xml_receipt',
                params:{receipt: $receipt}
            });

        return Promise.all([def, this._super.apply(this, arguments)]);
    },
});

core.action_registry.add('print_ticket_action', PrintTicket);
});
