/* @odoo-module */

import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { ORM, x2ManyCommands } from "@web/core/orm_service";
import { evaluateExpr } from "@web/core/py_js/py";
import { registry } from "@web/core/registry";
import { unique } from "@web/core/utils/arrays";
import { Deferred, KeepLast, Mutex } from "@web/core/utils/concurrency";
import { memoize } from "@web/core/utils/functions";
import { escape } from "@web/core/utils/strings";
import { session } from "@web/session";
import { FormArchParser } from "@web/views/form/form_arch_parser";
import { ListConfirmationDialog } from "@web/views/list/list_confirmation_dialog";
import { Model } from "@web/views/model";
import { archParseBoolean, evalDomain, isNumeric, isRelational, isX2Many } from "@web/views/utils";

const { DateTime } = luxon;
const { markRaw, markup, toRaw } = owl;

const preloadedDataRegistry = registry.category("preloadedData");

const { CREATE, UPDATE, DELETE, FORGET, LINK_TO, DELETE_ALL, REPLACE_WITH } = x2ManyCommands;
const QUICK_CREATE_FIELD_TYPES = ["char", "boolean", "many2one", "selection"];
const AGGREGATABLE_FIELD_TYPES = ["float", "integer", "monetary"]; // types that can be aggregated in grouped views
const DEFAULT_HANDLE_FIELD = "sequence";
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
export function isAllowedDateField(groupByField) {
    return (
        ["date", "datetime"].includes(groupByField.type) &&
        archParseBoolean(groupByField.rawAttrs.allow_group_range_value)
    );
}

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
 * @param {RawContext} rawContext
 * @param {Context} defaultContext
 * @returns {Context}
 */
