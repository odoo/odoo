import { markRaw, reactive } from "@odoo/owl";
import { _0, isRecord } from "./misc";

class RecordListInternal {
    /** @type {string} */
    name;
    /** @type {import("./record").Record} */
    owner;

    /**
     * Version of add() that does not update the inverse.
     * This is internally called when inserting (with intent to add)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {RecordList} reclist0
     * @param {...R}
     */
    addNoinv(reclist0, ...records) {
        const reclist2 = reclist0._2;
        const Model = this.owner.Model;
        if (Model._.fieldsOne.get(this.name)) {
            const last = records.at(-1);
            if (isRecord(last) && last.in(reclist0)) {
                return;
            }
            const record = this.insert(
                reclist0,
                last,
                function RL_addNoInv_insertOne(record) {
                    if (record.localId !== reclist0.value[0]) {
                        const old = reclist2.at(-1);
                        reclist2.value.pop();
                        old?._.uses.delete(reclist0);
                        reclist2.value.push(record.localId);
                        reclist0._.syncLength(reclist0);
                        record._.uses.add(reclist0);
                    }
                },
                { inv: false }
            );
            reclist0._store._.ADD_QUEUE("onAdd", this.owner, this.name, record);
            return;
        }
        for (const val of records) {
            if (isRecord(val) && val.in(reclist0)) {
                continue;
            }
            const record = this.insert(
                reclist0,
                val,
                function RL_addNoInv_insertMany(record) {
                    if (reclist0.value.indexOf(record.localId) === -1) {
                        reclist2.value.push(record.localId);
                        reclist0._.syncLength(reclist0);
                        record._.uses.add(reclist0);
                    }
                },
                { inv: false }
            );
            reclist0._store._.ADD_QUEUE("onAdd", this.owner, this.name, record);
        }
    }
    /**
     * @param {RecordList} reclist0
     * @param {R|any} val
     * @param {(R) => void} [fn] function that is called in-between preinsert and
     *   insert. Preinsert only inserted what's needed to make record, while
     *   insert finalize with all remaining data.
     * @param {boolean} [inv=true] whether the inverse should be added or not.
     *   It is always added except when during an insert on a relational field,
     *   in order to avoid infinite loop.
     * @param {"ADD"|"DELETE} [mode="ADD"] the mode of insert on the relation.
     *   Important to match the inverse. Most of the time it's "ADD", that is when
     *   inserting the relation the inverse should be added. Exception when the insert
     *   comes from deletion, we want to "DELETE".
     */
    /** @param {R[]|any[]} data */
    assign(reclist0, data) {
        const self = this;
        const Model = this.owner.Model;
        const inverse = Model._.fieldsInverse.get(this.name);
        return reclist0._store.MAKE_UPDATE(function RL_assign() {
            /** @type {Record[]|Set<Record>|RecordList<Record|any[]>} */
            const collection = isRecord(data) ? [data] : data;
            // l1 and collection could be same record list,
            // save before clear to not push mutated recordlist that is empty
            const vals = [...collection];
            /** @type {R[]} */
            const oldRecords2 = reclist0._1.slice.call(reclist0._2);
            const records2 = vals.map((val) =>
                self.insert(reclist0, val, function RL_assign_insert(record) {
                    const wasIn = record._.localIds.some(
                        (localId) => reclist0.value.indexOf(localId) !== -1
                    );
                    if (!wasIn) {
                        record._.uses.add(reclist0);
                        reclist0._store._.ADD_QUEUE("onAdd", self.owner, self.name, record);
                        if (inverse) {
                            record[inverse].add(self.owner);
                        }
                    }
                })
            );
            for (const oldRecord2 of oldRecords2) {
                const oldRecord = _0(oldRecord2);
                if (!oldRecord.in(records2)) {
                    oldRecord._.uses.delete(reclist0);
                    reclist0._store._.ADD_QUEUE("onDelete", self.owner, self.name, oldRecord);
                    if (inverse) {
                        oldRecord[inverse].delete(self.owner);
                    }
                }
            }
            reclist0._2.value = records2.map((record2) => _0(record2).localId);
            reclist0._.syncLength(reclist0);
        });
    }
    /**
     * Version of delete() that does not update the inverse.
     * This is internally called when inserting (with intent to delete)
     * on relational field with inverse, to prevent infinite loops.
     *
     * @param {RecordList} reclist0
     * @param {...R}
     */
    deleteNoinv(reclist0, ...records) {
        const reclist2 = reclist0._2;
        for (const val of records) {
            const record = this.insert(
                reclist0,
                val,
                function RL_deleteNoInv_insert(record) {
                    const index = reclist0.value.indexOf(record.localId);
                    if (index !== -1) {
                        const old = reclist2.at(-1);
                        reclist2.value.splice(index, 1);
                        reclist0._.syncLength(reclist0);
                        old._.uses.delete(reclist0);
                    }
                },
                { inv: false, mode: "DELETE" }
            );
            reclist0._store._.ADD_QUEUE("onDelete", this.owner, this.name, record);
        }
    }
    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     *
     * @param {RecordList} reclist0
     * @param {RecordList} reclist3
     */
    downgrade(reclist0, reclist3) {
        return reclist0._2 === reclist3 ? reclist0._1 : reclist3;
    }
    /**
     * @param {RecordList} reclist0
     * @param {any} val
     * @param {() => void} fn
     * @param {Obect} param3
     * @returns {import("./record").Record}
     */
    insert(reclist0, val, fn, { inv = true, mode = "ADD" } = {}) {
        const Model = this.owner.Model;
        const inverse = Model._.fieldsInverse.get(this.name);
        if (inverse && inv) {
            // special command to call _.addNoinv/_.deleteNoInv, to prevent infinite loop
            if (isRecord(val) && val._0 === val) {
                val._1[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
            } else {
                val[inverse] = [[mode === "ADD" ? "ADD.noinv" : "DELETE.noinv", this.owner]];
            }
        }
        /** @type {R} */
        let newRecord3;
        if (!isRecord(val)) {
            const targetModel = Model._.fieldsTargetModel.get(this.name);
            newRecord3 = reclist0._store[targetModel].preinsert(val);
        } else {
            newRecord3 = val;
        }
        const newRecord0 = _0(newRecord3);
        fn?.(newRecord0);
        if (!isRecord(val)) {
            // was preinserted, fully insert now
            newRecord3.update(val);
        }
        return newRecord0;
    }
    /**
     * Sync reclist.value length with array length, as to not introduce confusion while debugging
     *
     * @param {RecordList} reclist0
     */
    syncLength(reclist0) {
        reclist0.length = reclist0.value.length;
    }
}

/** * @template {import("./record").Record} R */
export class RecordList extends Array {
    /** @type {import("models").Store} */
    _store;
    /** @type {string[]} */
    value = [];
    /** @type {this} */
    _0; // previously "_raw"
    /** @type {this} */
    _1; // previously "_proxyInternal"
    /** @type {this} */
    _2; // previously "_proxy"
    _ = markRaw(new RecordListInternal());

