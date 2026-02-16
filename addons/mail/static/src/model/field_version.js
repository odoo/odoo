/**
 * Represents a PostgreSQL transaction snapshot. See:
 * https://www.postgresql.org/docs/13/functions-info.html#FUNCTIONS-PG-SNAPSHOT-PARTS
 *
 * @typedef {Object} IPgSnapshot
 * @property {string} xmin The lowest active transaction ID at the time this snapshot was
 * taken. Lower transaction IDs are completed.
 *
 * @property {string} xmax The upper bound of transaction IDs for this snapshot. Greater
 * or equals transaction IDs are invisible by this snapshot.
 *
 * @property {string} xip_bitmap A bitmap representing in progress transactions in the
 * range [xmin, xmax). Each bit corresponds to a transaction ID within this range. If the
 * bit is set, the transaction was in progress at the time this snapshot was taken.
 *
 * @property {string|null} current_xact_id The current transaction ID, assigned when a
 * transaction modify the database.
 *
 * A versioned field value tied to a database snapshot. It tracks what this revision "saw"
 * when this value was set, allowing the client to correctly order updates and ignore late
 * arriving, stale data.
 *
 * @typedef {Object} FieldRevision
 * @property {PgSnapshot} snapshot The transactional context defining what the current
 * revision could "see" in the database.
 * @property {boolean} isWrite Whether this revision modified the field.
 */

/**
 * VISUAL REPRESENTATION OF THE SNAPSHOT.
 * Legend: √ committed, ~ pending, × future.
 *
 *                                +-------------------------+
 *                                |     PENDING COUNT (4)   |
 *                     +--------> +-------------------------+ <------+------+
 *          XMIN 5     |                        ^                    |      |     XMAX 12
 *               v     |                        |                    |      |     v
 *               +--------+--------+--------+--------+--------+---------+---------+
 *    √ √ √ √    | TX_5 ~ | TX_6 √ | TX_7 √ | TX_8 ~ | TX_9 √ | TX_10 ~ | TX_11 ~ |    × × × ×
 *  <--------->  +--------+--------+--------+--------+--------+---------+---------+  <--------->
 *       |                     |        |                |
 *       |                     |        |                |
 *       |                     v        v                v
 *       +----------------> +-----------------------------------------+
 *                          |              FINISHED COUNT             |
 *                          |                                         |
 *                          |    xmax - 1 - len(xip) = 12 - 1 - 4 = 7 |
 *                          | OR xmin - 1 + len(xip) =  5 - 1 + 3 = 7 |
 *                          +-----------------------------------------+
 */
export class PgSnapshot {
    /** @param {IPgSnapshot} */
    constructor(params) {
        this.current_xact_id = params.current_xact_id
            ? BigInt(params.current_xact_id)
            : params.current_xact_id;
        this.xmin = BigInt(params.xmin);
        this.xmax = BigInt(params.xmax);
        const bitmapBinaryStr = atob(params.xip_bitmap);
        // Bitmap [xmin, xmax) showing which xact_ids are in progress of the time of the snapshot.
        this.xip_bitmap = new Uint8Array(bitmapBinaryStr.length).map((_, idx) =>
            bitmapBinaryStr.charCodeAt(idx)
        );
        let pendingCount = 0;
        for (let byte of this.xip_bitmap) {
            while (byte > 0) {
                byte &= byte - 1;
                pendingCount++;
            }
        }
        this.finishedCount = this.xmax - 1n - BigInt(pendingCount);
    }

    /**
     * Determine whether the given transaction was visibile by this snapshot.
     *
     * @param {BigInt} txid
     */
    knowsTransaction(txid) {
        // tx < xmin are completed. tx between xmin and xmax are completed if not in xip.
        if (txid >= this.xmin && txid < this.xmax) {
            const offset = Number(txid - this.xmin);
            const byteIndex = Math.floor(offset / 8);
            const bitIndex = offset % 8;
            return !(this.xip_bitmap[byteIndex] & (1 << bitIndex));
        }
        return txid < this.xmin;
    }

    /**
     * Determine whether the given revision comes from a newer snapshot than the current
     * one (i.e. if the given revision knows more committed transactions than the current
     * one).
     *
     * @param {PgSnapshot} other
     */
    isAfter(other) {
        return this.finishedCount > other.finishedCount;
    }

    /**
     * Checks whether this snapshot and another snapshot saw the same state of the database.
     *
     * @param {PgSnapshot} other
     */
    sawSameState(other) {
        return this.finishedCount === other.finishedCount;
    }
}

/**
 * Determines whether a candidate field revision should replace the current one.
 *
 * @param {FieldRevision} candidate
 * @param {FieldRevision} other
 * @returns {Boolean} Whether the candidate revision can replace the other one.
 */
