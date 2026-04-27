import { AbstractCellClipboardHandler } from "@odoo/o-spreadsheet";

export class FieldSyncClipboardHandler extends AbstractCellClipboardHandler {
    copy(data) {
        const { sheetId } = data;
        const { rowsIndexes, columnsIndexes } = data;
        const fieldSyncs = [];
        for (const row of rowsIndexes) {
            const fieldSyncsInRow = [];
            fieldSyncs.push(fieldSyncsInRow);
            for (const col of columnsIndexes) {
                const position = { sheetId, col, row };
                fieldSyncsInRow.push({
                    fieldSync: this.getters.getFieldSync(position),
                    position,
                });
            }
        }
        return fieldSyncs;
    }

    /**
     * Paste the clipboard content in the given target
     */
    paste(target, fieldSyncs, options) {
        if (options?.pasteOption) {
            return;
        }
        const zones = target.zones;
        const sheetId = target.sheetId;

        if (!options?.isCutOperation) {
            this.pasteFromCopy(sheetId, zones, fieldSyncs, options);
        }
    }

    pasteZone(sheetId, col, row, fieldSyncs, clipboardOptions) {
        for (const [r, rowCells] of fieldSyncs.entries()) {
            for (const [c, origin] of rowCells.entries()) {
                if (!origin.fieldSync) {
                    continue;
                }
                const position = { col: col + c, row: row + r, sheetId };
                const delta = position.row - origin.position.row;
                this.dispatch("ADD_FIELD_SYNC", {
                    ...position,
                    fieldName: origin.fieldSync.fieldName,
                    listId: origin.fieldSync.listId,
                    indexInList: origin.fieldSync.indexInList + delta,
                });
            }
        }
    }
}
