// @ts-check

import { helpers } from "@odoo/o-spreadsheet";
import { OdooCorePlugin } from "@spreadsheet/plugins";

const { toXC, toCartesian, expandZoneOnInsertion, reduceZoneOnDeletion } = helpers;

/**
 * @typedef {import("@spreadsheet").UID} UID
 *
 * @typedef ThreadInfo
 * @property {number} col
 * @property {number} row
 * @property {string} sheetId
 * @property {number} threadId
 * @property {boolean} isResolved
 *
 * @typedef ThreadEntry
 * @property {number} threadId
 * @property {boolean} isResolved
 * @property {number} col
 * @property {number} row
 *
 */

export class CellThreadsPlugin extends OdooCorePlugin {
    static getters = [
        "getCellThreads",
        "getThreadInfosInSheet",
        "getThreadInfo",
        "getSpreadsheetThreads",
    ];

    /**
     * @readonly
     * @type {Object<UID, Object<string, Array<ThreadEntry>>>}
     */
    cellThreads = {};

    /**
     * @param {import("@spreadsheet").AllCoreCommand} cmd
     */
    handle(cmd) {
        switch (cmd.type) {
            case "ADD_COMMENT_THREAD":
                {
                    const { sheetId, col, row, threadId } = cmd;
                    const xc = toXC(col, row);
                    if (!this.cellThreads[sheetId]) {
                        this.cellThreads[sheetId] = {};
                    }
                    const threads = this.cellThreads[sheetId]?.[xc] || [];
                    const newThreads = [...threads, { threadId, isResolved: false }];
                    this.history.update("cellThreads", sheetId, xc, newThreads);
                }
                break;
            case "EDIT_COMMENT_THREAD":
                {
                    const { threadId, isResolved, sheetId, col, row } = cmd;
                    const xc = toXC(col, row);
                    const threads = this.cellThreads[sheetId][xc];
                    const newThreads = threads.map((thread) =>
                        thread.threadId === threadId ? { ...thread, isResolved } : thread
                    );
                    this.history.update("cellThreads", sheetId, xc, newThreads);
                }
                break;
            case "DELETE_COMMENT_THREAD": {
                const { threadId, sheetId, col, row } = cmd;
                const xc = toXC(col, row);
                const currentThreadIds = this.cellThreads[sheetId]?.[xc] || [];
                const newThreadIds = currentThreadIds.filter(
                    (thread) => thread.threadId !== threadId
                );
                this.history.update("cellThreads", sheetId, xc, newThreadIds);
                break;
            }
            case "ADD_COLUMNS_ROWS":
                this.onAddColumnsRows(cmd);
                break;
            case "REMOVE_COLUMNS_ROWS":
                this.onDeleteColumnsRows(cmd);
                break;
            case "CREATE_SHEET":
                this.history.update("cellThreads", cmd.sheetId, {});
                break;
            case "DUPLICATE_SHEET":
                this.history.update("cellThreads", cmd.sheetIdTo, {});
                break;
            case "DELETE_SHEET":
                {
                    const threads = { ...this.cellThreads };
                    delete threads[cmd.sheetId];
                    this.history.update("cellThreads", threads);
                }
                break;
        }
    }

    /**
     * @param {number} threadId
     * @returns {ThreadInfo}
     */
    getThreadInfo(threadId) {
        for (const [sheetId, threadXcs] of Object.entries(this.cellThreads)) {
            for (const [xc, xcThreads] of Object.entries(threadXcs)) {
                const thread = xcThreads?.find((thread) => thread.threadId === threadId);
                if (thread) {
                    return { sheetId, ...toCartesian(xc), ...thread };
                }
            }
        }
    }

    /**
     * @returns {Array<number> | undefined} threadIds
     */
    getCellThreads({ sheetId, col, row }) {
        return (this.cellThreads[sheetId] || {})[toXC(col, row)];
    }

    /**
     * @param {string} sheetId
     * @returns {Array<ThreadInfo>}
     */
    getThreadInfosInSheet(sheetId) {
        return this.getSpreadsheetThreads([sheetId]);
    }

    /**
     *
     * @param {Array<UID>} sheetIds
     * @returns {Array<ThreadInfo>}
     */
    getSpreadsheetThreads(sheetIds) {
        const spreadsheetThreads = [];
        for (const sheetId of sheetIds) {
            const sheetThreads = this.cellThreads[sheetId];
            if (sheetThreads) {
                for (const [xc, threads] of Object.entries(sheetThreads)) {
                    const { col, row } = toCartesian(xc);
                    for (const thread of threads) {
                        spreadsheetThreads.push({ sheetId, col, row, ...thread });
                    }
                }
            }
        }
        return spreadsheetThreads;
    }
    // ---------------------------------------------------------------------------
    // Import/Export
    // ---------------------------------------------------------------------------

    export(data) {
        for (const sheet of data.sheets) {
            sheet.comments = this.cellThreads[sheet.id];
        }
    }

    import(data) {
        for (const sheet of data.sheets) {
            this.cellThreads[sheet.id] = {};
            if (sheet.comments) {
                this.cellThreads[sheet.id] = sheet.comments;
            }
        }
    }

    onAddColumnsRows({ sheetId, base, dimension, position, quantity }) {
        const newCellThreadIds = {};
        for (const xc of Object.keys(this.cellThreads[sheetId])) {
            const { col, row } = toCartesian(xc);
            const zone = { left: col, right: col, top: row, bottom: row };
            const newZone = expandZoneOnInsertion(
                zone,
                dimension === "COL" ? "left" : "top",
                base,
                position,
                quantity
            );
            if (newZone) {
                const { left, top } = newZone;
                const threads = this.cellThreads[sheetId][xc];
                const newXc = toXC(left, top);
                newCellThreadIds[newXc] = threads;
            }
        }
        this.history.update("cellThreads", sheetId, newCellThreadIds);
    }

    onDeleteColumnsRows({ sheetId, elements, dimension }) {
        const newCellThreadIds = {};
        for (const xc of Object.keys(this.cellThreads[sheetId])) {
            const { col, row } = toCartesian(xc);
            const zone = { left: col, right: col, top: row, bottom: row };
            const newZone = reduceZoneOnDeletion(
                zone,
                dimension === "COL" ? "left" : "top",
                elements
            );
            if (newZone) {
                const { left, top } = newZone;
                const threads = this.cellThreads[sheetId][xc];
                const newXc = toXC(left, top);
                newCellThreadIds[newXc] = threads;
            }
        }
        this.history.update("cellThreads", sheetId, newCellThreadIds);
    }
}
