// @ts-check

/** @module @web/views/list/list_selection - Hook for checkbox selection, shift-range selection, and long-touch selection in list views */

/** @odoo-module **/

import { useExternalListener } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { getActiveHotkey } from "@web/services/hotkeys/hotkey_service";

/**
 * Hook encapsulating selection/checkbox logic and touch-triggered selection for the list view.
 *
 * Manages shift-key range selection, long-touch selection on mobile, and click-capture
 * behavior in selection mode.
 *
 * @param {object} options
 * @param {() => import("./list_renderer").ListRendererProps} options.getProps
 * @param {() => boolean} options.getAllowSelectors
 * @param {(record: object) => void} options.toggleRecordSelection
 * @param {number} options.longTouchThreshold - ms before long-touch triggers selection
 * @param {() => any} options.getEnv
 * @returns {{
 *   toggleRangeSelection: (record: object) => void,
 *   expandCheckboxes: (record: object, direction: "up" | "down") => boolean,
 *   onRowTouchStart: (record: object, ev: TouchEvent) => void,
 *   onRowTouchEnd: (record: object) => void,
 *   onRowTouchMove: (record: object) => void,
 *   resetLongTouchTimer: () => void,
 *   onClickCapture: (record: object, ev: PointerEvent) => void,
 *   ignoreEventInSelectionMode: (ev: MouseEvent) => void,
 *   shiftKeyMode: boolean,
 *   shiftKeyedRecord: object | undefined,
 *   lastCheckedRecord: object | undefined,
 * }}
 */
export function useListSelection({
    getProps,
    getAllowSelectors,
    toggleRecordSelection,
    longTouchThreshold,
    getEnv,
}) {
    let longTouchTimer = null;
    let touchStartMs = 0;

    const self = {
        /** Whether shift key is currently held. */
        shiftKeyMode: false,

        /** Record where shift-selection started. */
        shiftKeyedRecord: undefined,

        /** Last record whose checkbox was toggled (for range selection). */
        lastCheckedRecord: undefined,

        /**
         * Reset the long-touch timer if one is running.
         */
        resetLongTouchTimer() {
            if (longTouchTimer) {
                browser.clearTimeout(longTouchTimer);
                longTouchTimer = null;
            }
        },

        /**
         * Select/deselect a range of records between lastCheckedRecord and the given record.
         *
         * @param {object} record
         */
        toggleRangeSelection(record) {
            const { records } = getProps().list;
            const recordIndex = records.indexOf(record);
            const lastCheckedRecordIndex = records.indexOf(self.lastCheckedRecord);
            if (lastCheckedRecordIndex === -1) {
                self.lastCheckedRecord = record;
                record.toggleSelection(!record.selected);
                return;
            }
            const start = Math.min(recordIndex, lastCheckedRecordIndex);
            const end = Math.max(recordIndex, lastCheckedRecordIndex);
            for (let i = start; i <= end; i++) {
                records[i].toggleSelection(!record.selected);
            }
        },

        /**
         * Expand checkbox selection by one record in the given direction (shift+arrow).
         *
         * @param {object} record
         * @param {"up" | "down"} direction
         * @returns {boolean} whether a checkbox was toggled
         */
        expandCheckboxes(record, direction) {
            const { records } = getProps().list;
            if (!record && direction === "down") {
                const defaultRecord = records[0];
                self.shiftKeyedRecord = defaultRecord;
                defaultRecord.toggleSelection(true);
                return true;
            }
            const recordIndex = records.indexOf(record);
            const shiftKeyedRecordIndex = records.indexOf(self.shiftKeyedRecord);
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
            }

            if (isExpanding) {
                record.toggleSelection(true);
                nextRecord.toggleSelection(true);
            } else {
                record.toggleSelection(false);
            }
            return true;
        },

        /**
         * Handle touch start on a record row for long-touch selection.
         *
         * @param {object} record
         * @param {TouchEvent} ev
         */
        onRowTouchStart(record, ev) {
            if (!getAllowSelectors()) {
                return;
            }
            if (getProps().list.selection.length) {
                ev.stopPropagation();
            }
            touchStartMs = Date.now();
            if (longTouchTimer === null) {
                longTouchTimer = browser.setTimeout(() => {
                    toggleRecordSelection(record);
                    self.resetLongTouchTimer();
                }, longTouchThreshold);
            }
        },

        /**
         * Handle touch end — cancel the long-touch timer if touch was short.
         *
         * @param {object} _record
         */
        onRowTouchEnd(_record) {
            const elapsedTime = Date.now() - touchStartMs;
            if (elapsedTime < longTouchThreshold) {
                self.resetLongTouchTimer();
            }
        },

        /**
         * Cancel long-touch on move.
         *
         * @param {object} _record
         */
        onRowTouchMove(_record) {
            self.resetLongTouchTimer();
        },

        /**
         * In mobile selection mode, prevent all other click handlers and toggle selection.
         *
         * @param {object} record
         * @param {PointerEvent} ev
         */
        onClickCapture(record, ev) {
            const { list } = getProps();
            if (getEnv().isSmall && list.selection.length) {
                ev.stopPropagation();
                ev.preventDefault();
                toggleRecordSelection(record);
            }
        },

        /**
         * In mobile selection mode, swallow events that aren't selection-related.
         *
         * @param {MouseEvent} ev
         */
        ignoreEventInSelectionMode(ev) {
            const { list } = getProps();
            if (getEnv().isSmall && list.selection.length) {
                ev.stopPropagation();
                ev.preventDefault();
            }
        },
    };

    useExternalListener(window, "keydown", (ev) => {
        self.shiftKeyMode = ev.shiftKey;
    });
    useExternalListener(window, "keyup", (ev) => {
        self.shiftKeyMode = ev.shiftKey;
        if (getActiveHotkey(ev) === "shift") {
            self.shiftKeyedRecord = undefined;
        }
    });
    useExternalListener(window, "blur", () => {
        self.shiftKeyMode = false;
    });

    return self;
}
