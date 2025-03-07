import * as spreadsheet from "@odoo/o-spreadsheet";
import { _t } from "@web/core/l10n/translation";

import {
    SEE_RECORDS_PIVOT,
    SEE_RECORDS_PIVOT_VISIBLE,
    SET_FILTER_MATCHING,
    SET_FILTER_MATCHING_CONDITION,
} from "@spreadsheet/pivot/pivot_actions";

const { clickableCellRegistry } = spreadsheet.registries;
const { setColorAlpha, positionToZone } = spreadsheet.helpers;

clickableCellRegistry.add("pivot", {
    condition: SEE_RECORDS_PIVOT_VISIBLE,
    execute: SEE_RECORDS_PIVOT,
    hoverStyle(position, getters) {
        const { col, row } = position;
        let rightest = col;
        let leftest = col;
        const pivotId = getters.getPivotIdFromPosition(position);
        while (
            SEE_RECORDS_PIVOT_VISIBLE({ ...position, col: leftest - 1 }, getters) &&
            getters.getPivotIdFromPosition({ ...position, col: leftest - 1 }) === pivotId
        ) {
            leftest--;
        }
        while (
            SEE_RECORDS_PIVOT_VISIBLE({ ...position, col: rightest + 1 }, getters) &&
            getters.getPivotIdFromPosition({ ...position, col: rightest + 1 }) === pivotId
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
        const { col, row } = position;
        let rightest = col;
        const pivotId = getters.getPivotIdFromPosition(position);
        while (
            SEE_RECORDS_PIVOT_VISIBLE({ ...position, col: rightest + 1 }, getters) &&
            getters.getPivotIdFromPosition({ ...position, col: rightest + 1 }) === pivotId
        ) {
            rightest++;
        }
        return [
            {
                zone: {
                    top: row,
                    bottom: row,
                    right: rightest,
                    left: col,
                },
                style: {
                    fillColor: setColorAlpha("#000000", 0.05),
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
