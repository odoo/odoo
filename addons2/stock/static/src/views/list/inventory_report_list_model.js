/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { DynamicRecordList } from "@web/model/relational_model/dynamic_record_list";
import { RelationalModel } from "@web/model/relational_model/relational_model";

export class InventoryReportListModel extends RelationalModel {
    /**
     * Override
     */
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        // model has not created any record yet
        this._lastCreatedRecordId;
        return super.setup(...arguments);
    }

    /**
     * Function called when a record has been _load (after saved).
     * We need to detect when the user added to the list a quant which already exists
     * (see stock.quant.create), either already loaded or not, to warn the user
     * the quant was updated.
     * This is done by checking :
     * - the record id against the '_lastCreatedRecordId' on model
     * - the create_date against the write_date (both are equal for newly created records).
     *
     */
    async _updateSimilarRecords(reloadedRecord, serverValues) {
        if (this.config.isMonoRecord) {
            return;
        }

        const justCreated = reloadedRecord.id == this._lastCreatedRecordId;
        if (justCreated && serverValues.create_date !== serverValues.write_date) {
            this.notification.add(
                _t(
                    "You tried to create a record that already exists. The existing record was modified instead."
                ),
                { title: _t("This record already exists.") }
            );
            const duplicateRecords = this.root.records.filter(
                (record) => record.resId === reloadedRecord.resId && record.id !== reloadedRecord.id
            );
            if (duplicateRecords.length > 0) {
                /* more than 1 'resId' record loaded in view (user added an already loaded record) :
                 * - both have been updated
                 * - remove the current record (the added one)
                 */
                await this.root._removeRecords([reloadedRecord.id]);
                for (const record of duplicateRecords) {
                    record._applyValues(serverValues);
                }
            }
        } else {
            super._updateSimilarRecords(...arguments)
        }
    }
}

export class InventoryReportListDynamicRecordList extends DynamicRecordList {
    /**
     * Override
     */
    async addNewRecord() {
        const record = await super.addNewRecord(...arguments);
        // keep created record id on model
        record.model._lastCreatedRecordId = record.id;
        return record;
    }
}

InventoryReportListModel.DynamicRecordList = InventoryReportListDynamicRecordList;
