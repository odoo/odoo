export class RecordUses {
    /**
     * Track the uses of a record. Each record contains a single `RecordUses`:
     * - Key: a localId of record that uses current record
     * - Value: Map where key is relational field name, and value is number
     *          of time current record is present in this relation.
     *
     * @type {Map<string, Map<string, number>>}}
     */
    data = new Map();
    /** @param {import("./record_list").RecordList} list */
    add(list) {
        const record = list._.owner;
        let ownerLocalId;
        for (const localId of record._.localIds) {
            if (this.data.has(localId)) {
                ownerLocalId = localId;
                break;
            }
        }
        if (!ownerLocalId) {
            ownerLocalId = list._.owner.localId;
            this.data.set(ownerLocalId, new Map());
        }
        const use = this.data.get(ownerLocalId);
        if (!use.get(list._.name)) {
            use.set(list._.name, 0);
        }
        use.set(list._.name, use.get(list._.name) + 1);
    }
    /** @param {import("./record_list").RecordList} list */
    delete(list) {
        const record = list._.owner;
        let ownerLocalId;
        for (const localId of record._.localIds) {
            if (this.data.has(localId)) {
                ownerLocalId = localId;
                break;
            }
        }
        if (!ownerLocalId) {
            return;
        }
        const use = this.data.get(ownerLocalId);
        if (!use.get(list._.name)) {
            return;
        }
        use.set(list._.name, use.get(list._.name) - 1);
        if (use.get(list._.name) === 0) {
            use.delete(list._.name);
        }
    }
}
