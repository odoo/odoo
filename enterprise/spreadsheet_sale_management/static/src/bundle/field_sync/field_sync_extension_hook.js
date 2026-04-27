import { registries, coreTypes, stores } from "@odoo/o-spreadsheet";
import { onMounted } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { sum } from "@spreadsheet/helpers/helpers";
import { addToRegistryWithCleanup } from "@spreadsheet_edition/bundle/helpers/misc";

import { FieldSyncCorePlugin } from "./model/field_sync_core_plugin";
import { FieldSyncUIPlugin } from "./model/field_sync_ui_plugin";
import { FieldSyncSidePanel } from "./side_panel/field_sync_side_panel";
import { FieldSyncClipboardHandler } from "./model/field_sync_clipboard_handler";
import { FieldSyncHighlightStore } from "./field_sync_highlight_store";

const { useStoreProvider } = stores;
const {
    cellMenuRegistry,
    clipboardHandlersRegistries,
    corePluginRegistry,
    featurePluginRegistry,
    inverseCommandRegistry,
    topbarMenuRegistry,
    sidePanelRegistry,
} = registries;

coreTypes.add("ADD_FIELD_SYNC").add("DELETE_FIELD_SYNCS");

/**
 * Adds the spreadsheet field sync plugins and menus
 * and removes them when the action is left
 */
export function useSpreadsheetFieldSyncStore() {
    const stores = useStoreProvider();
    onMounted(() => {
        stores.instantiate(FieldSyncHighlightStore);
    });
}

export function addSpreadsheetFieldSyncExtensionWithCleanUp(cleanUpHook = () => {}) {
    // plugins
    addToRegistryWithCleanup(
        cleanUpHook,
        featurePluginRegistry,
        "field_sync_ui_plugin",
        FieldSyncUIPlugin
    );
    addToRegistryWithCleanup(
        cleanUpHook,
        corePluginRegistry,
        "field_sync_plugin",
        FieldSyncCorePlugin
    );

    // menus
    const addMenuAction = {
        icon: "spreadsheet_sale_management.OdooLogo",
        name: (env) => {
            const position = env.model.getters.getActivePosition();
            const fieldSync = env.model.getters.getFieldSync(position);
            return fieldSync ? _t("Edit sync") : _t("Sync with field");
        },
        execute: (env) => {
            const position = env.model.getters.getActivePosition();
            const fieldSync = env.model.getters.getFieldSync(position);
            const list = env.model.getters.getMainSaleOrderLineList();
            const isNewlyCreate = Boolean(!fieldSync && list);
            if (isNewlyCreate) {
                env.model.dispatch("ADD_FIELD_SYNC", {
                    sheetId: position.sheetId,
                    col: position.col,
                    row: position.row,
                    listId: list.id,
                    indexInList: 0,
                    fieldName: "product_uom_qty",
                });
            }
            env.openSidePanel("FieldSyncSidePanel", { isNewlyCreate });
        },
        sequence: 2000,
    };
    addToRegistryWithCleanup(cleanUpHook, cellMenuRegistry, "add_field_sync", addMenuAction);
    topbarMenuRegistry.addChild("add_field_sync", ["insert"], addMenuAction, { force: true });
    cleanUpHook(() => {
        const menuIndex = topbarMenuRegistry.content.insert.children.findIndex(
            (menu) => menu.id === "add_field_sync"
        );
        topbarMenuRegistry.content.insert.children.splice(menuIndex, 1);
    });

    const deleteMenuAction = {
        icon: "o-spreadsheet-Icon.TRASH",
        isVisible: (env) => {
            const zones = env.model.getters.getSelectedZones();
            const sheetId = env.model.getters.getActiveSheetId();
            return zones.some((zone) => env.model.getters.getFieldSyncs(sheetId, zone).length);
        },
        name: (env) => {
            const zones = env.model.getters.getSelectedZones();
            const sheetId = env.model.getters.getActiveSheetId();
            const fieldSyncsCount = sum(
                zones.map((zone) => env.model.getters.getFieldSyncs(sheetId, zone).length)
            );
            if (fieldSyncsCount === 1) {
                return _t("Delete field syncing");
            }
            return _t("Delete field syncing");
        },
        execute: (env) => {
            const zones = env.model.getters.getSelectedZones();
            const sheetId = env.model.getters.getActiveSheetId();
            for (const zone of zones) {
                env.model.dispatch("DELETE_FIELD_SYNCS", { sheetId, zone });
            }
        },
        sequence: 2010,
    };
    addToRegistryWithCleanup(cleanUpHook, cellMenuRegistry, "delete_field_syncs", deleteMenuAction);
    topbarMenuRegistry.addChild(
        "delete_field_syncs",
        ["edit", "delete"],
        {
            ...deleteMenuAction,
            icon: undefined,
        },
        { force: true }
    );
    cleanUpHook(() => {
        const editAction = topbarMenuRegistry.content.edit;
        const deleteIndex = editAction.children.findIndex((menu) => menu.id === "delete");
        const deleteFieldSyncIndex = editAction.children[deleteIndex].children.findIndex(
            (menu) => menu.id === "delete_field_syncs"
        );
        editAction.children[deleteIndex].children.splice(deleteFieldSyncIndex, 1);
    });

    // side panel
    addToRegistryWithCleanup(cleanUpHook, sidePanelRegistry, "FieldSyncSidePanel", {
        title: _t("Field syncing"),
        Body: FieldSyncSidePanel,
        computeState(getters, initialProps) {
            const activePosition = getters.getActivePosition();
            const { sheetId, col, row } = activePosition;
            const fieldSync = getters.getFieldSync(activePosition);
            return {
                isOpen: !!fieldSync,
                props: { ...initialProps, position: activePosition },
                key: `${sheetId}-${col}-${row}`,
            };
        },
    });

    // clipboard
    addToRegistryWithCleanup(
        cleanUpHook,
        clipboardHandlersRegistries.cellHandlers,
        "fieldSync",
        FieldSyncClipboardHandler
    );

    // misc
    const identity = (cmd) => cmd;
    addToRegistryWithCleanup(cleanUpHook, inverseCommandRegistry, "ADD_FIELD_SYNC", identity);
    addToRegistryWithCleanup(cleanUpHook, inverseCommandRegistry, "DELETE_FIELD_SYNCS", identity);
}
