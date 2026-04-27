import { CommandResult, helpers } from "@odoo/o-spreadsheet";
import { OdooCorePlugin } from "@spreadsheet/plugins";

const { positionToZone, toCartesian, toXC } = helpers;

export class FieldSyncCorePlugin extends OdooCorePlugin {
    static getters = [
        "getAllFieldSyncs",
        "getFieldSync",
        "getFieldSyncs",
        "getMainSaleOrderLineList",
    ];

    fieldSyncs = {};

    allowDispatch(cmd) {
        switch (cmd.type) {
            case "ADD_FIELD_SYNC": {
                const fieldSync = this.getFieldSync(cmd);
                if (
                    fieldSync &&
                    fieldSync.listId === cmd.listId &&
                    fieldSync.indexInList === cmd.indexInList &&
                    fieldSync.fieldName === cmd.fieldName
                ) {
                    return CommandResult.NoChanges;
                } else if (cmd.indexInList < 0) {
                    return CommandResult.InvalidTarget;
                }
                break;
            }
            case "DELETE_FIELD_SYNCS": {
                if (this.getFieldSyncs(cmd.sheetId, cmd.zone).length === 0) {
                    return CommandResult.NoChanges;
                }
                break;
            }
            case "REMOVE_GLOBAL_FILTER":
                if (this.getters.getGlobalFilter(cmd.id)?.modelName === "sale.order") {
                    return CommandResult.Readonly;
                }
                break;
            case "REMOVE_ODOO_LIST": {
                if (cmd.listId === this.getMainSaleOrderLineList().id) {
                    return CommandResult.Readonly;
                }
                break;
            }
        }
        return CommandResult.Success;
    }

    handle(cmd) {
        switch (cmd.type) {
            case "ADD_FIELD_SYNC": {
                const { sheetId, col, row } = cmd;
                const fieldSync = {
                    listId: cmd.listId,
                    indexInList: cmd.indexInList,
                    fieldName: cmd.fieldName,
                };
                this.history.update("fieldSyncs", sheetId, col, row, fieldSync);
                break;
            }
            case "DELETE_FIELD_SYNCS": {
                const { sheetId, zone } = cmd;
                for (let col = zone.left; col <= zone.right; col++) {
                    for (let row = zone.top; row <= zone.bottom; row++) {
                        this.history.update("fieldSyncs", sheetId, col, row, undefined);
                    }
                }
                break;
            }
        }
    }

    adaptRanges(applyChange) {
        const deletedPositions = [];
        const newPositions = new Map();
        for (const [position, fieldSync] of this.getAllFieldSyncs()) {
            const { sheetId, col, row } = position;
            const change = applyChange(this._getFieldSyncRange(position));
            switch (change.changeType) {
                case "REMOVE":
                    this.history.update("fieldSyncs", sheetId, col, row, undefined);
                    break;
                case "NONE":
                    break;
                default: {
                    const { top, left } = change.range.zone;
                    deletedPositions.push(position);
                    newPositions.set({ sheetId, col: left, row: top}, fieldSync);
                    break;
                }
            }
        }
        for (const position of deletedPositions) {
            const { sheetId, col, row } = position;
            this.history.update("fieldSyncs", sheetId, col, row, undefined);
        }
        for (const [position, fieldSync] of newPositions) {
            const { sheetId, col, row } = position;
            this.history.update("fieldSyncs", sheetId, col, row, fieldSync);
        }
    }

    getAllFieldSyncs() {
        const fieldSyncs = new Map();
        for (const sheetId in this.fieldSyncs) {
            for (const col in this.fieldSyncs[sheetId]) {
                for (const row in this.fieldSyncs[sheetId][col]) {
                    const position = { sheetId, col: parseInt(col), row: parseInt(row) };
                    fieldSyncs.set(position, this.getFieldSync(position));
                }
            }
        }
        return fieldSyncs;
    }

    getFieldSyncs(sheetId, zone) {
        const fieldSyncs = [];
        for (let col = zone.left; col <= zone.right; col++) {
            for (let row = zone.top; row <= zone.bottom; row++) {
                const fieldSync = this.getFieldSync({ sheetId, col, row });
                if (fieldSync) {
                    fieldSyncs.push(fieldSync);
                }
            }
        }
        return fieldSyncs;
    }

    getFieldSync(position) {
        const { sheetId, col, row } = position;
        return this.fieldSyncs[sheetId]?.[col]?.[row];
    }

    getMainSaleOrderLineList() {
        const listIds = this.getters.getListIds();
        for (const listId of listIds) {
            const list = this.getters.getListDefinition(listId);
            if (list.model === "sale.order.line") {
                return list;
            }
        }
    }

    /**
     * @private
     */
    _getFieldSyncRange(position) {
        return this.getters.getRangeFromZone(position.sheetId, positionToZone(position));
    }

    export(data) {
        const fieldSyncs = this.getAllFieldSyncs();
        if (fieldSyncs.size) {
            const fieldSyncsBySheets = Object.groupBy(
                fieldSyncs.entries(),
                ([position, fieldSync]) => position.sheetId
            );
            for (const sheetId in fieldSyncsBySheets) {
                const sheet = data.sheets.find((sheet) => sheet.id === sheetId);
                sheet.fieldSyncs = {};
                for (const [position, fieldSync] of fieldSyncsBySheets[sheetId]) {
                    sheet.fieldSyncs[toXC(position.col, position.row)] = fieldSync;
                }
            }
        }
    }

    import(data) {
        for (const sheet of data.sheets) {
            if (sheet.fieldSyncs) {
                for (const [xc, fieldSync] of Object.entries(sheet.fieldSyncs)) {
                    const { col, row } = toCartesian(xc);
                    this.history.update("fieldSyncs", sheet.id, col, row, fieldSync);
                }
            }
        }
    }
}
