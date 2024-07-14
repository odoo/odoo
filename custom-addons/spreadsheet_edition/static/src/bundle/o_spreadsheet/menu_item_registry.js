/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import * as spreadsheet from "@odoo/o-spreadsheet";
import { REINSERT_LIST_CHILDREN } from "../list/list_actions";
import { INSERT_PIVOT_CELL_CHILDREN, REINSERT_PIVOT_CHILDREN } from "../pivot/pivot_actions";
const { topbarMenuRegistry } = spreadsheet.registries;

//--------------------------------------------------------------------------
// Spreadsheet context menu items
//--------------------------------------------------------------------------

topbarMenuRegistry.addChild("new_sheet", ["file"], {
    name: _t("New"),
    sequence: 10,
    isVisible: (env) => env.newSpreadsheet,
    execute: (env) => env.newSpreadsheet(),
    icon: "o-spreadsheet-Icon.NEW",
});
topbarMenuRegistry.addChild("make_copy", ["file"], {
    name: _t("Make a copy"),
    sequence: 20,
    isVisible: (env) => env.makeCopy,
    execute: (env) => env.makeCopy(),
    icon: "o-spreadsheet-Icon.COPY_FILE",
});
topbarMenuRegistry.addChild("save_as_template", ["file"], {
    name: _t("Save as template"),
    sequence: 40,
    isVisible: (env) => env.saveAsTemplate,
    execute: (env) => env.saveAsTemplate(),
    icon: "o-spreadsheet-Icon.SAVE",
});
topbarMenuRegistry.addChild("download", ["file"], {
    name: _t("Download"),
    sequence: 50,
    isVisible: (env) => env.download,
    execute: (env) => env.download(),
    isReadonlyAllowed: true,
    icon: "o-spreadsheet-Icon.DOWNLOAD",
});

topbarMenuRegistry.addChild("clear_history", ["file"], {
    name: _t("Snapshot"),
    sequence: 60,
    isVisible: (env) => env.debug,
    execute: (env) => {
        env.model.session.snapshot(env.model.exportData());
        env.model.garbageCollectExternalResources();
        window.location.reload();
    },
    icon: "o-spreadsheet-Icon.CAMERA",
});

topbarMenuRegistry.addChild("download_as_json", ["file"], {
    name: _t("Download as JSON"),
    sequence: 70,
    isVisible: (env) => env.debug && env.downloadAsJson,
    execute: (env) => env.downloadAsJson(),
    isReadonlyAllowed: true,
    icon: "o-spreadsheet-Icon.DOWNLOAD_AS_JSON",
});

topbarMenuRegistry.addChild("data_sources_data", ["data"], (env) => {
    let sequence = 1000;
    const pivots_items = env.model.getters.getPivotIds().map((pivotId, index) => ({
        id: `item_pivot_${pivotId}`,
        name: env.model.getters.getPivotDisplayName(pivotId),
        sequence: sequence++,
        execute: (env) => {
            env.model.dispatch("SELECT_PIVOT", { pivotId: pivotId });
            env.openSidePanel("PIVOT_PROPERTIES_PANEL", {});
        },
        icon: "o-spreadsheet-Icon.PIVOT",
        separator: index === env.model.getters.getPivotIds().length - 1,
    }));
    const lists_items = env.model.getters.getListIds().map((listId, index) => {
        return {
            id: `item_list_${listId}`,
            name: env.model.getters.getListDisplayName(listId),
            sequence: sequence++,
            execute: (env) => {
                env.model.dispatch("SELECT_ODOO_LIST", { listId: listId });
                env.openSidePanel("LIST_PROPERTIES_PANEL", {});
            },
            icon: "o-spreadsheet-Icon.ODOO_LIST",
            separator: index === env.model.getters.getListIds().length - 1,
        };
    });
    const charts_items = env.model.getters.getOdooChartIds().map((chartId, index) => {
        return {
            id: `item_chart_${chartId}`,
            name: env.model.getters.getOdooChartDisplayName(chartId),
            sequence: sequence++,
            execute: (env) => {
                env.model.dispatch("SELECT_FIGURE", { id: chartId });
                env.openSidePanel("ChartPanel");
            },
            icon: "o-spreadsheet-Icon.INSERT_CHART",
            separator: index === env.model.getters.getOdooChartIds().length - 1,
        };
    });
    return pivots_items
        .concat(lists_items)
        .concat(charts_items)
        .concat([
            {
                id: "refresh_all_data",
                name: _t("Refresh all data"),
                sequence: sequence++,
                execute: (env) => {
                    env.model.dispatch("REFRESH_ALL_DATA_SOURCES");
                },
                separator: true,
                icon: "o-spreadsheet-Icon.REFRESH_DATA",
            },
        ]);
});

const insertPivotMenu = {
    name: _t("Insert pivot"),
    sequence: 1020,
    icon: "o-spreadsheet-Icon.INSERT_PIVOT",
    isVisible: (env) => env.model.getters.getPivotIds().length,
};

const reInsertPivotMenu = {
    id: "reinsert_pivot",
    name: _t("Re-insert pivot"),
    sequence: 1,
    children: [REINSERT_PIVOT_CHILDREN],
    isVisible: (env) => env.model.getters.getPivotIds().length,
};

const insertPivotCellMenu = {
    id: "insert_pivot_cell",
    name: _t("Insert pivot cell"),
    sequence: 2,
    children: [INSERT_PIVOT_CELL_CHILDREN],
    isVisible: (env) => env.model.getters.getPivotIds().length,
};

const reInsertListMenu = {
    id: "reinsert_list",
    name: _t("Re-insert list"),
    sequence: 1021,
    children: [REINSERT_LIST_CHILDREN],
    isVisible: (env) => env.model.getters.getListIds().length,
    icon: "o-spreadsheet-Icon.INSERT_LIST",
};

const printMenu = {
    name: _t("Print"),
    sequence: 60,
    isVisible: (env) => env.print,
    execute: (env) => env.print(),
    icon: "o-spreadsheet-Icon.PRINT",
};

topbarMenuRegistry.addChild("print", ["file"], printMenu);

topbarMenuRegistry.addChild("insert_pivot", ["insert"], insertPivotMenu);
topbarMenuRegistry.addChild("reinsert_pivot", ["insert", "insert_pivot"], reInsertPivotMenu);
topbarMenuRegistry.addChild("insert_pivot_cell", ["insert", "insert_pivot"], insertPivotCellMenu);
topbarMenuRegistry.addChild("reinsert_list", ["insert"], reInsertListMenu);

topbarMenuRegistry.addChild("insert_pivot", ["data"], insertPivotMenu);
topbarMenuRegistry.addChild("reinsert_list", ["data"], reInsertListMenu);
