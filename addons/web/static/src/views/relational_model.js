/* @odoo-module */

import { ORM, x2ManyCommands } from "@web/core/orm_service";
import { Deferred, KeepLast, Mutex } from "@web/core/utils/concurrency";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { Domain } from "@web/core/domain";
import { isNumeric, isRelational, isX2Many } from "@web/views/helpers/view_utils";
import { isTruthy } from "@web/core/utils/xml";
import { makeContext } from "@web/core/context";
import { Model } from "@web/views/helpers/model";
import { registry } from "@web/core/registry";
import { escape } from "@web/core/utils/strings";
import { session } from "@web/session";
import { ListConfirmationDialog } from "@web/views/list/list_confirmation_dialog";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

const { DateTime } = luxon;
const { markRaw, markup, toRaw } = owl;

const preloadedDataRegistry = registry.category("preloadedData");

const { CREATE, UPDATE, DELETE, FORGET, LINK_TO, DELETE_ALL, REPLACE_WITH } = x2ManyCommands;
const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection"];
const DEFAULT_QUICK_CREATE_FIELDS = {
    display_name: { string: "Display name", type: "char" },
};
const DEFAULT_QUICK_CREATE_VIEW = {
    // note: the required modifier is written in the format returned by the server
    arch: /* xml */ `
        <form>
            <field name="display_name" placeholder="Title" modifiers='{"required": true}' />
        </form>`,
};

/**
 * @typedef {import("@web/core/context").ContextDescription} ContextDescription
 * @typedef {import("@web/core/context").ContextDescription} Context
 */

/**
 * @typedef {{
 *  parent?: RawContext;
 *  make: () => Context;
 * }} RawContext
 */

/**
 * @param {Object} groupByField
 * @returns {boolean}
 */
export const isAllowedDateField = (groupByField) => {
    return (
        ["date", "datetime"].includes(groupByField.type) &&
        isTruthy(groupByField.attrs.allow_group_range_value)
    );
};

/**
 * @typedef {Object} OrderTerm ?
 * @property {string} name
 * @property {boolean} asc
 */

/**
 * @param {OrderTerm[]} orderBy
 * @returns {string}
 */
function orderByToString(orderBy) {
    return orderBy.map((o) => `${o.name} ${o.asc ? "ASC" : "DESC"}`).join(", ");
}

/**
 * @param {any} string
 * @return {OrderTerm[]}
 */
export function stringToOrderBy(string) {
    if (!string) {
        return [];
    }
    return string.split(",").map((order) => {
        const splitOrder = order.trim().split(" ");
        if (splitOrder.length === 2) {
            return {
                name: splitOrder[0],
                asc: splitOrder[1].toLowerCase() === "asc",
            };
        } else {
            return {
                name: splitOrder[0],
                asc: true,
            };
        }
    });
}
/**
 * @param {Array[] | boolean} modifier
 * @param {Object} evalContext
 * @returns {boolean}
 */
export function evalDomain(modifier, evalContext) {
    if (Array.isArray(modifier)) {
        modifier = new Domain(modifier).contains(evalContext);
    }
    return !!modifier;
}

/**
 * FIXME: don't know where this function should be:
 *   - on a dataPoint: don't want to make it accessible everywhere (e.g. in Fields)
 *   - on the model: would still be accessible by views + I like the current light API of the model
 *
 * Given a model name and res ids, calls the method "action_archive" or
 * "action_unarchive", and executes the returned action any.
 *
 * @param {string} resModel
 * @param {integer[]} resIds
 * @param {boolean} doArchive archive the records if true, otherwise unarchive them
 */
async function toggleArchive(model, resModel, resIds, doArchive) {
    const method = doArchive ? "action_archive" : "action_unarchive";
    const action = await model.orm.call(resModel, method, [resIds]);
    if (action && Object.keys(action).length !== 0) {
        model.action.doAction(action);
    }
    //todo fge _invalidateCache
}

class RequestBatcherORM extends ORM {
    constructor() {
        super(...arguments);
        this.searchReadBatches = {};
        this.searchReadBatchId = 1;
        this.batches = {};
    }

    /**
     * @param {number[]} ids
     * @param {any[]} keys
     * @param {Function} callback
     * @returns {Promise<any>}
     */
    async batch(ids, keys, callback) {
        const key = JSON.stringify(keys);
        let batch = this.batches[key];
        if (!batch) {
            batch = {
                deferred: new Deferred(),
                scheduled: false,
                ids,
            };
            this.batches[key] = batch;
        }
        const previousIds = batch.ids;
        batch.ids = [...new Set([...previousIds, ...ids])];

        if (!batch.scheduled) {
            batch.scheduled = true;
            await Promise.resolve();
            delete this.batches[key];
            const result = await callback(batch.ids);
            batch.deferred.resolve(result);
        }

        return batch.deferred;
    }

    /**
     * Entry point to batch "name_get" calls. If the `resModel` argument has
     * already been called, the given ids are added to the previous list of ids
     * to perform a single name_get call.
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {object} context
     * @returns {Promise<[number, string][]>}
     */
    async nameGet(resModel, resIds, context) {
        const pairs = await this.batch(resIds, ["name_get", resModel, context], (resIds) =>
            super.nameGet(resModel, resIds, context)
        );
        return pairs.filter(([id]) => resIds.includes(id));
    }

    /**
     * Entry point to batch "read" calls. If the `fields` and `resModel`
     * arguments have already been called, the given ids are added to the
     * previous list of ids to perform a single read call. Once the server
     * responds, records are then dispatched to the callees based on the
     * given ids arguments (kept in the closure).
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @param {string[]} fields
     * @returns {Promise<Object[]>}
     */
    async read(resModel, resIds, fields, context) {
        const records = await this.batch(resIds, ["read", resModel, fields, context], (resIds) =>
            super.read(resModel, resIds, fields, context)
        );
        return records.filter((r) => resIds.includes(r.id));
    }

    /**
     * Entry point to batch "unlink" calls. If the `resModel` argument has
     * already been called, the given ids are added to the previous list of ids
     * to perform a single unlink call.
     *
     * @param {string} resModel
     * @param {number[]} resIds
     * @returns {Promise<boolean>}
     */
    async unlink(resModel, resIds, context) {
        return this.batch(resIds, ["unlink", resModel, context], (resIds) =>
            super.unlink(resModel, resIds, context)
        );
    }

    /**
     * @override
     */
    async webSearchRead(/*model*/) {
        // FIXME: discriminate on model? (it is always the same in our usecase)
        const batchId = this.searchReadBatchId;
        let batch = this.searchReadBatches[batchId];
        if (!batch) {
            batch = {
                deferred: new Deferred(),
                count: 0,
            };
            Promise.resolve().then(() => this.searchReadBatchId++);
            this.searchReadBatches[batchId] = batch;
        }
        batch.count++;
        const result = await super.webSearchRead(...arguments);
        batch.count--;
        if (batch.count === 0) {
            delete this.searchReadBatches[batchId];
            batch.deferred.resolve();
        }
        await batch.deferred;
        return result;
    }
}

