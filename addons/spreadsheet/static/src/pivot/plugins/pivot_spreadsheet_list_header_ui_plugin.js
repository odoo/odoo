import { localization } from "@web/core/l10n/localization";
import { _t } from "@web/core/l10n/translation";
import { getFirstListFunction } from "@spreadsheet/list/list_helpers";
import { OdooUIPlugin } from "@spreadsheet/plugins";

export class PivotSpreadsheetListHeaderUIPlugin extends OdooUIPlugin {
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_PIVOT":
            case "UPDATE_PIVOT":
                this._freezeListHeadersUsedByPivot(cmd.pivot);
                break;
        }
    }

    /**
     * Freeze the current labels of list headers used by a spreadsheet pivot so it
     * keeps working the same way in every language.
     */
    _freezeListHeadersUsedByPivot(pivot) {
        const dataSet = pivot.type === "SPREADSHEET" ? pivot.dataSet : undefined;
        if (!dataSet || !localization.multiLang) {
            return;
        }

        const columnsByList = this._getListFieldNamesInPivotZone(dataSet);
        if (!columnsByList.size) {
            return;
        }

        let hasUpdatedAnyList = false;
        for (const [listId, fieldNames] of columnsByList) {
            const definition = this.getters.getListDefinition(listId);
            let hasUpdatedCurrentList = false;
            const columns = definition.columns.map((column) => {
                if (!fieldNames.has(column.name) || column.string) {
                    return column;
                }
                const displayName = this.getters.getListHeaderValue(listId, column.name);
                if (!displayName) {
                    return column;
                }
                hasUpdatedCurrentList = true;
                return {
                    ...column,
                    string: displayName,
                };
            });
            if (!hasUpdatedCurrentList) {
                continue;
            }
            hasUpdatedAnyList = true;
            this.dispatch("UPDATE_ODOO_LIST", {
                listId,
                list: {
                    ...definition,
                    columns,
                },
            });
        }

        if (hasUpdatedAnyList) {
            this.ui.notifyUI({
                type: "info",
                sticky: false,
                text: _t("Some list column titles have been locked to avoid translation issues."),
            });
        }
    }

    /**
     * Find which list headers are actually used by the pivot, so we only lock
     * the labels that could make this pivot unstable across languages.
     */
    _getListFieldNamesInPivotZone(dataSet) {
        const { sheetId, zone } = dataSet;
        const columnsByList = new Map();

        for (let col = zone.left; col <= zone.right; col++) {
            const position = { sheetId, col, row: zone.top };
            const listId = this.getters.getListIdFromPosition(position);
            if (!listId) {
                continue;
            }

            const cell = this.getters.getCorrespondingFormulaCell(position);
            const listFunction = getFirstListFunction(cell.compiledFormula, this.getters);
            if (
                !listFunction ||
                !["ODOO.LIST", "ODOO.LIST.HEADER"].includes(listFunction.functionName)
            ) {
                continue;
            }

            const fieldName = this.getters.getListFieldFromPosition(position)?.name;
            if (!fieldName) {
                continue;
            }

            if (!columnsByList.has(listId)) {
                columnsByList.set(listId, new Set());
            }
            columnsByList.get(listId).add(fieldName);
        }

        return columnsByList;
    }
}
