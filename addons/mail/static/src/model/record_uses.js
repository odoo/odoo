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
        const localId = list._.owner.localId;
        let use = this.data.get(localId);
        if (!use) {
            use = new Map();
            this.data.set(localId, use);
        }
        const name = list._.name;
        use.set(name, (use.get(name) ?? 0) + 1);
    }
    /** @param {RecordList} list */
    delete(list) {
        const use = this.data.get(list._.owner.localId);
        if (!use) {
            return;
        }
        const name = list._.name;
        const count = use.get(name);
        if (!count) {
            return;
        }
        if (count === 1) {
            use.delete(name);
        } else {
            use.set(name, count - 1);
        }
    }
}