let nextId = 0;
class DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {Object} [params={}]
     * @param {Object} [state={}]
     */
    constructor(model, params = {}, state = {}) {
        this.id = `datapoint_${nextId++}`;

        this.model = model;
        this.resModel = params.resModel;
        this.fields = params.fields;
        this.activeFields = params.activeFields || {};

        this.rawContext = params.rawContext;
        this.defaultContext = params.defaultContext;
        this.setup(params, state);

        markRaw(this);
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get context() {
        const contexts = [];
        let rawContext = this.rawContext;
        if (!rawContext) {
            return Object.assign({}, this.defaultContext);
        }
        contexts.push({ ...this.defaultContext, ...rawContext.make() });

        while (rawContext.parent) {
            rawContext = rawContext.parent;
            const context = rawContext.make();
            for (const key in context) {
                if (key.startsWith("default_")) {
                    delete context[key];
                }
            }
            contexts.push(context);
        }

        return Object.assign({}, ...contexts.reverse());
    }

    get fieldNames() {
        return Object.keys(this.activeFields);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    exportState() {
        return {};
    }

    async load() {
        throw new Error("load must be implemented");
    }

    /**
     * @abstract
     * @param {Object} params
     * @param {Object} state
     */
    setup() {}

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _parseServerValue(field, value) {
        switch (field.type) {
            case "date": {
                return value ? deserializeDate(value) : false;
            }
            case "datetime": {
                return value ? deserializeDateTime(value) : false;
            }
            case "selection": {
                if (value === false) {
                    // process selection: convert false to 0, if 0 is a valid key
                    const hasKey0 = field.selection.find((option) => option[0] === 0);
                    return hasKey0 ? 0 : value;
                }
                break;
            }
        }
        return value;
    }

    _parseServerValues(values) {
        const parsedValues = {};
        if (!values) {
            return parsedValues;
        }
        for (const fieldName in values) {
            const value = values[fieldName];
            const field = this.fields[fieldName];
            parsedValues[fieldName] = this._parseServerValue(field, value);
        }
        return parsedValues;
    }
}

const clearObject = (obj) => {
    for (const key in obj) {
        delete obj[key];
    }
};

export class Record extends DataPoint {
    setup(params, state) {
        if ("resId" in params) {
            this.resId = params.resId;
        } else if (state) {
            this.resId = state.resId;
        }
        if (!this.resId) {
            this.resId = false;
            this.virtualId = params.virtualId || this.model.nextVirtualId;
        }
        this.resIds =
            (params.resIds ? toRaw(params.resIds) : null) || // FIXME WOWL reactivity
            state.resIds ||
            (this.resId ? [this.resId] : []);

        this._values = {};
        this._changes = {};
        this.data = {};

        this.parentActiveFields = params.parentActiveFields || false;
        this.onChanges = params.onChanges || (() => {});

        this._invalidFields = new Set();
        this._requiredFields = {};
        this._setRequiredFields();
        this.preloadedData = {};
        this.preloadedDataCaches = {};
        this.isInQuickCreation = params.isInQuickCreation || false;
        this._onChangePromise = Promise.resolve({});

        this._domains = {};

        this.relationField = params.relationField;
        this.parentRecord = params.parentRecord;

        this.getParentRecordContext = params.getParentRecordContext;

        this.selected = false;
        this.mode = params.mode || (this.resId ? state.mode || "readonly" : "edit");

        this._onWillSwitchMode = params.onRecordWillSwitchMode || (() => {});

        this.canBeAbandoned = this.isVirtual;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get dataContext() {
        // should not be called befor this.data is ready!
        const evalContext = { ...this.model.user.context };
        for (const fieldName in this.activeFields) {
            const value = this.data[fieldName];
            if ([null].includes(value)) {
                // simplify that?
                evalContext[fieldName] = false;
            } else if (isX2Many(this.fields[fieldName])) {
                const list = this._cache[fieldName];
                evalContext[fieldName] = list.getContext();
                // ---> implied to initialize (resIds, commands) currentIds before loading static list
            } else if (value && this.fields[fieldName].type === "date") {
                evalContext[fieldName] = value.toFormat("yyyy-LL-dd");
            } else if (value && this.fields[fieldName].type === "datetime") {
                evalContext[fieldName] = value.toFormat("yyyy-LL-dd HH:mm:ss");
            } else if (value && this.fields[fieldName].type === "many2one") {
                evalContext[fieldName] = value[0];
            } else if (value && this.fields[fieldName].type === "reference") {
                evalContext[fieldName] = `${value.resModel},${value.resId}`;
            } else {
                evalContext[fieldName] = value;
            }
        }
        evalContext.id = this.resId || false;
        if (this.getParentRecordContext) {
            evalContext.parent = this.getParentRecordContext();
        }
        return evalContext;
    }

    get evalContext() {
        return {
            // ...
            ...this.dataContext,
        };
    }

    /**
     * Since the ORM can support both `active` and `x_active` fields for
     * the archiving mechanism, check if any such field exists and prioritize
     * them. The `active` field should always take priority over its custom
     * version.
     *
     * @returns {boolean} true iff the field is active or there is no `active`
     *   or `x_active` field on the model
     */
    get isActive() {
        if ("active" in this.activeFields) {
            return this.data.active;
        } else if ("x_active" in this.activeFields) {
            return this.data.x_active;
        }
        return true;
    }

    get isDirty() {
        // to change (call isDirty on x2many children...) (maybe not)
        return this._changes ? Object.keys(this._changes).length > 0 : true;
    }

    get isInEdition() {
        return this.mode === "edit";
    }

    get isVirtual() {
        return !this.resId;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    async archive() {
        await toggleArchive(this.model, this.resModel, [this.resId], true);
        await this.load();
        this.model.notify();
    }

    checkValidity() {
        for (const fieldName in this._requiredFields) {
            const fieldType = this.fields[fieldName].type;
            if (!evalDomain(this._requiredFields[fieldName], this.evalContext)) {
                this._removeInvalidFields([fieldName]);
                continue;
            }
            switch (fieldType) {
                case "boolean":
                case "float":
                case "integer":
                    continue;
                case "one2many":
                case "many2many":
                    if (!this.isX2ManyValid(fieldName)) {
                        this.setInvalidField(fieldName);
                    }
                    break;
                default:
                    if (this.isRequired(fieldName) && !this.data[fieldName]) {
                        this.setInvalidField(fieldName);
                    }
            }
        }
        return !this._invalidFields.size;
    }

    async delete() {
        const unlinked = await this.model.orm.unlink(this.resModel, [this.resId], this.context);
        if (!unlinked) {
            return false;
        }
        const index = this.resIds.indexOf(this.resId);
        this.resIds.splice(index, 1);
        this.resId = this.resIds[Math.min(index, this.resIds.length - 1)] || false;
        if (this.resId) {
            await this.load();
            this.model.notify();
        } else {
            this.data = {};
            this._values = {};
            this._changes = {};
            this.preloadedData = {};
        }
    }

    discard() {
        clearObject(this._changes);
        clearObject(this._domains);
        for (const fieldName in this.activeFields) {
            // activeFields should be changed
            const field = this.fields[fieldName];
            if (isX2Many(field)) {
                this.data[fieldName].discard();
            } else if (fieldName in this._values) {
                this.data[fieldName] = this._values[fieldName];
            }
        }
        if (!this.isVirtual) {
            this.switchMode("readonly");
        }
        this.model.notify();
    }

    // FIXME AAB: to discuss: not sure we want to keep resIds in the model (this concerns
    // "duplicate" and "delete"). Alternative: handle this in form_view (but then what's the
    // point of calling a Record method to do the operation?)
    async duplicate() {
        const kwargs = { context: this.context };
        const index = this.resIds.indexOf(this.resId);
        this.resId = await this.model.orm.call(this.resModel, "copy", [this.resId], kwargs);
        this.resIds.splice(index + 1, 0, this.resId);
        await this.load();
        this.switchMode("edit");
        this.model.notify();
    }

    exportState() {
        return {
            mode: this.mode,
            resId: this.resId,
            resIds: this.resIds,
        };
    }

    getChanges(allFields = false, parentChanges = false) {
        const changes = { ...(allFields ? this.data : this._changes) };
        for (const fieldName in changes) {
            const fieldType = this.fields[fieldName].type;
            if (["one2many", "many2many"].includes(fieldType)) {
                const staticList = this._cache[fieldName];
                changes[fieldName] = staticList.getCommands(allFields); // always ask
                if (!changes[fieldName]) {
                    delete changes[fieldName];
                }
            } else if (fieldType === "many2one") {
                changes[fieldName] = changes[fieldName] ? changes[fieldName][0] : false;
            } else if (fieldType === "date") {
                changes[fieldName] = changes[fieldName] ? serializeDate(changes[fieldName]) : false;
            } else if (fieldType === "datetime") {
                changes[fieldName] = changes[fieldName]
                    ? serializeDateTime(changes[fieldName])
                    : false;
            } else if (fieldType === "reference") {
                const value = changes[fieldName];
                changes[fieldName] = value ? `${value.resModel},${value.resId}` : false;
            }
        }

        const relationalFieldChanges = {};
        if (allFields && parentChanges && this.relationField && this.parentRecord) {
            relationalFieldChanges[this.relationField] = this.parentRecord.getChanges(allFields);
        }

        return {
            ...this._rawChanges,
            ...changes,
            ...relationalFieldChanges,
        };
    }

    getFieldContext(fieldName) {
        return Object.assign(
            this.context,
            makeContext([this.activeFields[fieldName].context], this.evalContext)
        );
    }

    getFieldDomain(fieldName) {
        return Domain.and([
            this._domains[fieldName] || [],
            this.fields[fieldName].domain || [],
            this.activeFields[fieldName].domain || [],
        ]);
    }

    isInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isInvisible(fieldName) {
        const activeField = this.activeFields[fieldName];
        const { invisible } = activeField.modifiers || {};
        return invisible ? evalDomain(invisible, this.evalContext) : false;
    }

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isReadonly(fieldName) {
        const activeField = this.activeFields[fieldName];
        const { readonly } = activeField.modifiers || {};
        return readonly ? evalDomain(readonly, this.evalContext) : false;
    }

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isRequired(fieldName) {
        const required = this._requiredFields[fieldName];
        return required ? evalDomain(required, this.evalContext) : false;
    }

    isX2ManyValid(fieldName) {
        const value = this.data[fieldName];
        return value.records.every((r) => r.checkValidity());
    }

    async load(params = {}) {
        this._cache = {};
        for (const fieldName in this.activeFields) {
            const field = this.fields[fieldName];
            if (isX2Many(field)) {
                const staticList = this._createStaticList(fieldName);
                this._cache[fieldName] = staticList;
            }
        }

        if (this.isVirtual) {
            const changes = params.changes || (await this._onChange());
            await this._load({ changes });
        } else {
            let values = params.values || {};
            const missingFields = this.fieldNames.filter((fieldName) => !(fieldName in values));
            if (missingFields.length) {
                values = Object.assign({}, values, await this._read(missingFields));
            }
            await this._load({ values });
        }
    }

    async loadPreloadedData() {
        const fetchPreloadedData = async (info, fieldName) => {
            if (!info.loadOnTypes.includes(this.fields[fieldName].type)) {
                return;
            }
            const domain = this.getFieldDomain(fieldName).toList(this.evalContext).toString();
            const getExtraKey = info.extraMemoizationKey || (() => null);
            const key = JSON.stringify([domain, getExtraKey(this, fieldName)]);
            if (this.preloadedDataCaches[fieldName] !== key) {
                this.preloadedDataCaches[fieldName] = key;
                this.preloadedData[fieldName] = await info.preload(this.model.orm, this, fieldName);
            }
        };

        const proms = [];
        for (const fieldName in this.activeFields) {
            const activeField = this.activeFields[fieldName];
            // @FIXME type should not be get like this
            const type = activeField.widget || this.fields[fieldName].type;
            if (!this.isInvisible(fieldName) && preloadedDataRegistry.contains(type)) {
                proms.push(fetchPreloadedData(preloadedDataRegistry.get(type), fieldName));
            }
        }
        await Promise.all(proms);
    }

    async loadRelationalData() {
        const proms = [];
        for (const fieldName in this.activeFields) {
            const field = this.fields[fieldName];
            if (field.type === "many2one") {
                proms.push(
                    this._loadMany2OneData(fieldName, this.data[fieldName]).then((value) => {
                        this.data[fieldName] = value;
                        this._values[fieldName] = value;
                    })
                );
            } else if (field.type === "reference") {
                proms.push(
                    this._loadReference(fieldName, this.data[fieldName]).then((value) => {
                        this.data[fieldName] = value;
                        this._values[fieldName] = value;
                    })
                );
            } else if (isX2Many(field)) {
                proms.push(this._loadX2ManyData(fieldName));
            }
        }
        await Promise.all(proms);
    }

    /**
     *
     * @param {Object} options
     * @param {boolean} [options.stayInEdition=false]
     * @param {boolean} [options.noReload=false] prevents the record from
     *  reloading after changes are applied, typically used to defer the load.
     * @returns {Promise<boolean>}
     */
    async save(options = { stayInEdition: false, noReload: false }) {
        return this.model.mutex.exec(() => this._save(options));
    }

    async setInvalidField(fieldName) {
        if (this.selected && this.model.multiEdit) {
            const dialogProps = {
                body: this.model.env._t("No valid record to save"),
                confirm: () => {
                    this.discard();
                },
            };
            await this.model.dialogService.add(AlertDialog, dialogProps);
        } else {
            this._invalidFields.add(fieldName);
            this.model.notify();
        }
    }

    /**
     * @param {"edit" | "readonly"} mode
     * @returns {Promise<void>}
     */
    async switchMode(mode) {
        if (this.mode === mode) {
            return;
        }
        const preventSwitch = await this._onWillSwitchMode(this, mode);
        if (preventSwitch === false) {
            return;
        }
        if (mode === "readonly") {
            for (const fieldName in this.activeFields) {
                const field = this.fields[fieldName];
                if (isX2Many(field)) {
                    const editedRecord = this.data[fieldName] && this.data[fieldName].editedRecord;
                    if (editedRecord) {
                        editedRecord.switchMode("readonly");
                    }
                }
            }
        }
        this.mode = mode;
        this.model.notify();
    }

    toggleSelection(selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
        this.model.notify();
    }

    async unarchive() {
        await toggleArchive(this.model, this.resModel, [this.resId], false);
        await this.load();
        this.model.notify();
    }

    async update(changes) {
        return this.model.mutex.exec(async () => {
            await this._applyChanges(changes);
            if (this.selected && this.model.multiEdit) {
                await this.model.root._multiSave(this);
            } else {
                const proms = [];
                const fieldNames = Object.keys(changes);
                if (fieldNames.length) {
                    this.onChanges();
                }
                this._removeInvalidFields(fieldNames);
                if (
                    fieldNames.some(
                        (fieldName) =>
                            this.activeFields[fieldName] && this.activeFields[fieldName].onChange
                    )
                ) {
                    const changes = await this._onChange(fieldNames);
                    for (const [fieldName, value] of Object.entries(changes)) {
                        const field = this.fields[fieldName];
                        // for x2many fields, the onchange returns commands, not ids, so we need to process them
                        // for now, we simply return an empty list
                        if (isX2Many(field)) {
                            this._changes[fieldName] = value;
                            this.data[fieldName].applyCommands(value);
                            proms.push(this.data[fieldName].load());
                        } else {
                            this._changes[fieldName] = value;
                            this.data[fieldName] = this._changes[fieldName];
                        }
                    }
                }
                proms.push(this.loadPreloadedData());
                await Promise.all(proms);
                this.canBeAbandoned = false;
                this.model.notify();
            }
        });
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _applyChanges(changes) {
        for (let [fieldName, value] of Object.entries(changes)) {
            const field = this.fields[fieldName];
            if (field && isX2Many(field)) {
                this._changes[fieldName] = value;
                await this.data[fieldName].update(value);
            } else {
                if (field && field.type === "many2one") {
                    value = await this.__applyMany2OneChange(fieldName, value);
                } else if (field && field.type === "reference") {
                    value = await this._loadReference(fieldName, value);
                }
                this.data[fieldName] = value;
                this._changes[fieldName] = value;
            }
        }
    }

    async __applyMany2OneChange(fieldName, nameGet) {
        if (!nameGet) {
            return false;
        }
        let [id, label] = nameGet;

        if (!id && !label) {
            return [false, ""];
        }
        const relation = this.fields[fieldName].relation;
        if (!id && label) {
            // only display_name given -> do a name_create
            const res = await this.model.orm.call(relation, "name_create", [label], {
                context: this.context,
            });
            // Check if a record is really created. Models without defined
            // _rec_name cannot create record based on name_create.
            if (!res) {
                return [false, ""]; // not sure about ""
            }
            id = res[0];
            label = res[1];
        }
        return [id, label];
    }

    _createStaticList(fieldName) {
        const field = this.fields[fieldName];
        const activeField = this.activeFields[fieldName];
        const { fieldsToFetch, relatedFields = {}, views = {}, viewMode } = activeField;
        const fields = {
            id: { name: "id", type: "integer", readonly: true },
            ...relatedFields,
            ...fieldsToFetch,
        };
        const activeFields = (views[viewMode] && views[viewMode].activeFields) || {
            ...fieldsToFetch,
        };
        for (const fieldName in relatedFields) {
            if (relatedFields[fieldName].active) {
                activeFields[fieldName] = relatedFields[fieldName]; // a field and an active field are not the same thing
                // bad idea
            }
        }
        const limit = views[viewMode] && views[viewMode].limit;
        const orderBy = views[viewMode] && views[viewMode].defaultOrder;

        const editable = views[viewMode] && views[viewMode].editable;

        const list = this.model.createDataPoint("static_list", {
            resModel: this.fields[fieldName].relation,
            field,
            fields,
            activeFields,
            getParentRecordContext: () => this.dataContext,
            limit,
            orderBy,
            editable,
            rawContext: {
                parent: this.rawContext,
                make: () => {
                    return makeContext([activeField.context], {
                        ...this.evalContext,
                        ...list.evalContext,
                    });
                },
            },
            parentRecord: this,
            relationField: field.relation_field,
            views,
            viewMode,
            onChanges: async () => {
                this._changes[fieldName] = list;
                const proms = [];
                if (activeField && activeField.onChange && this.isX2ManyValid(fieldName)) {
                    const changes = await this._onChange([fieldName]);
                    const proms = [];
                    for (const [fieldName, value] of Object.entries(changes)) {
                        const field = this.fields[fieldName];
                        // for x2many fields, the onchange returns commands, not ids, so we need to process them
                        // for now, we simply return an empty list
                        if (isX2Many(field)) {
                            this._changes[fieldName] = value;
                            this.data[fieldName].applyCommands(value);
                            proms.push(this.data[fieldName].load());
                        } else {
                            this._changes[fieldName] = value;
                            this.data[fieldName] = this._changes[fieldName];
                        }
                    }
                }
                this.canBeAbandoned = false;
                await Promise.all(proms);
                if (this.selected && this.model.multiEdit) {
                    await this.model.root.multiSave(this);
                }
                this.onChanges();
            },
        });

        return list;
    }

    _getDefaultValues() {
        const defaultValues = {};
        for (const fieldName of this.fieldNames) {
            const field = this.fields[fieldName];
            if (isNumeric(field)) {
                defaultValues[fieldName] = 0;
            } else if (["date", "datetime"].includes(field.type)) {
                defaultValues[fieldName] = false;
            } else if (isX2Many(field)) {
                defaultValues[fieldName] = [];
            } else {
                defaultValues[fieldName] = null;
            }
        }
        return defaultValues;
    }

    _getOnchangeSpec() {
        const specs = {};
        function buildSpec(activeFields, prefix) {
            for (const [fieldName, activeField] of Object.entries(activeFields)) {
                const key = prefix ? `${prefix}.${fieldName}` : fieldName;
                specs[key] = activeField.onChange ? "1" : "";
                const subViewInfo = activeField.views && activeField.views[activeField.viewMode];
                if (subViewInfo) {
                    buildSpec(subViewInfo.activeFields, key);
                }
            }
        }
        buildSpec(this.activeFields);
        return specs;
    }

    /**
     * @param {Object} params
     * @param {Object} params.values
     * @param {Object} params.changes
     */
    async _load(params = {}) {
        this._values = params.values || {};
        this._changes = params.changes || {};
        this._rawChanges = { ...this._changes };
        const defaultValues = this._getDefaultValues();
        for (const fieldName in this.activeFields) {
            delete this._rawChanges[fieldName];
            const field = this.fields[fieldName];
            if (isX2Many(field)) {
                const resIds = this._values[fieldName];
                const commands = this._changes[fieldName];
                const staticList = this._cache[fieldName];
                staticList.setCurrentIds(resIds, commands);
                this._values[fieldName] = staticList;
                this._changes[fieldName] = staticList;
                this.data[fieldName] = staticList;
            } else {
                // smth is wrong here for many2one maybe
                if (fieldName in this._changes) {
                    this.data[fieldName] = this._changes[fieldName];
                } else if (fieldName in this._values) {
                    this.data[fieldName] = this._values[fieldName];
                } else {
                    this.data[fieldName] = defaultValues[fieldName];
                }
            }
        }

        await this.loadRelationalData();
        await this.loadPreloadedData();

        // every field value should be correct here
        this._invalidFields.clear();
    }

    async _loadMany2OneData(fieldName, value) {
        const relation = this.fields[fieldName].relation;
        const activeField = this.activeFields[fieldName];
        if (
            activeField &&
            !this.isInvisible(fieldName) &&
            value &&
            (!value[1] || activeField.options.always_reload)
        ) {
            const context = this.getFieldContext(fieldName);
            const result = await this.model.orm.nameGet(relation, [value[0]], context);
            return result[0];
        }
        return value;
    }

    async _loadReference(fieldName, value) {
        // const modelField = this.activeFields[fieldName].options.model_field;
        // if (modelField) {
        // }
        if (value) {
            if (typeof value === "string") {
                const [resModel, resId] = value.split(",");
                value = { resModel, resId: parseInt(resId, 10) };
            }
            const { resModel, resId } = value;
            const context = this.getFieldContext(fieldName);
            const nameGet = await this.model.orm.nameGet(resModel, [resId], context);
            return {
                resModel,
                resId,
                displayName: nameGet[0][1],
            };
        } else {
            return false;
        }
    }

    async _loadX2ManyData(fieldName) {
        if (!this.isInvisible(fieldName)) {
            await this.data[fieldName].load();
        }
    }

    async _onChange(fieldNames) {
        if (!this.fieldNames.length) {
            return;
        }

        const { domain, value: changes, warning } = await this.model.orm.call(
            this.resModel,
            "onchange",
            [
                [],
                this.getChanges(true, true),
                fieldNames && fieldNames.length ? fieldNames : [],
                this._getOnchangeSpec(),
            ],
            { context: this.context }
        );
        if (warning) {
            const { type, title, message } = warning;
            if (type === "dialog") {
                this.model.dialogService.add(WarningDialog, { title, message });
            } else {
                this.model.notificationService.add(message, {
                    className: warning.className,
                    sticky: warning.sticky,
                    title,
                    type: "warning",
                });
            }
        }
        if (domain) {
            // do this outside
            Object.assign(this._domains, domain);
        }
        return this._parseServerValues(changes);
    }

    async _read(fieldNames) {
        fieldNames = fieldNames || this.fieldNames;
        if (!fieldNames.length) {
            return {};
        }
        const [serverValues] = await this.model.orm.read(this.resModel, [this.resId], fieldNames, {
            bin_size: true,
            ...this.context,
        });
        return this._parseServerValues(serverValues);
    }

    _removeInvalidFields(fieldNames) {
        for (const fieldName of fieldNames) {
            this._invalidFields.delete(fieldName);
        }
    }

    _sanitizeValues(values) {
        if (this.resModel !== this.model.resModel) {
            return values;
        }
        const sanitizedValues = {};
        for (const fieldName in values) {
            if (this.fields[fieldName].type === "char") {
                sanitizedValues[fieldName] = values[fieldName] || "";
            } else {
                sanitizedValues[fieldName] = values[fieldName];
            }
        }
        return sanitizedValues;
    }

    /**
     *
     * @param {Object} options
     * @param {boolean} [options.stayInEdition=false]
     * @param {boolean} [options.noReload=false] prevents the record from
     *  reloading after changes are applied, typically used to defer the load.
     * @returns {Promise<boolean>}
     */
    async _save(options = { stayInEdition: false, noReload: false }) {
        if (!this.checkValidity()) {
            const invalidFields = [...this._invalidFields].map((fieldName) => {
                return `<li>${escape(this.fields[fieldName].string || fieldName)}</li>`;
            }, this);
            this.model.notificationService.add(markup(`<ul>${invalidFields.join("")}</ul>`), {
                title: this.model.env._t("Invalid fields: "),
                type: "danger",
            });
            return false;
        }
        const changes = this.getChanges();
        const keys = Object.keys(changes);
        const hasChanges = this.isVirtual || keys.length;
        const shouldReload = hasChanges ? !options.noReload : false;

        if (this.isVirtual) {
            if (keys.length === 1 && keys[0] === "display_name") {
                const [resId] = await this.model.orm.call(
                    this.resModel,
                    "name_create",
                    [changes.display_name],
                    { context: this.context }
                );
                this.resId = resId;
            } else {
                this.resId = await this.model.orm.create(this.resModel, changes, this.context);
            }
            delete this.virtualId;
            this.data.id = this.resId;
            this.resIds.push(this.resId);
        } else if (keys.length > 0) {
            await this.model.orm.write(this.resModel, [this.resId], changes, this.context);
        }
        // Switch to the parent active fields
        if (this.parentActiveFields) {
            this.activeFields = this.parentActiveFields;
            this.parentActiveFields = false;
        }
        this.isInQuickCreation = false;
        if (shouldReload) {
            this.model.trigger("record-updated", { record: this });
            await this.load();
            this.model.notify();
        }
        if (!options.stayInEdition) {
            this.switchMode("readonly");
        }
        return true;
    }

    _setRequiredFields() {
        for (const [fieldName, activeField] of Object.entries(this.activeFields)) {
            const { modifiers } = activeField;
            if (modifiers && modifiers.required) {
                this._requiredFields[fieldName] = modifiers.required;
            }
        }
    }
}

class DynamicList extends DataPoint {
    setup(params, state) {
        this.groupBy = params.groupBy || [];
        this.domain = markRaw(params.domain || []);
        this.orderBy = params.orderBy || []; // rename orderBy + get back from state
        this.offset = state.offset || 0;
        this.count = 0;
        this.limit = params.limit || state.limit || this.constructor.DEFAULT_LIMIT;
        this.isDomainSelected = false;
        this.loadedCount = state.loadedCount || 0;
        this.previousParams = state.previousParams || "[]";

        this.editedRecord = null;
        this.onCreateRecord = params.onCreateRecord || (() => {});
        this.onRecordWillSwitchMode = async (record, mode) => {
            const editedRecord = this.editedRecord;
            this.editedRecord = null;
            if (!params.onRecordWillSwitchMode && editedRecord) {
                // not really elegant, but we only need the root list to save the record
                if (editedRecord !== record && editedRecord.canBeAbandoned) {
                    this.abandonRecord(editedRecord.id);
                } else {
                    const isSaved = await editedRecord.save();
                    if (!isSaved) {
                        this.editedRecord = editedRecord;
                        return false;
                    }
                }
            }
            if (mode === "edit") {
                this.editedRecord = record;
            }
            if (params.onRecordWillSwitchMode) {
                params.onRecordWillSwitchMode(record, mode);
            }
        };
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get currentParams() {
        return JSON.stringify([this.domain, this.groupBy]);
    }

    get firstGroupBy() {
        return this.groupBy[0] || false;
    }

    get groupByField() {
        if (!this.firstGroupBy) {
            return false;
        }
        const [groupByFieldName] = this.firstGroupBy.split(":");
        return {
            attrs: {},
            ...this.fields[groupByFieldName],
            ...this.activeFields[groupByFieldName],
        };
    }

    get isM2MGrouped() {
        return this.groupBy.some((fieldName) => this.fields[fieldName].type === "many2many");
    }

    get selection() {
        return this.records.filter((r) => r.selected);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    abandonRecord(recordId) {
        // TODO
        const record = this.records.find((r) => r.id === recordId);
        this.removeRecord(record);
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async archive(isSelected) {
        const resIds = await this.getResIds(isSelected);
        await toggleArchive(this.model, this.resModel, resIds, true);
        await this.model.load();
        return resIds;
        //todo fge _invalidateCache
    }

    canQuickCreate() {
        return (
            this.groupByField &&
            this.model.onCreate === "quick_create" &&
            (isAllowedDateField(this.groupByField) ||
                QUICK_CREATE_FIELD_TYPES.includes(this.groupByField.type))
        );
    }

    exportState() {
        return {
            limit: this.limit,
            loadedCount: this.records.length,
            previousParams: this.currentParams,
        };
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async getResIds(isSelected) {
        let resIds;
        if (isSelected) {
            if (this.isDomainSelected) {
                resIds = await this.model.orm.search(this.resModel, this.domain, {
                    limit: session.active_ids_limit,
                });
            } else {
                resIds = this.selection.map((r) => r.resId);
            }
        } else {
            resIds = this.records.map((r) => r.resId);
        }
        return resIds;
    }

    async multiSave(record) {
        return this.model.mutex.exec(() => this._multiSave(record));
    }

    selectDomain(value) {
        this.isDomainSelected = value;
        this.model.notify();
    }

    async sortBy(fieldName) {
        if (this.orderBy.length && this.orderBy[0].name === fieldName) {
            this.orderBy[0].asc = !this.orderBy[0].asc;
        } else {
            this.orderBy = this.orderBy.filter((o) => o.name !== fieldName);
            this.orderBy.unshift({
                name: fieldName,
                asc: true,
            });
        }

        await this.load();
        this.model.notify();
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async unarchive(isSelected) {
        const resIds = await this.getResIds(isSelected);
        await toggleArchive(this.model, this.resModel, resIds, false);
        await this.model.load();
        return resIds;
        //todo fge _invalidateCache
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    async _multiSave(record) {
        if (this.blockUpdate) {
            return;
        }
        const selection = this.selection;
        const changes = record.getChanges();
        if (!changes) {
            return;
        }
        const validSelection = selection.reduce((result, record) => {
            if (
                !Object.keys(changes).filter(
                    (fieldName) =>
                        record.isReadonly(fieldName) ||
                        (record.isRequired(fieldName) && !changes[fieldName])
                ).length
            ) {
                result.push(record);
            }
            return result;
        }, []);

        if (validSelection.length === 0) {
            const dialogProps = {
                body: this.model.env._t("No valid record to save"),
                confirm: () => {
                    record.discard();
                },
            };
            await this.model.dialogService.add(AlertDialog, dialogProps);
        } else if (validSelection.length > 1) {
            this.editedRecord = null;
            const dialogProps = {
                confirm: async () => {
                    const resIds = validSelection.map((r) => r.resId);
                    await this.model.orm.write(this.resModel, resIds, changes, this.context);
                    validSelection.forEach((record) => {
                        record.selected = false;
                    });
                    await Promise.all(validSelection.map((record) => record.load()));
                    record.switchMode("readonly");
                },
                cancel: () => {
                    record.discard();
                },
                isDomainSelected: this.isDomainSelected,
                fields: Object.keys(changes).map((fieldName) => {
                    const label =
                        record.activeFields[fieldName].string || record.fields[fieldName].string;
                    const widget = record.activeFields[fieldName].widget;
                    return { name: fieldName, label, widget };
                }),
                nbRecords: selection.length,
                nbValidRecords: validSelection.length,
                record,
            };
            await this.model.dialogService.add(ListConfirmationDialog, dialogProps);
        } else {
            await record._save();
            record.selected = false;
        }
    }

    /**
     * Calls the method 'resequence' on the current resModel.
     * If 'movedId' is provided, the record matching that ID will be resequenced
     * in the current list of IDs, at the start of the list or after the record
     * matching 'targetId' if given as well.
     *
     * @param {(Group | Record)[]} list
     * @param {string} idProperty property on the given list used to determine each ID
     * @param {string} [movedId]
     * @param {string} [targetId]
     * @param {Object} [options={}]
     * @param {string} [options.handleField]
     * @returns {Promise<(Group | Record)[]>}
     */
    async _resequence(list, idProperty, movedId, targetId, options = {}) {
        if (movedId) {
            const target = list.find((r) => r.id === movedId);
            const index = targetId ? list.findIndex((r) => r.id === targetId) : 0;
            list = list.filter((r) => r.id !== movedId);
            list.splice(index, 0, target);
        }
        const handleField = options.handleField || "sequence";
        const model = this.resModel;
        const ids = [];
        const sequences = [];
        for (const el of list) {
            if (el[idProperty]) {
                ids.push(el[idProperty]);
                sequences.push(el[handleField]);
            }
        }
        // FIMME: can't go though orm, so no context given
        const wasResequenced = await this.model.rpc("/web/dataset/resequence", {
            model,
            ids,
            field: handleField,
            offset: Math.min(...sequences),
            context: this.context,
        });

        if (wasResequenced) {
            await this.model.orm.read(this.resModel, ids, [handleField], {
                context: this.context,
            });
            // TODO: use result of read (see wasResequenced in BasicModel)
        }

        this.model.notify();
        return list;
    }

    unselectRecord() {
        const editedRecord = this.editedRecord;
        if (editedRecord) {
            const canBeAbandoned = editedRecord.canBeAbandoned;
            if (!canBeAbandoned && editedRecord.checkValidity()) {
                return editedRecord.switchMode("readonly");
            } else if (canBeAbandoned) {
                return this.abandonRecord(editedRecord.id);
            }
        }
    }
}

DynamicList.DEFAULT_LIMIT = 80;

export class DynamicRecordList extends DynamicList {
    setup(params) {
        super.setup(...arguments);

        /** @type {Record[]} */
        this.records = [];
        this.data = params.data;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get quickCreateRecord() {
        return this.records.find((r) => r.isInQuickCreation);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {Record} record
     * @param {number} [index]
     * @returns {Record}
     */
    addRecord(record, index) {
        this.records.splice(Number.isInteger(index) ? index : this.records.length, 0, record);
        this.count++;
        this.model.notify();
        return record;
    }

    async cancelQuickCreate(force = false) {
        const record = this.quickCreateRecord;
        if (record && (force || !record.isDirty)) {
            this.removeRecord(record);
        }
    }

    /**
     * @param {Object} [params={}]
     * @param {boolean} [atFirstPosition]
     * @returns {Promise<Record>} the newly created record
     */
    async createRecord(params = {}, atFirstPosition = false) {
        const newRecord = this.model.createDataPoint("record", {
            resModel: this.resModel,
            fields: this.fields,
            activeFields: this.activeFields,
            parentActiveFields: this.activeFields,
            onRecordWillSwitchMode: this.onRecordWillSwitchMode,
            defaultContext: this.defaultContext,
            ...params,
        });
        if (this.model.useSampleModel) {
            this.model.useSampleModel = false;
            await this.load();
        }
        await this.model.mutex.exec(() => newRecord.load());
        this.editedRecord = newRecord;
        this.onCreateRecord(newRecord);
        return this.addRecord(newRecord, atFirstPosition ? 0 : this.count);
    }

    /**
     * @param {Record[]} [records=[]]
     * @returns {Promise<number[]>}
     */
    async deleteRecords(records = []) {
        let deleted = false;
        let resIds;
        if (records.length) {
            resIds = records.map((r) => r.resId);
        } else {
            resIds = await this.getResIds(true);
            records = this.records.filter((r) => resIds.includes(r.resId));
            if (this.isDomainSelected) {
                await this.model.orm.unlink(this.resModel, resIds, this.context);
                deleted = true;
            }
        }
        if (!deleted) {
            await Promise.all(records.map((record) => record.delete()));
        }
        for (const record of records) {
            this.removeRecord(record);
        }
        await this._adjustOffset();
        return resIds;
    }

    empty() {
        this.records = [];
        this.count = 0;
    }

    async load(params = {}) {
        this.limit = params.limit === undefined ? this.limit : params.limit;
        this.offset = params.offset === undefined ? this.offset : params.offset;
        this.records = await this._loadRecords();
        await this._adjustOffset();
    }

    async loadMore() {
        this.offset = this.records.length;
        const nextRecords = await this._loadRecords();
        for (const record of nextRecords) {
            this.addRecord(record);
        }
    }

    async quickCreate(activeFields, context) {
        const record = this.quickCreateRecord;
        if (record) {
            this.removeRecord(record);
        }
        const rawContext = {
            parent: this.rawContext,
            make: () => makeContext([context, {}]),
        };
        return this.createRecord({ activeFields, rawContext, isInQuickCreation: true }, true);
    }

    /**
     * @param {Record} record
     * @returns {Record}
     */
    removeRecord(record) {
        const index = this.records.findIndex((r) => r === record);
        if (index < 0) {
            return;
        }
        this.records.splice(index, 1);
        this.count--;
        if (this.editedRecord === record) {
            this.editedRecord = null;
        }
        this.model.notify();
        return record;
    }

    async resequence() {
        this.records = await this._resequence(this.records, "resId", ...arguments);
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    /**
     * Reload the model if more records should appear on the current page.
     *
     * @returns {Promise<void>}
     */
    async _adjustOffset() {
        if (this.offset && !this.records.length) {
            this.offset = Math.max(this.offset - this.limit, 0);
            await this.load();
        }
    }

    /**
     * @returns {Promise<Record[]>}
     */
    async _loadRecords() {
        const options = {
            limit: this.limit,
            offset: this.offset,
            order: orderByToString(this.orderBy),
        };
        if (this.loadedCount > this.limit) {
            // This condition means that we are reloading a list of records
            // that has been manually extended: we need to load exactly the
            // same amount of records.
            options.limit = this.loadedCount;
            options.offset = 0;
        }
        const { records: rawRecords, length } =
            this.data ||
            (await this.model.orm.webSearchRead(
                this.resModel,
                this.domain,
                this.fieldNames,
                options,
                { bin_size: true, ...this.context }
            ));

        const records = await Promise.all(
            rawRecords.map(async (data) => {
                data = this._parseServerValues(data);
                const record = this.model.createDataPoint("record", {
                    resModel: this.resModel,
                    resId: data.id,
                    fields: this.fields,
                    activeFields: this.activeFields,
                    rawContext: this.rawContext,
                    onRecordWillSwitchMode: this.onRecordWillSwitchMode,
                });
                await record.load({ values: data });
                return record;
            })
        );

        delete this.data;
        this.count = length;

        return records;
    }
}

export class DynamicGroupList extends DynamicList {
    setup(params, state) {
        super.setup(...arguments);

        this.groupByInfo = params.groupByInfo || {}; // FIXME: is this something specific to the list view?
        this.openGroupsByDefault = params.openGroupsByDefault || false;
        /** @type {Group[]} */
        this.groups = state.groups || [];
        this.activeFields = params.activeFields;
        this.isGrouped = true;
        this.quickCreateInfo = null; // Lazy loaded;
        this.expand = params.expand;
        this.limitByGroup = this.limit;
        this.limit =
            params.groupsLimit ||
            (this.expand ? this.constructor.DEFAULT_LOAD_LIMIT : this.constructor.DEFAULT_LIMIT);
        this.onCreateRecord =
            params.onCreateRecord ||
            ((record) => {
                this.editedRecord = record;
            });
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get commonGroupParams() {
        return {
            fields: this.fields,
            activeFields: this.activeFields,
            resModel: this.resModel,
            domain: this.domain,
            groupBy: this.groupBy.slice(1),
            orderBy: this.orderBy,
            limit: this.limitByGroup,
            groupByInfo: this.groupByInfo,
            rawContext: this.rawContext,
            onCreateRecord: this.onCreateRecord,
            onRecordWillSwitchMode: this.onRecordWillSwitchMode,
        };
    }

    /**
     * List of loaded records inside groups.
     */
    get records() {
        return this.groups
            .filter((group) => !group.isFolded)
            .map((group) => group.list.records)
            .flat();
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {Group} group
     * @param {number} [index]
     * @returns {Group}
     */
    addGroup(group, index) {
        this.groups.splice(Number.isInteger(index) ? index : this.count, 0, group);
        this.count++;
        this.model.notify();
        return group;
    }

    canQuickCreate() {
        return super.canQuickCreate() && this.groups.length;
    }

    /**
     * @param {any} value
     * @returns {Promise<Group>}
     */
    async createGroup(value) {
        const [id, displayName] = await this.model.mutex.exec(() =>
            this.model.orm.call(this.groupByField.relation, "name_create", [value], {
                context: this.context,
            })
        );
        const group = this.model.createDataPoint("group", {
            ...this.commonGroupParams,
            count: 0,
            value: id,
            displayName,
            aggregates: {},
            groupByField: this.groupByField,
            rawContext: this.rawContext,
            // FIXME
            // groupDomain: this.groupDomain,
        });
        group.isFolded = false;
        return this.addGroup(group);
    }

    /**
     * @param {Group[]} groups
     * @returns {Promise<void>}
     */
    async deleteGroups(groups) {
        let shouldReload = false;
        await Promise.all(
            groups.map(async (group) => {
                await group.delete();
                if (!this.model.useSampleModel && group.list.records.length) {
                    shouldReload = true;
                }
            })
        );
        if (shouldReload) {
            await this.model.load();
        } else {
            for (const group of groups) {
                this.removeGroup(group);
            }
        }
    }

    async deleteRecords() {
        for (const group of this.groups) {
            group.list.deleteRecords();
        }
    }

    exportState() {
        return {
            ...super.exportState(),
            groups: this.groups,
        };
    }

    /**
     * @param {string} shortType
     * @returns {boolean}
     */
    groupedBy(shortType) {
        const { type } = this.groupByField;
        switch (shortType) {
            case "m2o":
            case "many2one": {
                return type === "many2one";
            }
            case "o2m":
            case "one2many": {
                return type === "one2many";
            }
            case "m2m":
            case "many2many": {
                return type === "many2many";
            }
            case "m2x":
            case "many2x": {
                return ["many2one", "many2many"].includes(type);
            }
            case "x2m":
            case "x2many": {
                return ["one2many", "many2many"].includes(type);
            }
        }
        return false;
    }

    async load(params = {}) {
        this.limit = params.limit || this.limit;
        this.offset = params.offset || this.offset;
        /** @type {[Group, number][]} */
        const previousGroups = this.groups.map((g, i) => [g, i]);
        this.groups = await this._loadGroups();
        await Promise.all(this.groups.map((group) => group.load()));
        if (this.previousParams === this.currentParams) {
            for (const [group, index] of previousGroups) {
                const newGroup = this.groups.find((g) => group.valueEquals(g.value));
                if (!group.deleted && !newGroup) {
                    group.empty();
                    this.groups.splice(index, 0, group);
                }
            }
        }
    }

    async quickCreate(group) {
        if (this.model.useSampleModel) {
            // Empty the groups because they contain sample data
            this.groups.map((group) => group.empty());
        }
        this.model.useSampleModel = false;
        if (!this.quickCreateInfo) {
            this.quickCreateInfo = await this._loadQuickCreateView();
        }
        group = group || this.groups[0];
        if (group.isFolded) {
            await group.toggle();
        }
        await group.quickCreate(this.quickCreateInfo.activeFields, this.context);
    }

    /**
     * @param {Group} group
     * @returns {Group}
     */
    removeGroup(group) {
        const index = this.groups.findIndex((g) => g === group);
        this.groups.splice(index, 1);
        this.count--;
        this.model.notify();
        return group;
    }

    removeRecord(record) {
        for (const group of this.groups) {
            const removedRecord = group.list.removeRecord(record);
            if (removedRecord) {
                if (removedRecord === this.editedRecord) {
                    this.editedRecord = null;
                }
                return removedRecord;
            }
        }
    }

    async resequence() {
        this.groups = await this._resequence(this.groups, "value", ...arguments);
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    async _loadGroups() {
        const orderby = orderByToString(this.orderBy);
        const { groups, length } = await this.model.orm.webReadGroup(
            this.resModel,
            this.domain,
            this.fieldNames,
            this.groupBy,
            {
                orderby,
                lazy: true,
                expand: this.expand,
                offset: this.offset,
                limit: this.limit,
            }
        );
        this.count = length;

        const groupByField = this.groupByField;
        let openGroups = 0;

        const groupsParams = groups.map((data) => {
            const groupParams = {
                ...this.commonGroupParams,
                aggregates: {},
                groupByField,
            };
            for (const key in data) {
                const value = data[key];
                switch (key) {
                    case this.firstGroupBy: {
                        if (value && ["date", "datetime"].includes(groupByField.type)) {
                            const dateString = data.__range[groupByField.name].to;
                            const dateValue = this._parseServerValue(groupByField, dateString);
                            const granularity = groupByField.type === "date" ? "day" : "second";
                            groupParams.value = dateValue.minus({ [granularity]: 1 });
                        } else {
                            groupParams.value = Array.isArray(value) ? value[0] : value;
                        }
                        if (groupByField.type === "selection") {
                            groupParams.displayName = Object.fromEntries(groupByField.selection)[
                                groupParams.value
                            ];
                        } else {
                            groupParams.displayName = Array.isArray(value) ? value[1] : value;
                        }
                        if (this.groupedBy("m2x")) {
                            groupParams.recordParams = this.groupByInfo[this.firstGroupBy];
                        }
                        break;
                    }
                    case `${groupByField.name}_count`: {
                        groupParams.count = value;
                        break;
                    }
                    case "__domain": {
                        groupParams.groupDomain = value;
                        break;
                    }
                    case "__fold": {
                        // optional
                        groupParams.isFolded = value;
                        if (!value) {
                            openGroups++;
                        }
                        break;
                    }
                    case "__range": {
                        groupParams.range = value;
                        break;
                    }
                    case "__data": {
                        groupParams.data = value;
                        break;
                    }
                    default: {
                        // other optional aggregated fields
                        if (key in this.fields) {
                            groupParams.aggregates[key] = value;
                        }
                    }
                }
            }
            const previousGroup = this.groups.find(
                (g) => !g.deleted && g.value === groupParams.value
            );
            const state = previousGroup ? previousGroup.exportState() : {};
            return [groupParams, state];
        });

        // Unfold groups that can still be unfolded by default
        if (this.openGroupsByDefault || this.expand) {
            for (const [params, state] of groupsParams) {
                if (openGroups >= this.constructor.DEFAULT_LOAD_LIMIT) {
                    break;
                }
                if (!("isFolded" in { ...params, ...state })) {
                    params.isFolded = false;
                    openGroups++;
                }
            }
        }

        return groupsParams.map(([params, state]) =>
            this.model.createDataPoint("group", params, state)
        );
    }

    async _loadQuickCreateView() {
        if (this.isLoadingQuickCreate) {
            return;
        }
        this.isLoadingQuickCreate = true;
        const { quickCreateView: viewRef } = this.model;
        const { ArchParser } = registry.category("views").get("form");
        let quickCreateFields = DEFAULT_QUICK_CREATE_FIELDS;
        let quickCreateForm = DEFAULT_QUICK_CREATE_VIEW;
        let quickCreateRelatedModels = {};
        if (viewRef) {
            const { fields, relatedModels, views } = await this.model.keepLast.add(
                this.model.viewService.loadViews({
                    context: { ...this.context, form_view_ref: viewRef },
                    resModel: this.resModel,
                    views: [[false, "form"]],
                })
            );
            quickCreateFields = fields;
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        this.isLoadingQuickCreate = false;
        const models = {
            ...quickCreateRelatedModels,
            [this.modelName]: quickCreateFields,
        };
        return new ArchParser().parse(quickCreateForm.arch, models, this.modelName);
    }
}

DynamicGroupList.DEFAULT_LOAD_LIMIT = 10;

export class Group extends DataPoint {
    setup(params, state) {
        this.value = params.value;
        this.displayName = params.displayName;
        this.aggregates = params.aggregates;
        this.groupDomain = params.groupDomain;
        this.range = params.range;
        this.count = params.count;
        this.groupByField = params.groupByField;
        this.groupByInfo = params.groupByInfo;
        this.recordParams = params.recordParams;
        if ("isFolded" in state) {
            this.isFolded = state.isFolded;
        } else if ("isFolded" in params) {
            this.isFolded = params.isFolded;
        } else {
            this.isFolded = true;
        }
        if (isRelational(this.groupByField)) {
            // If the groupBy field is a relational field, the group model must
            // then be the relation of that field.
            this.resModel = this.groupByField.relation;
        }
        const listParams = {
            data: params.data,
            domain: Domain.and([params.domain, this.groupDomain]).toList(),
            groupBy: params.groupBy,
            rawContext: params.rawContext,
            orderBy: params.orderBy,
            resModel: params.resModel,
            activeFields: params.activeFields,
            fields: params.fields,
            limit: params.limit,
            groupByInfo: params.groupByInfo,
            onCreateRecord: params.onCreateRecord,
            onRecordWillSwitchMode: params.onRecordWillSwitchMode,
            defaultContext: {
                ...params.defaultContext,
                [`default_${this.groupByField.name}`]: this.getServerValue(),
            },
        };
        this.list = this.model.createDataPoint("list", listParams, state.listState);
    }

    // ------------------------------------------------------------------------
    // Public
    // ------------------------------------------------------------------------

    /**
     * @see DynamicRecordList.addRecord
     */
    addRecord(record, index) {
        this.count++;
        this.isFolded = false;
        return this.list.addRecord(record, index);
    }

    createRecord(params = {}, atFirstPosition = false) {
        this.count++;
        this.list.createRecord(params, atFirstPosition);
    }

    async delete() {
        this.deleted = true;
        if (this.record) {
            return this.record.delete();
        } else {
            return this.model.orm.unlink(this.resModel, [this.value], this.context);
        }
    }

    /**
     * @see DynamicRecordList.deleteRecords
     */
    async deleteRecords() {
        return this.list.deleteRecords(...arguments);
    }

    empty() {
        this.count = 0;
        this.aggregates = {};
        this.list.empty();
    }

    exportState() {
        return {
            isFolded: this.isFolded,
            listState: this.list.exportState(),
        };
    }

    getAggregableRecords() {
        return this.list.records.filter((r) => !r.isInQuickCreation);
    }

    getAggregates(fieldName) {
        return fieldName ? this.aggregates[fieldName] || 0 : this.count;
    }

    getServerValue() {
        const { name, selection, type } = this.groupByField;
        switch (type) {
            case "many2one":
            case "char":
            case "boolean": {
                return this.value || false;
            }
            case "selection": {
                const descriptor = selection.find((opt) => opt[0] === this.value);
                return descriptor && descriptor[0];
            }
            // for a date/datetime field, we take the last moment of the group as the group value
            case "date":
            case "datetime": {
                const range = this.range[name];
                if (!range) {
                    return false;
                }
                if (type === "date") {
                    return serializeDate(
                        DateTime.fromFormat(range.to, "yyyy-MM-dd", { zone: "utc" }).minus({
                            day: 1,
                        })
                    );
                } else {
                    return serializeDateTime(
                        DateTime.fromFormat(range.to, "yyyy-MM-dd HH:mm:ss").minus({ second: 1 })
                    );
                }
            }
            default: {
                return false; // other field types are not handled
            }
        }
    }

    async load() {
        if (!this.record && this.recordParams) {
            this.record = this.makeRecord(this.recordParams);
            await this.record.load();
        }
        if (!this.isFolded && this.count) {
            await this.list.load();
        }
    }

    makeRecord(params) {
        return this.model.createDataPoint("record", {
            resModel: this.resModel,
            resId: this.value,
            rawContext: this.rawContext,
            ...params,
        });
    }

    quickCreate(activeFields, context) {
        const ctx = {
            ...context,
            [`default_${this.groupByField.name}`]: this.getServerValue(),
        };
        return this.list.quickCreate(activeFields, ctx);
    }

    /**
     * @see DynamicRecordList.removeRecord
     */
    removeRecord(record) {
        this.count--;
        return this.list.removeRecord(record);
    }

    async toggle() {
        this.isFolded = !this.isFolded;
        await this.model.keepLast.add(this.load());
        this.model.notify();
    }

    async validateQuickCreate() {
        const record = this.list.quickCreateRecord;
        if (!record) {
            return false;
        }
        await record.save();
        this.addRecord(this.removeRecord(record));
        this.count++;
        this.list.count++;
        return record;
    }

    valueEquals(value) {
        return this.value instanceof DateTime ? this.value.equals(value) : this.value === value;
    }
}

const add = (arr, el) => {
    const index = arr.indexOf(el);
    if (index === -1) {
        arr.push(el);
    }
};

const remove = (arr, el) => {
    const index = arr.indexOf(el);
    if (index > -1) {
        arr.splice(index, 1);
    }
};

const symbolValues = Symbol("values");

export class StaticList extends DataPoint {
    setup(params, state) {
        this.offset = params.offset || 0;
        this.limit = params.limit || state.limit || this.constructor.DEFAULT_LIMIT;
        this.initialLimit = this.limit;
        this.editable = params.editable || false; // ("bottom" or "top")
        this.field = params.field;
        this.relationField = params.relationField;
        this.parentRecord = params.parentRecord;

        this.orderBy = params.orderBy || [];
        this.isOrder = true;

        // async computation that depends on previous params
        // to be initialized
        this.records = [];

        this._cache = {};
        this._mapping = {}; // maps record.resId || record.virtualId to record.id

        this.views = params.views || {};
        this.viewMode = params.viewMode;

        this.onChanges = params.onChanges || (() => {});

        this.getParentRecordContext = params.getParentRecordContext;

        this.editedRecord = null;
        this.onRecordWillSwitchMode = async (record, mode) => {
            const editedRecord = this.editedRecord;
            this.editedRecord = null;
            if (editedRecord === record && mode === "readonly") {
                return record.checkValidity();
            }
            if (editedRecord) {
                await editedRecord.switchMode("readonly");
            }
            if (mode === "edit") {
                this.editedRecord = record;
            }
        };
    }

    //--------------------------------------------------------------------------
    // Getters
    //--------------------------------------------------------------------------

    /**
     * @returns {number}
     */
    get count() {
        if (!this.currentIds) {
            throw new Error("you rascal");
        }
        return this.currentIds.length;
    }

    get evalContext() {
        return {
            // ...
            parent: this.getParentRecordContext(),
        };
    }

    // ------------------------------------------------------------------------
    // Public
    // ------------------------------------------------------------------------

    /**
     * Add a true record in relation
     * see final API of StaticList in basic_relational_model.js
     */
    async add(params) {
        //
        // if (!params.resId) {
        //     throw new Error("you rascal");
        // }
        // const { resId } = params;
        // this.limit++;
        // this.applyCommand(x2ManyCommands.linkTo(resId));
        // if (!this._mapping[resId]) {
        //     const record = this._createRecord(params);
        //     await record.load();
        // }
        // this.isOrder = false;
        // this.records = this._getRecords();
        // this.onChanges();
        // this.model.notify(); // should be in onChanges?
    }

    /**
     * Add a new record in relation
     * @param {Object} params
     */
    async addNew(params) {
        if (params.resId) {
            throw new Error("you rascal");
        }

        const record = this._createRecord(params);
        await record.load();

        record._onWillSwitchMode(record, "edit"); // bof

        this.limit++;
        this.applyCommand(x2ManyCommands.create(record.virtualId, symbolValues));

        this.isOrder = false;
        this.records = this._getRecords();
        this.onChanges();
        this.model.notify();

        return record;
    }

    applyCommand(command) {
        this.applyCommands([command]);
    }

    /**
     * @param {Array[]} commands  array of commands
     */
    applyCommands(commands) {
        this._commands = this._getNormalizedCommands(this._commands, commands);
        this.currentIds = this._getCurrentIds(this.currentIds, commands);
        this._mapping = this._getNextMapping(this._mapping, commands);
    }

    /**
     * @param {RecordId} recordId
     */
    async delete(recordId) {
        const record = this._cache[recordId];
        if (record.isVirtual) {
            delete this._cache[recordId];
        }
        const id = record.resId || record.virtualId;
        this.applyCommand(x2ManyCommands.delete(id));
        await this._loadRecords();
        this.records = this._getRecords();
        this.onChanges();
        this.model.notify();
    }

    discard() {
        for (const record of Object.values(this._cache)) {
            if (record.isVirtual) {
                delete this._cache[record.id];
            } else {
                record.discard();
            }
        }
        this.limit = this.initialLimit;
        this._commands = [];
        this._commandsById = {};
        this.currentIds = [...this._serverIds];
        this.records = this._getRecords();
    }

    exportState() {
        return {
            limit: this.limit,
        };
    }

    async load() {
        if (!this.count) {
            this.records = [];
            return;
        }

        const orderFieldNames = this.orderBy.map((o) => o.name);
        const isAscByFieldName = {};
        for (const o of this.orderBy) {
            isAscByFieldName[o.name] = o.asc;
        }
        const compareRecords = (d1, d2) => {
            for (const fieldName of orderFieldNames) {
                let v1 = d1[fieldName];
                let v2 = d2[fieldName];
                if (this.fields[fieldName].type === "many2one") {
                    v1 = v1[1];
                    v2 = v2[1];
                }
                if (v1 !== v2) {
                    if (v1 < v2) {
                        return isAscByFieldName[fieldName] ? -1 : 1;
                    } else {
                        return isAscByFieldName[fieldName] ? 1 : -1;
                    }
                }
            }
            return 0;
        };

        const hasSeveralPages = this.limit < this.count;
        if (hasSeveralPages && orderFieldNames.length) {
            // there several pages in the x2many and it is ordered, so we must know the value
            // for the sorted field for all records and sort the resIds w.r.t. to those values
            // before fetching the activeFields for the resIds of the current page.
            // 1) populate values for already fetched records
            const recordValues = {};
            const resIds = [];
            for (const id of this.currentIds) {
                const recordId = this._mapping[id];
                if (recordId) {
                    const record = this._cache[recordId];
                    recordValues[id] = {};
                    for (const fieldName of orderFieldNames) {
                        recordValues[id][fieldName] = record.data[fieldName];
                    }
                } else {
                    resIds.push(id); // id is a resId
                }
            }
            // 2) fetch values for non loaded records
            if (resIds.length) {
                const result = await this.model.orm.read(this.resModel, resIds, orderFieldNames);
                for (const values of result) {
                    const resId = values.id;
                    recordValues[resId] = {};
                    for (const fieldName of orderFieldNames) {
                        recordValues[resId][fieldName] = values[fieldName];
                    }
                }
            }
            // 3) sort this.currentIds
            this.currentIds.sort((id1, id2) => {
                return compareRecords(recordValues[id1], recordValues[id2]);
            });
        }

        await this._loadRecords();

        if (!hasSeveralPages && orderFieldNames.length) {
            this.currentIds.sort((id1, id2) => {
                const recId1 = this._mapping[id1];
                const recId2 = this._mapping[id2];
                return compareRecords(this._cache[recId1].data, this._cache[recId2].data);
            });
        }

        this.records = this._getRecords();
    }

    moveRecord() {
        // used only in the context of a basic_relational_model
    }

    /**
     * @returns {Array[] | null}
     */
    getCommands(allFields = false) {
        if (this._commands.length) {
            const commands = [];

            const getRecordValues = (id) => {
                const recordId = this._mapping[id];
                if (recordId) {
                    const record = this._cache[recordId];
                    return record.getChanges(allFields);
                } else {
                    const values = {};
                    for (const fieldName in this._initialValues[id]) {
                        const field = this.fields[fieldName];
                        let fieldValue = this._initialValues[id][fieldName];
                        if (isX2Many(field)) {
                            if (fieldValue[0][0] === DELETE_ALL) {
                                fieldValue = fieldValue.slice(1);
                            }
                        }
                        values[fieldName] = fieldValue;
                    }
                    return values;
                }
            };

            const hasReplaceWithCommand = this._commands && REPLACE_WITH === this._commands[0][0];
            if (hasReplaceWithCommand) {
                commands.push(this._commands[0]);
            }

            for (const resId of this.currentIds) {
                const dictCommand = this._commandsById[resId];
                if (dictCommand) {
                    if (dictCommand[CREATE]) {
                        const id = (dictCommand[CREATE] || dictCommand[UPDATE])[1];
                        commands.push(x2ManyCommands.create(id, getRecordValues(id)));
                    } else if (dictCommand[UPDATE]) {
                        const id = dictCommand[UPDATE][1];
                        commands.push(x2ManyCommands.update(id, getRecordValues(id)));
                    } else if (dictCommand[LINK_TO]) {
                        commands.push(x2ManyCommands.linkTo(resId));
                    }
                } else if (!hasReplaceWithCommand) {
                    commands.push(x2ManyCommands.linkTo(resId));
                }
            }

            for (const command of this._commands) {
                const code = command[0];
                if ([DELETE].includes(code)) {
                    commands.push(command);
                }
            }

            if (DELETE_ALL === this._commands[0][0] && !allFields) {
                for (const resId of this._serverIds) {
                    if (!this.currentIds.includes(resId)) {
                        commands.push(x2ManyCommands.delete(resId));
                    }
                }
            }
            return commands;
        }
        return null;
    }

    getContext() {
        const commands = [];
        if (this.field.type === "one2many") {
            if (this.currentIds) {
                for (const resId of this.currentIds) {
                    const record = this._cache[this._mapping[resId]];
                    if (record && record.isVirtual) {
                        commands.push(x2ManyCommands.create(resId, record.data));
                    } else {
                        commands.push(x2ManyCommands.linkTo(resId));
                    }
                }
            }
        } else {
            if (this.currentIds && this.currentIds.length) {
                commands.push(x2ManyCommands.replaceWith(this.currentIds));
            }
        }
        return commands;
    }

    async replaceWith(resIds) {
        this.applyCommand(x2ManyCommands.replaceWith(resIds));
        await this.load();
        this.onChanges();
        this.model.notify();
    }

    setCurrentIds(resIds = [], commands = []) {
        this._serverIds = resIds;
        this._commandsById = {}; // to remove?
        this._commands = this._getNormalizedCommands([], commands); // modifies commands and this._commandsById in places
        this.currentIds = this._getCurrentIds(this._serverIds, this._commands, true);
    }

    async sortBy(fieldName) {
        if (this.orderBy.length && this.orderBy[0].name === fieldName) {
            if (this.isOrder) {
                this.orderBy[0].asc = !this.orderBy[0].asc;
            }
        } else {
            this.orderBy = this.orderBy.filter((o) => o.name !== fieldName);
            this.orderBy.unshift({
                name: fieldName,
                asc: true,
            });
        }

        this.isOrder = true;
        await this.load();
        this.model.notify();
    }

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    // TO DISCUSS AND IMP
    _getNextMapping(mapping, commands) {
        let nextMapping = mapping;
        for (const command of commands) {
            const code = command[0];
            const id = command[1];

            switch (code) {
                case UPDATE:
                    nextMapping[id] = mapping[id];
                    break;
                case LINK_TO:
                    nextMapping[id] = mapping[id];
                    break;
                case DELETE_ALL:
                    nextMapping = {};
                    break;
                case REPLACE_WITH:
                    break;
            }
        }
        return nextMapping;
    }

    /**
     * @param {Object} params
     * @returns {Record}
     */
    _createRecord(params = {}) {
        const record = this.model.createDataPoint("record", {
            resModel: this.resModel,
            fields: this.fields,
            activeFields: this.activeFields,
            viewMode: this.viewMode,
            views: this.views,
            onRecordWillSwitchMode: this.onRecordWillSwitchMode,
            onChanges: async () => {
                this.applyCommand(
                    x2ManyCommands.update(record.resId || record.virtualId, symbolValues)
                );
                this.onChanges();
            },
            rawContext: {
                parent: this.rawContext,
                make: () => {
                    return makeContext([params.context], this.evalContext);
                },
            },
            ...params,

            getParentRecordContext: this.getParentRecordContext,
            parentRecord: this.parentRecord,
            relationField: this.relationField,
        });
        const id = record.resId || record.virtualId; // is resId sometimes changed after record creation? (for a record in a staticList)

        this._mapping[id] = record.id;
        this._cache[record.id] = record;

        return record;
    }

    _getCurrentIds(currentIds, commands, serverCommands = false) {
        let nextIds = [...currentIds];
        for (const command of commands) {
            const code = command[0];
            const id = command[1];
            switch (code) {
                case 0: // create
                    if (nextIds.indexOf(id) === -1) {
                        const index =
                            this.editable === "top" && !serverCommands
                                ? this.offset
                                : this.offset + this.limit - 1;
                        nextIds.splice(index, 0, id);
                    } else {
                        throw new Error("you rascal");
                    }
                    break;
                case 1: // update
                    add(nextIds, id);
                    break;
                case 2: // delete
                case 3: // forget
                    remove(nextIds, id);
                    break;
                case 4: // linkTo
                    add(nextIds, id);
                    break;
                case 5: // deleteAll
                case 6: // replaceWith
                    nextIds = command[2] || [];
                    break;
            }
        }
        return nextIds;
    }

    /**
     * Returns the array of visible ids (resId or virtualId)
     * @returns {Record[]}
     */
    _getDisplayedIds() {
        const hasSeveralPages = this.limit < this.count;
        let displayedIds = this.currentIds.slice(0);
        if (hasSeveralPages) {
            displayedIds = this.currentIds.slice(this.offset, this.offset + this.limit);
        }
        return displayedIds;
    }

    /**
     * Concat two arrays of commands and normalize the result
     * The first array must be normalized.
     * ! modifies in place the commands themselves ! TODO fix this
     * @param {Array[]} normalizedCommands normalized array of commands
     * @param {Array[]} commands  array of commands
     * @returns {Array[]} a normalized array of commands
     */
    _getNormalizedCommands(normalizedCommands, commands) {
        let nextCommands = [...normalizedCommands];
        for (const command of commands) {
            const code = command[0];

            if (code === CREATE && !command[1]) {
                // FIXME WOWL: works because we change command in place (also stored in parent _changes)
                command[1] = this.model.nextVirtualId;
            }

            const id = command[1];

            if ([CREATE, UPDATE].includes(code)) {
                if (!this._commandsById[id]) {
                    if (!this._initialValues) {
                        this._initialValues = {};
                    }
                    this._initialValues[id] = this._parseServerValues(command[2]);
                }
                command[2] = symbolValues;
            }

            if ([DELETE_ALL, REPLACE_WITH].includes(code)) {
                this._commandsById = {};
                nextCommands = [command];
                continue;
            } else if (!this._commandsById[id]) {
                // possible problem with same ids (0) returned by server in accounting
                // -> add a test
                this._commandsById[id] = { [code]: command };
                nextCommands.push(command);
                continue;
            }

            switch (code) {
                case UPDATE:
                    // we assume that delete/forget cannot be found in this._commandsById[id]
                    // we can find create/linkTo/update
                    // we merge create/update and update/update
                    if (this._commandsById[id][LINK_TO]) {
                        this._commandsById[id][UPDATE] = { [UPDATE]: command };
                        remove(nextCommands, this._commandsById[id][LINK_TO]);
                        nextCommands.push(command);
                    }
                    break;
                case DELETE:
                    // we assume that delete/forget cannot be found in this._commandsById[id]
                    // we can find create/linkTo/update
                    // if one finds create, we erase everything
                    // else we add delete and remove linkTo/update
                    if (this._commandsById[id][UPDATE]) {
                        remove(nextCommands, this._commandsById[id][UPDATE]);
                    }
                    if (this._commandsById[id][CREATE]) {
                        remove(nextCommands, this._commandsById[id][CREATE]);
                        delete this._commandsById[id];
                    } else {
                        if (this._commandsById[id][LINK_TO]) {
                            remove(nextCommands, this._commandsById[id][LINK_TO]);
                        }
                        this._commandsById[id] = { [DELETE]: command };
                        nextCommands.push(command);
                    }
                    break;
                case FORGET:
                    // we assume that delete/forget cannot be found in this._commandsById[id]
                    // we can find create/linkTo/update
                    // if one finds linkTo, we erase linkTo and forget
                    if (this._commandsById[id][LINK_TO]) {
                        remove(nextCommands, this._commandsById[id][LINK_TO]);
                        delete this._commandsById[id][LINK_TO];
                        // do we need to remove update?
                    } else {
                        this._commandsById[id][FORGET] = command;
                        nextCommands.push(command);
                    }
                    break;
                case LINK_TO:
                    // we assume that that create/delete cannot be found in this._commandsById[id]
                    if (this._commandsById[id][FORGET]) {
                        delete this._commandsById[id][FORGET];
                        remove(nextCommands, this._commandsById[id][FORGET]);
                    } else {
                        this._commandsById[id][LINK_TO] = command;
                        nextCommands.push(command);
                    }
                    break;
            }
        }
        return nextCommands;
    }

    /**
     * Returns visible records
     * @returns {Record[]}
     */
    _getRecords() {
        const displayedIds = this._getDisplayedIds();
        return displayedIds.map((id) => this._cache[this._mapping[id]]);
    }

    /**
     * Add missing records to display to cache and load them
     */
    async _loadRecords() {
        const displayedIds = this._getDisplayedIds();
        const proms = [];
        for (const id of displayedIds) {
            const recordId = this._mapping[id];
            if (!recordId) {
                const key = typeof id === "number" ? "resId" : "virtualId";
                const record = this._createRecord({ [key]: id, mode: "readonly" });
                let changes;
                const createCommand = this._commandsById[id] && this._commandsById[id][CREATE];
                if (createCommand) {
                    changes = this._initialValues[id];
                }
                proms.push(record.load({ changes }));
            }
        }
        await Promise.all(proms);
    }

    // FIXME WOWL: factorize this (needed in both DynamicList and StaticList)
    unselectRecord() {
        const editedRecord = this.editedRecord;
        if (editedRecord) {
            const canBeAbandoned = editedRecord.canBeAbandoned;
            if (!canBeAbandoned && editedRecord.checkValidity()) {
                return editedRecord.switchMode("readonly");
            } else if (canBeAbandoned) {
                return this.abandonRecord(editedRecord.id);
            }
        }
    }
}

StaticList.DEFAULT_LIMIT = 40;

export class RelationalModel extends Model {
    setup(params, { action, dialog, notification, rpc, user, view }) {
        this.action = action;
        this.dialogService = dialog;
        this.notificationService = notification;
        this.rpc = rpc;
        this.user = user;
        this.viewService = view;
        this.orm = new RequestBatcherORM(rpc, user);
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();

        this.onCreate = params.onCreate;
        this.multiEdit = params.multiEdit || false;
        this.quickCreateView = params.quickCreateView;
        this.defaultGroupBy = params.defaultGroupBy || false;
        this.defaultOrderBy = params.defaultOrder;
        this.rootType = params.rootType || "list";
        this.rootParams = {
            activeFields: params.activeFields || {},
            fields: params.fields || {},
            viewMode: params.viewMode || null,
            resModel: params.resModel,
            groupByInfo: params.groupByInfo,
        };
        if (this.rootType === "record") {
            this.rootParams.resId = params.resId;
            this.rootParams.resIds = params.resIds;
            if (params.mode) {
                this.rootParams.mode = params.mode;
            }
        } else {
            this.rootParams.openGroupsByDefault = params.openGroupsByDefault || false;
            this.rootParams.limit = params.limit;
            this.rootParams.expand = params.expand;
            this.rootParams.groupsLimit = params.groupsLimit;
        }

        // this.db = Object.create(null);
        this.root = null;

        this.nextId = 1;

        // debug
        window.basicmodel = this;
        // console.group("Current model");
        // console.log(this);
        // console.groupEnd();
    }

    /**
     * @param {Object} [params={}]
     * @param {Comparison | null} [params.comparison]
     * @param {Context} [params.context]
     * @param {DomainListRepr} [params.domain]
     * @param {string[]} [params.groupBy]
     * @param {Object[]} [params.orderBy]
     * @param {number} [params.resId] should not be there
     * @returns {Promise<void>}
     */
    async load(params = {}) {
        const rootParams = { ...this.rootParams, ...params };
        if (this.defaultOrderBy && !(params.orderBy && params.orderBy.length)) {
            rootParams.orderBy = this.defaultOrderBy;
        }
        if (
            this.defaultGroupBy &&
            !this.env.inDialog &&
            !(params.groupBy && params.groupBy.length)
        ) {
            rootParams.groupBy = [this.defaultGroupBy];
        }
        rootParams.rawContext = {
            make: () => {
                return makeContext([rootParams.context], {});
            },
        };
        const state = this.root ? this.root.exportState() : {};
        const newRoot = this.createDataPoint(this.rootType, rootParams, state);
        await this.keepLast.add(newRoot.load());
        this.root = newRoot;
        this.rootParams = rootParams;
        this.notify();
    }

    /**
     * @param {"group" | "list" | "record"} type
     * @param {Record<any, any>} params
     * @param {Record<any, any>} [state={}]
     * @returns {DataPoint}
     */
    createDataPoint(type, params, state = {}) {
        let DpClass;
        switch (type) {
            case "group": {
                DpClass = this.constructor.Group;
                break;
            }
            case "list": {
                if ((params.groupBy || []).length) {
                    DpClass = this.constructor.DynamicGroupList;
                } else {
                    DpClass = this.constructor.DynamicRecordList;
                }
                break;
            }
            case "record": {
                DpClass = this.constructor.Record;
                break;
            }
            case "static_list": {
                DpClass = this.constructor.StaticList;
                break;
            }
        }
        return new DpClass(this, params, state);
    }

    hasData() {
        return this.root.count > 0;
    }

    get nextVirtualId() {
        return `virtual_${this.nextId++}`;
    }

    /**
     * @override
     */
    getGroups() {
        return this.root.groups && this.root.groups.length ? this.root.groups : null;
    }
}

RelationalModel.services = ["action", "dialog", "notification", "rpc", "user", "view"];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;
