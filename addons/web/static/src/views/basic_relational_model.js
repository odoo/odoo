/* @odoo-module */

import BasicModel from "web.BasicModel";
import fieldRegistry from "web.field_registry";
import { parse } from "web.field_utils";
import { parseArch } from "web.viewUtils";
import { traverse } from "web.utils";

import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { Dialog } from "@web/core/dialog/dialog";
import { Domain } from "@web/core/domain";
import { Model } from "@web/views/helpers/model";
import { KeepLast } from "@web/core/utils/concurrency";
import { escape } from "@web/core/utils/strings";

const { date: parseDate, datetime: parseDateTime } = parse;
const { markup, xml } = owl;
// const preloadedDataRegistry = registry.category("preloadedData");

const warningDialogBodyTemplate = xml`<t t-esc="props.message"/>`;

function mapWowlValueToLegacy(value, type) {
    switch (type) {
        case "date":
            // from luxon to moment
            return value ? parseDate(serializeDate(value), null, { isUTC: true }) : false;
        case "datetime":
            // from luxon to moment
            return value ? parseDateTime(serializeDateTime(value), null, { isUTC: true }) : false;
        case "many2one":
            return value ? { id: value[0], display_name: value[1] } : false;
        case "one2many":
        case "many2many":
            if (value.operation === "REPLACE_WITH") {
                return { operation: "REPLACE_WITH", ids: value.resIds };
            }
            break;
        default:
            return value;
    }
}

function mapViews(views) {
    const res = {};
    for (const [viewType, viewDescr] of Object.entries(views || {})) {
        const arch = parseArch(viewDescr.__rawArch);
        traverse(arch, function (node) {
            if (typeof node === "string") {
                return false;
            }
            node.attrs.modifiers = node.attrs.modifiers ? JSON.parse(node.attrs.modifiers) : {};
            return true;
        });
        // the basic model expects the former shape of load_views result, where we don't know
        // all co-model fields, only those in the subview, so we filter the fields here
        const fields = {};
        for (const f in viewDescr.activeFields) {
            fields[f] = viewDescr.fields[f];
        }
        res[viewType] = {
            arch,
            fields,
            type: viewType,
            fieldsInfo: mapActiveFieldsToFieldsInfo(viewDescr.activeFields, fields, viewType),
        };
        for (const fieldName in res[viewType].fieldsInfo[viewType]) {
            if (!res[viewType].fields[fieldName]) {
                res[viewType].fields[fieldName] = {
                    name: fieldName,
                    type: res[viewType].fieldsInfo[viewType][fieldName].type,
                };
            }
        }
    }
    return res;
}

function mapActiveFieldsToFieldsInfo(activeFields, fields, viewType) {
    const fieldsInfo = {};
    fieldsInfo[viewType] = {};
    for (const [fieldName, fieldDescr] of Object.entries(activeFields)) {
        const views = mapViews(fieldDescr.views);
        let Widget;
        if (fieldDescr.widget) {
            Widget = fieldRegistry.getAny([`${viewType}.${fieldDescr.widget}`, fieldDescr.widget]);
        } else {
            Widget = fieldRegistry.getAny([`${viewType}.${fieldDescr.type}`, fieldDescr.type]);
        }
        Widget = Widget || fieldRegistry.get("abstract");
        let domain;
        if (fieldDescr.domain && fieldDescr.domain.toString() !== "[]") {
            domain = fieldDescr.domain.toString();
        }
        const fieldInfo = {
            Widget,
            domain,
            context: fieldDescr.context,
            fieldDependencies: {}, // ??
            mode: fieldDescr.viewMode,
            modifiers: fieldDescr.modifiers,
            name: fieldName,
            options: fieldDescr.options,
            views,
            __WOWL_FIELD_DESCR__: fieldDescr,
        };

        if (fieldDescr.FieldComponent && fieldDescr.FieldComponent.limit) {
            fieldInfo.limit = fieldDescr.FieldComponent.limit;
        }

        if (Widget.prototype.fieldsToFetch) {
            fieldInfo.relatedFields = { ...Widget.prototype.fieldsToFetch };
            fieldInfo.viewType = "default";
            const defaultView = {};
            for (const fieldName of Object.keys(Widget.prototype.fieldsToFetch)) {
                defaultView[fieldName] = {};
                if (fieldDescr.fieldsToFetch[fieldName]) {
                    defaultView[fieldName].__WOWL_FIELD_DESCR__ =
                        fieldDescr.fieldsToFetch[fieldName];
                }
            }
            fieldInfo.fieldsInfo = { default: defaultView };
            const colorField = fieldInfo.options && fieldInfo.options.color_field;
            if (colorField) {
                fieldInfo.relatedFields[colorField] = { type: "integer" };
                fieldInfo.fieldsInfo.default[colorField] = {};
                if (fieldDescr.fieldsToFetch[colorField]) {
                    fieldInfo.fieldsInfo.default[colorField].__WOWL_FIELD_DESCR__ =
                        fieldDescr.fieldsToFetch[colorField];
                }
            }
        }
        if (fieldDescr.views && fieldDescr.views[fieldDescr.viewMode]) {
            fieldInfo.limit = fieldDescr.views[fieldDescr.viewMode].limit || 40;
            fieldInfo.orderedBy = fieldDescr.views[fieldDescr.viewMode].defaultOrder;
        }
        if (fieldDescr.onChange && !fields[fieldName].onChange) {
            fields[fieldName].onChange = "1";
        }
        // TODO: __no_fetch
        // FIXME? FieldWidget in kanban undefined
        fieldsInfo[viewType][fieldName] = fieldInfo;
    }
    return fieldsInfo;
}

