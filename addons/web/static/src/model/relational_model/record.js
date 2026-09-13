// @ts-check
/** @odoo-module native */

import { markRaw, toRaw } from "@odoo/owl";
import { makeLogger } from "@web/core/debug/debug_logger";
import { ModelEvent } from "@web/core/events";
import { isX2Many } from "@web/core/field_types";
import { deepEqual, omit } from "@web/core/utils/collections/objects";
import { Operation } from "@web/core/utils/operation";

import { DataPoint } from "./datapoint.js";

const log = makeLogger("web.model.record");
import { getBasicEvalContext, getFieldContext } from "./field_context.js";
import { sameFieldValue, sameMany2OneValue } from "./field_values.js";
import { RecordEditState } from "./record_edit_state.js";
import {
    archive,
    deleteRecord,
    duplicateRecord,
    unarchive,
} from "./record_lifecycle.js";
import {
    preprocessHtmlChanges,
    preprocessMany2oneChanges,
    preprocessMany2OneReferenceChanges,
    preprocessPropertiesChanges,
    preprocessReferenceChanges,
    preprocessRelatedPropertyChanges,
    preprocessX2manyChanges,
} from "./record_preprocessors.js";
import { processProperties as processRecordProperties } from "./record_properties.js";
import { save } from "./record_save.js";
import { RecordSaveCoordinator } from "./record_save_coordinator.js";
import { addSavePoint, discard } from "./record_savepoint.js";
import {
    computeChangeset,
    computeRevalidationScope,
    isFieldInvisible as isActiveFieldInvisible,
    isFieldReadonly as isActiveFieldReadonly,
    isFieldRequired as isActiveFieldRequired,
} from "./record_utils.js";
import {
    checkValidity,
    displayInvalidFieldNotification as notifyInvalidFields,
    removeInvalidFields,
    resetFieldValidity,
    setInvalidField,
} from "./record_validator.js";
import {
    computeDataContext,
    formatServerValue,
    getDefaultValues as defaultValuesOf,
    getTextValues,
    parseServerValues as parseRecordServerValues,
} from "./record_value_transforms.js";

/**
 * @template {keyof any} K
 * @template T
 * @typedef {{ [P in K]: T }} RecordType
 */

/**
 * @typedef {{
 * currentValues?: RecordType<string, unknown>;
 * orderBys?: RecordType<string, unknown>;
 * withInvisible?: boolean;
 * withReadonly?: boolean;
 * keepChanges?: boolean;
 * }} FieldSpecifications
 * @typedef {"edit" | "readonly"} Mode
 */

const NO_UNDO = () => {};

const MULTI_EDIT_RESULT = Symbol("multiEditResult");

/**
 * @param {any} dispatched
 * @returns {{ dispatched: boolean, result: any }}
 */
function openMultiEditEnvelope(dispatched) {
    if (dispatched && MULTI_EDIT_RESULT in dispatched) {
        return { dispatched: true, result: dispatched[MULTI_EDIT_RESULT] };
    }
    return { dispatched: false, result: undefined };
}

export class RelationalRecord extends DataPoint {
    static type = "Record";

    /**
     * @type {typeof DataPoint.prototype.setup<{
     * manuallyAdded?: boolean;
     * onUpdate?: (params?: { withoutParentUpdate?: boolean }) => any;
     * parentRecord?: RelationalRecord;
     * virtualId?: string;
     * }>}
     */
    setup(_config, data, options = {}) {
        this.manuallyAdded = options.manuallyAdded === true;
        this._onUpdate = options.onUpdate || (() => {});
        this._parentRecord = options.parentRecord;
        this.canSaveOnUpdate = !options.parentRecord;
        this.virtualId = options.virtualId || false;
        this._isEvalContextReady = false;
        this._noUpdateParent = false;

        this._editState = new RecordEditState();

        this.selected = false;
        /** @type {RecordSaveCoordinator} */
        this.saveState = markRaw(new RecordSaveCoordinator());

        const parentRecord = this._parentRecord;
        if (parentRecord) {
            this.evalContext = {
                get parent() {
                    return parentRecord.evalContext;
                },
            };
            this.evalContextWithVirtualIds = {
                get parent() {
                    return parentRecord.evalContextWithVirtualIds;
                },
            };
        } else {
            this.evalContext = {};
            this.evalContextWithVirtualIds = {};
        }
        /** @type {Set<string>} */
        this.loadedFieldNames = markRaw(new Set(Object.keys(data)));
        /** @type {Record<string, unknown>} */
        this._x2manyPayloads = markRaw({});
        const missingFields = this.fieldNames.filter(
            (fieldName) => !(fieldName in data),
        );
        data = { ...this.getDefaultValues(missingFields), ...data };
        this.setData(data);
    }

