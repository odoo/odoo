// @ts-check
/** @odoo-module native */

import { onWillDestroy, useExternalListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/core/browser/hotkeys";

/**
 * @typedef {object} RecordSelectionContext
 * @property {() => any[]} getRecords
 * @property {(record: any) => void} [rangeToggle]
 * @property {(available: boolean) => void} [onSelectionModifier]
 */

/**
 * @param {any[]} records
 * @param {any} record
 * @returns {number}
 */
function indexOfRecord(records, record) {
    if (!record) {
        return -1;
    }
    return records.findIndex((r) => r.id === record.id);
}

class RecordSelection {
    /** @type {any} */
    lastCheckedRecord = undefined;
    shiftKeyMode = false;
    /** @type {any} */
    shiftKeyedRecord = undefined;

    /** @param {RecordSelectionContext} ctx */
    constructor(ctx) {
        this.ctx = ctx;
    }

    /** @returns {boolean} */
    isAnchorPresent() {
        return indexOfRecord(this.ctx.getRecords(), this.lastCheckedRecord) !== -1;
    }

    /**
     * @param {any} record
     * @param {boolean} [isRange]
     */
    toggleSelection(record, isRange = false) {
        if (isRange && this.isAnchorPresent()) {
            (this.ctx.rangeToggle || ((r) => this.toggleRangeSelection(r)))(record);
        } else {
            record.toggleSelection();
        }
        this.lastCheckedRecord = record;
    }

    /** @param {any} record */
    toggleRangeSelection(record) {
        const records = this.ctx.getRecords();
        const lastCheckedRecordIndex = indexOfRecord(records, this.lastCheckedRecord);
        if (lastCheckedRecordIndex === -1) {
            this.lastCheckedRecord = record;
            record.toggleSelection(!record.selected);
            return;
        }
        const recordIndex = indexOfRecord(records, record);
        const start = Math.min(recordIndex, lastCheckedRecordIndex);
        const end = Math.max(recordIndex, lastCheckedRecordIndex);
        const selected = !record.selected;
        for (let i = start; i <= end; i++) {
            records[i].toggleSelection(selected);
        }
    }

    /**
     * @param {any} record
     * @param {"up" | "down"} direction
     * @returns {boolean}
     */
    expandCheckboxes(record, direction) {
        const records = this.ctx.getRecords();
        if (!record && direction === "down") {
            const defaultRecord = records[0];
            if (!defaultRecord) {
                return false;
            }
            this.shiftKeyedRecord = defaultRecord;
            defaultRecord.toggleSelection(true);
            return true;
        }
        const recordIndex = indexOfRecord(records, record);
        const shiftKeyedRecordIndex = indexOfRecord(records, this.shiftKeyedRecord);
        let nextRecord;
        let isExpanding;
        switch (direction) {
            case "up":
                if (recordIndex <= 0) {
                    return false;
                }
                nextRecord = records[recordIndex - 1];
                isExpanding = shiftKeyedRecordIndex > recordIndex - 1;
                break;
            case "down":
                if (recordIndex === records.length - 1) {
                    return false;
                }
                nextRecord = records[recordIndex + 1];
                isExpanding = shiftKeyedRecordIndex < recordIndex + 1;
                break;
            default:
                return false;
        }
        if (isExpanding) {
            record.toggleSelection(true);
            nextRecord.toggleSelection(true);
        } else {
            record.toggleSelection(false);
        }
        return true;
    }
}

/**
 * @param {RecordSelectionContext} ctx
 * @returns {RecordSelection}
 */
export function useRecordSelection(ctx) {
    const { onSelectionModifier } = ctx;
    const self = new RecordSelection(ctx);

    useExternalListener(window, "keydown", (ev) => {
        self.shiftKeyMode = ev.shiftKey;
        if (ev.key === "Alt") {
            onSelectionModifier?.(true);
        }
    });
    useExternalListener(window, "keyup", (ev) => {
        self.shiftKeyMode = ev.shiftKey;
        if (getActiveHotkey(ev) === "shift") {
            self.shiftKeyedRecord = undefined;
        }
        if (ev.key === "Alt" || !ev.altKey) {
            onSelectionModifier?.(false);
        }
    });
    useExternalListener(window, "blur", () => {
        self.shiftKeyMode = false;
        self.shiftKeyedRecord = undefined;
        onSelectionModifier?.(false);
    });

    return self;
}

/**
 * @param {object} config
 * @param {() => number} config.getLongTouchThreshold
 * @param {(record: any) => void} config.onLongTouch
 * @returns {{
 * onTouchStart: (record?: any) => void,
 * onTouchEnd: () => void,
 * onTouchMove: () => void,
 * resetLongTouchTimer: () => void,
 * }}
 */
export function useLongTouchSelection({ getLongTouchThreshold, onLongTouch }) {
    /** @type {ReturnType<typeof browser.setTimeout> | null} */
    let longTouchTimer = null;

    const self = {
        resetLongTouchTimer() {
            if (longTouchTimer !== null) {
                browser.clearTimeout(longTouchTimer);
                longTouchTimer = null;
            }
        },

        /** @param {any} [record] */
        onTouchStart(record) {
            if (longTouchTimer === null) {
                longTouchTimer = browser.setTimeout(() => {
                    self.resetLongTouchTimer();
                    onLongTouch(record);
                }, getLongTouchThreshold());
            }
        },

        onTouchEnd() {
            // A due timer may still be queued when the release is delivered.
            self.resetLongTouchTimer();
        },

        onTouchMove() {
            self.resetLongTouchTimer();
        },
    };

    onWillDestroy(() => self.resetLongTouchTimer());

    return self;
}