/**
 * @param {any} modifier
 * @param {Object} evalContext
 * @returns {boolean}
 */
export function evalDomain(modifier, evalContext) {
    if (Array.isArray(modifier)) {
        modifier = new Domain(modifier).contains(evalContext);
    }
    return !!modifier;
}

let nextId = 0;
class DataPoint {
    /**
     * @param {RelationalModel} model
     * @param {Object} [params={}]
     * @param {Object} [state={}]
     */
    constructor(model, params, state = {}) {
        this.id = `datapoint_${nextId++}`;
        this.model = model;

        let info;
        if (params.__bm_load_params__) {
            this.__bm_load_params__ = params.__bm_load_params__;
            info = this.__bm_load_params__;
        } else if (params.handle) {
            this.__bm_handle__ = params.handle;
            info = this.model.__bm__.get(this.__bm_handle__);
        } else {
            throw new Error("Datapoint needs load params or handle");
        }
        this.context = info.context;
        this.resModel = info.model || info.modelName;
        this.fields = info.fields;
        this.activeFields = {};

        this.__viewType = params.viewType || info.viewType;
        const fieldsInfo = (info.fieldsInfo && info.fieldsInfo[this.__viewType]) || {};
        for (const [name, descr] of Object.entries(fieldsInfo)) {
            this.activeFields[name] = descr.__WOWL_FIELD_DESCR__ || {};
        }
        this.fieldNames = Object.keys(this.activeFields);

        this.setup(params, state);
    }

    /**
     * @abstract
     * @param {Object} params
     * @param {Object} state
     */
    setup() {}

    get evalContext() {
        const datapoint = this.model.__bm__.localData[this.__bm_handle__];
        const evalContext = this.model.__bm__._getEvalContext(datapoint);
        // FIXME: in the basic model, we set the toJSON function on x2many values
        // s.t. we send commands to the server. In wowl Domain, we JSON.stringify
        // values to compare them, so it doesn't work as expected.
        for (const key in evalContext) {
            if (evalContext[key]) {
                delete evalContext[key].toJSON;
            }
        }
        return evalContext;
    }

    exportState() {
        return {};
    }

    async load() {
        throw new Error("load must be implemented");
    }
}

export class Record extends DataPoint {
    setup(params, state) {
        this.data = {};
        this._invalidFields = new Set();
        this.preloadedData = {};
        this.selected = false;
        this.isInQuickCreation = params.isInQuickCreation || false;
        this._onChangePromise = Promise.resolve({});
        this._domains = {};

        this.canBeAbandoned = this.isVirtual;

        this._requiredFields = {};
        for (const [fieldName, activeField] of Object.entries(this.activeFields)) {
            const { modifiers } = activeField;
            if (modifiers && modifiers.required) {
                this._requiredFields[fieldName] = modifiers.required;
            }
        }

        this.mode = params.mode || (this.resId ? state.mode || "readonly" : "edit");
        this._onWillSwitchMode = params.onRecordWillSwitchMode || (() => {});

        if (this.__bm_handle__) {
            this.__syncData();
        }
    }

