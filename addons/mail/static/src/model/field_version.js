/**
 * A version as sent by the server: a fixed-width ISO datetime string, comparable
 * lexicographically as if it were a date.
 *
 * @typedef {string} WriteDate
 */

export const SKIP_REVISION = Symbol("SKIP");

/** Sentinel older than any real write date, used when there is no version to compare against. */
const OLDEST_WRITE_DATE = "0001-01-01T00:00:00.000000";

/**
 * Track a single value field's latest write date and determine if a new value
 * can be applied according to the incoming data write date.
 */
export class SingleFieldVersion {
    /** @type {WriteDate} */
    lastWriteDate = OLDEST_WRITE_DATE;

    /**
     * Determine if the incoming value can overwrite the current one.
     *
     * @template T
     * @param {T} value
     * @param {WriteDate} incomingWriteDate
     * @param {Object} [options={}]
     * @param {boolean} [options.forceApply=true] Apply the value even when its
     * write date is outdated. Only versioned server data turns it off.
     * @returns {typeof SKIP_REVISION|T} The skip symbol, or the value to update the
     * field.
     */
    resolveApply(value, incomingWriteDate, { forceApply = true } = {}) {
        if (incomingWriteDate >= this.lastWriteDate) {
            this.lastWriteDate = incomingWriteDate;
            return value;
        }
        return forceApply ? value : SKIP_REVISION;
    }
}

/**
 * Track the history of a multi-value field and determine which commands to apply.
 *
 * ADD and DELETE are versioned per value (using each value's own version), since one
 * command can bundle values that were actually added/removed at different times.
 *
 * Commands arriving out of order are inserted at their chronological place in the
 * history, which is then replayed into a single REPLACE.
 *
 * REPLACE is never versioned, as its date can't be trusted against other commands (e.g.
 * many2many): it resets the history, and the last one to arrive always wins.
 */
export class ManyFieldVersion {
    /** @type {import("@mail/model/record").Record} */
    TargetModel;
    /**
     * Tracks the command history for this field, in chronological order. Each entry
     * represents a single command along with the write date at which it was applied.
     *
     * @type {{cmd: [string, any[]], writeDate: WriteDate}[]}
     */
    history = [{ cmd: ["REPLACE", []], writeDate: OLDEST_WRITE_DATE }];

    constructor(TargetModel) {
        this.TargetModel = TargetModel;
    }

    /**
     * Determine what commands should be applied. A value with no version of its own is
     * placed at the end of the history.
     *
     * @param {[string, any[], WriteDate|undefined][]} commands
     * @param {Object} [options={}]
     * @param {boolean} [options.forceApply=true] Apply the commands as-is even when their
     * write date is out of order. Only versioned server data turns it off.
     * @returns {Array[]} the commands to apply to update the field.
     */
    resolveApply(commands, { forceApply = true } = {}) {
        let appliedCommands = [];
        let allAtTheEnd = true;
        for (const [mode, values, commandWriteDate] of commands) {
            if (mode === "REPLACE") {
                const cmd = ["REPLACE", values];
                this.history = [{ cmd, writeDate: OLDEST_WRITE_DATE }];
                appliedCommands = [cmd];
                continue;
            }
            for (const item of values) {
                const writeDate = item?.__version__ ?? commandWriteDate ?? this.lastWriteDate;
                const cmd = [mode, [item]];
                const insertionIndex = this._findInsertionIndex(writeDate);
                const insertedAtEnd = insertionIndex === this.history.length;
                this.history.splice(insertionIndex, 0, { cmd, writeDate });
                allAtTheEnd = allAtTheEnd && insertedAtEnd;
                if (insertedAtEnd || forceApply) {
                    appliedCommands.push(cmd);
                }
            }
        }
        return allAtTheEnd || forceApply ? appliedCommands : this._generateReplaceFromHistory();
    }

    /**
     * Index of the first element strictly greater than `writeDate`, keeping identical
     * dates in arrival order.
     *
     * @param {WriteDate} writeDate
     */
    _findInsertionIndex(writeDate) {
        let start = 0;
        let end = this.history.length;
        while (start < end) {
            const mid = Math.floor((start + end) / 2);
            if (writeDate >= this.history[mid].writeDate) {
                start = mid + 1;
            } else {
                end = mid;
            }
        }
        return start;
    }

    get lastWriteDate() {
        return this.history.at(-1).writeDate;
    }

    /** Returns a replace command, equivalent to all the commands in history. */
    _generateReplaceFromHistory() {
        const positionByLocalId = {};
        for (let idx = 0; idx < this.history.length; idx++) {
            const [name, values] = this.history[idx].cmd;
            for (const value of values) {
                const localId = this.TargetModel.localId(value);
                if (["REPLACE", "ADD", "ADD.noinv"].includes(name)) {
                    positionByLocalId[localId] ??= { value, idx };
                } else {
                    delete positionByLocalId[localId];
                }
            }
        }
        const sortedValues = Object.values(positionByLocalId)
            .sort((a, b) => a.idx - b.idx)
            .map((p) => p.value);
        return [["REPLACE", sortedValues]];
    }
}
