export class RecordUses {
    /**
     * Track the uses of a record. Each record contains a single `RecordUses`:
     * - Key: localId of record that uses current record
     * - Value: Map where key is relational field name, and value is number
     *          of time current record is present in this relation.
     *
     * @type {Map<string, Map<string, number>>}}
     */
    data = new Map();
    /** @param {RecordList} list */
    add(list) {
        const record = list._.owner;
        if (!this.data.has(record.localId)) {
            this.data.set(record.localId, new Map());
        }
        const use = this.data.get(record.localId);
        if (!use.get(list._.name)) {
            use.set(list._.name, 0);
        }
        use.set(list._.name, use.get(list._.name) + 1);
    }
    /** @param {RecordList} list */
    delete(list) {
        const record = list._.owner;
        if (!this.data.has(record.localId)) {
            return;
        }
        const use = this.data.get(record.localId);
        if (!use.get(list._.name)) {
            return;
        }
        use.set(list._.name, use.get(list._.name) - 1);
        if (use.get(list._.name) === 0) {
            use.delete(list._.name);
        }
    }
}
