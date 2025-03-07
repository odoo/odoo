import { SEE_RECORD_LIST, SEE_RECORD_LIST_VISIBLE } from "@spreadsheet/list/list_actions";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

const { clickableCellRegistry } = spreadsheet.registries;
const { setColorAlpha } = spreadsheet.helpers;

clickableCellRegistry.add("list", {
    condition: SEE_RECORD_LIST_VISIBLE,
    execute: SEE_RECORD_LIST,
    hoverStyle(position, getters) {
        const { col, row } = position;
        let rightest = col;
        let leftest = col;
        const listId = getters.getListIdFromPosition(position);
        while (
            SEE_RECORD_LIST_VISIBLE({ ...position, col: leftest - 1 }, getters) &&
            getters.getListIdFromPosition({ ...position, col: leftest - 1 }) === listId
        ) {
            leftest--;
        }
        while (
            SEE_RECORD_LIST_VISIBLE({ ...position, col: rightest + 1 }, getters) &&
            getters.getListIdFromPosition({ ...position, col: rightest + 1 }) === listId
        ) {
            rightest++;
        }
        return [
            {
                zone: {
                    top: row,
                    bottom: row,
                    right: rightest,
                    left: leftest,
                },
                style: {
                    fillColor: setColorAlpha("#000000", 0.05),
                },
            },
        ];
    },
    sequence: 10,
    title: _t("Open record"),
});
