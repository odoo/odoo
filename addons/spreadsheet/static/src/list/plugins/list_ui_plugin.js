import * as spreadsheet from "@odoo/o-spreadsheet";
import { OdooUIPlugin } from "@spreadsheet/plugins";
import { _t } from "@web/core/l10n/translation";

const { constants, helpers } = spreadsheet;
const { PIVOT_STATIC_TABLE_CONFIG } = constants;

const { UuidGenerator, sanitizeSheetName } = helpers;
const uuidGenerator = new UuidGenerator();

/**
 * @typedef {import("./list_core_plugin").SpreadsheetList} SpreadsheetList
 */

export class ListUIPlugin extends OdooUIPlugin {
    /**
     * Handle a spreadsheet command
     * @param {Object} cmd Command
     */
    handle(cmd) {
        switch (cmd.type) {
            case "INSERT_ODOO_LIST_WITH_TABLE": {
                const { sheetId, col, row, listId, linesNumber, definition, mode } = cmd;
                this._inserListWithTable(sheetId, col, row, definition, listId, linesNumber, mode);
                break;
            }
            case "RE_INSERT_ODOO_LIST_WITH_TABLE": {
                this.dispatch("RE_INSERT_ODOO_LIST", cmd);
                const { sheetId, col, row, linesNumber, mode, columns } = cmd;
                this._addTable(sheetId, col, row, linesNumber, columns, mode);
                break;
            }

            case "INSERT_NEW_ODOO_LIST": {
                let sheetName = sanitizeSheetName(
                    _t("%(list_name)s (List #%(list_id)s)", {
                        list_name: cmd.name,
                        list_id: cmd.listId,
                    })
                );
                if (cmd.insertInNewSheet) {
                    const sheetIdFrom = this.getters.getActiveSheetId();
                    const sheetId = uuidGenerator.smallUuid();
                    if (this.getters.getSheetIdByName(sheetName)) {
                        sheetName = undefined;
                    }
                    this.dispatch("CREATE_SHEET", {
                        sheetId,
                        position: this.getters.getSheetIds().length,
                        name: sheetName,
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
                break;
            }

            case "DUPLICATE_ODOO_LIST_IN_NEW_SHEET": {
                const duplicatedListName = sanitizeSheetName(
                    _t("%s (copy)", this.getters.getListDefinition(cmd.listId).name)
                );
                this.dispatch("DUPLICATE_ODOO_LIST", {
                    listId: cmd.listId,
                    newListId: cmd.newListId,
                    duplicatedListName,
                });

                const sheetIdFrom = this.getters.getActiveSheetId();
                const sheetId = uuidGenerator.smallUuid();

                console.log(
                    this.dispatch("CREATE_SHEET", {
                        sheetId,
                        position: this.getters.getSheetIds().length,
                        name: this.getters.getSheetIdByName(duplicatedListName)
                            ? undefined
                            : duplicatedListName,
                    })
                );
                this.dispatch("ACTIVATE_SHEET", { sheetIdFrom, sheetIdTo: sheetId });
                // sheetId, col, row,   listId, linesNumber, columns, mode
                const columns = this.getters.getListDefinition(cmd.listId).columns;
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
                break;
            }
        }
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
}
