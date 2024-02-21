import { ATTR_SYM, MANY_SYM, ONE_SYM, _0, isCommand, isRecord, isRelation } from "./misc";

export class ModelInternal {
    /**
     * Technical attribute, DO NOT USE in business code.
     * This class is almost equivalent to current class of model,
     * except this is a function, so we can new() it, whereas
     * `this` is not, because it's an object.
     * (in order to comply with OWL reactivity)
     *
     * @type {typeof import("./record").Record}
     */
    Class;
    NEXT_LOCAL_ID = 1;
    /** @type {Map<string, boolean>} */
    fields = new Map();
    /** @type {Map<string, any>} */
    fieldsDefault = new Map();
    /** @type {Map<string, boolean>} */
    fieldsDefaultAsInit = new Map();
    /** @type {Map<string, boolean>} */
    fieldsAttr = new Map();
    /** @type {Map<string, boolean>} */
    fieldsOne = new Map();
    /** @type {Map<string, boolean>} */
    fieldsMany = new Map();
    /** @type {Map<string, boolean>} */
    fieldsHtml = new Map();
    /** @type {Map<string, string>} */
    fieldsTargetModel = new Map();
    /** @type {Map<string, () => any>} */
    fieldsCompute = new Map();
    /** @type {Map<string, boolean>} */
    fieldsEager = new Map();
    /** @type {Map<string, string>} */
    fieldsInverse = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnAdd = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnDelete = new Map();
    /** @type {Map<string, () => void>} */
    fieldsOnUpdate = new Map();
    /** @type {Map<string, () => number>} */
    fieldsSort = new Map();
    /** @type {Map<string, number>} */
    fieldsNextTs = new Map();
    /** @type {Map<string, string>} */
    fieldsType = new Map();
    /**
     * Normalized version of static id.
     * Should not be defined by business code, as this is deduced from provided static id.
     * It contains a list whose item are lists of string.
     * 1st-level depth of listing is a "OR" between items, and 2nd-level depth of
     * listing is an "AND" between items.
     * This _.id is simpler to navigate than static id which is a sort of Domain-Specific-Language.
     * To avoid parsing it again and again, static _id is preferred for internal code.
     *
     * @type {Array<string[]>}
     */
    id = [];
    /**
     * Fields that contribute to object ids.
     * Should not be defined by business code, as this is deduced from provided static id.
     * Useful to track when their value change on a record, to adapt object id that maps to
     * this record... and maybe need to reconcile with another existing record that has the
     * same identity!
     *
     * @type {Object<string, true>}
     */
    objectIdFields = {};
    get singleIds() {
        return this.id
            .filter((item) => Object.keys(item).length === 1)
            .map((item) => Object.keys(item)[0]);
    }