    /**
     * @param {Record<string, any>} data
     * @param {FieldSpecifications} [params]
     */
    setData(data, { orderBys, keepChanges } = {}) {
        this._isEvalContextReady = false;
        const inPlace = Boolean(this.data && this.resId && !keepChanges);
        if (this.data) {
            for (const fieldName of Object.keys(data)) {
                this.loadedFieldNames.add(fieldName);
            }
        }
        if (this.resId) {
            const currentValues = inPlace ? this._unchangedX2Manys(data) : undefined;
            this._values = markRaw(
                this.parseServerValues(data, { orderBys, currentValues }),
            );
            this._rememberX2ManyPayloads(data);
            Object.assign(this._textValues, this._getTextValues(data));
        } else {
            const allVals = { ...this.getDefaultValues(), ...data };
            this._values = markRaw(this.parseServerValues(allVals, { orderBys }));
            Object.assign(this._textValues, this._getTextValues(allVals));
        }
        for (const fieldName of Object.keys(this._textValues)) {
            if (!(fieldName in this._values)) {
                delete this._textValues[fieldName];
            }
        }
        if (!keepChanges) {
            this._clearChanges();
        } else {
            this.dirty = this.dirty || this._hasChanges;
        }
        if (inPlace) {
            this._reconcileData({ ...this._values, ...this.changes });
        } else {
            this.data = { ...this._values, ...this.changes };
        }
        this._initialTextValues = markRaw({ ...this._textValues });
        if (keepChanges) {
            Object.assign(this._textValues, this._getTextValues(this.changes));
        }
        this.setEvalContext();

        if (!keepChanges) {
            this.clearValidity();
            this._savePoint = undefined;
        }
        if (!this.isNew && this.isInEdition && !this._parentRecord) {
            this.checkValidityLocked();
        }
    }

    get canBeAbandoned() {
        return this.isNew && !this.dirty && this.manuallyAdded;
    }

    get hasData() {
        return true;
    }

    /** @type {boolean} */
    get isActive() {
        if ("active" in this.activeFields) {
            return this.data.active;
        } else if ("x_active" in this.activeFields) {
            return this.data.x_active;
        }
        return true;
    }

    get isInEdition() {
        if (this.config.mode === "readonly") {
            return false;
        } else {
            return this.config.mode === "edit" || !this.resId;
        }
    }

    get isNew() {
        return !this.resId;
    }

    get isValid() {
        return !this.invalidFields.size;
    }

    get resId() {
        return this.config.resId;
    }

    get resIds() {
        return this.config.resIds;
    }

    /** @returns {boolean} */
    get skipsParentUpdate() {
        return this._noUpdateParent;
    }

    archive(/** @type {any} */ reload) {
        return this.model.mutex.exec(() => archive(this, reload));
    }

    /** @param {{ displayNotification?: boolean }} [options] */
    async checkValidity({ displayNotification } = {}) {
        await this.model.urgentSave.awaitUnlessUrgent(this.model.askChanges());
        if (this.model.urgentSave.isActive) {
            return this.checkValidityLocked({ displayNotification });
        }
        return this.model.mutex.exec(() =>
            this.checkValidityLocked({ displayNotification }),
        );
    }

    /**
     * @param {() => void} close
     * @returns {void}
     */
    setInvalidFieldsNotification(close) {
        this._editState.closeInvalidFieldsNotification = close;
    }

    /** @returns {void} */
    closeInvalidFieldsNotification() {
        this._editState.closeInvalidFieldsNotification();
        this._editState.closeInvalidFieldsNotification = () => {};
    }

    /**
     * @param {Record<string, any>} activeFieldsToRestore
     * @returns {void}
     */
    extendActiveFields(activeFieldsToRestore) {
        this._noUpdateParent = true;
        this._activeFieldsToRestore = { ...activeFieldsToRestore };
    }

