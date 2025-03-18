import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

import {
    SEE_RECORDS_PIVOT,
    SEE_RECORDS_PIVOT_VISIBLE,
    SET_FILTER_MATCHING,
    SET_FILTER_MATCHING_CONDITION,
    hasPivotFunction,
} from "@spreadsheet/pivot/pivot_actions";
import { HOVER_CELL_LIGHT_GREY } from "../constants";

const { clickableCellRegistry } = spreadsheet.registries;
const { setColorAlpha, positionToZone } = spreadsheet.helpers;

clickableCellRegistry.add("pivot", {
    condition: SEE_RECORDS_PIVOT_VISIBLE,
    execute: SEE_RECORDS_PIVOT,
    hoverStyle(position, getters) {
        const { row } = position;
        const pivotId = getters.getPivotIdFromPosition(position);
        const { rightest, leftest } = extendPivotLine(getters, pivotId, position);
        return [
            {
                zone: {
                    top: row,
                    bottom: row,
                    right: rightest,
                    left: leftest,
                },
                style: {
                    fillColor: HOVER_CELL_LIGHT_GREY,
                },
            },
            {
                zone: positionToZone(position),
                style: {
                    textColor: "#017E84",
                },
            },
        ];
    },
    title: _t("See records"),
    sequence: 3,
});

clickableCellRegistry.add("pivot_set_filter_matching", {
    condition: SET_FILTER_MATCHING_CONDITION,
    execute: SET_FILTER_MATCHING,
    hoverStyle(position, getters) {
        const { row } = position;
        const pivotId = getters.getPivotIdFromPosition(position);
        const { rightest, leftest } = extendPivotLine(getters, pivotId, position);
        return [
            {
                zone: {
                    top: row,
                    bottom: row,
                    right: rightest,
                    left: leftest,
                },
                style: {
                    fillColor: HOVER_CELL_LIGHT_GREY,
                },
            },
            {
                zone: positionToZone(position),
                style: {
                    fillColor: setColorAlpha("#000000", 0.1),
                },
            },
        ];
    },
    title: _t("Filter on this value"),
    sequence: 2,
});

function extendPivotLine(getters, pivotId, position) {
    const { col } = position;
    let rightest = col;
    let leftest = col;
    while (
        hasPivotFunction({ ...position, col: leftest - 1 }, getters) &&
        getters.getPivotIdFromPosition({ ...position, col: leftest - 1 }) === pivotId
    ) {
        leftest--;
    }
    while (
        hasPivotFunction({ ...position, col: rightest + 1 }, getters) &&
        getters.getPivotIdFromPosition({ ...position, col: rightest + 1 }) === pivotId
    ) {
        rightest++;
    }
    return { rightest, leftest };
}
