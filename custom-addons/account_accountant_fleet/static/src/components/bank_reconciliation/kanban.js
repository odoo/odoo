/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

import { BankRecKanbanController } from "@account_accountant/components/bank_reconciliation/kanban";

patch(BankRecKanbanController.prototype, {
    getOne2ManyColumns() {
        const columns = super.getOne2ManyColumns(...arguments);
        const lineIdsRecords = this.state.bankRecRecordData.line_ids.records;

        if (lineIdsRecords.some((r) => r.data.vehicle_id || r.data.vehicle_required)) {
            const debit_col_index = columns.findIndex((col) => col[0] === "debit");
            columns.splice(debit_col_index, 0, ["vehicle", _t("Vehicle")]);
        }
        return columns;
    }
});
