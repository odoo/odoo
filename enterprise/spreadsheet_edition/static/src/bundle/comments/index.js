import { _t } from "@web/core/l10n/translation";

import { CellThreadsPlugin } from "./plugins/comments_core_plugin";

import { coreTypes, registries, stores, addRenderingLayer } from "@odoo/o-spreadsheet";
import { CommentThreadsSidePanel } from "./side_panel/comment_threads_side_panel";
import { CellThreadPopover } from "./components/cell_thread_popover";
import { CommentsStore } from "./comments_store";
import { CellThreadsClipboardHandler } from "./clipboard_handler";

const { CellPopoverStore } = stores;

const {
    cellPopoverRegistry,
    cellMenuRegistry,
    corePluginRegistry,
    clipboardHandlersRegistries,
    inverseCommandRegistry,
    topbarMenuRegistry,
    sidePanelRegistry,
    otRegistry,
} = registries;

corePluginRegistry.add("odooCellThreadsPlugin", CellThreadsPlugin);
clipboardHandlersRegistries.cellHandlers.add("commentThreads", CellThreadsClipboardHandler);

function identity(cmd) {
    return [cmd];
}

coreTypes.add("ADD_COMMENT_THREAD");
coreTypes.add("DELETE_COMMENT_THREAD");
coreTypes.add("EDIT_COMMENT_THREAD");

inverseCommandRegistry.add("ADD_COMMENT_THREAD", identity);
inverseCommandRegistry.add("DELETE_COMMENT_THREAD", identity);
inverseCommandRegistry.add("EDIT_COMMENT_THREAD", identity);

otRegistry.addTransformation(
    "DELETE_COMMENT_THREAD",
    ["ADD_COMMENT_THREAD", "EDIT_COMMENT_THREAD"],
    (toTransform, executed) => {
        if (toTransform.threadId === executed.threadId) {
            return undefined;
        }
        return toTransform;
    }
);

cellPopoverRegistry.add("OdooCellComment", {
    onOpen: (position, getters) => {
        if (getters.isReadonly()) {
            return;
        }
        const sheetId = getters.getActiveSheetId();
        const thread =
            getters
                .getCellThreads({ sheetId, ...position })
                ?.filter((thread) => !thread.isResolved)
                ?.at(-1) || {};
        return {
            Component: CellThreadPopover,
            cellCorner: "TopRight",
            props: {
                threadId: thread.threadId,
                position,
                isInteractive: true,
            },
            isOpen: true,
            positioning: "TopRight",
        };
    },
    onHover: (position, getters) => {
        if (getters.isReadonly()) {
            return;
        }
        const sheetId = getters.getActiveSheetId();
        const threads = getters
            .getCellThreads({ sheetId, ...position })
            ?.filter((thread) => !thread.isResolved);
        if (!threads || !threads.length) {
            return undefined;
        }
        return {
            Component: CellThreadPopover,
            cellCorner: "TopRight",
            props: {
                threadId: threads.at(-1).threadId,
                position,
                isInteractive: false,
            },
            isOpen: true,
            positioning: "TopRight",
        };
    },
});

const INSERT_COMMENT_ACTION = {
    name: _t("Insert comment"),
    isVisible: (env) => env.insertThreadInSheet && env.getStore(CommentsStore).areCommentsActive,
    execute: async (env) => {
        const { col, row } = env.model.getters.getActivePosition();
        env.getStore(CellPopoverStore).open({ col, row }, "OdooCellComment");
    },
    icon: "o-spreadsheet-Icon.COMMENTS",
};

cellMenuRegistry.add("insert_comment", {
    ...INSERT_COMMENT_ACTION,
    sequence: 150,
    separator: true,
});

topbarMenuRegistry.addChild("insert_comment", ["insert"], {
    ...INSERT_COMMENT_ACTION,
    sequence: 150,
});

topbarMenuRegistry.addChild("show_comments", ["view", "show"], {
    name: _t("Comments"),
    sequence: 1500,
    execute: (env) => env.getStore(CommentsStore).toggleComments(),
    isActive: (env) => env.getStore(CommentsStore).areCommentsActive,
    isVisible: (env) => env.insertThreadInSheet,
});

topbarMenuRegistry.addChild("view_comments", ["view"], {
    name: _t("All Comments"),
    sequence: 1500,
    execute: (env) => env.openSidePanel("Comments"),
    icon: "o-spreadsheet-Icon.COMMENTS",
    isVisible: (env) => env.insertThreadInSheet,
});

sidePanelRegistry.add("Comments", {
    title: _t("Comments"),
    Body: CommentThreadsSidePanel,
});

// after the grid but before the highlights
addRenderingLayer("Triangle", 0.5);
