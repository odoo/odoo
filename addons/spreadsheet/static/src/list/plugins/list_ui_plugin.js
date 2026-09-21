import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { _t } from "@web/core/l10n/translation";

const { constants, helpers } = spreadsheet;
const { PIVOT_STATIC_TABLE_CONFIG } = constants;

const { UuidGenerator, sanitizeSheetName, getUniqueText } = helpers;

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListUIPlugin extends OdooUIPlugin {
    handlers = {
        INSERT_ODOO_LIST_WITH_TABLE: this.onInsertOdooListWithTable,
        RE_INSERT_ODOO_LIST_WITH_TABLE: this.onReInsertOdooListWithTable,
        INSERT_NEW_ODOO_LIST: this.onInsertNewOdooList,
        DUPLICATE_ODOO_LIST_IN_NEW_SHEET: this.onDuplicateOdooListInNewSheet,
    };

    onInsertOdooListWithTable(cmd) {
        const { sheetId, col, row, listId, linesNumber, definition, mode } = cmd;
        this._inserListWithTable(sheetId, col, row, definition, listId, linesNumber, mode);
    }

    onReInsertOdooListWithTable(cmd) {
        this.dispatch("RE_INSERT_ODOO_LIST", cmd);
        const { sheetId, col, row, linesNumber, mode, columns } = cmd;
        this._addTable(sheetId, col, row, linesNumber, columns, mode);
    }

    onInsertNewOdooList(cmd) {
        const sheetName = sanitizeSheetName(
            _t("%(list_name)s (List #%(list_id)s)", {
                list_name: cmd.name,
                list_id: cmd.listId,
            })
        );
        if (cmd.insertInNewSheet) {
            const sheetIdFrom = this.getters.getActiveSheetId();
            const sheetId = UuidGenerator.smallUuid();

            this.dispatch("CREATE_SHEET", {
                sheetId,
                position: this.getters.getSheetIds().length,
                name: this._computeValidSheetName(sheetName),
            });
            this.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        } else {
            const sheetId = this.getters.getActiveSheetId();
            this.dispatch("RENAME_SHEET", {
                sheetId,
                oldName: this.getters.getSheetName(sheetId),
                newName: sheetName,
            });
        }
        this._inserListWithTable(
            this.getters.getActiveSheetId(),
            0,
            0,
            cmd.definition,
            cmd.listId,
            cmd.linesNumber,
            cmd.mode
        );
    }

    onDuplicateOdooListInNewSheet(cmd) {
        const duplicatedListName = _t("%s (copy)", this.getters.getListDefinition(cmd.listId).name);
        this.dispatch("DUPLICATE_ODOO_LIST", {
            listId: cmd.listId,
            newListId: cmd.newListId,
            duplicatedListName,
        });

        const sheetName = sanitizeSheetName(
            _t("%(list_name)s (List #%(list_id)s)", {
                list_name: duplicatedListName,
                list_id: cmd.newListId,
            })
        );

        const sheetIdFrom = this.getters.getActiveSheetId();
        const sheetId = UuidGenerator.smallUuid();

        this.dispatch("CREATE_SHEET", {
            sheetId,
            position: this.getters.getSheetIds().length,
            name: this._computeValidSheetName(sheetName),
        });
        this.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
        const columns = this.getters.getListDefinition(cmd.newListId).columns;
        this.dispatch("RE_INSERT_ODOO_LIST", {
            sheetId,
            col: 0,
            row: 0,
            columns,
            listId: cmd.newListId,
            linesNumber: cmd.linesNumber,
            mode: "dynamic",
        });
        this._addTable(sheetId, 0, 0, cmd.linesNumber, columns, "dynamic");
    }

    _inserListWithTable(sheetId, col, row, definition, listId, linesNumber, mode) {
        this.dispatch("INSERT_ODOO_LIST", {
            sheetId,
            col,
            row,
            definition,
            linesNumber,
            listId,
            mode,
        });
        const columns = this.getters.getListDefinition(listId).columns;
        this._addTable(sheetId, col, row, linesNumber, columns, mode);
    }

    _addTable(sheetId, col, row, linesNumber, columns, mode) {
        let zone;
        if (mode === "static") {
            zone = {
                left: col,
                right: col + columns.length - 1,
                top: row,
                bottom: row + linesNumber,
            };
        } else {
            zone = {
                left: col,
                right: col,
                top: row,
                bottom: row,
            };
        }
        this.dispatch("CREATE_TABLE", {
            tableType: mode,
            sheetId,
            ranges: [this.getters.getRangeDataFromZone(sheetId, zone)],
            config: { ...PIVOT_STATIC_TABLE_CONFIG, firstColumn: false },
        });
    }

    _computeValidSheetName(name) {
        const sanitized = sanitizeSheetName(name);
        const allNames = this.getters.getSheetIds().map((id) => this.getters.getSheetName(id));
        return getUniqueText(sanitized, allNames);
    }
}
