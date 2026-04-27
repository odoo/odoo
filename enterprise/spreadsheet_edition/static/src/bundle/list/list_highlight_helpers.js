import { helpers } from "@odoo/o-spreadsheet";

const { positionToZone, mergeContiguousZones } = helpers;

export function getListHighlights(getters, listId) {
    const sheetId = getters.getActiveSheetId();
    const listCellPositions = getVisibleListCellPositions(getters, listId);
    const mergedZones = mergeContiguousZones(listCellPositions.map(positionToZone));
    return mergedZones.map((zone) => ({ sheetId, zone, noFill: true }));
}

function getVisibleListCellPositions(getters, listId) {
    const positions = [];
    const sheetId = getters.getActiveSheetId();
    for (const col of getters.getSheetViewVisibleCols()) {
        for (const row of getters.getSheetViewVisibleRows()) {
            const position = { sheetId, col, row };
            const cellListId = getters.getListIdFromPosition(position);
            if (listId === cellListId) {
                positions.push(position);
            }
        }
    }
    return positions;
}
