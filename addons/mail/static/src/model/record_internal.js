/** @typedef {import("./record").Record} Record */
/** @typedef {import("./record_list").RecordList} RecordList */

import { onChange } from "@mail/utils/common/misc";
import { IS_DELETED_SYM, IS_RECORD_SYM, isRelation } from "./misc";
import { RecordList } from "./record_list";
import { reactive, toRaw } from "@odoo/owl";
import { RecordUses } from "./record_uses";

export class RecordInternal {
    [IS_RECORD_SYM] = true;
    // Note: state of fields in Maps rather than object is intentional for improved performance.
    /**
     * For computed field, determines whether the field is computing its value.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputing = new Map();
    /**
     * On lazy-sorted field, determines whether the field should be (re-)sorted
     * when it's needed (i.e. accessed). Eager sorted fields are immediately re-sorted at end of update cycle,
     * whereas lazy sorted fields wait extra for them being needed.
     *
     * @type {Map<string, boolean>}
     */
    fieldsSortOnNeed = new Map();
    /**
     * On lazy sorted-fields, determines whether this field is needed (i.e. accessed).
     *
     * @type {Map<string, boolean>}
     */
    fieldsSortInNeed = new Map();
    /**
     * For sorted field, determines whether the field is sorting its value.
     *
     * @type {Map<string, boolean>}
     */
    fieldsSorting = new Map();
    /**
     * On lazy computed-fields, determines whether this field is needed (i.e. accessed).
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputeInNeed = new Map();
    /**
     * on lazy-computed field, determines whether the field should be (re-)computed
     * when it's needed (i.e. accessed). Eager computed fields are immediately re-computed at end of update cycle,
     * whereas lazy computed fields wait extra for them being needed.
     *
     * @type {Map<string, boolean>}
     */
    fieldsComputeOnNeed = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnUpdateObserves = new Map();
    /** @type {Map<string, this>} */
    fieldsSortProxy2 = new Map();
    /** @type {Map<string, this>} */
    fieldsComputeProxy2 = new Map();
    uses = new RecordUses();
    updatingAttrs = new Map();
    proxyUsed = new Map();
    /** @type {string} */
    localId;
    gettingField = false;

