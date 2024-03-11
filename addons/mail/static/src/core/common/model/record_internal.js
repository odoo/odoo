import { onChange } from "@mail/utils/common/misc";
import { _0, isCommand, isRelation } from "./misc";
import { RecordList } from "./record_list";
import { RecordUses } from "./record_uses";
import { reactive } from "@odoo/owl";

export class RecordInternal {
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
    /** @type {Map<string, number>} */
    fieldsTs = new Map();
    /** @type {boolean} */
    reconciling;
    /** @type {() => void>} */
    customAssignThroughProxy;
    /** @type {boolean} */
    reconciled;
    /** @type {Set<string>} */
    updatingFieldsThroughProxy = new Set();
    /** @type {Set<string>} */
    updatingAttrs = new Set();
    /** @type {boolean} */
    gettingField;
    uses = new RecordUses();
    /**
     * List of all local ids related to this record.
     * Most of time records only have a single local id.
     * Multiple local ids happen when 2 or more records happen
     * to share same identity and they have being reconciled.
     * Eventually record will keep a single local id, but to
     * smooth transition a record can have temporarily many local
     * ids.
     *
     * @type {string[]}
     */
    localIds = [];
    /**
     * List of object ids of the record.
     * Object ids include local ids, and also all currently known way
     * to identify this record. An object id is a stringified version
     * of data that identify the record. A non-local object id matches
     * an AND expression in static id.
     *
     * @type {string[]}
     */
    objectIds = [];

