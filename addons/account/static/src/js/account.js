odoo.define('account.kanban', function(require) {
"use strict";

var KanbanRecord = require('web.KanbanRecord');

KanbanRecord.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     * @private
     */
    _openRecord: function () {
        if (this.modelName === 'account.invoice' && _.contains(['sale', 'purchase'], this.record.journal_type.raw_value)) {
            var action = this.record.journal_type.raw_value == 'purchase' ? 'account.action_vender_bill' : 'account.action_customer_invoice';
            this.do_action(action, {'res_id': this.id});
        } else {
            this._super.apply(this, arguments);
        }
    }
});

});