    /** @param {Object} vals */
    constructor({ store, owner, name }) {
        super();
        const this0 = this;
        this0._store = store;
        this0._.name = name;
        this0._.owner = owner;
        this0._0 = this0;
        const Model = this._.owner.Model;
        const this1 = new Proxy(this0, {
            /** @param {RecordList<R>} this3 */
            get(this0, name, this3) {
                this3 = this0._.downgrade(this0, this3);
                if (
                    typeof name === "symbol" ||
                    Object.keys(this0).includes(name) ||
                    Object.prototype.hasOwnProperty.call(this0.constructor.prototype, name)
                ) {
                    return Reflect.get(this0, name, this3);
                }
                if (
                    Model._.fieldsCompute.get(this0._.name) &&
                    !Model._.fieldsEager.get(this0._.name)
                ) {
                    this0._.owner._.fieldsComputeInNeed.set(this0._.name, true);
                    if (this0._.owner._.fieldsComputeOnNeed.get(this0._.name)) {
                        this0._.owner._.computeField(this0._.owner, this0._.name);
                    }
                }
                if (name === "length") {
                    return this3.value.length;
                }
                if (
                    Model._.fieldsSort.get(this0._.name) &&
                    !Model._.fieldsEager.get(this0._.name)
                ) {
                    this0._.owner._.fieldsSortInNeed.set(this0._.name, true);
                    if (this0._.owner._.fieldsSortOnNeed.get(this0._.name)) {
                        this0._.owner._.sortField(this0._.owner, this0._.name);
                    }
                }
                if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                    // support for "array[index]" syntax
                    const index = parseInt(name);
                    return this3._store.localIdToRecord.get(this3.value[index]);
                }
                // Attempt an unimplemented array method call
                const array = [...this0._1[Symbol.iterator].call(this3)];
                return array[name]?.bind(array);
            },
            /** @param {RecordList<R>} this3 */
            set(this0, name, val, this3) {
                return this0._store.MAKE_UPDATE(function RL_set() {
                    if (typeof name !== "symbol" && !window.isNaN(parseInt(name))) {
                        // support for "array[index] = r3" syntax
                        const index = parseInt(name);
                        this0._.insert(this0, val, function RL_set_insert(newRecord) {
                            const oldRecord = _0(this0._store.localIdToRecord).get(
                                this0.value[index]
                            );
                            if (oldRecord && oldRecord.notEq(newRecord)) {
                                oldRecord._.uses.delete(this0);
                            }
                            this0._store._.ADD_QUEUE(
                                "onDelete",
                                this0._.owner,
                                this0._.name,
                                oldRecord
                            );
                            const inverse = Model._.fieldsInverse.get(this0._.name);
                            if (inverse) {
                                oldRecord[inverse].delete(this0);
                            }
                            this3.value[index] = newRecord?.localId;
                            if (newRecord) {
                                newRecord._.uses.add(this0);
                                this0._store._.ADD_QUEUE(
                                    "onAdd",
                                    this0._.owner,
                                    this0._.name,
                                    newRecord
                                );
                                if (inverse) {
                                    newRecord[inverse].add(this0);
                                }
                            }
                        });
                    } else if (name === "length") {
                        const newLength = parseInt(val);
                        if (newLength !== this0.value.length) {
                            if (newLength < this0.value.length) {
                                this0.splice.call(this3, newLength, this0.length - newLength);
                            }
                            this3.value.length = newLength;
                            this0._.syncLength(this0);
                        }
                    } else {
                        return Reflect.set(this0, name, val, this3);
                    }
                    return true;
                });
            },
        });
        this0._1 = this1;
        this0._2 = reactive(this1);
        return this0;
    }

