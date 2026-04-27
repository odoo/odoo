import { astToFormula, helpers, stores } from "@odoo/o-spreadsheet";
import { getFirstListFunction } from "@spreadsheet/list/list_helpers";

const { positionToZone } = helpers;

const { SpreadsheetStore, HighlightStore, HoveredCellStore } = stores;

export class FieldSyncHighlightStore extends SpreadsheetStore {
    constructor(get) {
        super(get);
        this.hoveredCell = get(HoveredCellStore);
        const highlightStore = get(HighlightStore);
        highlightStore.register(this);
        this.onDispose(() => {
            highlightStore.unRegister(this);
        });
    }

    get highlights() {
        if (this.hoveredCell.col === undefined || this.hoveredCell.row === undefined) {
            return [];
        }
        const sheetId = this.getters.getActiveSheetId();
        const fieldSync = this.getters.getFieldSync({
            sheetId,
            col: this.hoveredCell.col,
            row: this.hoveredCell.row,
        });
        if (!fieldSync) {
            return [];
        }
        const highlights = [];
        const cells = this.getters.getCells(sheetId);
        for (const cellId in cells) {
            const cell = cells[cellId];
            const cellPosition = this.getters.getCellPosition(cellId);
            if (cell.isFormula && this.getters.isPositionVisible(cellPosition)) {
                const listFunction = getFirstListFunction(cell.compiledFormula.tokens);
                if (!listFunction) {
                    continue;
                }
                const [listIdArg, positionArg, fieldNameArg] = listFunction.args;
                if (!listIdArg || !positionArg || !fieldNameArg) {
                    continue;
                }
                const listId = this.getters
                    .evaluateFormula(sheetId, astToFormula(listIdArg))
                    ?.toString();
                const position = this.getters.evaluateFormula(sheetId, astToFormula(positionArg));
                const fieldName = this.getters.evaluateFormula(sheetId, astToFormula(fieldNameArg));
                if (
                    listId === fieldSync.listId &&
                    position - 1 === fieldSync.indexInList &&
                    fieldName === fieldSync.fieldName
                ) {
                    highlights.push({
                        zone: positionToZone(cellPosition),
                        sheetId,
                        color: "#875A7B",
                    });
                }
            }
        }
        return highlights;
    }
}
