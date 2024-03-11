export class StoreInternal {
    /**
     * Determines whether the inserts are considered trusted or not.
     * Useful to auto-markup html fields when this is set
     */
    trusted = false;
    /** @type {RecordField[]} */
    FC_QUEUE = []; // field-computes
    /** @type {RecordField[]} */
    FS_QUEUE = []; // field-sorts
    /** @type {Array<{field: RecordField, records: Record[]}>} */
    FA_QUEUE = []; // field-onadds
    /** @type {Array<{field: RecordField, records: Record[]}>} */
    FD_QUEUE = []; // field-ondeletes
    /** @type {RecordField[]} */
    FU_QUEUE = []; // field-onupdates
    /** @type {Function[]} */
    RO_QUEUE = []; // record-onchanges
    /** @type {Record[]} */
    RD_QUEUE = []; // record-deletes
    RHD_QUEUE = []; // record-hard-deletes
    UPDATE = 0;
}