    /**
     * @param {number} resId
     * @returns {void}
     */
    assignResId(resId) {
        this.model.patchConfig(this.config, { resId, resIds: [resId] });
        this.virtualId = false;
    }

    delete() {
        return this.model.mutex.exec(() => deleteRecord(this));
    }

    async discard() {
        log.logic("discard", () => ({
            resModel: this.resModel,
            resId: this.resId,
            dirty: this.dirty,
        }));
        this.model.closeUrgentSaveNotification();
        await this.model.askChanges();
        return this.model.mutex.exec(() => this.discardLocked());
    }

    duplicate() {
        return this.model.mutex.exec(() => duplicateRecord(this));
    }

    /** @param {FieldSpecifications} [params] */
    async getChanges({ withReadonly } = {}) {
        await this.model.askChanges();
        return this.model.mutex.exec(() =>
            this.getChangesLocked(this.changes, { withReadonly }),
        );
    }

    async isDirty() {
        await this.model.askChanges();
        return this.dirty;
    }

    /** @param {string} fieldName */
    isFieldInvalid(fieldName) {
        return this.invalidFields.has(fieldName);
    }

    load() {
        if (arguments.length) {
            throw new Error("Record.load() does not accept arguments");
        }
        return this.model.mutex.exec(() => this.loadLocked());
    }

    /** @param {Parameters<RelationalRecord["saveLocked"]>[0]} [options] */
    async save(options) {
        await this.model.askChanges();
        return this.model.mutex.exec(() => this.saveLocked(options));
    }

    /** @param {string} fieldName */
    async setInvalidField(fieldName) {
        this._markDirty();
        return this._setInvalidField(fieldName);
    }

    /** @param {string} fieldName */
    async resetFieldValidity(fieldName) {
        return this._resetFieldValidity(fieldName);
    }

    /** @param {Mode} mode */
    switchMode(mode) {
        return this.model.mutex.exec(() => this.switchModeLocked(mode));
    }

    toggleSelection(/** @type {any} */ selected) {
        return this.model.mutex.exec(() => {
            this._toggleSelection(selected);
        });
    }

    unarchive(/** @type {any} */ reload) {
        return this.model.mutex.exec(() => unarchive(this, reload));
    }

    /**
     * @param {Object} changes
     * @param {{ save?: boolean, withoutParentUpdate?: boolean }} [options]
     */
    async update(changes, { save, withoutParentUpdate } = {}) {
        log.logic("update", () => ({
            resModel: this.resModel,
            resId: this.resId,
            fields: Object.keys(changes),
            save: Boolean(save),
            urgent: this.model.urgentSave.isActive,
        }));
        if (this.model.urgentSave.isActive) {
            const envelope = await this.updateLocked(changes, { withoutParentUpdate });
            return openMultiEditEnvelope(envelope).result;
        }
        return this.model.mutex.exec(async () => {
            const envelope = await this.updateLocked(changes, {
                withoutOnchange: save,
                withoutParentUpdate,
            });
            const { dispatched, result } = openMultiEditEnvelope(envelope);
            if (dispatched) {
                return result;
            }
            if (save && this.canSaveOnUpdate) {
                return this.saveLocked();
            }
        });
    }

    urgentSave() {
        if (toRaw(this).saveState.isInFlight) {
            return true;
        }
        return this.model.urgentSave.run(() => this.saveLocked({ reload: false }));
    }

    /** @returns {boolean} */
    get hasPendingChanges() {
        return this._editState.hasPendingChanges;
    }

    /** @returns {boolean} */
    get _hasChanges() {
        return !this._editState.isChangeSetEmpty;
    }

    /** @returns {Record<string, any>} */
    get savedData() {
        return this._values;
    }

    /** @returns {boolean} */
    get dirty() {
        return this._editState.dirty;
    }

    set dirty(value) {
        this._editState.dirty = value;
    }

    /** @returns {Record<string, any>} */
    get changes() {
        return this._editState.changes;
    }

    set changes(initial) {
        this._editState.changes = initial;
    }

    /** @returns {Set<string>} */
    get invalidFields() {
        return this._editState.invalidFields;
    }

    set invalidFields(value) {
        this._editState.invalidFields = value;
    }

