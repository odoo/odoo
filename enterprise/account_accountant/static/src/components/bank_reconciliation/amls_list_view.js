/** @odoo-module **/

import { registry } from "@web/core/registry";
import { EmbeddedListView } from "./embedded_list_view";
import { ListRenderer } from "@web/views/list/list_renderer";
import { useState, onWillUnmount } from "@odoo/owl";

export class BankRecAmlsRenderer extends ListRenderer {
    setup() {
        super.setup();
        this.globalState = useState(this.env.methods.getState());

        onWillUnmount(this.saveSearchState);
    }

    /** @override **/
    getRowClass(record) {
        const classes = super.getRowClass(record);
        const amlId = this.globalState.bankRecRecordData.selected_aml_ids.currentIds.find((x) => x === record.resId);
        if (amlId){
            return `${classes} o_rec_widget_list_selected_item table-info`;
        }
        return classes;
    }

    /** @override **/
    async onCellClicked(record, column, ev) {
        const amlId = this.globalState.bankRecRecordData.selected_aml_ids.currentIds.find((x) => x === record.resId);
        if (amlId) {
            this.env.config.actionRemoveNewAml(record.resId);
        } else {
            this.env.config.actionAddNewAml(record.resId);
        }
    }

    /** Backup the search facets in order to restore them when the user comes back on this view. **/
    saveSearchState() {
        const initParams = this.globalState.bankRecEmbeddedViewsData.amls;
        const searchModel = this.env.searchModel;
        initParams.exportState = {searchModel: JSON.stringify(searchModel.exportState())};
    }
}

export const BankRecAmls = {
    ...EmbeddedListView,
    Renderer: BankRecAmlsRenderer,
};

registry.category("views").add("bank_rec_amls_list_view", BankRecAmls);
