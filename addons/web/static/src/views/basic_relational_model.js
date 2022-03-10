/* @odoo-module */

import BasicModel from "web.BasicModel";
import fieldRegistry from "web.field_registry";
import { parse } from "web.field_utils";
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

const { date: parseDate, datetime: parseDateTime } = parse;
const { xml } = owl;
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
        res[viewType] = {
            fields: viewDescr.fields,
            type: viewType,
            fieldsInfo: mapActiveFieldsToFieldsInfo(
                viewDescr.activeFields,
                viewDescr.fields,
                viewType
            ),
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
        const fieldInfo = {
            Widget: Widget || fieldRegistry.get("abstract"),
            domain: fieldDescr.domain ? fieldDescr.domain.toString() : [],
            context: fieldDescr.context,
            fieldDependencies: {}, // ??
            mode: fieldDescr.viewMode,
            modifiers: fieldDescr.modifiers,
            name: fieldName,
            options: fieldDescr.options,
            views,
            __WOWL_FIELD_DESCR__: fieldDescr,
        };
        if (fieldDescr.views && fieldDescr.views[fieldDescr.viewMode]) {
            fieldInfo.limit = fieldDescr.views[fieldDescr.viewMode].limit;
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
        this.resModel = info.model || info.modelName;
        this.fields = info.fields;
        this.activeFields = {};
        const fieldsInfo = (info.fieldsInfo && info.fieldsInfo[info.viewType]) || {};
        for (const [name, descr] of Object.entries(fieldsInfo)) {
            this.activeFields[name] = descr.__WOWL_FIELD_DESCR__;
        }
        this.fieldNames = Object.keys(this.activeFields);
        this.context = info.context;

        this.setup(params, state);
    }

    /**
     * @abstract
     * @param {Object} params
     * @param {Object} state
     */
    setup() {}

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

        this.__viewType = params.viewType;

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

    get evalContext() {
        const datapoint = this.model.__bm__.localData[this.__bm_handle__];
        const evalContext = this.model.__bm__._getEvalContext(datapoint);
        // FIXME: in the basic model, we set the toJSON function on x2many values
        // s.t. we send commands to the server. In wowl Domain, we JSON.stringify
        // values to compare them, so it doesn't work as expected.
        for (const key in evalContext) {
            delete evalContext[key].toJSON;
        }
        return evalContext;
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

    async switchMode(mode) {
        if (this.mode === mode) {
            return;
        }
        await this._onWillSwitchMode(this, mode);
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
        const { readonly } = this.activeFields[fieldName].modifiers;
        return evalDomain(readonly, this.evalContext);
    }

    /**
     * FIXME: memoize this at some point?
     * @param {string} fieldName
     * @returns {boolean}
     */
    isRequired(fieldName) {
        const { required } = this.activeFields[fieldName].modifiers;
        return evalDomain(required, this.evalContext);
    }

    setInvalidField(fieldName) {
        this._invalidFields.add({ fieldName });
        this.model.notify();
    }

    isInvalid(fieldName) {
        for (const invalid of this._invalidFields) {
            if (invalid.fieldName === fieldName) return true;
        }
        return false;
    }

    async load() {
        if (!this.__bm_handle__) {
            this.__bm_handle__ = await this.model.__bm__.load({ ...this.__bm_load_params__ });
        } else {
            await this.model.__bm__.reload(this.__bm_handle__, { viewType: this.__viewType });
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
        const legDP = this.model.__bm__.get(this.__bm_handle__);
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
                        });
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
        return this.model.__bm__.localData[this.__bm_handle__].getContext({ fieldName });
    }

    getFieldDomain(fieldName) {
        return Domain.and([
            this.model.__bm__.localData[this.__bm_handle__].getDomain({ fieldName }),
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
            await this.model.__bm__.notifyChanges(this.__bm_handle__, changes);
            this.__syncData();
        }
        let toDelete;
        for (let x of this._invalidFields) {
            if (x.fieldName === fieldName) {
                toDelete = x;
                break;
            }
        }
        if (toDelete) {
            this._invalidFields.delete(toDelete);
        }
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
        if (this._invalidFields.size > 0) {
            let invalidStringArr = [];
            for (const invalid of this._invalidFields) {
                // TODO only add debugMessage if debug mode is active.
                if (invalid.debugMessage) {
                    invalidStringArr.push(invalid.fieldName + ":" + invalid.debugMessage);
                } else {
                    invalidStringArr.push(invalid.fieldName);
                }
            }
            this.model.notificationService.add(
                this.model.env._t("Invalid fields: ") + invalidStringArr.join(", ")
            );
            return false;
        }
        const { noReload, savePoint } = options;
        await this.model.__bm__.save(this.__bm_handle__, { reload: !noReload, savePoint });
        this.__syncData(true);
        if (!options.stayInEdition) {
            this.switchMode("readonly");
        }
        this.model.notify();
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
}

export class StaticList extends DataPoint {
    setup(params, state) {
        // this.isOne2Many = params.field.type === "one2many"; // bof

        const legDP = this.model.__bm__.get(params.handle);
        /** @type {Record[]} */
        this.records = [];

        this.views = legDP.fieldsInfo;
        this.viewMode = legDP.viewType;
        this.orderBy = legDP.orderedBy;
        this.limit = legDP.limit;
        this.offset = legDP.offset;

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
                });
                if (record.mode === "edit" && this.editedRecord) {
                    this.editedRecord.mode = "readonly";
                }
            }
            return record;
        });
        this.editedRecord = this.records.find((r) => r.mode === "edit") || null;
    }

    get resIds() {
        return this.model.__bm__.get(this.__bm_handle__).res_ids;
    }

    async delete(record) {
        const legDP = this.model.__bm__.localData[this.__bm_handle__];
        const parentLegDP = this.model.__bm__.localData[legDP.parentID];
        const parentValues = { ...parentLegDP.data, ...parentLegDP._changes };
        const fieldName = Object.keys(parentValues).find(
            (name) => parentValues[name] === this.__bm_handle__
        );
        const changes = {};
        changes[fieldName] = { operation: "DELETE", ids: [record.__bm_handle__] };
        await this.model.__bm__.notifyChanges(parentLegDP.id, changes);
        this.model.root.__syncData();
        this.model.notify();
    }

    async add(context) {
        const legDP = this.model.__bm__.localData[this.__bm_handle__];
        const parentLegDP = this.model.__bm__.localData[legDP.parentID];
        const parentValues = { ...parentLegDP.data, ...parentLegDP._changes };
        const fieldName = Object.keys(parentValues).find(
            (name) => parentValues[name] === this.__bm_handle__
        );
        const changes = {};
        changes[fieldName] = { context: [context], operation: "CREATE", position: "bottom" }; // FIXME position
        await this.model.__bm__.notifyChanges(parentLegDP.id, changes);
        this.model.root.__syncData();
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

    get count() {
        return this.model.__bm__.localData[this.__bm_handle__].count;
    }

    async load() {}

    async sortBy(fieldName) {
        await this.model.__bm__.setSort(this.__bm_handle__, fieldName);
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

    duplicateDatapoint(record, params) {
        const fieldsInfo = mapViews(params.views);
        this.__bm__.addFieldsInfo(record.__bm_handle__, {
            fields: params.fields,
            viewType: params.viewMode,
            fieldInfo: fieldsInfo[params.viewMode].fieldsInfo[params.viewMode],
        });
        return new Record(this, {
            handle: record.__bm_handle__,
            viewType: params.viewMode,
            mode: params.mode,
        });
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
}
RelationalModel.services = ["dialog", "notification"];
