odoo.define('sale.ReconciliationModel', function (require) {
"use strict";

var ReconciliationModel = require('account.ReconciliationModel');

ReconciliationModel.StatementModel.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @param {string} handle
     * @param {Object[]}
     * @returns {Deferred}
     */
    addMultiPropositions: function (handle, props) {
        var line = this.getLine(handle);
        this._formatLineProposition(line, props);
        if (!line.reconciliation_proposition) {
            line.reconciliation_proposition = [];
        }
        line.reconciliation_proposition.push.apply(line.reconciliation_proposition, props);
        return this._computeLine(line);
    },
    /**
     * @private
     * @override
     */
    changePartner: function (handle, partner) {
        return this._super(handle, partner).then(this.getSaleOrders.bind(this, handle), this.getSaleOrders.bind(this, handle));
    },
    /**
     * @param {string} handle
     * @returns {Deferred}
     */
    getSaleOrders: function (handle) {
        var line = this.getLine(handle);
        var domain = [
            ['state', 'in', ['sent', 'sale']],
            ['invoice_status', '!=', 'invoiced'],
            ['currency_id', '=', line.st_line.currency_id]];
        if (line.st_line.partner_id) {
            domain.push(['partner_id', '=', line.st_line.partner_id]);
        }
        return this._rpc({
            model: 'sale.order',
            method: 'search',
            args: [domain],
        }).then(function (ids) {
            line.order_ids = ids;
        });
    },
});

return ReconciliationModel;
});
