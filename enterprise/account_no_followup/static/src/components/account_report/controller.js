/** @odoo-module */
import { AccountReportController } from "@account_reports/components/account_report/controller";

import { patch } from "@web/core/utils/patch";

patch(AccountReportController.prototype, {
    updateLines(lineIds, key, value) {
        for (const lineId of lineIds) {
            const lineIndex = this.lines.findIndex((line) => line.id === lineId);
            this.lines.splice(lineIndex, 1, { ...this.lines[lineIndex], [key]: value });
        }
    }
})
