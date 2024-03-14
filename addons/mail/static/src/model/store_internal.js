/** @typedef {import("./record").Record} Record */
/** @typedef {import("./misc").RecordField} RecordField */

import { RecordInternal } from "./record_internal";

export class StoreInternal extends RecordInternal {
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    trusted = false;
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FC_QUEUE = new Map(); // field-computes
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FS_QUEUE = new Map(); // field-sorts
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FA_QUEUE = new Map(); // field-onadds
    /** @type {Map<import("./record").Record, Map<string, Map<import("./record").Record, true>>>} */
    FD_QUEUE = new Map(); // field-ondeletes
    /** @type {Map<import("./record").Record, Map<string, true>>} */
    FU_QUEUE = new Map(); // field-onupdates
    /** @type {Map<Function, true>} */
    RO_QUEUE = new Map(); // record-onchanges
    /** @type {Map<Record, true>} */
    RD_QUEUE = new Map(); // record-deletes
    /** @type {Map<Record, true>} */
    RHD_QUEUE = new Map(); // record-hard-deletes
    UPDATE = 0;
}
