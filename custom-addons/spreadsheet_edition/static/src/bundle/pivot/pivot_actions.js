/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { PivotDialog } from "./spreadsheet_pivot_dialog";

export const REINSERT_PIVOT_CHILDREN = (env) =>
    env.model.getters.getPivotIds().map((pivotId, index) => ({
        id: `reinsert_pivot_${pivotId}`,
        name: env.model.getters.getPivotDisplayName(pivotId),
        sequence: index,
        execute: async (env) => {
            const dataSource = env.model.getters.getPivotDataSource(pivotId);
            const model = await dataSource.copyModelWithOriginalDomain();
            const table = model.getTableStructure().export();
            const zone = env.model.getters.getSelectedZone();
            env.model.dispatch("RE_INSERT_PIVOT", {
                id: pivotId,
                col: zone.left,
                row: zone.top,
                sheetId: env.model.getters.getActiveSheetId(),
                table,
            });
            env.model.dispatch("REFRESH_PIVOT", { id: pivotId });
        },
    }));

export const INSERT_PIVOT_CELL_CHILDREN = (env) =>
    env.model.getters.getPivotIds().map((pivotId, index) => ({
        id: `insert_pivot_cell_${pivotId}`,
        name: env.model.getters.getPivotDisplayName(pivotId),
        sequence: index,
        execute: async (env) => {
            env.model.dispatch("REFRESH_PIVOT", { id: pivotId });
            const { sheetId, col, row } = env.model.getters.getActivePosition();
            await env.model.getters.getAsyncPivotDataSource(pivotId);
            // make sure all cells are evaluated
            for (const sheetId of env.model.getters.getSheetIds()) {
                env.model.getters.getEvaluatedCells(sheetId);
            }
            const insertPivotValueCallback = (formula) => {
                env.model.dispatch("UPDATE_CELL", {
                    sheetId,
                    col,
                    row,
                    content: formula,
                });
            };

            const getMissingValueDialogTitle = () => {
                const title = _t("Insert pivot cell");
                const pivotTitle = getPivotTitle();
                if (pivotTitle) {
                    return `${title} - ${pivotTitle}`;
                }
                return title;
            };

            const getPivotTitle = () => {
                if (pivotId) {
                    return env.model.getters.getPivotDisplayName(pivotId);
                }
                return "";
            };

            env.services.dialog.add(PivotDialog, {
                title: getMissingValueDialogTitle(),
                pivotId,
                insertPivotValueCallback,
                getters: env.model.getters,
            });
        },
    }));
