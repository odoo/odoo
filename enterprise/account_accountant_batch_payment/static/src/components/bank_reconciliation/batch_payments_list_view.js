/** @odoo-module **/

import { registry } from "@web/core/registry";
import { EmbeddedListView } from "@account_accountant/components/bank_reconciliation/embedded_list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useState, onWillUnmount } from "@odoo/owl";

export class BankRecBatchPaymentsRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.globalState = useState(this.env.methods.getState());

        onWillUnmount(this.saveSearchState);
    }

    /** @override **/
    getRowClass(record) {
        const classes = super.getRowClass(record);
        const batchId = this.globalState.bankRecRecordData.selected_batch_payment_ids.currentIds.find((x) => x === record.resId);
        if (batchId){
            return `${classes} o_rec_widget_list_selected_item table-info`;
        }
        return classes;
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        const batchId = this.globalState.bankRecRecordData.selected_batch_payment_ids.currentIds.find((x) => x === record.resId);
        if (batchId) {
            this.env.config.actionRemoveNewBatchPayment(record.resId);
        } else {
            this.env.config.actionAddNewBatchPayment(record.resId);
        }
    }

    /** Backup the search facets in order to restore them when the user comes back on this view. **/
    saveSearchState() {
        const initParams = this.globalState.bankRecEmbeddedViewsData.batch_payments;
        const searchModel = this.env.searchModel;
        initParams.exportState = {searchModel: JSON.stringify(searchModel.exportState())};
    }
}

export const BankRecBatchPayments = {
    ...EmbeddedListView,
    Renderer: BankRecBatchPaymentsRenderer,
};

registry.category("views").add("bank_rec_batch_payments_list_view", BankRecBatchPayments);