    /**
     * @param {Record} record
     * @param {string} fieldName
     * @param {Record} recordProxy
     */
    prepareField(record, fieldName, recordProxy) {
        const self = this;
        const Model = toRaw(record).Model;
        if (isRelation(Model, fieldName)) {
            // Relational fields contain symbols for detection in original class.
            // This constructor is called on genuine records:
            // - 'one' fields => undefined
            // - 'many' fields => RecordList
            // record[name]?.[0] is ONE_SYM or MANY_SYM
            const recordList = new RecordList();
            Object.assign(recordList._, {
                name: fieldName,
                owner: record,
            });
            Object.assign(recordList, {
                _raw: recordList,
                _store: record.store,
            });
            record[fieldName] = recordList;
        } else {
            record[fieldName] = record[fieldName].default;
        }
        if (Model._.fieldsCompute.get(fieldName)) {
            if (!Model._.fieldsEager.get(fieldName)) {
                onChange(recordProxy, fieldName, () => {
                    if (this.fieldsComputing.get(fieldName)) {
                        /**
                         * Use a reactive to reset the computeInNeed flag when there is
                         * a change. This assumes when other reactive are still
                         * observing the value, its own callback will reset the flag to
                         * true through the proxy getters.
                         */
                        this.fieldsComputeInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                this.fieldsComputeInNeed.delete(fieldName);
                this.fieldsSortInNeed.delete(fieldName);
            }
            const cb = function computeObserver() {
                self.requestCompute(record, fieldName);
            };
            const computeProxy2 = reactive(recordProxy, cb);
            this.fieldsComputeProxy2.set(fieldName, computeProxy2);
        }
        if (Model._.fieldsSort.get(fieldName)) {
            if (!Model._.fieldsEager.get(fieldName)) {
                onChange(recordProxy, fieldName, () => {
                    if (this.fieldsSorting.get(fieldName)) {
                        /**
                         * Use a reactive to reset the inNeed flag when there is a
                         * change. This assumes if another reactive is still observing
                         * the value, its own callback will reset the flag to true
                         * through the proxy getters.
                         */
                        this.fieldsSortInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                this.fieldsComputeInNeed.delete(fieldName);
                this.fieldsSortInNeed.delete(fieldName);
            }
            const sortProxy2 = reactive(recordProxy, function sortObserver() {
                self.requestSort(record, fieldName);
            });
            this.fieldsSortProxy2.set(fieldName, sortProxy2);
        }
        if (Model._.fieldsOnUpdate.get(fieldName)) {
            const store = Model.store;
            store._onChange(recordProxy, fieldName, (obs) => {
                this.fieldsOnUpdateObserves.set(fieldName, obs);
                if (store._.UPDATE !== 0) {
                    store._.ADD_QUEUE("onUpdate", record, fieldName);
                } else {
                    this.onUpdate(record, fieldName);
                }
            });
        }
    }

    requestCompute(record, fieldName, { force = false } = {}) {
        if (record[IS_DELETED_SYM]) {
            return;
        }
        const Model = record.Model;
        if (!Model._.fieldsCompute.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        if (store._.UPDATE !== 0 && !force) {
            store._.ADD_QUEUE("compute", record, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsComputeInNeed.get(fieldName)) {
                this.compute(record, fieldName);
            } else {
                this.fieldsComputeOnNeed.set(fieldName, true);
            }
        }
    }
    requestSort(record, fieldName, { force } = {}) {
        if (record[IS_DELETED_SYM]) {
            return;
        }
        const Model = record.Model;
        if (!Model._.fieldsSort.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        if (store._.UPDATE !== 0 && !force) {
            store._.ADD_QUEUE("sort", record, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsSortInNeed.get(fieldName)) {
                this.sort(record, fieldName);
            } else {
                this.fieldsSortOnNeed.set(fieldName, true);
            }
        }
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     */
    compute(record, fieldName) {
        const Model = record.Model;
        const store = record._rawStore;
        this.fieldsComputing.set(fieldName, true);
        this.fieldsComputeOnNeed.delete(fieldName);
        store._.updateFields(record, {
            [fieldName]: Model._.fieldsCompute
                .get(fieldName)
                .call(this.fieldsComputeProxy2.get(fieldName)),
        });
        this.fieldsComputing.delete(fieldName);
    }
    /**
     * @param {Record} record
     * @param {string} fieldName
     */
    sort(record, fieldName) {
        const Model = record.Model;
        if (!Model._.fieldsSort.get(fieldName)) {
            return;
        }
        const store = record._rawStore;
        this.fieldsSortOnNeed.delete(fieldName);
        this.fieldsSorting.set(fieldName, true);
        const proxy2Sort = this.fieldsSortProxy2.get(fieldName);
        const func = Model._.fieldsSort.get(fieldName).bind(proxy2Sort);
        if (isRelation(Model, fieldName)) {
            store._.sortRecordList(proxy2Sort[fieldName]._proxy, func);
        } else {
            // sort on copy of list so that reactive observers not triggered while sorting
            const copy = [...proxy2Sort[fieldName]];
            copy.sort(func);
            const hasChanged = copy.some((item, index) => item !== record[fieldName][index]);
            if (hasChanged) {
                proxy2Sort[fieldName] = copy;
            }
        }
        this.fieldsSorting.delete(fieldName);
    }
    onUpdate(record, fieldName) {
        const Model = record.Model;
        if (!Model._.fieldsOnUpdate.get(fieldName)) {
            return;
        }
        /**
         * Forward internal proxy for performance as onUpdate does not
         * need reactive (observe is called separately).
         */
        Model._.fieldsOnUpdate.get(fieldName).call(record._proxyInternal);
        this.fieldsOnUpdateObserves.get(fieldName)?.();
    }
    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     */
    downgradeProxy(record, fullProxy) {
        return record._proxy === fullProxy ? record._proxyInternal : fullProxy;
    }
}
