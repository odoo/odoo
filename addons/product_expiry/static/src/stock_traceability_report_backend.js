import { patch } from "@web/core/utils/patch";
import { TraceabilityReport } from "@stock/client_actions/stock_traceability_report_backend";

const EXPIRATION_DATE_COLUMN = "expiration_date";

function hasVisibleExpirationDate(lines) {
    return lines.some(
        (line) =>
            line.columns.some((column) => column.name === EXPIRATION_DATE_COLUMN && column.value) ||
            (!line.isFolded && hasVisibleExpirationDate(line.lines))
    );
}

patch(TraceabilityReport.prototype, {
    async onWillStart() {
        await super.onWillStart();
        this.updateExpirationDateColumn();
    },

    get hasExpirationDate() {
        return this._hasExpirationDate;
    },

    async onClickUnfold() {
        await super.onClickUnfold();
        this.updateExpirationDateColumn();
    },

    async toggleLine(line, line_type=false) {
        await super.toggleLine(line, line_type);
        this.updateExpirationDateColumn();
    },

    updateExpirationDateColumn() {
        this._hasExpirationDate = hasVisibleExpirationDate(this.state.lines);
    },
});
