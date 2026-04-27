import { CorePlugin } from "@odoo/o-spreadsheet";


export class QualitySpreadsheetPlugin extends CorePlugin {
    static getters = [
        "getQualityCheckResultCellString",
        "getQualityCheckResultPosition",
    ];
    constructor(config) {
        super(config);
        this.resultCellString = config.custom.qualitySuccessCell;
    }

    adaptRanges(applyChange, sheetId) {
        if (!this.resultCell) {
            return;
        }
        const change = applyChange(this.resultCell);
        switch (change.changeType) {
            case "REMOVE":
                this.history.update("resultCell", undefined);
                break;
            case "RESIZE":
            case "MOVE":
            case "CHANGE":
                this.history.update("resultCell", change.range);
                break;
        }
    }

    getQualityCheckResultPosition() {
        if (!this.resultCell || this.resultCell.invalidXc) {
            return;
        }
        return {
            sheetId: this.resultCell.sheetId,
            col: this.resultCell.zone.left,
            row: this.resultCell.zone.top
        }
    }

    getQualityCheckResultCellString() {
        if (!this.resultCell || this.resultCell.invalidXc) {
            return "#REF";
        }
        return this.getters.getRangeString(this.resultCell, this.getters.getSheetIds()[0])
    }

    import() {
        if (this.resultCellString) {
            this.resultCell = this.getters.getRangeFromSheetXC(
                this.getters.getSheetIds()[0],
                this.resultCellString,
            )
        }
    }
}
