import { AbstractCellClipboardHandler, helpers } from "@odoo/o-spreadsheet";

const { isInside } = helpers;

export class CellThreadsClipboardHandler extends AbstractCellClipboardHandler {
    copy(data) {
        if (!data.zones.length) {
            return;
        }

        const zones = data.zones;
        const sheetId = this.getters.getActiveSheetId();
        const sheetThreads = this.getters.getSpreadsheetThreads([sheetId]);
        // we only support cut which means one 1 zone - no need to fetch the entire planet
        const threads = sheetThreads.filter((thread) => isInside(thread.col, thread.row, zones[0]));
        return { threads, zones };
    }

    /**
     * Paste the clipboard content in the given target
     */
    paste(target, content, options) {
        if (!content.threads?.length || !target.zones.length) {
            return;
        }
        if (options?.isCutOperation && !options?.pasteOption) {
            const zones = target.zones;
            const sheetId = this.getters.getActiveSheetId();
            this.pasteFromCut(sheetId, zones, content);
        }
    }

    pasteFromCut(sheetId, target, content) {
        const cutZone = content.zones[0];

        const deltaCol = target[0].left - cutZone.left;
        const deltaRow = target[0].top - cutZone.top;
        for (const thread of content.threads) {
            this.dispatch("DELETE_COMMENT_THREAD", {
                sheetId: thread.sheetId,
                col: thread.col,
                row: thread.row,
                threadId: thread.threadId,
            });

            this.dispatch("ADD_COMMENT_THREAD", {
                sheetId,
                col: thread.col + deltaCol,
                row: thread.row + deltaRow,
                threadId: thread.threadId,
            });
        }
    }
}