    /** @returns {Set<string>} */
    get unsetRequiredFields() {
        return this._editState.unsetRequiredFields;
    }

    /** @returns {Record<string, any>} */
    get _textValues() {
        return this._editState.textValues;
    }

    set _textValues(value) {
        this._editState.textValues = value;
    }

    /** @returns {Record<string, any>} */
    get _initialTextValues() {
        return this._editState.initialTextValues;
    }

    set _initialTextValues(value) {
        this._editState.initialTextValues = value;
    }

    /** @returns {any} */
    get _savePoint() {
        return this._editState.savePoint;
    }

    set _savePoint(value) {
        this._editState.savePoint = value;
    }

    _clearChanges() {
        this._editState.clearChanges();
    }

    /**
     * A reload writes only the fields that read differently, so the
     * components subscribed to the others are left alone.
     *
     * @param {Record<string, any>} next
     */
    _reconcileData(next) {
        const written = [];
        for (const fieldName of Object.keys(this.data)) {
            if (!(fieldName in next)) {
                delete this.data[fieldName];
                written.push(`-${fieldName}`);
            }
        }
        for (const fieldName of Object.keys(next)) {
            const field = this.fields[fieldName];
            if (
                !field ||
                !sameFieldValue(field, this.data[fieldName], next[fieldName])
            ) {
                this.data[fieldName] = next[fieldName];
                written.push(fieldName);
            }
        }
        log.logic("reconcileData", () => ({
            resModel: this.resModel,
            resId: this.resId,
            written,
        }));
    }

    /**
     * The x2many lists a reload may keep: the server sent the rows it sent
     * last time, and nothing local is staged on them.
     *
     * @param {Record<string, any>} data
     * @returns {Record<string, any>}
     */
    _unchangedX2Manys(data) {
        /** @type {Record<string, any>} */
        const kept = {};
        for (const fieldName of Object.keys(data)) {
            if (!isX2Many(this.fields[fieldName]) || !this.activeFields[fieldName]) {
                continue;
            }
            const list = toRaw(this.data[fieldName]);
            if (
                list &&
                !list.hasStagedCommands &&
                !list.records.some((record) => record.hasPendingChanges) &&
                deepEqual(this._x2manyPayloads[fieldName], data[fieldName])
            ) {
                kept[fieldName] = list;
            }
        }
        return kept;
    }

    /** @param {Record<string, any>} data */
    _rememberX2ManyPayloads(data) {
        for (const fieldName of Object.keys(data)) {
            if (isX2Many(this.fields[fieldName])) {
                this._x2manyPayloads[fieldName] = data[fieldName];
            }
        }
    }

    rebuildData() {
        this.data = { ...this._values, ...this.changes };
        this.setEvalContext();
    }

    /** @param {Record<string, any>} [extraValues] */
    commitChanges(extraValues) {
        this._values = markRaw({
            ...this._values,
            ...this.changes,
            ...extraValues,
        });
        this._editState.commit();
        this.rebuildData();
    }

    discardChanges() {
        this._editState.rollback();
        this.rebuildData();
    }

    /** @param {Record<string, any>} values */
    resetValues(values) {
        this._values = markRaw(values);
        this._editState.reset();
        this.rebuildData();
    }

    clearValidity() {
        this._editState.clearValidity();
    }

    _markDirty() {
        this._editState.markDirty();
    }

    _addSavePoint() {
        addSavePoint(this);
    }

    /** @returns {void} */
    snapshotEditState() {
        this._editState.snapshot();
    }

    /** @returns {boolean} */
    restoreEditState() {
        return this._editState.restoreSnapshot();
    }