    constructor(data) {
        Object.assign(this, data);
    }
    /**
     * Find the local id from data on current model (if exists)
     *
     * @param {typeof import("./record").Record} Model0
     * @param {any} data
     */
    dataToLocalId(Model0, data) {
        let localId;
        if (Model0.singleton) {
            return Object.keys(Model0.records)[0];
        }
        if (typeof data !== "object" || data === null) {
            // special shorthand when record has a single single-id primitive.
            // Note that this is not working on object field due to ambiguity
            // on whether it targets this single-id or data are on self object.
            const singleIds = this.singleIds;
            if (singleIds.length !== 1) {
                throw new Error(`
                    Model "${Model0.name}" has more than one single-id.
                    Shorthand to get/insert records with non-object is only supported with a single single-id.
                    Found singleIds: ${singleIds.map((item) => item[0]).join(",")}
                `);
            }
            return this.dataToLocalId(Model0, { [singleIds[0]]: data });
        }
        for (let i = 0; i < this.id.length && !localId; i++) {
            /** @type {Object<string, false | () => boolean>} */
            const expr = this.id[i];
            if (
                Object.entries(expr).some(
                    ([fieldName, eligible]) => !(fieldName in data && (!eligible || eligible(data)))
                )
            ) {
                continue;
            }
            this.retrieveObjectIdsFromExpr(Model0, expr, data, {
                earlyStop: () => localId,
                onObjectId: (objectId) => {
                    localId = Model0.store0.objectIdToLocalId.get(objectId);
                },
            });
        }
        return localId;
    }
    prepareField(fieldName, data) {
        this.fields.set(fieldName, true);
        if (data[ATTR_SYM]) {
            this.fieldsAttr.set(fieldName, data[ATTR_SYM]);
        }
        if (data[ONE_SYM]) {
            this.fieldsOne.set(fieldName, data[ONE_SYM]);
        }
        if (data[MANY_SYM]) {
            this.fieldsMany.set(fieldName, data[MANY_SYM]);
        }
        for (const key in data) {
            const value = data[key];
            switch (key) {
                case "html": {
                    if (!value) {
                        break;
                    }
                    this.fieldsHtml.set(fieldName, value);
                    break;
                }
                case "default": {
                    if (value === undefined) {
                        break;
                    }
                    this.fieldsDefault.set(fieldName, value);
                    break;
                }
                case "defaultAsInit": {
                    // Fields made without Record.attr() might contain arrow functions.
                    // To bind it to current record, tricks is to store default on record
                    // using its initial value
                    this.fieldsDefaultAsInit.set(fieldName, true);
                    break;
                }
                case "targetModel": {
                    this.fieldsTargetModel.set(fieldName, value);
                    break;
                }
                case "compute": {
                    this.fieldsCompute.set(fieldName, value);
                    break;
                }
                case "eager": {
                    if (!value) {
                        break;
                    }
                    this.fieldsEager.set(fieldName, value);
                    break;
                }
                case "sort": {
                    this.fieldsSort.set(fieldName, value);
                    break;
                }
                case "inverse": {
                    this.fieldsInverse.set(fieldName, value);
                    break;
                }
                case "onAdd": {
                    this.fieldsOnAdd.set(fieldName, value);
                    break;
                }
                case "onDelete": {
                    this.fieldsOnDelete.set(fieldName, value);
                    break;
                }
                case "onUpdate": {
                    this.fieldsOnUpdate.set(fieldName, value);
                    break;
                }
                case "type": {
                    this.fieldsType.set(fieldName, value);
                    break;
                }
            }
        }
        this.fieldsNextTs.set(fieldName, 0);
    }
    /**
     * @param {Record} a record that triggered same identity detection
     * @param {Record} b record that has been detected as having same identity
     */
    reconcile(a, b) {
        a._.reconciling = true;
        b._.reconciling = true;
        const Model = a.Model;
        const store0 = Model.store0;
        for (const localId of a._.localIds) {
            store0.localIdToRecord.set(localId, b._1);
            b._.localIds.push(localId);
        }
        for (const objectId of a._.objectIds) {
            store0.objectIdToLocalId.set(objectId, b.localId);
        }
        a._.localIds = b._.localIds;
        a._.objectIds = b._.objectIds;
        a._.reconciled = true;
        // Most recent values have precedence over old conflicting ones
        for (const fieldName of this.fields.keys()) {
            const aTs = a._.fieldsTs.get(fieldName);
            const bTs = b._.fieldsTs.get(fieldName);
            let resVal;
            if (aTs && !bTs) {
                resVal = a[fieldName];
                b._.customAssignThroughProxy = () => {
                    b[fieldName] = resVal;
                };
            } else if (!aTs && bTs) {
                // use b
                resVal = b[fieldName];
                a._.customAssignThroughProxy = () => {
                    a[fieldName] = resVal;
                };
            } else if (!aTs && !bTs) {
                // none have been converted to record field... nothing to do!
            } else if (aTs > bTs) {
                // use a
                resVal = a[fieldName];
                b._.customAssignThroughProxy = () => {
                    b[fieldName] = resVal;
                };
            } else {
                // use b
                resVal = b[fieldName];
                a._.customAssignThroughProxy = () => {
                    a[fieldName] = resVal;
                };
            }
            /** @type {RecordList} */
            let a2Reclist;
            /** @type {RecordList} */
            let b2Reclist;
            if (isRelation(Model, fieldName)) {
                /** @type {RecordList} */
                const aReclist = a[fieldName];
                /** @type {RecordList} */
                const bReclist = b[fieldName];
                a2Reclist = aReclist._2;
                b2Reclist = bReclist._2;
                /** @type {RecordList} */
                const reclist = resVal;
                aReclist._0 = reclist._0;
                aReclist._1 = reclist._1;
                aReclist._2 = reclist._2;
                aReclist._0 = reclist._0;
                aReclist._1 = reclist._1;
                aReclist._2 = reclist._2;
                const inverse = this.fieldsInverse.get(fieldName);
                if (inverse) {
                    const removedRecs = [];
                    for (const localId of [...aReclist.value, ...bReclist.value]) {
                        let otherRec = _0(_0(store0.localIdToRecord).get(localId));
                        for (let i = 0; otherRec && i < otherRec._.localIds.length; i++) {
                            const localId = otherRec._.localIds[i];
                            if (reclist.value.some((d) => d === localId)) {
                                otherRec = false;
                            }
                        }
                        if (otherRec && !removedRecs.some((rec) => rec.eq(otherRec))) {
                            removedRecs.push(otherRec);
                        }
                    }
                    for (const removedRec of removedRecs) {
                        const otherReclist = removedRec[inverse];
                        const owner = reclist._.owner;
                        for (const localId of owner._.localIds) {
                            otherReclist.value = otherReclist.value.filter((d) => d !== localId);
                            store0._.ADD_QUEUE(
                                "onDelete",
                                otherReclist._.owner,
                                otherReclist._.name,
                                owner
                            );
                            store0._.ADD_QUEUE(
                                "onDelete",
                                reclist._.owner,
                                reclist._.name,
                                removedRec
                            );
                        }
                    }
                }
            }
            if (a._.customAssignThroughProxy) {
                a._2[fieldName] = resVal;
            }
            if (b._.customAssignThroughProxy) {
                b._2[fieldName] = resVal;
            }
            if (a2Reclist) {
                a2Reclist.value = resVal.value;
            }
            if (b2Reclist) {
                b2Reclist.value = resVal.value;
            }
        }
        // TODO combine the uses
        // the tracked uses are for efficient deletion of self,
        // so it's fine if we overestimate it a bit
        const data = a._.uses.data;
        for (const [localId, bFields] of b._.uses.data.entries()) {
            const aFields = data.get(localId);
            if (!aFields) {
                data.set(localId, bFields);
            } else {
                for (const [name, bCount] of bFields.entries()) {
                    const aCount = aFields.get(name);
                    if (aCount === undefined) {
                        aFields.set(name, bCount);
                    } else {
                        aFields.set(name, aCount + bCount);
                    }
                }
            }
        }
        b._.uses.data = data;
        // TODO combine _.updatingAttrs
        a._.updatingAttrs = b._.updatingAttrs;
        // TODO combine _.updatingFieldsThroughProxy
        a._.updatingFieldsThroughProxy = b._.updatingFieldsThroughProxy;
        a._0 = b._0;
        a._1 = b._1;
        a._2 = b._2;
        a._.reconciling = false;
        b._.reconciling = false;
    }
    /**
     * @param {typeof import("./record").Record} Model0
     * @param {Object<string, false | () => boolean>} expr part of an AND expression in model ids. See static _.id
     * @param {Object|Record} data
     * @param {Object} [param2={}]
     * @param {() => boolean} [param2.earlyStop] if provided, truthy value means the retrieve
     *   process should stop. Useful when using this function requires to only find a
     *   single match.
     * @param {(string) => void} [param2.onObjectId] if provided, called whenever an object id
     *   has been retrieved by this function. Param is the currently retrieved object id.
     */
    retrieveObjectIdsFromExpr(Model0, expr, data, { earlyStop, onObjectId } = {}) {
        const self = this;
        // Try each combination of potential objectId, using all localIds of relations
        const fields = Object.entries(expr).map(([fieldName, eligibility]) => ({
            name: fieldName,
            relation: isRelation(Model0, fieldName),
        }));
        const fieldToIndex = Object.fromEntries(
            fields.filter((f) => f.relation).map((f, index) => [f.name, index])
        );
        const fcounts = fields.map((field) => (field.relation ? 0 : -1));
        const iteration = { value: 0 };
        const MAX_ITER = 1000;

        const loop = function (index, ...fcounts2) {
            /** @param {string} name */
            const getRelatedRecord = function (name) {
                if (isRecord(data[name])) {
                    return data[name];
                } else if (isCommand(data[name])) {
                    const param2 = data[name]?.[0]?.at(-1);
                    if (!param2) {
                        return;
                    } else if (isRecord(param2)) {
                        return param2;
                    }
                    const targetModel = self.fieldsTargetModel.get(name);
                    return Model0.store0[targetModel].get(param2);
                } else if ([null, false, undefined].includes(data[name])) {
                    return undefined;
                } else {
                    const targetModel = self.fieldsTargetModel.get(name);
                    return Model0.store0[targetModel].get(data[name]);
                }
            };
            if (index >= fields.length) {
                let ok = true;
                const fieldVals = Object.entries(expr)
                    .map(([fieldName, eligible]) => {
                        if (typeof eligible === "function" && !eligible(data)) {
                            ok = false;
                            return;
                        }
                        if (isRelation(Model0, fieldName)) {
                            const i = fcounts2[fieldToIndex[fieldName]];
                            const relatedRecord = getRelatedRecord(fieldName);
                            if (!relatedRecord) {
                                ok = false;
                                return;
                            }
                            const relatedRec0 = _0(relatedRecord);
                            return `${fieldName}: (${relatedRec0._.localIds[i]})`;
                        } else {
                            return `${fieldName}: ${data[fieldName]}`;
                        }
                    })
                    .join(", ");
                if (!ok) {
                    return;
                }
                const objectId = `${Model0.name}{${fieldVals}}`;
                onObjectId?.(objectId);
                iteration.value++;
                return;
            }
            const fieldName = fields[index].name;
            if (!fields[index].relation) {
                return loop(index + 1, ...fcounts2);
            }
            const relatedRecord = getRelatedRecord(fieldName);
            if (!relatedRecord) {
                return; // not a candidate
            }
            const relatedRec0 = _0(relatedRecord);
            for (
                let i = 0;
                i < relatedRec0._.localIds.length && !earlyStop?.() && iteration.value < MAX_ITER;
                i++
            ) {
                loop(index + 1, ...fcounts2);
            }
        };
        loop(0, ...fcounts);
        if (iteration.value === MAX_ITER) {
            throw new Error("Too many reconciled records with residual data");
        }
    }
}