function processRawContext(rawContext, defaultContext) {
    const contexts = [];
    if (!rawContext) {
        return Object.assign({}, defaultContext);
    }
    contexts.push({ ...defaultContext, ...rawContext.make() });
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
 * @param {Context} context
 */
async function toggleArchive(model, resModel, resIds, doArchive, context) {
    const method = doArchive ? "action_archive" : "action_unarchive";
    const action = await model.orm.call(resModel, method, [resIds], { context });
    if (action && Object.keys(action).length !== 0) {
        model.action.doAction(action);
    }
}

async function unselectRecord(editedRecord, abandonRecord) {
    if (editedRecord) {
        const isValid = await editedRecord.checkValidity();
        const canBeAbandoned = editedRecord.canBeAbandoned;
        if (isValid && !canBeAbandoned) {
            return editedRecord.switchMode("readonly");
        } else if (canBeAbandoned) {
            return abandonRecord(editedRecord.id);
        }
    }
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
                ids: [],
            };
            this.batches[key] = batch;
        }
        batch.ids = unique([...batch.ids, ...ids]);

        if (!batch.scheduled) {
            batch.scheduled = true;
            Promise.resolve().then(async () => {
                delete this.batches[key];
                const result = await callback(batch.ids);
                batch.deferred.resolve(result);
            });
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
    async nameGet(resModel, resIds, kwargs) {
        const pairs = await this.batch(resIds, ["name_get", resModel, kwargs], (resIds) =>
            super.nameGet(resModel, resIds, kwargs)
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
    async read(resModel, resIds, fields, kwargs) {
        const records = await this.batch(resIds, ["read", resModel, fields, kwargs], (resIds) =>
            super.read(resModel, resIds, fields, kwargs)
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
    async unlink(resModel, resIds, kwargs) {
        return this.batch(resIds, ["unlink", resModel, kwargs], (resIds) =>
            super.unlink(resModel, resIds, kwargs)
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
        this.setActiveFields(params.activeFields);

        this.rawContext = params.rawContext;
        this.defaultContext = params.defaultContext;
        this.setup(params, state);
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get context() {
        return processRawContext(this.rawContext, this.defaultContext);
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

    /**
     * TODO WOWL: adapt this comment to new system
     * Also, is datapoint the best place ? Could be in record.
     *
     * Invalidates the DataManager's cache if the main model (i.e. the model of
     * its root parent) of the given dataPoint is a model in 'noCacheModels'.
     *
     * Reloads the currencies if the main model is 'res.currency'.
     * Reloads the webclient if we modify a res.company, to (un)activate the
     * multi-company environment if we are not in a tour test.
     *
     */
    invalidateCache() {
        if (this.resModel === "res.currency") {
            // TODO WOWL: this needs to be ported from basic model for the list view to have it.
            // session.reloadCurrencies();
            // There is a test in form view but it uses the basic model for now.
        }
        if (this.resModel === "res.company") {
            this.model.action.doAction("reload_context");
        }
        if (this.model.noCacheModels.includes(this.resModel)) {
            this.model.env.bus.trigger("CLEAR-CACHES");
        }
    }

    /**
     * @param {Object} [activeFields={}]
     */
    setActiveFields(activeFields) {
        this.activeFields = activeFields || {};
    }

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
            case "html": {
                return markup(value);
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

markRaw(DataPoint.prototype);

function clearObject(obj) {
    for (const key in obj) {
        delete obj[key];
    }
}

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
                evalContext[fieldName] = serializeDate(value);
            } else if (value && this.fields[fieldName].type === "datetime") {
                evalContext[fieldName] = serializeDateTime(value);
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
            active_id: this.resId || false,
            active_ids: this.resId ? [this.resId] : [],
            active_model: this.resModel,
            current_company_id: this.model.company.currentCompany.id,
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
        if (this.canBeAbandoned) {
            // for a new record, have changes does not necessarily mean to be dirty!
            return false;
        }

        const changes = { ...this._changes };
        for (const fieldName in changes) {
            const fieldType = this.fields[fieldName].type;
            if (["one2many", "many2many"].includes(fieldType)) {
                if (changes[fieldName].getCommands()) {
                    return true;
                }
            } else {
                return true;
            }
        }
        return false;
    }

    get dirtyFields() {
        if (!this.isDirty) {
            return [];
        }
        return this._changes.map((change) => this.activeFields[change]);
    }

    get isInEdition() {
        return this.mode === "edit";
    }

    get isNew() {
        return this.isVirtual;
    }

    get isVirtual() {
        return !this.resId;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * To be called **only** when Odoo is about to be closed, and we want to
     * save potential changes on a given record.
     *
     * We can't follow the normal flow (onchange(s) + save, mutexified),
     * because the 'beforeunload' handler must be *almost* sync (< 10 ms
     * setTimeout seems fine, but an rpc roundtrip is definitely too long),
     * so here we bypass the standard mechanism of notifying changes and
     * saving them:
     *  - we ask the model to bypass its mutex for upcoming 'notifyChanges' and
     *   'save' requests
     *  - we ask all fields to commit their changes (in case there would
     *    be a focused field with a fresh value)
     *  - we take all changes that have been reported to the
     *    controller, but not yet sent to the model because of the mutex,
     *    and directly notify the model about them, see update.
     *  - we reset the widgets with all those changes, s.t. a further call
     *    to 'canBeRemoved' uses the correct data (it asks the widgets if
     *    they are set/valid, based on their internal state)
     *  - if the record is dirty, we save directly
     */
    async urgentSave() {
        this._urgentSave = true;
        this.model.env.bus.trigger("RELATIONAL_MODEL:WILL_SAVE_URGENTLY");
        this._save({ stayInEdition: true, noReload: true });
    }

    async archive() {
        await toggleArchive(this.model, this.resModel, [this.resId], true, this.context);
        await this.load();
        this.model.notify();
        this.invalidateCache();
    }

    async checkValidity() {
        if (!this._urgentSave) {
            const proms = [];
            this.model.env.bus.trigger("RELATIONAL_MODEL:NEED_LOCAL_CHANGES", { proms });
            await Promise.all([...proms, this.model.mutex.getUnlockedDef()]);
        }
        return this._checkValidity();
    }

    _checkValidity() {
        for (const fieldName in this._requiredFields) {
            const fieldType = this.fields[fieldName].type;
            const activeField = this.activeFields[fieldName];
            if (
                !evalDomain(this._requiredFields[fieldName], this.evalContext) ||
                (activeField && activeField.alwaysInvisible)
            ) {
                this._removeInvalidFields([fieldName]);
                continue;
            }

            const isSet =
                activeField && activeField.FieldComponent && activeField.FieldComponent.isSet;

            if (this.isRequired(fieldName) && isSet && !isSet(this.data[fieldName])) {
                this.setInvalidField(fieldName);
                continue;
            }

            switch (fieldType) {
                case "boolean":
                case "float":
                case "integer":
                case "monetary":
                    continue;
                case "one2many":
                case "many2many":
                    if (!this.isX2ManyValid(fieldName)) {
                        this.setInvalidField(fieldName);
                    }
                    break;
                default:
                    if (!isSet && this.isRequired(fieldName) && !this.data[fieldName]) {
                        this.setInvalidField(fieldName);
                    }
            }
        }
        return !this._invalidFields.size;
    }

    async delete() {
        const unlinked = await this.model.orm.unlink(this.resModel, [this.resId], {
            context: this.context,
        });
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
        this.invalidateCache();
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
            if (
                !allFields &&
                fieldName in this.activeFields &&
                !this.activeFields[fieldName].forceSave &&
                this.isReadonly(fieldName)
            ) {
                delete changes[fieldName];
                continue;
            }
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
        const rawDomains = [
            this._domains[fieldName] || [],
            this.fields[fieldName].domain || [],
            this.activeFields[fieldName].domain,
        ];

        const evalContext = this.evalContext;
        return Domain.and(
            rawDomains.map((d) => (typeof d === "string" ? evaluateExpr(d, evalContext) : d))
        );
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
        return value.records.every(async (r) => await r.checkValidity());
    }

    /**
     * @param {Object} [params={}]
     * @param {Object} [params.values]
     * @param {Object} [params.changes]
     */
    async load(params = {}) {
        this._cache = {};
        for (const fieldName in this.activeFields) {
            const field = this.fields[fieldName];
            if (isX2Many(field)) {
                const staticList = this._createStaticList(fieldName);
                this._cache[fieldName] = staticList;
            }
        }
        for (const fieldName in this.data) {
            if (!(fieldName in this.activeFields)) {
                delete this.data[fieldName];
            }
        }

        if (!(params.values || !this.isVirtual)) {
            const changes = params.changes || (await this._onChange());
            await this._load({ changes });
        } else {
            let values = this._parseServerValues(params.values);
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

    /**
     * Overridden to set required fields based on the new active fields.
     *
     * @override
     */
    setActiveFields(activeFields) {
        super.setActiveFields(activeFields);

        this._requiredFields = {};
        for (const [fieldName, activeField] of Object.entries(this.activeFields)) {
            const { modifiers } = activeField;
            if (modifiers && modifiers.required) {
                this._requiredFields[fieldName] = modifiers.required;
            }
        }
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
     * @returns {Promise<Boolean>}
     */
    async switchMode(mode) {
        if (this.mode === mode) {
            return true;
        }
        const canSwitch = await this._onWillSwitchMode(this, mode);
        if (canSwitch === false) {
            return false;
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
        return true;
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
        await toggleArchive(this.model, this.resModel, [this.resId], false, this.context);
        await this.load();
        this.model.notify();
        this.invalidateCache();
    }

    async update(changes) {
        if (this._urgentSave) {
            return this._update(changes);
        }
        return this.model.mutex.exec(async () => {
            await this._update(changes);
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
                context: processRawContext({
                    parent: this.rawContext,
                    make: () => {
                        return makeContext(
                            [this.activeFields[fieldName].context],
                            this.evalContext
                        );
                    },
                }),
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
            const result = await this.model.orm.nameGet(relation, [value[0]], { context });
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
            const nameGet = await this.model.orm.nameGet(resModel, [resId], { context });
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
                this.resId ? [this.resId] : [],
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
            context: {
                bin_size: true,
                ...this.context,
            },
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
        if (!this._checkValidity()) {
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
        const context = this.context;

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
                this.resId = await this.model.orm.create(this.resModel, [changes], { context });
            }
            delete this.virtualId;
            this.data.id = this.resId;
            this.resIds.push(this.resId);
            this.invalidateCache();
        } else if (keys.length > 0) {
            try {
                await this.model.orm.write(this.resModel, [this.resId], changes, { context });
            } catch (e) {
                if (!this.isInEdition) {
                    await this.model.reloadRecords(this);
                }
                throw e;
            }
            this.invalidateCache();
        }

        // Switch to the parent active fields
        if (this.parentActiveFields) {
            this.setActiveFields(this.parentActiveFields);
            this.parentActiveFields = false;
        }
        this.isInQuickCreation = false;
        if (shouldReload) {
            await this.model.reloadRecords(this);
        }
        if (!options.stayInEdition) {
            this.switchMode("readonly");
        }
        return true;
    }

    async _update(changes) {
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
    }
}

class DynamicList extends DataPoint {
    setup(params, state) {
        this.groupBy = params.groupBy || [];
        this.domain = markRaw(params.domain || []);
        this.orderBy =
            params.orderBy && params.orderBy.length ? params.orderBy : state.orderBy || []; // rename orderBy
        this.offset = state.offset || 0;
        this.count = 0;
        this.limit = params.limit || state.limit || this.constructor.DEFAULT_LIMIT;
        this.isDomainSelected = false;
        this.loadedCount = state.loadedCount || 0;
        this.previousParams = state.previousParams || "[]";

        this.editedRecord = null;
        this.onCreateRecord = params.onCreateRecord || (() => {});
        this.onRecordWillSwitchMode = async (record, mode, options) => {
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
                await params.onRecordWillSwitchMode(record, mode, options);
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
        const [groupByFieldName, granularity] = this.firstGroupBy.split(":");
        return {
            rawAttrs: {},
            ...this.fields[groupByFieldName],
            ...this.activeFields[groupByFieldName],
            granularity: granularity,
        };
    }

    get isM2MGrouped() {
        return this.groupBy.some((groupBy) => {
            const fieldName = groupBy.split(":")[0];
            return this.fields[fieldName].type === "many2many";
        });
    }

    get selection() {
        return this.records.filter((r) => r.selected);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    abandonRecord(recordId) {
        const record = this.records.find((r) => r.id === recordId);
        return this.removeRecord(record);
    }

    /**
     * @param {boolean} [isSelected]
     * @returns {Promise<number[]>}
     */
    async archive(isSelected) {
        const resIds = await this.getResIds(isSelected);
        await toggleArchive(this.model, this.resModel, resIds, true, this.context);
        await this.model.load();
        this.invalidateCache();
        return resIds;
    }

    canQuickCreate() {
        return (
            this.groupByField &&
            (isAllowedDateField(this.groupByField) ||
                QUICK_CREATE_FIELD_TYPES.includes(this.groupByField.type))
        );
    }

    canResequence() {
        return this.model.handleField || DEFAULT_HANDLE_FIELD in this.fields;
    }

    exportState() {
        return {
            limit: this.limit,
            loadedCount: this.records.length,
            orderBy: this.orderBy,
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
                    context: this.context,
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
        await toggleArchive(this.model, this.resModel, resIds, false, this.context);
        await this.model.load();
        this.invalidateCache();
        return resIds;
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
                    try {
                        const context = this.context;
                        await this.model.orm.write(this.resModel, resIds, changes, { context });
                        this.invalidateCache();
                        validSelection.forEach((record) => {
                            record.selected = false;
                        });
                        await Promise.all(validSelection.map((record) => record.load()));
                        record.switchMode("readonly");
                        this.model.notify();
                    } catch (_) {
                        record.discard();
                    }
                    validSelection.forEach((record) => {
                        record.selected = false;
                    });
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
                fieldNodes: this.model.fieldNodes,
            };
            this.model.trigger("list-confirmation-dialog-will-open");
            await this.model.dialogService.add(ListConfirmationDialog, dialogProps, {
                onClose: () => {
                    this.model.trigger("list-confirmation-dialog-closed");
                },
            });
        } else {
            await record._save();
            record.selected = false;
        }
    }

    /**
     * Calls the method 'resequence' on the given resModel.
     * The record matching that 'moveId' will be resequenced in the given list of
     * records, at the start of the list or after the record matching 'targetId' (if any).
     *
     * @param {(Group | Record)[]} originalList
     * @param {string} resModel
     * @param {string} movedId
     * @param {string} [targetId]
     * @returns {Promise<(Group | Record)[]>}
     */
    async _resequence(originalList, resModel, movedId, targetId) {
        if (this.resModel === resModel && !this.canResequence()) {
            // There is no handle field on the current model
            return originalList;
        }

        const handleField = this.model.handleField || DEFAULT_HANDLE_FIELD;
        const records = [...originalList];
        const order = this.orderBy.find((o) => o.name === handleField);
        const asc = !order || order.asc;

        // Find indices
        const fromIndex = records.findIndex((r) => r.id === movedId);
        let toIndex = 0;
        if (targetId !== null) {
            const targetIndex = records.findIndex((r) => r.id === targetId);
            toIndex = fromIndex > targetIndex ? targetIndex + 1 : targetIndex;
        }

        const getSequence = (rec) => rec && rec.data[handleField];

        // Determine what records need to be modified
        const firstIndex = Math.min(fromIndex, toIndex);
        const lastIndex = Math.max(fromIndex, toIndex) + 1;
        let reorderAll = false;
        let lastSequence = (asc ? -1 : 1) * Infinity;
        for (let index = 0; index < records.length; index++) {
            const sequence = getSequence(records[index]);
            if (
                ((index < firstIndex || index >= lastIndex) &&
                    ((asc && lastSequence >= sequence) || (!asc && lastSequence <= sequence))) ||
                (index >= firstIndex && index < lastIndex && lastSequence === sequence)
            ) {
                reorderAll = true;
            }
            lastSequence = sequence;
        }

        // Perform the resequence in the list of records
        const [record] = records.splice(fromIndex, 1);
        records.splice(toIndex, 0, record);

        // Creates the list of to modify
        let toReorder = records;
        if (!reorderAll) {
            toReorder = toReorder.slice(firstIndex, lastIndex).filter((r) => r.id !== movedId);
            if (fromIndex < toIndex) {
                toReorder.push(record);
            } else {
                toReorder.unshift(record);
            }
        }
        if (!asc) {
            toReorder.reverse();
        }

        const ids = toReorder.map((r) => r.resId).filter((s) => s === 0 || (s && !isNaN(s)));
        const sequences = toReorder.map(getSequence);
        const offset = sequences.length && Math.min(...sequences);

        // Assemble the params
        const params = { model: resModel, ids, context: this.context };
        if (offset) {
            params.offset = offset;
        }
        if (this.model.handleField) {
            params.field = handleField;
        }

        // Try to write new sequences on the affected records
        const wasResequenced = await this.model.keepLast.add(
            this.model.rpc("/web/dataset/resequence", params)
        );
        if (!wasResequenced) {
            return originalList;
        }

        // Read the actual values set by the server and update the records
        const result = await this.model.keepLast.add(
            this.model.orm.read(resModel, ids, [handleField], { context: this.context })
        );
        for (const recordData of result) {
            const record = records.find((r) => r.resId === recordData.id);
            const value = { [handleField]: recordData[handleField] };
            if (record instanceof Record) {
                await record.update(value);
            } else {
                Object.assign(record.data, value);
            }
        }

        return records;
    }

    unselectRecord() {
        return unselectRecord(this.editedRecord, this.abandonRecord.bind(this));
    }
}

DynamicList.DEFAULT_LIMIT = 80;

export class DynamicRecordList extends DynamicList {
    setup(params) {
        super.setup(...arguments);

        /** @type {Record[]} */
        this.records = [];
        this.data = params.data;
        this.countLimit = this.constructor.WEB_SEARCH_READ_COUNT_LIMIT;
        this.hasLimitedCount = false;
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get quickCreateRecord() {
        return this.records.find((r) => r.isInQuickCreation);
    }

    get quickCreateRecordIndex() {
        return this.records.findIndex((r) => r.isInQuickCreation);
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    /**
     * @param {number} resId
     * @param {boolean} [atFirstPosition]
     * @returns {Promise<Record>} the newly created record
     */
    async addExistingRecord(resId, atFirstPosition) {
        const newRecord = this.model.createDataPoint("record", {
            resModel: this.resModel,
            fields: this.fields,
            activeFields: this.activeFields,
            onRecordWillSwitchMode: this.onRecordWillSwitchMode,
            defaultContext: this.defaultContext,
            rawContext: {
                parent: this.rawContext,
                make: () => this.context,
            },
            resId,
        });
        if (this.model.useSampleModel) {
            this.model.useSampleModel = false;
            await this.load();
        }
        await this.model.keepLast.add(this.model.mutex.exec(() => newRecord.load()));
        return this.addRecord(newRecord, atFirstPosition ? 0 : this.count);
    }

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
            rawContext: {
                parent: this.rawContext,
                make: () => this.context,
            },
            ...params,
        });
        if (this.model.useSampleModel) {
            this.model.useSampleModel = false;
            await this.load();
        }
        await this.model.keepLast.add(this.model.mutex.exec(() => newRecord.load()));
        this.editedRecord = newRecord;
        this.onRemoveNewRecord = await this.onCreateRecord(newRecord);

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
                await this.model.orm.unlink(this.resModel, resIds, {
                    context: this.context,
                });
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

    exportState() {
        return {
            ...super.exportState(),
            offset: this.offset,
        };
    }

    /**
     * Performs a search_count with the current domain to set the count. This is
     * useful as web_search_read limits the count for performance reasons, so it
     * might sometimes be less than the real number of records matching the domain.
     *
     * @returns {number}
     */
    async fetchCount() {
        const keepLast = this.model.keepLast;
        this.count = await keepLast.add(this.model.orm.searchCount(this.resModel, this.domain));
        this.countLimit = this.count;
        this.hasLimitedCount = false;
        this.model.notify();
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

    async quickCreate(activeFields, context, atFirstPosition = true) {
        await this.model.mutex.getUnlockedDef();
        const record = this.quickCreateRecord;
        if (record) {
            this.removeRecord(record);
        }
        const rawContext = {
            parent: this.rawContext,
            make: () => makeContext([context, {}]),
        };
        return this.createRecord(
            { activeFields, rawContext, isInQuickCreation: true },
            atFirstPosition
        );
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
            if (this.onRemoveNewRecord) {
                this.onRemoveNewRecord(record);
                this.onRemoveNewRecord = null;
            }
        }

        this.model.notify();
        return record;
    }

    async resequence() {
        this.records = await this._resequence(this.records, this.resModel, ...arguments);
        this.model.notify();
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
        const kwargs = {
            limit: this.limit,
            offset: this.offset,
            order: orderByToString(this.orderBy),
            count_limit: this.countLimit + 1,
            context: {
                bin_size: true,
                ...this.context,
            },
        };
        if (this.loadedCount > this.limit) {
            // This condition means that we are reloading a list of records
            // that has been manually extended: we need to load exactly the
            // same amount of records.
            kwargs.limit = this.loadedCount;
            kwargs.offset = 0;
        }
        const { records: rawRecords, length } =
            this.data ||
            (await this.model.orm.webSearchRead(
                this.resModel,
                this.domain,
                this.fieldNames,
                kwargs
            ));

        const records = await Promise.all(
            rawRecords.map(async (data) => {
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
        if (length === this.countLimit + 1) {
            this.hasLimitedCount = true;
            this.count = length - 1;
        } else {
            this.count = length;
        }

        return records;
    }
}
DynamicRecordList.WEB_SEARCH_READ_COUNT_LIMIT = 10000;

export class DynamicGroupList extends DynamicList {
    setup(params, state) {
        super.setup(...arguments);

        this.groupByInfo = params.groupByInfo || {}; // FIXME: is this something specific to the list view?
        this.openGroupsByDefault = params.openGroupsByDefault || false;
        /** @type {Group[]} */
        this.groups = state.groups || [];
        this.isGrouped = true;
        this.quickCreateInfo = null; // Lazy loaded;
        this.expand = params.expand;
        this.limitByGroup = this.limit;
        this.limit =
            params.groupsLimit ||
            (this.expand ? this.constructor.DEFAULT_LOAD_LIMIT : this.constructor.DEFAULT_LIMIT);
        this.onCreateRecord =
            params.onCreateRecord ||
            (async (record) => {
                const editedRecord = this.editedRecord;
                if (editedRecord && !record.isInQuickCreation) {
                    if (editedRecord.canBeAbandoned) {
                        this.abandonRecord(editedRecord.id);
                    } else {
                        await editedRecord.save();
                    }
                }
                this.editedRecord = record;
                const onRemoveRecord = (record) => {
                    if (this.editedRecord === record) {
                        this.editedRecord = null;
                    }
                };
                return onRemoveRecord;
            });

        this._loadQuickCreateView = memoize(this._loadQuickCreateView.bind(this));
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
            .map((group) => group.records)
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
     * @see {_createGroup}
     */
    async createGroup(groupName) {
        await this.model.mutex.exec(() => this._createGroup(groupName));
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

    get nbTotalRecords() {
        return this.groups.reduce((acc, group) => acc + group.count, 0);
    }

    async quickCreate(group, atFirstPosition = true) {
        group = group || this.groups[0];
        if (this.model.useSampleModel) {
            // Empty the groups because they contain sample data
            this.groups.forEach((g) => g.empty());
        }
        this.model.useSampleModel = false;
        const { isFolded } = group;
        this.quickCreateInfo = await this._loadQuickCreateView();
        if (isFolded !== group.isFolded) {
            // Group has been manually (un)folded => drop the quickCreate action
            return;
        }
        if (isFolded) {
            await group.toggle();
        }
        await group.quickCreate(this.quickCreateInfo.activeFields, this.context, atFirstPosition);
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
                group.count--;
                if (removedRecord === this.editedRecord) {
                    this.editedRecord = null;
                }
                return removedRecord;
            }
        }
    }

    async resequence() {
        const resModel = isRelational(this.groupByField)
            ? this.groupByField.relation
            : this.resModel;
        this.groups = await this._resequence(this.groups, resModel, ...arguments);
        this.model.notify();
    }

    // ------------------------------------------------------------------------
    // Protected
    // ------------------------------------------------------------------------

    /**
     * @param {string} groupName
     * @returns {Promise<Group>}
     */
    async _createGroup(groupName) {
        const [id, displayName] = await this.model.orm.call(
            this.groupByField.relation,
            "name_create",
            [groupName],
            { context: this.context }
        );
        const [lastGroup] = this.groups.slice(-1);
        const group = this.model.createDataPoint("group", {
            ...this.commonGroupParams,
            count: 0,
            value: id,
            displayName,
            aggregates: {},
            groupByField: this.groupByField,
            groupDomain: Domain.and([this.domain, [[this.groupByField.name, "=", id]]]).toList(),
            rawContext: this.rawContext,
        });
        group.isFolded = false;
        this.addGroup(group);

        if (lastGroup) {
            await this.resequence(group.id, lastGroup.id);
        }

        return group;
    }

    /**
     * @param {Object} groupData
     * @param {string} fieldName
     * @returns {any}
     */
    _getValueFromGroupData(groupData, fieldName) {
        const field = this.fields[fieldName.split(":")[0]];
        if (["date", "datetime"].includes(field.type)) {
            const range = groupData.__range[fieldName];
            if (!range) {
                return false;
            }
            const dateValue = this._parseServerValue(field, range.to);
            return dateValue.minus({ [field.type === "date" ? "day" : "second"]: 1 });
        } else {
            const value = this._parseServerValue(field, groupData[fieldName]);
            return Array.isArray(value) ? value[0] : value;
        }
    }

    async _loadGroups() {
        const firstGroupByName = this.firstGroupBy.split(":")[0];
        const _orderBy = this.orderBy.filter(
            (o) => o.name === firstGroupByName || this.fields[o.name].group_operator !== undefined
        );
        const orderby = orderByToString(_orderBy);
        const { groups, length } = await this.model.orm.webReadGroup(
            this.resModel,
            this.domain,
            unique([...this.fieldNames, firstGroupByName]),
            [this.firstGroupBy],
            {
                orderby,
                lazy: true,
                expand: this.expand,
                offset: this.offset,
                limit: this.limit,
                context: this.context,
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
                        groupParams.value = this._getValueFromGroupData(data, key);
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
                            if (AGGREGATABLE_FIELD_TYPES.includes(this.fields[key].type)) {
                                groupParams.aggregates[key] = value;
                            }
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
                const finalState = { ...params, ...state };
                const hasValue = isRelational(this.groupByField) ? finalState.value : true;
                if (hasValue && !("isFolded" in finalState)) {
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
        const { quickCreateView: viewRef } = this.model;
        let quickCreateFields = DEFAULT_QUICK_CREATE_FIELDS;
        let quickCreateForm = DEFAULT_QUICK_CREATE_VIEW;
        let quickCreateRelatedModels = {};
        if (viewRef) {
            const { fields, relatedModels, views } = await this.model.viewService.loadViews({
                context: { ...this.context, form_view_ref: viewRef },
                resModel: this.resModel,
                views: [[false, "form"]],
            });
            quickCreateFields = fields;
            quickCreateForm = views.form;
            quickCreateRelatedModels = relatedModels;
        }
        const models = {
            ...quickCreateRelatedModels,
            [this.modelName]: quickCreateFields,
        };
        return new FormArchParser().parse(quickCreateForm.arch, models, this.modelName);
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
            this.resId = params.value || false;
            this.data = {};
        } else {
            this.data = null;
        }
        const listParams = {
            data: params.data,
            domain: this.groupDomain,
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

    get records() {
        return this.list.records;
    }

    // ------------------------------------------------------------------------
    // Public
    // ------------------------------------------------------------------------

    /**
     * @see DynamicRecordList.addRecord
     */
    addRecord(record, index) {
        this.count++;
        return this.list.addRecord(record, index);
    }

    addExistingRecord(resId, atFirstPosition = false) {
        this.count++;
        return this.list.addExistingRecord(resId, atFirstPosition);
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
            return this.model.orm.unlink(this.resModel, [this.value], {
                context: this.context,
            });
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
        const { name, selection, type, granularity } = this.groupByField;
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
                const groupedBy = granularity ? `${name}:${granularity}` : name;
                const range = this.range[groupedBy];
                if (!range) {
                    return false;
                }
                if (type === "date") {
                    return serializeDate(deserializeDate(range.to).minus({ day: 1 }));
                } else {
                    return serializeDateTime(deserializeDateTime(range.to).minus({ second: 1 }));
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

    quickCreate(activeFields, context, atFirstPosition = false) {
        const ctx = {
            ...context,
            [`default_${this.groupByField.name}`]: this.getServerValue(),
        };
        return this.list.quickCreate(activeFields, ctx, atFirstPosition);
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

    valueEquals(value) {
        return this.value instanceof DateTime ? this.value.equals(value) : this.value === value;
    }
}

function add(arr, el) {
    const index = arr.indexOf(el);
    if (index === -1) {
        arr.push(el);
    }
}

function remove(arr, el) {
    const index = arr.indexOf(el);
    if (index > -1) {
        arr.splice(index, 1);
    }
}

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
        this.onRecordWillSwitchMode = async (record, mode, options) => {
            const editedRecord = this.editedRecord;
            this.editedRecord = null;
            if (editedRecord) {
                // Validity is checked if one of the following is true:
                // - "switchMode" has been called with explicit "checkValidity"
                // - the record is dirty
                // - the record is new and can be abandonned
                const shouldCheckValidity =
                    options.checkValidity || editedRecord.isDirty || editedRecord.canBeAbandoned;
                const isValid = !shouldCheckValidity || (await editedRecord.checkValidity());
                if (isValid) {
                    await editedRecord.switchMode("readonly");
                } else if (editedRecord.id !== record.id && editedRecord.canBeAbandoned) {
                    this.abandonRecord(editedRecord.id);
                } else {
                    this.editedRecord = editedRecord;
                    return false;
                }
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
    async delete(recordIds) {
        if (!Array.isArray(recordIds)) {
            recordIds = [recordIds];
        }
        const ids = [];
        for (const recordId of recordIds) {
            const record = this._cache[recordId];
            if (record.isVirtual) {
                delete this._cache[recordId];
            }
            const id = record.resId || record.virtualId;
            ids.push(id);
        }
        if (this.field.type === "many2many") {
            const nextIds = this.records.filter((rec) => !ids.includes(rec.resId || rec.virtualId));
            return this.replaceWith(nextIds);
        }
        const commands = ids.map((id) => x2ManyCommands.delete(id));
        this.applyCommands(commands);
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
                const result = await this.model.orm.read(this.resModel, resIds, orderFieldNames, {
                    context: this.context,
                });
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
                    this._initialValues[id] = command[2];
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

    unselectRecord() {
        return unselectRecord(this.editedRecord);
    }
}

StaticList.DEFAULT_LIMIT = 40;

export class RelationalModel extends Model {
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        this.action = action;
        this.dialogService = dialog;
        this.notificationService = notification;
        this.rpc = rpc;
        this.user = user;
        this.company = company;
        this.viewService = view;
        this.orm = new RequestBatcherORM(rpc, user);
        this.keepLast = new KeepLast();
        this.mutex = new Mutex();

        this.onCreate = params.onCreate;
        this.multiEdit = params.multiEdit || false;
        this.quickCreateView = params.quickCreateView;
        this.defaultGroupBy = params.defaultGroupBy || false;
        this.defaultOrderBy = params.defaultOrder;
        this.handleField = params.handleField;
        this.rootType = params.rootType || "list";
        this.initialRootState = params.rootState;
        this.rootParams = {
            activeFields: params.activeFields || {},
            fields: params.fields || {},
            viewMode: params.viewMode || null,
            resModel: params.resModel,
            groupByInfo: params.groupByInfo,
        };
        this.fieldNodes = params.fieldNodes; // used by the ListConfirmationDialog
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
        this.initialValues = params.initialValues;

        // this.db = Object.create(null);
        this.root = null;

        this.nextId = 1;

        // list of models for which the DataManager's cache should be cleared on create, update and delete operations
        this.noCacheModels = ["ir.actions.act_window", "ir.filters", "ir.ui.view", "res.currency"];
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
        const state = this.root ? this.root.exportState() : this.initialRootState;
        const newRoot = this.createDataPoint(this.rootType, rootParams, state);
        await this.keepLast.add(newRoot.load({ values: this.initialValues }));
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

    /**
     * Reloads a given record and all related records (those sharing the same resId).
     * A "record-updated" event containing the given and related records is then
     * triggered on the model.
     *
     * @param {Record} record
     */
    async reloadRecords(record) {
        const records = this.rootType === "record" ? [this.root] : this.root.records;
        const relatedRecords = records.filter(
            (r) => r.id !== record.id && r.resId === record.resId
        );

        await Promise.all([record, ...relatedRecords].map((r) => r.load()));

        this.trigger("record-updated", { record, relatedRecords });
        this.notify();
    }
}

RelationalModel.services = ["action", "dialog", "notification", "rpc", "user", "view", "company"];
RelationalModel.Record = Record;
RelationalModel.Group = Group;
RelationalModel.DynamicRecordList = DynamicRecordList;
RelationalModel.DynamicGroupList = DynamicGroupList;
RelationalModel.StaticList = StaticList;