    /** @param {R[]} records */
    push(...records) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        const Model = this0._.owner.Model;
        return this0._store.MAKE_UPDATE(function RL_push() {
            for (const val of records) {
                const record = this0._.insert(this0, val, function RL_push_insert(record) {
                    this0._2.value.push(record.localId);
                    this0._.syncLength(this0);
                    record._.uses.add(this0);
                });
                this0._store._.ADD_QUEUE("onAdd", this0._.owner, this0._.name, record);
                const inverse = Model._.fieldsInverse.get(this0._.name);
                if (inverse) {
                    record[inverse].add(this0._.owner);
                }
            }
            return this3.value.length;
        });
    }
    /** @returns {R} */
    pop() {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        return this0._store.MAKE_UPDATE(function RL_pop() {
            /** @type {R} */
            const oldRecord3 = this3.at(-1);
            if (oldRecord3) {
                this0.splice.call(this3, this3.length - 1, 1);
            }
            return oldRecord3;
        });
    }
    /** @returns {R} */
    shift() {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        const Model = this0._.owner.Model;
        return this0._store.MAKE_UPDATE(function RL_shift() {
            const record3 = this3._store.localIdToRecord.get(this3.value.shift());
            this0._.syncLength(this0);
            if (!record3) {
                return;
            }
            const record0 = _0(record3);
            record0._.uses.delete(this0);
            this0._store._.ADD_QUEUE("onDelete", this0._.owner, this0._.name, record0);
            const inverse = Model._.fieldsInverse.get(this0._.name);
            if (inverse) {
                record0[inverse].delete(this0._.owner);
            }
            return record3;
        });
    }
    /** @param {R[]} records */
    unshift(...records) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        const Model = this0._.owner.Model;
        return this0._store.MAKE_UPDATE(function RL_unshift() {
            for (let i = records.length - 1; i >= 0; i--) {
                const record = this0._.insert(this0, records[i], (record) => {
                    this0._2.value.unshift(record.localId);
                    this0._.syncLength(this0);
                    record._.uses.add(this0);
                });
                this0._store._.ADD_QUEUE("onAdd", this0._.owner, this0._.name, record);
                const inverse = Model._.fieldsInverse.get(this0._.name);
                if (inverse) {
                    record[inverse].add(this0._.owner);
                }
            }
            return this3.value.length;
        });
    }
    /** @param {R} record3 */
    indexOf(record3) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        let index = -1;
        for (const localId of _0(record3)?._.localIds || []) {
            index = this3.value.indexOf(localId);
            if (index !== -1) {
                break;
            }
        }
        return index;
    }
    /**
     * @param {number} [start]
     * @param {number} [deleteCount]
     * @param {...R} [newRecords3]
     */
    splice(start, deleteCount, ...newRecords3) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        const Model = this0._.owner.Model;
        const inverse = Model._.fieldsInverse.get(this0._.name);
        return this0._store.MAKE_UPDATE(function RL_splice() {
            const oldRecords3 = this0._1.slice.call(this3, start, start + deleteCount);
            const list = this3.value.slice(); // splice on copy of list so that reactive observers not triggered while splicing
            list.splice(
                start,
                deleteCount,
                ...newRecords3.map((newRecord3) => _0(newRecord3).localId)
            );
            this0._2.value = list;
            for (const oldRecord3 of oldRecords3) {
                const oldRecord0 = _0(oldRecord3);
                oldRecord0._.uses.delete(this0);
                this0._store._.ADD_QUEUE("onDelete", this0._.owner, this0._.name, oldRecord0);
                if (inverse) {
                    oldRecord0[inverse]?.delete(this0._.owner);
                }
            }
            for (const newRecord3 of newRecords3) {
                const newRecord = _0(newRecord3);
                newRecord._.uses.add(this0);
                this0._store._.ADD_QUEUE("onAdd", this0._.owner, this0._.name, newRecord);
                if (inverse) {
                    newRecord[inverse].add(this0._.owner);
                }
            }
        });
    }
    /** @param {(a: R, b: R) => boolean} func */
    sort(func) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        return this0._store.MAKE_UPDATE(function RL_sort() {
            this0._store._.sortRecordList(this3, func);
            return this3;
        });
    }
    /** @param {...R[]|...RecordList[R]} collections */
    concat(...collections) {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        return this3.value
            .map((localId) => this3._store.localIdToRecord.get(localId))
            .concat(...collections.map((c) => [...c]));
    }
    /** @param {...R}  */
    add(...records) {
        const this0 = _0(this);
        const Model = this0._.owner.Model;
        return this0._store.MAKE_UPDATE(function RL_add() {
            if (Model._.fieldsOne.get(this0._.name)) {
                const last = records.at(-1);
                if (isRecord(last) && this0.value.includes(_0(last).localId)) {
                    return;
                }
                this0._.insert(this0, last, function RL_add_insertOne(record) {
                    if (record.localId !== this0.value[0]) {
                        this0.pop.call(this0._2);
                        this0.push.call(this0._2, record);
                    }
                });
                return;
            }
            for (const val of records) {
                if (isRecord(val) && this0.value.includes(val.localId)) {
                    continue;
                }
                this0._.insert(this0, val, function RL_add_insertMany(record) {
                    if (this0.value.indexOf(record.localId) === -1) {
                        this0.push.call(this0._2, record);
                    }
                });
            }
        });
    }
    /** @param {...R}  */
    delete(...records) {
        const this0 = _0(this);
        return this0._store.MAKE_UPDATE(function RL_delete() {
            for (const val of records) {
                this0._.insert(
                    this0,
                    val,
                    function RL_delete_insert(record) {
                        const index = this0.value.indexOf(record.localId);
                        if (index !== -1) {
                            this0.splice.call(this0._2, index, 1);
                        }
                    },
                    { mode: "DELETE" }
                );
            }
        });
    }
    clear() {
        const this0 = _0(this);
        return this0._store.MAKE_UPDATE(function RL_clear() {
            while (this0.value.length > 0) {
                this0.pop.call(this0._2);
            }
        });
    }
    /** @yields {R} */
    *[Symbol.iterator]() {
        const this0 = _0(this);
        const this3 = this0._.downgrade(this0, this);
        for (const localId of this3.value) {
            yield this3._store.localIdToRecord.get(localId);
        }
    }
}