    /**
     * For computed field, invoking this function (re-)computes the field.
     *
     * @param {import("./record").Record} rec0
     * @type {string} fieldName
     */
    computeField(rec0, fieldName) {
        const compute = rec0.Model._.fieldsCompute.get(fieldName);
        if (!compute) {
            return;
        }
        this.fieldsComputing.set(fieldName, true);
        this.fieldsComputeOnNeed.delete(fieldName, true);
        const proxy2 = this.fieldsComputeProxy2.get(fieldName);
        rec0._store0.MAKE_UPDATE(() => {
            rec0._store0._.update(rec0, { [fieldName]: compute.call(proxy2) });
        });
        this.fieldsComputing.delete(fieldName);
    }
    /**
     * The internal reactive is only necessary to trigger outer reactives when
     * writing on it. As it has no callback, reading through it has no effect,
     * except slowing down performance and complexifying the stack.
     *
     * @param {import("./record").Record} rec0
     * @param {import("./record").Record} rec3
     */
    downgrade(rec0, rec3) {
        return rec0._2 === rec3 ? rec0._1 : rec3;
    }
    /** @param {import("./record").Record} rec0 */
    onRecomputeObjectIds(rec0) {
        if (rec0._.reconciled) {
            return;
        }
        const store0 = rec0._store0;
        // 1. compute object ids
        const objectIds = rec0._.recordToObjectIds(rec0);
        const oldObjectIds = rec0._.objectIds.filter((objectId) => !objectIds.includes(objectId));
        const newObjectIds = objectIds.filter((objectId) => !rec0._.objectIds.includes(objectId));
        // 2. old object ids => remove the mapping
        for (const oldOid of oldObjectIds) {
            rec0._.objectIds = rec0._.objectIds.filter((oid) => oid !== oldOid);
            store0.objectIdToLocalId.delete(oldOid);
        }
        // 3. new object ids
        for (const newOid of newObjectIds) {
            const otherLocalId = store0.objectIdToLocalId.get(newOid);
            if (otherLocalId && !rec0._.localIds.includes(otherLocalId)) {
                // Detected other record matching same identity => reconcile
                const otherRec = _0(_0(store0.localIdToRecord).get(otherLocalId));
                if (!rec0._.reconciling && !otherRec._.reconciling) {
                    rec0.Model._.reconcile(rec0, otherRec);
                }
            }
            rec0._.objectIds.push(newOid);
            store0.objectIdToLocalId.set(newOid, rec0.localId);
        }
    }
    /**
     * Function that contains functions to be called when the value of field has changed, e.g. sort and onUpdate.
     *
     * @param {import("./record").Record} rec0
     * @param {string} fieldName
     */
    onUpdateField(rec0, fieldName) {
        const onUpdate = rec0.Model._.fieldsOnUpdate.get(fieldName);
        if (!onUpdate) {
            return;
        }
        rec0._store0.MAKE_UPDATE(() => {
            /**
             * Forward internal proxy for performance as onUpdate does not
             * need reactive (observe is called separately).
             */
            onUpdate.call(rec0._1);
            this.fieldsOnUpdateObserves.get(fieldName)?.();
        });
    }
    /**
     * @param {import("./record").Record} rec0
     * @param {string} fieldName
     */
    prepareField(rec0, fieldName) {
        const rec2 = rec0._2;
        const Model = rec0.Model;
        if (isRelation(Model, fieldName)) {
            const reclist0 = new RecordList({
                owner: rec0,
                name: fieldName,
                store: rec0._store0,
            });
            reclist0._0 = reclist0;
            rec0[fieldName] = reclist0;
        }
        if (rec0.Model._.objectIdFields[fieldName]) {
            this.prepareFieldOnRecomputeObjectIds(rec0, fieldName);
        }
        if (Model._.fieldsAttr.get(fieldName)) {
            if (!Model._.fieldsDefaultAsInit.get(fieldName)) {
                const defaultVal = Model._.fieldsDefault.get(fieldName);
                if (defaultVal === undefined) {
                    rec0[fieldName] = defaultVal;
                } else {
                    rec2[fieldName] = defaultVal;
                }
            }
        }
        const nextTs = Model._.fieldsNextTs.get(fieldName);
        this.fieldsTs.set(fieldName, nextTs);
        Model._.fieldsNextTs.set(fieldName, nextTs + 1);
        if (Model._.fieldsCompute.get(fieldName)) {
            if (!Model._.fieldsEager.get(fieldName)) {
                onChange(rec2, fieldName, () => {
                    if (rec0._.fieldsComputing.get(fieldName)) {
                        /**
                         * Use a reactive to reset the computeInNeed flag when there is
                         * a change. This assumes when other reactive are still
                         * observing the value, its own callback will reset the flag to
                         * true through the proxy getters.
                         */
                        rec0._.fieldsComputeInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                rec0._.fieldsComputeInNeed.delete(fieldName);
                rec0._.fieldsSortInNeed.delete(fieldName);
            }
            const proxy2 = reactive(rec2, function RF_computeObserver() {
                rec0._.requestComputeField(rec0, fieldName);
            });
            rec0._.fieldsComputeProxy2.set(fieldName, proxy2);
        }
        if (Model._.fieldsSort.get(fieldName)) {
            if (!Model._.fieldsEager.get(fieldName)) {
                onChange(rec2, fieldName, () => {
                    if (rec0._.fieldsSorting.get(fieldName)) {
                        /**
                         * Use a reactive to reset the inNeed flag when there is a
                         * change. This assumes if another reactive is still observing
                         * the value, its own callback will reset the flag to true
                         * through the proxy getters.
                         */
                        rec0._.fieldsSortInNeed.delete(fieldName);
                    }
                });
                // reset flags triggered by registering onChange
                rec0._.fieldsComputeInNeed.delete(fieldName);
                rec0._.fieldsSortInNeed.delete(fieldName);
            }
            const proxy2 = reactive(rec2, function RF_sortObserver() {
                rec0._.requestSortField(rec0, fieldName);
            });
            rec0._.fieldsSortProxy2.set(fieldName, proxy2);
        }
        if (Model._.fieldsOnUpdate.get(fieldName)) {
            rec0._store0._onChange(rec2, fieldName, (obs) => {
                rec0._.fieldsOnUpdateObserves.set(fieldName, obs);
                if (rec0._store0._.UPDATE !== 0) {
                    rec0._store0._.ADD_QUEUE("onUpdate", rec0, fieldName);
                } else {
                    rec0._.onUpdateField(rec0, fieldName);
                }
            });
        }
    }
    /**
     * @param {import("./record").Record} rec0
     * @param {string} fieldName
     */
    prepareFieldOnRecomputeObjectIds(rec0, fieldName) {
        const self = this;
        const rec2 = rec0._2;
        const Model = rec0.Model;
        onChange(rec2, fieldName, function RF_onChangeRecomputeObjectIds_attr() {
            self.onRecomputeObjectIds(rec0);
        });
        if (isRelation(Model, fieldName)) {
            let reclistProxy;
            if (Model._.fieldsOne.get(fieldName)) {
                reclistProxy = reactive(rec0[fieldName]);
            }
            if (Model._.fieldsMany.get(fieldName)) {
                reclistProxy = rec2[fieldName];
            }
            onChange(reclistProxy, "value", function RF_onChangeRecomputeObjectIds_rel_value() {
                self.onRecomputeObjectIds(rec0);
            });
            onChange(
                reclistProxy.value,
                "length",
                function RF_onChangeRecomputeObjectIds_rel_length() {
                    self.onRecomputeObjectIds(rec0);
                }
            );
        }
    }
    /**
     * Compute object ids of the record, without updating them.
     * Useful to compare with old object ids and determine strategy to
     * update them and/or reconcile records if needed.
     *
     * @param {import("./record").Record} rec0
     */
    recordToObjectIds(rec0) {
        const rec1 = rec0._1;
        const Model = rec0.Model;
        const objectIds = [...rec0._.localIds];
        for (let i = 0; i < Model._.id.length; i++) {
            /** @type {Object<string, false | () => boolean>} */
            const expr = Model._.id[i];
            if (
                Object.entries(expr).some(
                    ([fieldName, eligible]) =>
                        rec1[fieldName] === undefined && (!eligible || eligible(rec1))
                )
            ) {
                continue;
            }
            Model._.retrieveObjectIdsFromExpr(Model, expr, rec1, {
                onObjectId: (objectId) => {
                    objectIds.push(objectId);
                },
            });
        }
        return objectIds;
    }
    /**
     * on computed field, calling this function makes a request to compute
     * the field. This doesn't necessarily mean the field is immediately re-computed: during an update cycle, this
     * is put in the compute FC_QUEUE and will be invoked at end.
     *
     * @param {import("./record").Record} rec0
     * @param {string} fieldName
     * @param {Object} [param1={}]
     * @param {boolean} [param1.force=false]
     */
    requestComputeField(rec0, fieldName, { force = false } = {}) {
        const Model = rec0.Model;
        if (!Model._.fieldsCompute.get(fieldName)) {
            return;
        }
        if (rec0._store0._.UPDATE !== 0 && !force) {
            rec0._store0._.ADD_QUEUE("compute", rec0, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsComputeInNeed.get(fieldName)) {
                this.computeField(rec0, fieldName);
            } else {
                this.fieldsComputeOnNeed.set(fieldName, true);
            }
        }
    }
    /**
     * on sorted field, calling this function makes a request to sort
     * the field. This doesn't necessarily mean the field is immediately re-sorted: during an update cycle, this
     * is put in the sort FS_QUEUE and will be invoked at end.
     *
     * @param {import("./record").Record} rec0
     * @param {string} fieldName
     * @param {Object} [param1={}]
     * @param {boolean} [param1.force=false]
     */
    requestSortField(rec0, fieldName, { force } = {}) {
        const Model = rec0.Model;
        if (!Model._.fieldsSort.get(fieldName)) {
            return;
        }
        if (rec0._store0._.UPDATE !== 0 && !force) {
            rec0._store0._.ADD_QUEUE("sort", rec0, fieldName);
        } else {
            if (Model._.fieldsEager.get(fieldName) || this.fieldsSortInNeed.get(fieldName)) {
                this.sortField(rec0, fieldName);
            } else {
                this.fieldsSortOnNeed.set(fieldName, true);
            }
        }
    }
    /**
     * AKU TODO: relies on old id... so obsolete
     *
     * @param {import("./record").Record} rec0
     */
    retrieveIdValue(rec0) {
        const Model = rec0.Model;
        const rec1 = rec0._1;
        const res = {};
        function _deepRetrieve(expr2) {
            if (typeof expr2 === "string") {
                if (isCommand(rec1[expr2])) {
                    // Note: only R.one() is supported
                    const [cmd, data2] = rec1[expr2].at(-1);
                    return Object.assign(res, {
                        [expr2]:
                            cmd === "DELETE"
                                ? undefined
                                : cmd === "DELETE.noinv"
                                ? [["DELETE.noinv", data2]]
                                : cmd === "ADD.noinv"
                                ? [["ADD.noinv", data2]]
                                : data2,
                    });
                }
                return Object.assign(res, { [expr2]: rec1[expr2] });
            }
            if (expr2 instanceof Array) {
                for (const expr of this.id) {
                    if (typeof expr === "symbol") {
                        continue;
                    }
                    _deepRetrieve(expr);
                }
            }
        }
        if (rec0.id === undefined) {
            return res;
        }
        if (typeof Model.id === "string") {
            if (typeof data !== "object" || rec1 === null) {
                return { [Model.id]: rec1 }; // non-object data => single id
            }
            if (isCommand(rec1[Model.id])) {
                // Note: only one() is supported
                const [cmd, data2] = rec1[Model.id].at(-1);
                return Object.assign(res, {
                    [Model.id]:
                        cmd === "DELETE"
                            ? undefined
                            : cmd === "DELETE.noinv"
                            ? [["DELETE.noinv", data2]]
                            : cmd === "ADD.noinv"
                            ? [["ADD.noinv", data2]]
                            : data2,
                });
            }
            return { [Model.id]: rec1[Model.id] };
        }
        for (const expr of Model.id) {
            if (typeof expr === "symbol") {
                continue;
            }
            _deepRetrieve(expr);
        }
        return res;
    }
    /**
     * For sorted field, invoking this function (re-)sorts the field.
     *
     * @param {import("./record").Record} rec0
     * @type {string} fieldName
     */
    sortField(rec0, fieldName) {
        const sort = rec0.Model._.fieldsSort.get(fieldName);
        if (!sort) {
            return;
        }
        this.fieldsSortOnNeed.delete(fieldName);
        this.fieldsSorting.set(fieldName, true);
        const proxy2 = this.fieldsSortProxy2.get(fieldName);
        rec0._store0.MAKE_UPDATE(() => {
            if (rec0.Model._.fieldsAttr.get(fieldName)) {
                proxy2[fieldName].sort(sort);
            } else {
                rec0._store0._.sortRecordList(proxy2[fieldName]._2, sort.bind(proxy2));
            }
        });
        this.fieldsSorting.delete(fieldName);
    }
}