    /** @param {any} changes */
    applyChanges(changes, serverChanges = {}, { undoable = false } = {}) {
        log.pipeline("applyChanges", () => ({
            resModel: this.resModel,
            resId: this.resId,
            changes: Object.keys(changes),
            serverChanges: Object.keys(serverChanges),
            undoable,
        }));
        let undoChanges = NO_UNDO;
        if (undoable) {
            const initialTextValues = { ...this._textValues };
            const initialChanges = { ...this.changes };
            const initialData = { ...toRaw(this.data) };
            const initialDirty = this.dirty;
            const invalidFields = [...toRaw(this.invalidFields)];
            const unsetRequiredFields = [...toRaw(this.unsetRequiredFields)];
            const listSnapshots = [];
            for (const fieldName of new Set([
                ...Object.keys(changes),
                ...Object.keys(serverChanges),
            ])) {
                const value = toRaw(this.data)[fieldName];
                if (isX2Many(this.fields[fieldName]) && value?._commands) {
                    listSnapshots.push({ list: value, snapshot: value.snapshot() });
                }
            }
            undoChanges = () => {
                for (const fieldName of invalidFields) {
                    this._setInvalidFieldFlag(fieldName);
                }
                for (const fieldName of unsetRequiredFields) {
                    this.unsetRequiredFields.add(fieldName);
                }
                for (const fieldName of Object.keys(toRaw(this.data))) {
                    if (!(fieldName in initialData)) {
                        delete this.data[fieldName];
                    }
                }
                Object.assign(this.data, initialData);
                for (const { list, snapshot } of listSnapshots) {
                    list.restoreSnapshot(snapshot);
                }
                this.changes = markRaw(initialChanges);
                Object.assign(this._textValues, initialTextValues);
                this.dirty = initialDirty;
                this.setEvalContext();
            };
        }

        for (const fieldName of Object.keys(changes)) {
            let change = changes[fieldName];
            if (change instanceof Operation) {
                change = change.compute(this.data[fieldName]);
            }
            this.changes[fieldName] = change;
            this.data[fieldName] = change;
            if (this.fields[fieldName].type === "html") {
                this._textValues[fieldName] =
                    change === false ? false : change.toString();
            } else if (["char", "text"].includes(this.fields[fieldName].type)) {
                this._textValues[fieldName] = change;
            }
        }

        const parsedChanges = this.parseServerValues(serverChanges, {
            currentValues: this.data,
        });
        for (const fieldName of Object.keys(parsedChanges)) {
            this.changes[fieldName] = parsedChanges[fieldName];
            this.data[fieldName] = parsedChanges[fieldName];
        }
        Object.assign(this._textValues, this._getTextValues(serverChanges));

        this.setEvalContext();

        const changedFieldNames = [
            ...Object.keys(changes),
            ...Object.keys(serverChanges),
        ];
        this._removeInvalidFields(...changedFieldNames);
        const scopedFields = computeRevalidationScope(
            changedFieldNames,
            this.activeFields,
        );
        this.checkValidityLocked({ removeInvalidOnly: true, scopedFields });
        return undoChanges;
    }

    applyDefaultValues() {
        const fieldNames = this.fieldNames.filter(
            (fieldName) => !(fieldName in this.data),
        );
        const defaultValues = this.getDefaultValues(fieldNames);
        if (this.isNew) {
            this.applyChanges({}, defaultValues);
        } else {
            this.applyValues(defaultValues);
        }
    }

    applyValues(/** @type {any} */ values) {
        const x2manyMerges = [];
        for (const fieldName of Object.keys(values)) {
            const field = this.fields[fieldName];
            if (isX2Many(field) && this.changes[fieldName]?._commands?.length) {
                x2manyMerges.push(fieldName);
            }
        }
        const newValues = this.parseServerValues(
            x2manyMerges.length ? omit(values, ...x2manyMerges) : values,
        );
        for (const fieldName of x2manyMerges) {
            const list = this.changes[fieldName];
            list.applyServerValues(values[fieldName]);
            newValues[fieldName] = list;
        }
        Object.assign(this._values, newValues);
        for (const fieldName of Object.keys(newValues)) {
            this.loadedFieldNames.add(fieldName);
            if (fieldName in this.changes) {
                if (isX2Many(this.fields[fieldName])) {
                    this.changes[fieldName] = newValues[fieldName];
                }
            }
        }
        Object.assign(this.data, this._values, this.changes);
        const textValues = this._getTextValues(values);
        Object.assign(this._initialTextValues, textValues);
        Object.assign(this._textValues, textValues, this._getTextValues(this.changes));
        this.setEvalContext();
    }

    /** @param {{ silent?: boolean, displayNotification?: boolean, removeInvalidOnly?: boolean, scopedFields?: Set<string> }} [options] */
    checkValidityLocked(options) {
        return checkValidity(this, options);
    }