function shouldReplace(candidate, other) {
    if (candidate.snapshot.sawSameState(other.snapshot)) {
        return true;
    }
    // candidate is a read:
    // - vs write: can replace if the candidate revision knows about the transaction the
    //   write originates from.
    // - vs read: can replace if the candidate revision comes from a newer snapshot (i.e.
    //   this revision knows more committed transactions).
    if (!candidate.isWrite) {
        return other.isWrite
            ? candidate.snapshot.knowsTransaction(other.snapshot.current_xact_id)
            : candidate.snapshot.isAfter(other.snapshot);
    }
    // Candidate is a write: we can replace any revision that didn't know
    // about this transaction.
    return !other.snapshot.knowsTransaction(candidate.snapshot.current_xact_id);
}

export const SKIP_REVISION = Symbol("SKIP");

/**
 * Track a single value field's latest revision and allow to determine if a new value can
 * be applied based on snapshot visibility.
 */
export class SingleFieldVersion {
    lastRevision = {
        snapshot: new PgSnapshot({ xmin: 0, xmax: 0, xip_bitmap: "" }),
        isWrite: false,
    };

    /**
     * Determine if the current revision can replace the given one.
     *
     * @template T
     * @param {T} value
     * @param {FieldRevision} incomingRevision
     * @returns {typeof SKIP_REVISION|T} The skip symbol, or the value to update the
     * field.
     */
    resolveApply(value, incomingRevision) {
        if (shouldReplace(incomingRevision, this.lastRevision)) {
            this.lastRevision = incomingRevision;
            return value;
        }
        return SKIP_REVISION;
    }
}

/**
 * Track a multi value field's command history and determine which commands can be applied
 * based on revision snapshots.
 */
export class ManyFieldVersion {
    /** @type {import("@mail/model/record").Record} */
    TargetModel;
    /**
     * Tracks the command history for this field, in chronological order. Each entry
     * represents a single command along with the revision at which it was applied.
     *
     * @type {{cmd: [], revision: FieldRevision}[]}
     */
    history = [
        {
            cmd: ["REPLACE", []],
            revision: {
                snapshot: new PgSnapshot({ xmin: 0, xmax: 0, xip_bitmap: "" }),
                isWrite: false,
            },
        },
    ];

    constructor(TargetModel) {
        this.TargetModel = TargetModel;
    }

    /**
     * Determine what commands should be applied.
     *
     * @param {Array[]} commands
     * @param {FieldRevision} incomingRevision
     * @returns {Array[]|typeof SKIP_REVISION} The skip symbol, or the commands to apply
     * to update the field.
     */
    resolveApply(commands, incomingRevision) {
        if (!shouldReplace(incomingRevision, this.history[0].revision)) {
            return SKIP_REVISION;
        }
        const insertionIndex = this._findInsertionIndex(incomingRevision);
        const insertAtTheEnd = insertionIndex === this.history.length;
        this.history.splice(
            insertionIndex,
            0,
            ...commands.map((cmd) => ({ cmd, revision: incomingRevision }))
        );
        const lastReplaceIndex = this.history.findLastIndex((entry) => entry.cmd[0] === "REPLACE");
        if (lastReplaceIndex >= insertionIndex) {
            this.history = this.history.slice(lastReplaceIndex);
        }
        if (insertAtTheEnd) {
            return commands;
        }
        return this._generateReplaceFromHistory();
    }

    /**
     * Returns the index of the first element strictly greater than the given revision.
     * This ensures identical revisions are kept in their original arrival order.
     *
     * @param {FieldRevision} revision
     */
    _findInsertionIndex(revision) {
        let start = 0;
        let end = this.history.length;
        while (start < end) {
            const mid = Math.floor((start + end) / 2);
            const midRevision = this.history[mid].revision;
            if (shouldReplace(revision, midRevision)) {
                start = mid + 1;
            } else {
                end = mid;
            }
        }
        return start;
    }

    get lastRevision() {
        return this.history.at(-1).revision;
    }

    /** Returns a replace command, equivalent to all the commands in history. */
    _generateReplaceFromHistory() {
        const positionByLocalId = {};
        for (let idx = 0; idx < this.history.length; idx++) {
            const [name, values] = this.history[idx].cmd;
            for (let subIdx = 0; subIdx < values.length; subIdx++) {
                const value = values[subIdx];
                const localId = this.TargetModel.localId(value);
                if (["REPLACE", "ADD", "ADD.noinv"].includes(name)) {
                    positionByLocalId[localId] ??= { value, idx, subIdx };
                } else {
                    delete positionByLocalId[localId];
                }
            }
        }
        const sortedValues = Object.values(positionByLocalId)
            .sort((a, b) => a.idx - b.idx || a.subIdx - b.subIdx)
            .map((p) => p.value);
        return [["REPLACE", sortedValues]];
    }
}