    get isVirtual() {
        // FIXME: not sure about this virtual thing
        return !this.resId;
    }

    get resId() {
        if (this.__bm_handle__) {
            const resId = this.model.__bm__.localData[this.__bm_handle__].res_id;
            if (typeof resId === "string") {
                return false;
            }
            return resId;
        } else {
            // record not loaded yet
            return this.__bm_load_params__.res_id;
        }
    }

    get resIds() {
        return this.model.__bm__.localData[this.__bm_handle__].res_ids;
    }

    get isDirty() {
        return this.model.__bm__.isDirty(this.__bm_handle__);
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

    get isNew() {
        return this.model.__bm__.isNew(this.__bm_handle__);
    }

    get isInEdition() {
        return this.mode === "edit";
    }

    checkValidity() {
        for (const fieldName in this.activeFields) {
            const fieldType = this.fields[fieldName].type;
            if (fieldName in this._requiredFields) {
                if (!evalDomain(this._requiredFields[fieldName], this.evalContext)) {
                    this._removeInvalidField(fieldName);
                    continue;
                }
            }
            switch (fieldType) {
                case "boolean":
                case "float":
                case "integer":
                    continue;
                case "one2many":
                case "many2many":
                    if (!this.checkX2ManyValidity(fieldName)) {
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
                if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
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

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isReadonly(fieldName) {
        const { readonly } = this.activeFields[fieldName].modifiers || {};
        return evalDomain(readonly, this.evalContext);
    }

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isRequired(fieldName) {
        const { required } = this.activeFields[fieldName].modifiers || {};
        return evalDomain(required, this.evalContext);
    }

    checkX2ManyValidity(fieldName) {
        const value = this.data[fieldName];
        const toAbandon = [];
        let isValid = true;
        for (const record of value.records) {
            if (!record.checkValidity()) {
                if (record.canBeAbandoned) {
                    toAbandon.push(record);
                } else {
                    isValid = false;
                }
            }
        }
        for (const record of toAbandon) {
            value.abandonRecord(record.id);
        }
        return isValid;
    }

    setInvalidField(fieldName) {
        this._invalidFields.add(fieldName);
        const bm = this.model.__bm__;
        bm.setDirty(this.__bm_handle__);
        this.model.notify();
    }

    isInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    async load() {
        if (!this.__bm_handle__) {
            this.__bm_handle__ = await this.model.__bm__.load({ ...this.__bm_load_params__ });
        } else if (!this.isVirtual) {
            await this.model.__bm__.reload(this.__bm_handle__, { viewType: this.__viewType });
        } else {
            this.model.__bm__.generateDefaultValues(this.__bm_handle__, {
                viewType: this.__viewType,
            });
        }
        this.__syncData();
        this._invalidFields = new Set();
    }

    exportState() {
        return {
            mode: this.mode,
            resId: this.resId,
            resIds: this.resIds,
        };
    }

    __syncData(force) {
        const bm = this.model.__bm__;
        const legDP = bm.get(this.__bm_handle__);
        this.canBeAbandoned = bm.canBeAbandoned(this.__bm_handle__);
        const data = Object.assign({}, legDP.data);
        for (const fieldName of Object.keys(data)) {
            const fieldType = legDP.fields[fieldName].type;
            switch (fieldType) {
                case "date":
                    // from moment to luxon
                    if (data[fieldName]) {
                        data[fieldName] = deserializeDate(JSON.stringify(data[fieldName]));
                    }
                    break;
                case "datetime":
                    // from moment to luxon
                    if (data[fieldName]) {
                        data[fieldName] = deserializeDateTime(JSON.stringify(data[fieldName]));
                    }
                    break;
                case "one2many":
                case "many2many":
                    if (this.data[fieldName] && !force) {
                        data[fieldName] = this.data[fieldName];
                        data[fieldName].__syncData();
                    } else {
                        data[fieldName] = new StaticList(this.model, {
                            handle: data[fieldName].id,
                            viewType: this.activeFields[fieldName].viewMode,
                            parentViewType: this.__viewType,
                        });
                        data[fieldName].__fieldName__ = fieldName;
                    }
                    break;
                case "many2one":
                    data[fieldName] = data[fieldName]
                        ? [data[fieldName].data.id, data[fieldName].data.display_name]
                        : false;
                    break;
                case "char":
                    data[fieldName] = data[fieldName] || "";
            }
            if (legDP.specialData[fieldName]) {
                this.preloadedData[fieldName] = legDP.specialData[fieldName];
            }
        }
        this.data = data;
    }

    getFieldContext(fieldName) {
        return this.model.__bm__.localData[this.__bm_handle__].getContext({
            fieldName,
            viewType: this.__viewType,
        });
    }

    getFieldDomain(fieldName) {
        return Domain.and([
            this.model.__bm__.localData[this.__bm_handle__].getDomain({
                fieldName,
                viewType: this.__viewType,
            }),
        ]);
    }

    // loadPreloadedData() {
    //     const fetchPreloadedData = async (fetchFn, fieldName) => {
    //         const domain = this.getFieldDomain(fieldName).toList(this.evalContext).toString();
    //         if (domain.toString() !== this.preloadedDataCaches[fieldName]) {
    //             this.preloadedDataCaches[fieldName] = domain.toString();
    //             this.preloadedData[fieldName] = await fetchFn(this.model.orm, this, fieldName);
    //         }
    //     };

    //     const proms = [];
    //     for (const fieldName in this.activeFields) {
    //         const activeField = this.activeFields[fieldName];
    //         // @FIXME type should not be get like this
    //         const type = activeField.widget || this.fields[fieldName].type;
    //         if (!activeField.invisible && preloadedDataRegistry.contains(type)) {
    //             proms.push(fetchPreloadedData(preloadedDataRegistry.get(type), fieldName));
    //         }
    //     }
    //     return Promise.all(proms);
    // }

    async update(fieldName, value) {
        const fieldType = this.fields[fieldName].type;
        const parentID = this.model.__bm__.localData[this.__bm_handle__].parentID;
        if (parentID) {
            //  && fieldType === "one2many"
            // inside an x2many (parentID is the id of the static list datapoint)
            const mainRecordId = this.model.__bm__.localData[parentID].parentID;
            const mainRecordDP = this.model.__bm__.localData[mainRecordId];
            const mainRecordValues = { ...mainRecordDP.data, ...mainRecordDP._changes };
            const x2manyFieldName = Object.keys(mainRecordValues).find(
                (name) => mainRecordValues[name] === parentID
            );
            if (!x2manyFieldName) {
                throw new Error("couldn't find x2many field name");
            }
            const changes = {};
            const data = {};
            data[fieldName] = mapWowlValueToLegacy(value, fieldType);
            changes[x2manyFieldName] = { operation: "UPDATE", id: this.__bm_handle__, data };
            await this.model.__bm__.notifyChanges(mainRecordId, changes);
            this.model.root.__syncData();
        } else {
            const changes = {};
            changes[fieldName] = mapWowlValueToLegacy(value, fieldType);
            await this.model.__bm__.notifyChanges(this.__bm_handle__, changes, {
                viewType: this.__viewType,
            });
            this.__syncData();
        }
        this._removeInvalidField(fieldName);
        this.canBeAbandoned = false;
        this.model.notify();
    }

    /**
     *
     * @param {Object} options
     * @param {boolean} [options.stayInEdition=false]
     * @param {boolean} [options.noReload=false] prevents the record from
     *  reloading after changes are applied, typically used to defer the load.
     * @returns {Promise<boolean>}
     */
    async save(options = { stayInEdition: false, noReload: false, savePoint: false }) {
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
        const saveOptions = {
            reload: !options.noReload,
            savePoint: options.savePoint,
        };
        const changedFields = await this.model.__bm__.save(this.__bm_handle__, saveOptions);
        this.__syncData(true);
        if (!options.stayInEdition) {
            this.switchMode("readonly");
        }
        if (this.isVirtual || changedFields.length) {
            this.model.notify();
        }
        return true;
    }

    async archive() {
        await this.model.__bm__.actionArchive([this.resId], this.__bm_handle__);
        this.__syncData();
        this.model.notify();
    }

    async unarchive() {
        await this.model.__bm__.actionUnarchive([this.resId], this.__bm_handle__);
        this.__syncData();
        this.model.notify();
    }

    // FIXME AAB: to discuss: not sure we want to keep resIds in the model (this concerns
    // "duplicate" and "delete"). Alternative: handle this in form_view (but then what's the
    // point of calling a Record method to do the operation?)
    async duplicate() {
        this.__bm_handle__ = await this.model.__bm__.duplicateRecord(this.__bm_handle__);
        this.__syncData();
        this.switchMode("edit");
        this.model.notify();
    }

    async delete() {
        await this.model.__bm__.deleteRecords([this.__bm_handle__], this.resModel);
        if (this.resIds.length) {
            await this.model.__bm__.reload(this.__bm_handle__);
            this.__syncData();
        }
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

    discard() {
        this.model.__bm__.discardChanges(this.__bm_handle__);
        this.__syncData();
        if (this.resId) {
            this.switchMode("readonly");
        }
        this.model.notify();
    }

    _removeInvalidField(fieldName) {
        this._invalidFields.delete(fieldName);
    }
}

export class StaticList extends DataPoint {
    setup(params, state) {
        // this.isOne2Many = params.field.type === "one2many"; // bof

        // const legDP = this.model.__bm__.get(params.handle);
        /** @type {Record[]} */
        this.records = [];

        this.__parentViewType = params.parentViewType;

        // this.views = legDP.fieldsInfo;
        // this.viewMode = legDP.viewType;

        // this.validated = {};
        // this.rawContext = params.rawContext;
        // this.getEvalContext = params.getEvalContext;

        this.editedRecord = null;
        this.onRecordWillSwitchMode = async (record, mode) => {
            if (params.onRecordWillSwitchMode) {
                params.onRecordWillSwitchMode(record, mode);
            }
            const editedRecord = this.editedRecord;
            this.editedRecord = null;
            if (editedRecord && editedRecord.id === record.id && mode === "readonly") {
                return record.checkValidity();
            }
            if (editedRecord) {
                await editedRecord.switchMode("readonly");
            }
            if (mode === "edit") {
                this.editedRecord = record;
            }
        };

        this.__syncData();
    }

    __syncData() {
        const legacyListDP = this.model.__bm__.get(this.__bm_handle__);
        this.records = legacyListDP.data.map((dp) => {
            let record = this.records.find((r) => r.__bm_handle__ === dp.id);
            if (record) {
                record.__syncData();
            } else {
                record = new Record(this.model, {
                    handle: dp.id,
                    onRecordWillSwitchMode: this.onRecordWillSwitchMode,
                    mode: "readonly",
                    viewType: this.__viewType,
                });
                if (record.mode === "edit" && this.editedRecord) {
                    this.editedRecord.mode = "readonly";
                }
            }
            return record;
        });
        this.editedRecord = this.records.find((r) => r.mode === "edit") || null;
    }

    // FIXME: remove?
    get resIds() {
        return this.model.__bm__.get(this.__bm_handle__).res_ids;
    }
    get currentIds() {
        return this.model.__bm__.get(this.__bm_handle__).res_ids;
    }

    get orderBy() {
        return this.model.__bm__.localData[this.__bm_handle__].orderedBy;
    }
    get limit() {
        return this.model.__bm__.localData[this.__bm_handle__].limit;
    }
    get offset() {
        return this.model.__bm__.localData[this.__bm_handle__].offset;
    }
    get count() {
        return this.currentIds.length;
    }

    abandonRecord(recordId) {
        const record = this.records.find((r) => r.id === recordId);
        this.model.__bm__.removeLine(record.__bm_handle__);
        this.__syncData();
        this.model.notify();
    }

    removeRecord(record) {
        // if (true) { see _onRemoveRecord in rel fields
        this.delete(record.id);
        // }
    }

    async delete(recordId, operation = "DELETE") {
        const legDP = this.model.__bm__.localData[this.__bm_handle__];
        const parentLegDP = this.model.__bm__.localData[legDP.parentID];
        const parentValues = { ...parentLegDP.data, ...parentLegDP._changes };
        const fieldName = Object.keys(parentValues).find(
            (name) => parentValues[name] === this.__bm_handle__
        );
        // can use this.__fieldName__
        const changes = {};
        const record = this.records.find((r) => r.id === recordId);
        changes[fieldName] = { operation, ids: [record.__bm_handle__] };
        await this.model.__bm__.notifyChanges(parentLegDP.id, changes);
        this.model.root.__syncData();
        this.model.notify();
    }

    async add(res) {
        if (!(res instanceof Record)) {
            throw new Error("LPE CRASH => the RelationalModel.add API is unclear");
        }
        const legDP = this.model.__bm__.localData[this.__bm_handle__];
        const parentLegDP = this.model.__bm__.localData[legDP.parentID];
        const parentValues = { ...parentLegDP.data, ...parentLegDP._changes };
        // can use this.__fieldName
        const fieldName = Object.keys(parentValues).find(
            (name) => parentValues[name] === this.__bm_handle__
        );

        const record = res;

        const recHandle = record.__bm_handle__;
        await this.model.__bm__.save(recHandle, { savePoint: true });
        const changes = {};
        changes[fieldName] = { operation: "ADD", id: recHandle };
        await this.model.__bm__.notifyChanges(parentLegDP.id, changes);
        this.__syncData();
        this.model.notify();
    }

    /** Creates a Draft record from nothing and edits it. Relevant in editable x2m's */
    async addNew(params) {
        const legDP = this.model.__bm__.localData[this.__bm_handle__];
        const parentLegDP = this.model.__bm__.localData[legDP.parentID];
        const parentValues = { ...parentLegDP.data, ...parentLegDP._changes };
        // can use this.__fieldName
        const fieldName = Object.keys(parentValues).find(
            (name) => parentValues[name] === this.__bm_handle__
        );
        const position = params.position;
        const changes = {};
        changes[fieldName] = { context: [params.context], operation: "CREATE", position };
        await this.model.__bm__.save(this.__bm_handle__, { savePoint: true });
        this.model.__bm__.freezeOrder(this.__bm_handle__);
        await this.model.__bm__.notifyChanges(parentLegDP.id, changes, {
            viewType: this.__parentViewType,
        });
        this.__syncData();
        if (params.mode === "edit") {
            const newRecord = this.records[position === "bottom" ? this.records.length - 1 : 0];
            await newRecord.switchMode("edit");
        }
        this.model.notify();
    }

    // x2many dialog edition
    // addRecord(record) {
    //     this.onChanges();
    //     this._cache[record.virtualId] = record;
    //     this._cache[record.virtualId] = record;
    //     this.records.push(record);
    //     this.resIds.push(record.virtualId);
    //     this.limit = this.limit + 1; // might be not good
    //     this.validated[record.virtualId] = false;
    //     this.model.notify();
    // }

    exportState() {
        return {
            limit: this.limit,
        };
    }

    async load(params) {
        await this.model.__bm__._reload(this.__bm_handle__, params);
        this.__syncData();
    }

    async sortBy(fieldName) {
        await this.model.__bm__.setSort(this.__bm_handle__, fieldName);
        this.__syncData();
        this.model.notify();
    }

    async replaceWith(resIds) {
        const basicModel = this.model.__bm__;
        const addedIds = resIds.filter((id) => !this.currentIds.includes(id));
        const deletedIds = this.currentIds.filter((id) => !resIds.includes(id));
        let operation;
        if (addedIds.length && deletedIds.length) {
            operation = {
                ids: resIds,
                operation: "REPLACE_WITH",
            };
        } else if (addedIds.length) {
            operation = {
                ids: addedIds.map((id) => ({ id })),
                operation: "ADD_M2M",
            };
        } else if (deletedIds.length) {
            operation = {
                ids: deletedIds,
                operation: "FORGET",
            };
        } else {
            // no change?
            return;
        }
        const changes = { [this.__fieldName__]: operation };
        await basicModel.notifyChanges(basicModel.localData[this.__bm_handle__].parentID, changes);
        this.__syncData();
        this.model.notify();
    }
}

export class RelationalModel extends Model {
    setup(params, { dialog, notification }) {
        this.dialogService = dialog;
        this.notificationService = notification;
        this.keepLast = new KeepLast();

        if (params.rootType !== "record") {
            throw "only record root type is supported";
        }

        this.root = null;

        this.__bm__ = new BasicModel(this, {
            fields: params.fields || {},
            modelName: params.resModel,
            useSampleModel: false, // FIXME AAB
        });
        this.__activeFields = params.activeFields;
        this.__fields = params.fields;
        this.__bm_load_params__ = {
            type: "record",
            modelName: params.resModel,
            res_id: params.resId || undefined,
            res_ids: params.resIds ? [...params.resIds] : [], // mark raw
            fields: params.fields || {},
            viewType: "form",
        };

        window.basicmodel = this;
    }

    async duplicateDatapoint(record, params) {
        const fieldsInfo = mapViews(params.views);
        await this.__bm__.addFieldsInfo(record.__bm_handle__, {
            fields: params.fields,
            viewType: params.viewMode,
            fieldInfo: fieldsInfo[params.viewMode].fieldsInfo[params.viewMode],
        });
        const newRecord = new Record(this, {
            handle: record.__bm_handle__,
            viewType: params.viewMode,
            mode: params.mode,
        });
        newRecord.canBeAbandoned = record.canBeAbandoned;
        await newRecord.load();
        return newRecord;
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
        if (!this.__bm_load_params__.fieldsInfo) {
            // only the first time (must wait for the subviews to be loaded)
            this.__bm_load_params__.fieldsInfo = mapActiveFieldsToFieldsInfo(
                this.__activeFields || {},
                this.__fields || {},
                "form"
            );
        }
        const loadParams = { ...this.__bm_load_params__ };
        if ("resId" in params) {
            loadParams.res_id = params.resId || undefined;
        }
        if ("context" in params) {
            loadParams.context = params.context;
        }
        const state = this.root ? this.root.exportState() : {};
        const nextRoot = new Record(this, { __bm_load_params__: loadParams }, state);
        await this.keepLast.add(nextRoot.load());
        this.root = nextRoot;
        this.__bm_load_params__ = loadParams;
        this.notify();
    }
    _trigger_up(ev) {
        const evType = ev.name;
        const payload = ev.data;
        if (evType === "call_service") {
            let args = payload.args || [];
            if (payload.service === "ajax" && payload.method === "rpc") {
                // ajax service uses an extra 'target' argument for rpc
                args = args.concat(ev.target);
                return payload.callback(owl.Component.env.session.rpc(...args));
            }
            throw new Error(`call service ${payload.service} not handled in relational model`);
        } else if (evType === "warning") {
            if (payload.type === "dialog") {
                class WarningDialog extends Dialog {
                    setup() {
                        super.setup();
                        this.title = this.props.title;
                    }
                }
                WarningDialog.bodyTemplate = warningDialogBodyTemplate;
                return this.dialogService.add(WarningDialog, {
                    title: payload.title,
                    message: payload.message,
                });
            } else {
                return this.notificationService.add(payload.message, {
                    className: payload.className,
                    sticky: payload.sticky,
                    title: payload.title,
                    type: "warning",
                });
            }
        }
        throw new Error(`trigger_up(${evType}) not handled in relational model`);
    }
    createDataPoint(type, params, state = {}) {
        if (type !== "record") {
            throw new Error("LPE CRASH");
        }
        const fieldsInfo = mapActiveFieldsToFieldsInfo(
            params.activeFields,
            params.fields,
            params.viewType
        );
        fieldsInfo.context = params.context;
        params = Object.assign({}, params, {
            __bm_load_params__: {
                type: "record",
                modelName: params.resModel,
                fields: params.fields || {},
                viewType: "form",
                fieldsInfo,
                parentID: params.parentID,
                context: params.context,
            },
        });
        return new Record(this, params, state);
    }
}
RelationalModel.services = ["dialog", "notification"];