    /** @returns {{ withVirtualIds: Object, withoutVirtualIds: Object }} */
    _computeDataContext() {
        return computeDataContext(
            toRaw(this.data),
            this.fields,
            this._textValues,
            this.resId,
        );
    }

    /**
     * @param {Array<{id: number, [key: string]: any}>} data
     * @param {string} fieldName
     * @param {FieldSpecifications} [params]
     */
    createStaticListDatapoint(data, fieldName, { orderBys } = {}) {
        const { related, limit, defaultOrderBy } = this.activeFields[fieldName];
        const relatedActiveFields = related?.activeFields || {};
        const config = {
            resModel: this.fields[fieldName].relation,
            activeFields: relatedActiveFields,
            fields: related?.fields || {},
            relationField: this.fields[fieldName].relation_field || false,
            offset: 0,
            resIds: data.map((r) => r.id),
            orderBy: orderBys?.[fieldName] || defaultOrderBy || [],
            limit:
                limit ||
                (Object.keys(relatedActiveFields).length ? Number.MAX_SAFE_INTEGER : 1),
            context: {},
        };
        const options = {
            onUpdate: (
                /** @type {{ withoutOnchange?: boolean }} */ { withoutOnchange } = {},
            ) => this.updateLocked({ [fieldName]: [] }, { withoutOnchange }),
            parent: this,
        };
        return new this.model.Class.StaticList(
            this.model,
            /** @type {any} */ (config),
            /** @type {any} */ (data),
            options,
        );
    }

    discardLocked() {
        discard(this);
        this.model.bus.trigger(ModelEvent.RECORD_DISCARDED, { recordId: this.id });
    }

    displayInvalidFieldNotification() {
        return notifyInvalidFields(this);
    }

    _formatServerValue(/** @type {any} */ fieldType, /** @type {any} */ value) {
        return formatServerValue(fieldType, value);
    }

    /**
     * @param {RecordType<string, unknown>} [changes]
     * @param {FieldSpecifications} [params]
     * @returns {Record<string, any>}
     */
    getChangesLocked(changes = this.changes, { withReadonly } = {}) {
        return computeChangeset({
            changes,
            values: this._values,
            isNew: !this.resId,
            fields: this.fields,
            activeFields: this.activeFields,
            evalContext: this.evalContextWithVirtualIds,
            options: { withReadonly },
            getCommands: (fieldName, value, wr) =>
                /** @type {import("./static_list").StaticList} */ (value).getCommands({
                    withReadonly: wr,
                }),
        });
    }

    getDefaultValues(fieldNames = this.fieldNames) {
        return defaultValuesOf(fieldNames, this.fields);
    }

    /** @param {RecordType<string, unknown>} values */
    _getTextValues(values) {
        return getTextValues(values, this.activeFields, this.fields);
    }

