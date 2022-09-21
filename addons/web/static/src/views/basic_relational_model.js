/* @odoo-module */

import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { KeepLast } from "@web/core/utils/concurrency";
import { escape } from "@web/core/utils/strings";
import { mapDoActionOptionAPI } from "@web/legacy/backend_utils";
import { Model } from "@web/views/model";
import { evalDomain } from "@web/views/utils";
import { localization } from "@web/core/l10n/localization";
import BasicModel from "web.BasicModel";
import Context from "web.Context";
import fieldRegistry from "web.field_registry";
import { parse } from "web.field_utils";
import { traverse } from "web.utils";
import { parseArch } from "web.viewUtils";

const { date: parseDate, datetime: parseDateTime } = parse;
const { markup, toRaw } = owl;

const DEFAULT_HANDLE_FIELD = "sequence";

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
        case "reference":
            return value
                ? { id: value.resId, display_name: value.displayName, model: value.resModel }
                : false;
        case "one2many":
        case "many2many":
            if (value.operation === "REPLACE_WITH") {
                return { operation: "REPLACE_WITH", ids: value.resIds };
            }
            return value;
        default:
            return value;
    }
}

function mapViews(views, env) {
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
            fieldsInfo: mapActiveFieldsToFieldsInfo(viewDescr.activeFields, fields, viewType, env),
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

function mapActiveFieldsToFieldsInfo(activeFields, fields, viewType, env) {
    const fieldsInfo = {};
    fieldsInfo[viewType] = {};
    for (const [fieldName, fieldDescr] of Object.entries(activeFields)) {
        const views = mapViews(fieldDescr.views, env);
        const field = fields[fieldName];
        let Widget;
        if (fieldDescr.widget) {
            Widget = fieldRegistry.getAny([`${viewType}.${fieldDescr.widget}`, fieldDescr.widget]);
        } else {
            Widget = fieldRegistry.getAny([`${viewType}.${field.type}`, field.type]);
        }
        Widget = Widget || fieldRegistry.get("abstract");
        let domain;
        if (fieldDescr.domain) {
            domain = fieldDescr.domain.toString();
        }
        let mode = fieldDescr.viewMode;
        if (mode && mode.split(",").length !== 1) {
            mode = env.isSmall ? "kanban" : "list";
        }
        const fieldInfo = {
            Widget,
            domain,
            context: fieldDescr.context,
            fieldDependencies: {}, // ??
            force_save: fieldDescr.forceSave,
            mode,
            modifiers: fieldDescr.modifiers,
            name: fieldName,
            options: fieldDescr.options,
            views,
            widget: fieldDescr.widget,
            __WOWL_FIELD_DESCR__: fieldDescr,
        };

        if (fieldDescr.FieldComponent && fieldDescr.FieldComponent.limit) {
            fieldInfo.limit = fieldDescr.FieldComponent.limit;
        }

        if (fieldDescr.modifiers && fieldDescr.modifiers.invisible === true) {
            fieldInfo.__no_fetch = true;
        }

        if (!fieldInfo.__no_fetch && Widget.prototype.fieldsToFetch) {
            fieldDescr.fieldsToFetch = fieldDescr.fieldsToFetch || {};
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
        // FIXME? FieldWidget in kanban undefined
        fieldsInfo[viewType][fieldName] = fieldInfo;
    }
    return fieldsInfo;
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
            this.context = info.context;
        } else if (params.handle) {
            this.__bm_handle__ = params.handle;
            info = this.model.__bm__.get(this.__bm_handle__);
            this.context = this.model.__bm__.localData[this.__bm_handle__].getContext();
        } else {
            throw new Error("Datapoint needs load params or handle");
        }
        this.resModel = info.model || info.modelName;
        this.fields = info.fields;
        this.activeFields = {};

        this.__syncParent = params.__syncParent || (() => {});
        this.__viewType = params.viewType || info.viewType;
        const fieldsInfo = (info.fieldsInfo && info.fieldsInfo[this.__viewType]) || {};
        for (const [name, descr] of Object.entries(fieldsInfo)) {
            this.activeFields[name] = descr.__WOWL_FIELD_DESCR__ || {};
        }

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
        return this.model.__bm__._getLazyEvalContext(datapoint);
    }

    get fieldNames() {
        return Object.keys(this.activeFields);
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
        this._savePromise = Promise.resolve();
        this._domains = {};
        this._closeInvalidFieldsNotification = () => {};

        this._requiredFields = {};
        for (const [fieldName, activeField] of Object.entries(this.activeFields)) {
            const { modifiers } = activeField;
            if (modifiers && modifiers.required) {
                this._requiredFields[fieldName] = modifiers.required;
            }
        }

        if (!this.resId && this.__viewType === "form") {
            this.mode = "edit"; // always edit a new record in form view.
        } else {
            this.mode = params.mode || state.mode || "readonly";
        }

        this._onWillSwitchMode = params.onRecordWillSwitchMode || (() => {});

        if (this.__bm_handle__) {
            this.__syncData();
        }
    }

    // -------------------------------------------------------------------------
    // Getters
    // -------------------------------------------------------------------------

    get canBeAbandoned() {
        return this.model.__bm__.canBeAbandoned(this.__bm_handle__);
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
        return this.model.__bm__.isDirty(this.__bm_handle__);
    }

    get dirtyFields() {
        const changes = this.model.__bm__.localData[this.__bm_handle__]._changes;
        if (!changes) {
            return [];
        }
        return Object.keys(changes).map((change) => this.activeFields[change]);
    }

    get translatableFields() {
        if (!localization.multiLang) {
            return [];
        }
        return Object.values(this.fields)
            .filter((f) => f.translate)
            .map((f) => this.activeFields[f.name]);
    }

    get dirtyTranslatableFields() {
        return this.translatableFields.filter((f) => this.dirtyFields.includes(f));
    }

    get isInEdition() {
        return this.mode === "edit";
    }

    get isNew() {
        return this.model.__bm__.isNew(this.__bm_handle__);
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

    async askChanges() {
        const proms = [];
        this.model.env.bus.trigger("RELATIONAL_MODEL:NEED_LOCAL_CHANGES", { proms });
        return Promise.all([...proms, this._updatePromise]);
    }

    async checkValidity(urgent) {
        if (!urgent) {
            await this.askChanges();
        }
        for (const fieldName in this.activeFields) {
            const fieldType = this.fields[fieldName].type;
            const activeField = this.activeFields[fieldName];
            if (fieldName in this._requiredFields) {
                if (
                    !evalDomain(this._requiredFields[fieldName], this.evalContext) ||
                    (activeField && activeField.alwaysInvisible)
                ) {
                    this._removeInvalidFields([fieldName]);
                    continue;
                }
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
                case "properties":
                    if (!this.checkPropertiesValidity(fieldName)) {
                        this._setInvalidField(fieldName);
                    }
                    break;
                case "one2many":
                case "many2many":
                    if (!(await this.checkX2ManyValidity(fieldName))) {
                        this._setInvalidField(fieldName);
                    }
                    break;
                default:
                    if (!isSet && this.isRequired(fieldName) && !this.data[fieldName]) {
                        this._setInvalidField(fieldName);
                    }
            }
        }
        return !this._invalidFields.size;
    }

    async switchMode(mode, options) {
        if (this.mode === mode) {
            return true;
        }
        const canSwitch = await this._onWillSwitchMode(this, mode, options);
        if (canSwitch === false) {
            return false;
        }

        if (mode === "edit") {
            // wait for potential pending changes to be saved (done with widgets
            // allowing to edit in readonly)
            await this.model.__bm__.mutex.getUnlockedDef();
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
        return true;
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

    async checkX2ManyValidity(fieldName) {
        const list = this.data[fieldName];
        const record = list.editedRecord;
        if (record && !(await record.checkValidity())) {
            if (record.canBeAbandoned && !record.isDirty) {
                list.abandonRecord(record.id);
            } else {
                return false;
            }
        }
        return true;
    }

    /**
     * The label and the id of the properties are always required.
     *
     * @param {string} fieldName
     * @returns {boolean}
     */
    checkPropertiesValidity(fieldName) {
        const value = this.data[fieldName];
        if (!value) {
            return true;
        }
        return value.every(
            (propertyDefinition) =>
                !propertyDefinition.id ||
                (propertyDefinition.string && propertyDefinition.string.length)
        );
    }

    _setInvalidField(fieldName) {
        this._invalidFields.add(fieldName);
        this.model.notify();
    }

    setInvalidField(fieldName) {
        const bm = this.model.__bm__;
        bm.setDirty(this.__bm_handle__);
        this._setInvalidField(fieldName);
    }

    isInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    async load(params = {}) {
        if (!this.__bm_handle__) {
            this.__bm_handle__ = await this.model.__bm__.load({
                ...this.__bm_load_params__,
                viewType: this.__viewType,
            });
        } else {
            this.__bm_handle__ = await this.model.__bm__.reload(this.__bm_handle__, {
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
        const data = Object.assign({}, legDP.data);
        for (const fieldName of this.fieldNames) {
            const fieldType = legDP.fields[fieldName].type;
            switch (fieldType) {
                case "date":
                case "datetime": {
                    // from moment to luxon
                    if (data[fieldName]) {
                        const deserialize =
                            fieldType === "date" ? deserializeDate : deserializeDateTime;
                        data[fieldName] = deserialize(data[fieldName].toJSON());
                    }
                    break;
                }
                case "one2many":
                case "many2many": {
                    const currentVal = this.data[fieldName];
                    if (
                        !data[fieldName] ||
                        (currentVal && currentVal.__bm_handle__ === data[fieldName].id && !force)
                    ) {
                        data[fieldName] = this.data[fieldName];
                        data[fieldName].__syncData();
                    } else {
                        const { viewMode, views } = this.activeFields[fieldName];
                        const handleField =
                            (views && views[viewMode] && views[viewMode].handleField) || null;
                        data[fieldName] = new StaticList(this.model, {
                            handle: data[fieldName].id,
                            handleField,
                            viewType: viewMode,
                            __syncParent: async (value) => {
                                await this.model.__bm__.save(this.__bm_handle__, {
                                    savePoint: true,
                                });
                                await this.update({ [fieldName]: value });
                            },
                        });
                        data[fieldName].__fieldName__ = fieldName;
                    }
                    break;
                }
                case "many2one": {
                    if (data[fieldName]) {
                        data[fieldName] = [
                            data[fieldName].data.id,
                            data[fieldName].data.display_name || "",
                        ];
                    } else {
                        data[fieldName] = false;
                    }
                    break;
                }
                case "reference": {
                    data[fieldName] = data[fieldName]
                        ? {
                              resModel: data[fieldName].model,
                              resId: data[fieldName].data.id,
                              displayName: data[fieldName].data.display_name,
                          }
                        : false;
                    break;
                }
                case "char": {
                    data[fieldName] = data[fieldName] || "";
                    break;
                }
                case "html": {
                    data[fieldName] = markup(data[fieldName] || "");
                    break;
                }
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
        const domain = this.model.__bm__.localData[this.__bm_handle__].getDomain({
            fieldName,
            viewType: this.__viewType,
        });
        return new Domain(JSON.parse(JSON.stringify(domain))); // legacy pyjs inserts weird structures
    }

    async update(changes) {
        if (this.batchingUpdateProm) {
            // Assign changes in the current batch
            Object.assign(this.batchChanges, changes);
            return this._updatePromise;
        }

        this.batchingUpdateProm = Promise.resolve();
        this.batchChanges = Object.assign({}, changes);

        let resolveUpdatePromise;
        this._updatePromise = new Promise((r) => {
            resolveUpdatePromise = r;
        });

        await this.batchingUpdateProm;
        changes = this.batchChanges;
        this.batchingUpdateProm = null;
        this.batchChanges = null;

        const data = {};
        for (const [fieldName, value] of Object.entries(changes)) {
            const fieldType = this.fields[fieldName].type;
            data[fieldName] = mapWowlValueToLegacy(value, fieldType);
        }
        if (this._urgentSave) {
            return this.model.__bm__.notifyChanges(this.__bm_handle__, data, {
                viewType: this.__viewType,
                notifyChange: false,
            });
        }

        const parentID = this.model.__bm__.localData[this.__bm_handle__].parentID;
        if (parentID && this.__viewType === "list") {
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
            const operation = { operation: "UPDATE", id: this.__bm_handle__, data };
            const prom = this.__syncParent(operation);
            prom.catch(resolveUpdatePromise);
            await prom;
        } else {
            const prom = this.model.__bm__.notifyChanges(this.__bm_handle__, data, {
                viewType: this.__viewType,
            });
            prom.catch(resolveUpdatePromise); // onchange rpc may return an error
            await prom;
            this.__syncData();
        }
        this._removeInvalidFields(Object.keys(changes));
        this.model.notify();
        resolveUpdatePromise();
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
        const shouldSwitchToReadonly = !options.stayInEdition && this.isInEdition;
        let resolveSavePromise;
        this._savePromise = new Promise((r) => {
            resolveSavePromise = r;
        });
        this._closeInvalidFieldsNotification();
        if (!(await this.checkValidity())) {
            const invalidFields = [...this._invalidFields].map((fieldName) => {
                return `<li>${escape(this.fields[fieldName].string || fieldName)}</li>`;
            }, this);
            this._closeInvalidFieldsNotification = this.model.notificationService.add(
                markup(`<ul>${invalidFields.join("")}</ul>`),
                {
                    title: this.model.env._t("Invalid fields: "),
                    type: "danger",
                }
            );
            resolveSavePromise();
            return false;
        }
        const saveOptions = {
            reload: !options.noReload,
            savePoint: options.savePoint,
        };
        try {
            await this.model.__bm__.save(this.__bm_handle__, saveOptions);
        } catch (_e) {
            resolveSavePromise();
            if (!this.isInEdition) {
                await this.load();
                this.model.notify();
            }
            return false;
        }
        this.__syncData(true);
        if (shouldSwitchToReadonly) {
            this.switchMode("readonly");
        }
        this.model.notify();
        resolveSavePromise();
        return true;
    }

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
     *
     * @param {string} recordID
     * @private
     */
    async urgentSave() {
        this.model.__bm__.bypassMutex = true;
        this._urgentSave = true;
        this.model.env.bus.trigger("RELATIONAL_MODEL:WILL_SAVE_URGENTLY");
        await Promise.resolve();
        this.__syncData();
        if (this.isDirty && (await this.checkValidity(true))) {
            this.model.__bm__.save(this.__bm_handle__, { reload: false });
        }
        this.model.__bm__.bypassMutex = false;
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
            await this.load();
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

    async discard() {
        await this._savePromise;
        this._closeInvalidFieldsNotification();
        this.model.__bm__.discardChanges(this.__bm_handle__);
        this._invalidFields = new Set();
        this.__syncData();
        if (this.resId) {
            this.switchMode("readonly");
        }
        this.model.notify();
    }

    _removeInvalidFields(fieldNames) {
        for (const fieldName of fieldNames) {
            this._invalidFields.delete(fieldName);
        }
    }
}

export class StaticList extends DataPoint {
    setup(params) {
        /** @type {Record[]} */
        this.records = [];

        this.handleField = params.handleField;

        this.editedRecord = null;
        this.onRecordWillSwitchMode = async (record, mode, options = {}) => {
            if (mode === "edit") {
                await this.model.__bm__.save(this.__bm_handle__, { savePoint: true });
                this.model.__bm__.freezeOrder(this.__bm_handle__);
            }

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

        this.__syncData();
    }

    __syncData() {
        const legacyListDP = this.model.__bm__.get(this.__bm_handle__);
        this.records = legacyListDP.data.map((dp) => {
            let record = this.records.find((r) => r.__bm_handle__ === dp.id);
            if (record) {
                record.__syncData();
            } else {
                record = new this.model.constructor.Record(this.model, {
                    handle: dp.id,
                    onRecordWillSwitchMode: this.onRecordWillSwitchMode,
                    mode: "readonly",
                    viewType: this.__viewType,
                    __syncParent: async (value) => {
                        await this.__syncParent(value);
                    },
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

    canResequence() {
        return this.handleField || DEFAULT_HANDLE_FIELD in this.fields;
    }

    removeRecord(record) {
        // if (true) { see _onRemoveRecord in rel fields
        this.delete(record.id);
        // }
    }

    async delete(recordId, operation = "DELETE") {
        const record = this.records.find((r) => r.id === recordId);
        await this.__syncParent({ operation, ids: [record.__bm_handle__] });
    }

    async add(object, params = { isM2M: false }) {
        let operation;
        const bm = this.model.__bm__;
        if (object instanceof Record) {
            const recHandle = object.__bm_handle__;
            await bm.save(recHandle, { savePoint: !params.isM2M, viewType: object.__viewType });
            if (params.isM2M) {
                const id = bm.localData[recHandle].res_id;
                operation = { operation: "ADD_M2M", ids: [{ id }] };
            } else {
                operation = { operation: "ADD", id: recHandle };
            }
        } else if (Array.isArray(object) && params.isM2M) {
            const oldIds = this.resIds;
            const newIds = object.filter((id) => !oldIds.includes(id)).map((id) => ({ id }));
            operation = { operation: "ADD_M2M", ids: newIds };
        }
        await this.__syncParent(operation);
    }

    /** Creates a Draft record from nothing and edits it. Relevant in editable x2m's */
    async addNew(params) {
        const position = params.position;
        const operation = { context: [params.context], operation: "CREATE", position };
        await this.model.__bm__.save(this.__bm_handle__, { savePoint: true });
        this.model.__bm__.freezeOrder(this.__bm_handle__);
        await this.__syncParent(operation);
        if (params.mode === "edit") {
            const newRecord = this.records[position === "bottom" ? this.records.length - 1 : 0];
            await newRecord.switchMode("edit");
        }
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
        await this.__syncParent(operation);
    }

    /**
     * @param {string} dataRecordId
     * @param {string} dataGroupId
     * @param {string} refId
     * @param {string} targetGroupId
     * @returns {Promise<Record>}
     */
    async moveRecord(dataRecordId, dataGroupId, refId, targetGroupId) {
        await this.resequence(dataRecordId, refId);
    }

    /**
     * @param {RecordId} movedId  // id of the moved record
     * @param {RecordId | null} targetId // id of the record (if any) that must be before moved record after operation is done
     */
    async resequence(movedId, targetId) {
        if (!this.canResequence()) {
            // There is no handle field on the current model
            return;
        }

        if (this.__viewType === "list") {
            await this.model.__bm__.save(this.__bm_handle__, { savePoint: true });
            this.model.__bm__.freezeOrder(this.__bm_handle__);
        }

        const handleField = this.handleField || DEFAULT_HANDLE_FIELD;
        const records = [...this.records];
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

        const sequences = toReorder.map(getSequence);
        const offset = sequences.length && Math.min(...sequences);

        const operations = toReorder.map((record, i) => ({
            operation: "UPDATE",
            id: record.__bm_handle__,
            data: { [handleField]: offset + i },
        }));
        const lastOperation = operations.pop();

        const parentID = this.model.__bm__.localData[this.__bm_handle__].parentID;

        await Promise.all(
            operations.map((op) => {
                this.model.__bm__.notifyChanges(
                    parentID,
                    { [this.__fieldName__]: op },
                    { notifyChange: false }
                );
            })
        );

        try {
            await this.model.__bm__.notifyChanges(parentID, {
                [this.__fieldName__]: lastOperation,
            });
        } finally {
            if (this.__viewType === "list") {
                await this.model.__bm__.setSort(this.__bm_handle__, handleField);
            }
        }

        this.records = records;

        this.__syncData();
        this.model.notify();
    }

    async unselectRecord(canDiscard = false) {
        // something seems wrong with switchMode --> review system?
        const editedRecord = this.editedRecord;
        if (!editedRecord) {
            return true;
        }

        const isValid = await editedRecord.checkValidity();
        const handle = editedRecord.__bm_handle__;
        if (!editedRecord.isDirty && ((canDiscard && editedRecord.isNew) || !isValid)) {
            this.model.__bm__.discardChanges(handle);
            if (editedRecord.canBeAbandoned) {
                this.model.__bm__.removeLine(handle);
            }
            this.__syncData();
            this.editedRecord = null;
            return await editedRecord.switchMode("readonly");
        } else if (isValid) {
            return await editedRecord.switchMode("readonly");
        }
        return false;
    }
}

export class RelationalModel extends Model {
    setup(params, { action, dialog, notification }) {
        this.actionService = action;
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

        const res_id = params.resId || undefined;
        const res_ids = (params.resIds ? toRaw(params.resIds) : null) || (res_id ? [res_id] : []);

        this.__bm_load_params__ = {
            type: "record",
            modelName: params.resModel,
            res_id,
            res_ids,
            fields: params.fields || {},
            viewType: "form",
        };

        this.initialMode = params.mode;
    }

    async duplicateDatapoint(record, params) {
        const bm = this.__bm__;
        const fieldsInfo = mapViews(params.views, this.env);
        const handle = record.__bm_handle__;

        // Sync with the mutex to wait for potential onchanges
        await bm.mutex.getUnlockedDef();

        await bm.addFieldsInfo(handle, {
            fields: params.fields,
            viewType: params.viewMode,
            fieldInfo: fieldsInfo[params.viewMode].fieldsInfo[params.viewMode],
        });

        // determine fieldNames to load (comes from basic_view.js)
        const legRec = this.__bm__.get(record.__bm_handle__);
        const viewType = params.viewMode;
        const viewFields = Object.keys(legRec.fieldsInfo[viewType]);
        const fieldNames = _.difference(viewFields, Object.keys(legRec.data));
        const legFieldsInfo = legRec.fieldsInfo[viewType];

        // Suppose that in a form view, there is an x2many list view with
        // a field F, and that F is also displayed in the x2many form view.
        // In this case, F is represented in legRec.data (as it is known by
        // the x2many list view), but the loaded information may not suffice
        // in the form view (e.g. if field is a many2many list in the form
        // view, or if it is displayed by a widget requiring specialData).
        // So when this happens, F is added to the list of fieldNames to fetch.
        for (const name of viewFields) {
            if (!fieldNames.includes(name)) {
                const fieldType = legRec.fields[name].type;
                const fieldInfo = legFieldsInfo[name];

                // SpecialData case: field requires specialData that haven't
                // been fetched yet.
                if (fieldInfo.Widget) {
                    const requiresSpecialData = fieldInfo.Widget.prototype.specialData;
                    if (requiresSpecialData && !(name in legRec.specialData)) {
                        fieldNames.push(name);
                        continue;
                    }
                }

                // X2Many case: field is an x2many displayed as a list or
                // kanban view, but the related fields haven't been loaded yet.
                if (fieldType === "one2many" || fieldType === "many2many") {
                    if (!("fieldsInfo" in legRec.data[name])) {
                        fieldNames.push(name);
                    } else {
                        const x2mFieldInfo = legRec.fieldsInfo[params.viewMode][name];
                        const viewType = x2mFieldInfo.viewType || x2mFieldInfo.mode;
                        const knownFields = Object.keys(
                            legRec.data[name].fieldsInfo[legRec.data[name].viewType] || {}
                        );
                        const newFields = Object.keys(legRec.data[name].fieldsInfo[viewType] || {});
                        if (newFields.filter((f) => !knownFields.includes(f)).length) {
                            fieldNames.push(name);
                        }

                        if (legRec.data[name].viewType === "default") {
                            // Use case: x2many (tags) in x2many list views
                            // When opening the x2many legRec form view, the
                            // x2many will be reloaded but it may not have
                            // the same fields (ex: tags in list and list in
                            // form) so we need to merge the fieldsInfo to
                            // avoid losing the initial fields (display_name)
                            const fieldViews = fieldInfo.views || fieldInfo.fieldsInfo || {};
                            const defaultFieldInfo = legRec.data[name].fieldsInfo.default;
                            _.each(fieldViews, function (fieldView) {
                                _.defaults(fieldView.fields, defaultFieldInfo);
                                _.each(fieldView.fieldsInfo, function (x2mFieldInfo) {
                                    _.defaults(x2mFieldInfo, defaultFieldInfo);
                                });
                            });
                        }
                    }
                }
                // Many2one: context is not the same between the different views
                // this means the result of a name_get could differ
                if (fieldType === "many2one") {
                    if (
                        JSON.stringify(legRec.data[name].context) !==
                        JSON.stringify(fieldInfo.context)
                    ) {
                        fieldNames.push(name);
                    }
                }
            }
        }

        if (fieldNames.length) {
            if (this.__bm__.isNew(record.__bm_handle__)) {
                await this.__bm__.generateDefaultValues(record.__bm_handle__, {
                    fieldNames: fieldNames,
                    viewType: viewType,
                });
            } else {
                await this.__bm__.reload(record.__bm_handle__, {
                    fieldNames: fieldNames,
                    keepChanges: true,
                    viewType: viewType,
                });
            }
        }

        const Record = this.constructor.Record;
        const newRecord = new Record(this, {
            handle,
            viewType: params.viewMode,
            mode: params.mode,
        });

        const recordSave = Record.prototype.save;
        record.save = recordSave;
        record.save = async (...args) => {
            record.__syncData();
            const res = await recordSave.call(record, ...args);
            record.save = recordSave;
            return res;
        };

        return newRecord;
    }
    async addNewRecord(list, params) {
        const parentId = this.__bm__.localData[list.__bm_handle__].parentID;
        const fieldName = list.__fieldName__;
        const context = this.__bm__._getContext(this.__bm__.localData[parentId], { fieldName });
        params.context = makeContext([context, params.context]);
        params.__syncParent = () => list.__syncData();
        const newRecord = this.createDataPoint("record", params);
        newRecord.__bm_load_params__.parentID = list.__bm_handle__;
        await newRecord.load();
        return newRecord;
    }
    async updateRecord(list, record, params = { isM2M: false }) {
        let operation;
        const isM2M = params.isM2M;
        if (!isM2M) {
            operation = { operation: "UPDATE", id: record.__bm_handle__ };
        } else {
            await record.save({ noReload: true });
            operation = { operation: "TRIGGER_ONCHANGE" };
        }
        await list.__syncParent(operation);
        if (isM2M) {
            await record.load();
        }
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
                "form",
                this.env
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
        const nextRoot = new this.constructor.Record(
            this,
            {
                __bm_load_params__: loadParams,
                mode: this.initialMode,
            },
            state
        );
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
            } else if (payload.service === "notification") {
                return this.notificationService.add(payload.message, {
                    className: payload.className,
                    sticky: payload.sticky,
                    title: payload.title,
                    type: payload.type,
                });
            }
            throw new Error(`call service ${payload.service} not handled in relational model`);
        } else if (evType === "warning") {
            if (payload.type === "dialog") {
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
        } else if (evType === "do_action") {
            // SAME CODE AS legacy_service_provider
            if (payload.action.context) {
                payload.action.context = new Context(payload.action.context).eval();
            }
            const legacyOptions = mapDoActionOptionAPI(payload.options);
            return this.actionService.doAction(payload.action, legacyOptions);
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
            params.viewType,
            this.env
        );
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
        return new this.constructor.Record(this, params, state);
    }
}
RelationalModel.services = ["action", "dialog", "notification"];
RelationalModel.Record = Record;
