odoo.define('sale.ReconciliationRenderer', function (require) {
"use strict";

var ReconciliationRenderer = require('account.ReconciliationRenderer');

ReconciliationRenderer.LineRenderer.include({
    events: _.extend({}, ReconciliationRenderer.LineRenderer.prototype.events, {
        'click .accounting_view .o_reconcile_so': '_onReconcileWithSaleOrder',
    }),

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    update: function (state) {
        this._super(state);
        this.$('caption .o_buttons button.o_reconcile_so')
            .toggleClass('hidden', state.balance.amount <= 0 || state.balance.type > 0 || !state.order_ids.length);
        this.$('.o_reconciliation_blockui').toggleClass('hidden', !state.blockUI);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onReconcileWithSaleOrder: function () {
        this.trigger_up('reconcile_with_sale_order');
    },
});

ReconciliationRenderer.ManualLineRenderer.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    update: function (state) {
        this._super(state);
        this.$('caption .o_buttons button.o_reconcile_so')
            .toggleClass('hidden', state.balance.amount <= 0 || state.balance.type > 0 || !state.order_ids.length || _.filter(state.reconciliation_proposition, {'display': true}).length !== 1);
    },
});


return ReconciliationRenderer;
});