    /** @param {string} fieldName */
    isFieldInvisible(fieldName) {
        return isActiveFieldInvisible(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    /** @param {string} fieldName */
    isFieldReadonly(fieldName) {
        return isActiveFieldReadonly(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    /** @param {string} fieldName */
    isFieldRequired(fieldName) {
        return isActiveFieldRequired(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    async loadLocked(nextConfig = {}) {
        if ("resId" in nextConfig && this.resId) {
            throw new Error("Cannot change resId of a record");
        }
        await this.model.reloadWithConfig(this.config, nextConfig, {
            commit: (values) => {
                if (this.resId) {
                    this.model.updateSimilarRecords(this, values);
                }
                this.setData(values);
            },
        });
    }

    /**
     * @param {Object[]} properties
     * @param {string} fieldName
     * @param {any} parent
     * @param {Object} [currentValues]
     */
    processProperties(properties, fieldName, parent, currentValues) {
        return processRecordProperties(
            this,
            properties,
            fieldName,
            parent,
            currentValues,
        );
    }

    /**
     * @param {RecordType<string, unknown>} serverValues
     * @param {FieldSpecifications} [options]
     */
    parseServerValues(serverValues, options) {
        return parseRecordServerValues(this, serverValues, options);
    }

    /** @param {...string} fieldNames */
    _removeInvalidFields(...fieldNames) {
        return removeInvalidFields(this, ...fieldNames);
    }

    /** @returns {void} */
    restoreActiveFields() {
        this._noUpdateParent = false;
        if (!this._activeFieldsToRestore) {
            return;
        }
        this.model.patchConfig(this.config, {
            activeFields: { ...this._activeFieldsToRestore },
        });
        this._activeFieldsToRestore = undefined;
    }

    /** @param {{ reload?: boolean, onError?: (e: Error, actions: { discard: () => void, retry: () => any }) => any, nextId?: number }} [options] */
    async saveLocked(options) {
        return save(this, options);
    }

    setEvalContext() {
        const evalContext = getBasicEvalContext(this.config);
        const dataContext = this._computeDataContext();
        Object.assign(this.evalContext, evalContext, dataContext.withoutVirtualIds);
        Object.assign(
            this.evalContextWithVirtualIds,
            evalContext,
            dataContext.withVirtualIds,
        );
        this._isEvalContextReady = true;

        if (!this._parentRecord || this._parentRecord._isEvalContextReady) {
            for (const [fieldName, value] of Object.entries(toRaw(this.data))) {
                if (isX2Many(this.fields[fieldName])) {
                    value.updateContext(getFieldContext(this, fieldName));
                }
            }
        }
    }

    /** @param {string} fieldName */
    async _setInvalidField(fieldName) {
        return setInvalidField(this, fieldName);
    }

    /** @param {string} fieldName */
    _setInvalidFieldFlag(fieldName) {
        this.invalidFields.add(fieldName);
    }

    _resetFieldValidity(/** @type {any} */ fieldName) {
        return resetFieldValidity(this, fieldName);
    }

    /** @param {Mode} mode */
    switchModeLocked(mode) {
        log.lifecycle("switchMode", () => ({
            resModel: this.resModel,
            resId: this.resId,
            from: this.config.mode,
            to: mode,
        }));
        this.model.patchConfig(this.config, { mode });
        if (mode === "readonly") {
            this._noUpdateParent = false;
            this.clearValidity();
        }
    }

    _toggleSelection(/** @type {any} */ selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
        if (!this.selected) {
            this.model.root.onRecordDeselected?.();
        }
    }

    /**
     * @param {Record<string, any>} changes
     * @returns {Promise<Record<string, any>>}
     */
    async _getOnchangeValues(changes) {
        const originalChanges = changes;
        for (const fieldName of Object.keys(originalChanges)) {
            if (originalChanges[fieldName] instanceof Operation) {
                if (changes === originalChanges) {
                    changes = { ...originalChanges };
                }
                changes[fieldName] = originalChanges[fieldName].compute(
                    this.data[fieldName],
                );
            }
        }
        const onChangeFields = Object.keys(changes).filter(
            (fieldName) =>
                this.activeFields[fieldName] && this.activeFields[fieldName].onChange,
        );
        if (!onChangeFields.length) {
            return /** @type {Record<string, any>} */ ({});
        }
        log.pipeline("onchange", () => ({
            resModel: this.resModel,
            resId: this.resId,
            fields: onChangeFields,
        }));

        const localChanges = this.getChangesLocked(
            { ...this.changes, ...changes },
            { withReadonly: true },
        );
        if (this.config.relationField) {
            const parentRecord = this._parentRecord;
            localChanges[this.config.relationField] = parentRecord.getChangesLocked(
                parentRecord.changes,
                { withReadonly: true },
            );
            if (!this._parentRecord.isNew) {
                localChanges[this.config.relationField].id = this._parentRecord.resId;
            }
        }
        return this.model.onchange(this.config, {
            changes: localChanges,
            fieldNames: onChangeFields,
            evalContext: toRaw(this.evalContext),
            onError: (e) => {
                // apply-then-undo is a state no-op on purpose: it forces the
                // Field components to re-render from the pre-onchange values
                const undoChanges = this.applyChanges(
                    changes,
                    {},
                    {
                        undoable: true,
                    },
                );
                undoChanges();
                throw e;
            },
        });
    }

    /**
     * @param {Record<string, any>} changes
     * @returns {{ list: any, snapshot: any }[]}
     */
    _snapshotTouchedLists(changes) {
        const listSnapshots = [];
        for (const fieldName of Object.keys(changes)) {
            if (!isX2Many(this.fields[fieldName])) {
                continue;
            }
            const list = toRaw(this.data)[fieldName];
            if (list?._commands) {
                listSnapshots.push({ list, snapshot: list.snapshot() });
            }
        }
        return listSnapshots;
    }

    /**
     * @param {Record<string, any>} changes
     * @returns {Promise<unknown[]>}
     */
    _preprocessChanges(changes) {
        const relatedPropertyNames = Object.keys(changes).filter(
            (name) => this.fields[name]?.relatedPropertyField,
        );
        /** @type {Promise<unknown>[]} */
        const pending = [];
        for (const preprocess of [
            preprocessMany2oneChanges,
            preprocessMany2OneReferenceChanges,
            preprocessReferenceChanges,
            preprocessX2manyChanges,
            preprocessPropertiesChanges,
            preprocessHtmlChanges,
        ]) {
            try {
                // Invoke synchronously: urgent saves depend on the initial
                // property composition even when they skip asynchronous waits.
                pending.push(Promise.resolve(preprocess(this, changes)));
            } catch (error) {
                pending.push(Promise.reject(error));
                break;
            }
        }
        return Promise.all(pending).then(
            (results) => {
                // Keep the initial synchronous composition for urgent saves, but
                // replace incomplete relation values before a normal save/onchange.
                preprocessRelatedPropertyChanges(this, changes, relatedPropertyNames);
                return results;
            },
            async (error) => {
                // Join started work before rollback without adding a promise
                // continuation to successful updates (which changes render timing).
                await Promise.allSettled(pending);
                throw error;
            },
        );
    }

    /**
     * @param {Record<string, any>} changes
     * @returns {void}
     */
    _removeUnchangedMany2ones(changes) {
        for (const fieldName of Object.keys(changes)) {
            if (this.fields[fieldName].type !== "many2one") {
                continue;
            }
            const current = toRaw(this.data[fieldName]);
            const next = changes[fieldName];
            if (current && next && sameMany2OneValue(current, next)) {
                delete changes[fieldName];
            }
        }
    }

    async updateLocked(
        /** @type {any} */ changes,
        /** @type {{ withoutOnchange?: boolean, withoutParentUpdate?: boolean }} */ {
            withoutOnchange,
            withoutParentUpdate,
        } = {},
    ) {
        changes = { ...changes };
        const raw = toRaw(this);
        const wasDirty = raw.dirty;
        this._markDirty();
        const restoreDirty = () => {
            if (!raw._hasChanges && !raw.invalidFields.size) {
                this.dirty = wasDirty;
            }
        };
        const listSnapshots = this._snapshotTouchedLists(changes);
        const rollbackLists = () => {
            for (const { list, snapshot } of listSnapshots) {
                list.restoreSnapshot(snapshot);
            }
        };

        try {
            await this.model.urgentSave.awaitUnlessUrgent(
                this._preprocessChanges(changes),
            );
        } catch (e) {
            rollbackLists();
            restoreDirty();
            throw e;
        }

        if (this.selected && this.model.multiEdit) {
            let result;
            try {
                result = await this.model.multiEditDispatch(this, changes);
            } catch (e) {
                rollbackLists();
                restoreDirty();
                throw e;
            }
            restoreDirty();
            return { [MULTI_EDIT_RESULT]: result };
        }

        let onchangeServerValues = {};
        if (!withoutOnchange) {
            try {
                onchangeServerValues =
                    (await this.model.urgentSave.unlessUrgent(() =>
                        this._getOnchangeValues(changes),
                    )) ?? {};
            } catch (e) {
                rollbackLists();
                restoreDirty();
                throw e;
            }
        }

        this._removeUnchangedMany2ones(changes);

        const undoChanges = this.applyChanges(changes, onchangeServerValues, {
            undoable: true,
        });
        const changedSomething =
            Object.keys(changes).length > 0 ||
            Object.keys(onchangeServerValues).length > 0;
        if (!changedSomething) {
            restoreDirty();
            return;
        }
        try {
            await this._onUpdate({ withoutParentUpdate });
        } catch (e) {
            undoChanges();
            rollbackLists();
            restoreDirty();
            throw e;
        }
        if (this.model.hasOnRecordChangedHook) {
            await this.model.notifyLifecycle(
                "onRecordChanged",
                this,
                this.getChangesLocked(),
            );
        }
    }
}
