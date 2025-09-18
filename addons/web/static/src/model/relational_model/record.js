// @ts-check

/** @module @web/model/relational_model/record - Field value management, change tracking, dirty state, and save/discard for individual records */

import { markRaw, markup, toRaw } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/services/orm_service";

import { DataPoint } from "./datapoint";
import { FetchRecordError } from "./errors";
import { getBasicEvalContext, getFieldContext } from "./field_context";
import { createPropertyActiveField } from "./field_metadata";
import { getFieldsSpec } from "./field_spec";
import { parseServerValue } from "./field_values";
import { Operation } from "./operation";
import { isFieldInvisible, isFieldReadonly, isFieldRequired } from "./record_utils";
import { findUnsetRequiredFields } from "./record_validator";
import {
    computeDataContext,
    formatServerValue,
    getDefaultValues,
    getTextValues,
} from "./record_value_transforms";

/**
 * @template {keyof any} K
 * @template T
 * @typedef {{ [P in K]: T }} RecordType
 */

/**
 * @typedef {{
 *  currentValues?: RecordType<string, unknown>;
 *  orderBys?: RecordType<string, unknown>;
 *  withInvisible?: boolean;
 *  withReadonly?: boolean;
 *  keepChanges?: boolean;
 * }} FieldSpecifications
 *
 * @typedef {"edit" | "readonly"} Mode
 */

export class RelationalRecord extends DataPoint {
    static type = "Record";

    /**
     * @type {typeof DataPoint.prototype.setup<{
     *  manuallyAdded?: boolean;
     *  onUpdate?: (params?: { withoutParentUpdate?: boolean }) => any;
     *  parentRecord?: RelationalRecord;
     *  virtualId?: string;
     * }>}
     */
    setup(_config, data, options = {}) {
        this._manuallyAdded = options.manuallyAdded === true;
        this._onUpdate = options.onUpdate || (() => {});
        this._parentRecord = options.parentRecord;
        this.canSaveOnUpdate = !options.parentRecord;
        this._virtualId = options.virtualId || false;
        this._isEvalContextReady = false;

        // Be careful that pending changes might not have been notified yet, so the "dirty" flag may
        // be false even though there are changes in a field. Consider calling "isDirty()" instead.
        this.dirty = false;
        this.selected = false;

        /** @type {Set<string>} */
        this._invalidFields = new Set();
        /** @type {Set<string>} */
        this._unsetRequiredFields = markRaw(new Set());
        this._closeInvalidFieldsNotification = () => {};

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
        const missingFields = this.fieldNames.filter(
            (fieldName) => !(fieldName in data),
        );
        data = { ...this._getDefaultValues(missingFields), ...data };
        // In db, char, text and html fields can be not set (NULL) and set to the empty string. In
        // the UI, there's no difference, but in the eval context, it's not the same. The next
        // structure keeps track of the server values we received for those fields (which can thus
        // be false or a string). This allows us to properly build the eval context, and to always
        // expose string values (false fallbacks on the empty string) in this.data.
        this._textValues = markRaw({});
        this._setData(data);
    }

    /**
     * @param {Record<string, any>} data
     * @param {FieldSpecifications} [params]
     */
    _setData(data, { orderBys, keepChanges } = {}) {
        this._isEvalContextReady = false;
        if (this.resId) {
            this._values = this._parseServerValues(data, { orderBys });
            Object.assign(this._textValues, this._getTextValues(data));
        } else {
            const allVals = { ...this._getDefaultValues(), ...data };
            this._values = markRaw(this._parseServerValues(allVals, { orderBys }));
            Object.assign(this._textValues, this._getTextValues(allVals));
        }
        if (!keepChanges) {
            this._changes = markRaw({});
        }
        this.dirty = false;
        this.data = { ...this._values, ...this._changes };
        this._setEvalContext();
        this._initialTextValues = { ...this._textValues };

        this._invalidFields.clear();
        if (!this.isNew && this.isInEdition && !this._parentRecord) {
            this._checkValidity();
        }
        this._savePoint = undefined;
    }

    // -------------------------------------------------------------------------
    // Getter
    // -------------------------------------------------------------------------

    get canBeAbandoned() {
        return this.isNew && !this.dirty && this._manuallyAdded;
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
        return !this._invalidFields.size;
    }

    get resId() {
        return this.config.resId;
    }

    get resIds() {
        return this.config.resIds;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    archive() {
        return this.model.mutex.exec(() => this._toggleArchive(true));
    }

    /** @param {{ displayNotification?: boolean }} [options] */
    async checkValidity({ displayNotification } = {}) {
        if (!this.model._urgentSave) {
            await this.model._askChanges();
        }
        return this._checkValidity({ displayNotification });
    }

    delete() {
        return this.model.mutex.exec(async () => {
            const unlinked = await this.model.orm.unlink(this.resModel, [this.resId], {
                context: this.context,
            });
            if (!unlinked) {
                return false;
            }
            const resIds = this.resIds.slice();
            const index = resIds.indexOf(/** @type {number} */ (this.resId));
            resIds.splice(index, 1);
            const resId = resIds[Math.min(index, resIds.length - 1)] || false;
            if (resId) {
                await this.model.load({ resId, resIds });
            } else {
                this.model._updateConfig(
                    this.config,
                    { resId: false },
                    { reload: false },
                );
                this.dirty = false;
                this._changes = markRaw({});
                this._values = markRaw(
                    this._parseServerValues(this._getDefaultValues()),
                );
                this._textValues = markRaw({});
                this.data = { ...this._values };
                this._setEvalContext();
            }
        });
    }

    async discard() {
        if (this.model._closeUrgentSaveNotification) {
            this.model._closeUrgentSaveNotification();
        }
        await this.model._askChanges();
        return this.model.mutex.exec(() => this._discard());
    }

    duplicate() {
        return this.model.mutex.exec(async () => {
            const kwargs = { context: this.context };
            const index = this.resIds.indexOf(/** @type {number} */ (this.resId));
            const [resId] = await this.model.orm.call(
                this.resModel,
                "copy",
                [[this.resId]],
                kwargs,
            );
            const resIds = this.resIds.slice();
            resIds.splice(index + 1, 0, resId);
            await this.model.load({ resId, resIds, mode: "edit" });
        });
    }

    /**
     * @param {FieldSpecifications} [params]
     */
    async getChanges({ withReadonly } = {}) {
        await this.model._askChanges();
        return this.model.mutex.exec(() =>
            this._getChanges(this._changes, { withReadonly }),
        );
    }

    async isDirty() {
        await this.model._askChanges();
        return this.dirty;
    }

    /**
     * @param {string} fieldName
     */
    isFieldInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    load() {
        if (arguments.length > 0) {
            throw new Error("Record.load() does not accept arguments");
        }
        return this.model.mutex.exec(() => this._load());
    }

    /**
     * @param {Parameters<RelationalRecord["_save"]>[0]} [options]
     */
    async save(options) {
        await this.model._askChanges();
        return this.model.mutex.exec(() => this._save(options));
    }

    /**
     * @param {string} fieldName
     */
    async setInvalidField(fieldName) {
        this.dirty = true;
        return this._setInvalidField(fieldName);
    }

    /**
     * @param {string} fieldName
     */
    async resetFieldValidity(fieldName) {
        this.dirty = true;
        return this._resetFieldValidity(fieldName);
    }

    /**
     * @param {Mode} mode
     */
    switchMode(mode) {
        return this.model.mutex.exec(() => this._switchMode(mode));
    }

    toggleSelection(selected) {
        return this.model.mutex.exec(() => {
            this._toggleSelection(selected);
        });
    }

    unarchive() {
        return this.model.mutex.exec(() => this._toggleArchive(false));
    }

    /** @param {Object} changes @param {{ save?: boolean }} [options] */
    update(changes, { save } = {}) {
        if (this.model._urgentSave) {
            return this._update(changes);
        }
        return this.model.mutex.exec(async () => {
            await this._update(changes, { withoutOnchange: save });
            if (save && this.canSaveOnUpdate) {
                return this._save();
            }
        });
    }

    async urgentSave() {
        this.model._urgentSave = true;
        this.model.bus.trigger("WILL_SAVE_URGENTLY");
        try {
            const succeeded = await this._save({ reload: false });
            return succeeded;
        } finally {
            this.model._urgentSave = false;
        }
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _addSavePoint() {
        this._savePoint = markRaw({
            dirty: this.dirty,
            textValues: { ...this._textValues },
            changes: { ...this._changes },
        });
        for (const fieldName in this._changes) {
            if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                this._changes[fieldName]._addSavePoint();
            }
        }
    }

    _applyChanges(changes, serverChanges = {}) {
        // We need to generate the undo function before applying the changes
        const initialTextValues = { ...this._textValues };
        const initialChanges = { ...this._changes };
        const initialData = { ...toRaw(this.data) };
        const invalidFields = [...toRaw(this._invalidFields)];
        const undoChanges = () => {
            for (const fieldName of invalidFields) {
                this.setInvalidField(fieldName);
            }
            Object.assign(this.data, initialData);
            this._changes = markRaw(initialChanges);
            Object.assign(this._textValues, initialTextValues);
            this._setEvalContext();
        };

        // Apply changes
        for (const fieldName in changes) {
            let change = changes[fieldName];
            if (change instanceof Operation) {
                change = change.compute(this.data[fieldName]);
            }
            this._changes[fieldName] = change;
            this.data[fieldName] = change;
            if (this.fields[fieldName].type === "html") {
                this._textValues[fieldName] =
                    change === false ? false : change.toString();
            } else if (["char", "text"].includes(this.fields[fieldName].type)) {
                this._textValues[fieldName] = change;
            }
        }

        // Apply server changes
        const parsedChanges = this._parseServerValues(serverChanges, {
            currentValues: this.data,
        });
        for (const fieldName in parsedChanges) {
            this._changes[fieldName] = parsedChanges[fieldName];
            this.data[fieldName] = parsedChanges[fieldName];
        }
        Object.assign(this._textValues, this._getTextValues(serverChanges));

        this._setEvalContext();

        // mark changed fields as valid if they were not, and re-evaluate required attributes
        // for all fields, as some of them might still be unset but become valid with those changes
        this._removeInvalidFields(
            ...Object.keys(changes),
            ...Object.keys(serverChanges),
        );
        this._checkValidity({ removeInvalidOnly: true });
        return undoChanges;
    }

    _applyDefaultValues() {
        const fieldNames = this.fieldNames.filter(
            (fieldName) => !(fieldName in this.data),
        );
        const defaultValues = this._getDefaultValues(fieldNames);
        if (this.isNew) {
            this._applyChanges({}, defaultValues);
        } else {
            this._applyValues(defaultValues);
        }
    }

    _applyValues(values) {
        const newValues = this._parseServerValues(values);
        Object.assign(this._values, newValues);
        for (const fieldName in newValues) {
            if (fieldName in this._changes) {
                if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                    this._changes[fieldName] = newValues[fieldName];
                }
            }
        }
        Object.assign(this.data, this._values, this._changes);
        const textValues = this._getTextValues(values);
        Object.assign(this._initialTextValues, textValues);
        Object.assign(this._textValues, textValues, this._getTextValues(this._changes));
        this._setEvalContext();
    }

    /** @param {{ silent?: boolean, displayNotification?: boolean, removeInvalidOnly?: boolean }} [options] */
    _checkValidity({ silent, displayNotification, removeInvalidOnly } = {}) {
        const unsetRequiredFields = findUnsetRequiredFields(
            this.activeFields,
            this.fields,
            this.data,
            {
                isInvisible: (fieldName) => this._isInvisible(fieldName),
                isRequired: (fieldName) => this._isRequired(fieldName),
                isChildListValid: (_fieldName, list) =>
                    list.records.every(
                        (r) =>
                            !r.dirty || r._checkValidity({ silent, removeInvalidOnly }),
                    ),
            },
        );

        if (silent) {
            return !unsetRequiredFields.size;
        }

        if (removeInvalidOnly) {
            for (const fieldName of Array.from(this._unsetRequiredFields)) {
                if (!unsetRequiredFields.has(fieldName)) {
                    this._unsetRequiredFields.delete(fieldName);
                    this._invalidFields.delete(fieldName);
                }
            }
        } else {
            for (const fieldName of Array.from(this._unsetRequiredFields)) {
                this._invalidFields.delete(fieldName);
            }
            this._unsetRequiredFields.clear();
            for (const fieldName of unsetRequiredFields) {
                this._unsetRequiredFields.add(fieldName);
                this._invalidFields.add(fieldName);
            }
        }
        const isValid = !this._invalidFields.size;
        if (!isValid && displayNotification) {
            this._closeInvalidFieldsNotification =
                this._displayInvalidFieldNotification();
        }
        return isValid;
    }

    /**
     * Given a possibily incomplete value for a many2one field (i.e. a object { id, display_name } but
     * with id and/or display_name being undefined), return the complete value as follows:
     *  - if a display_name is given but no id, perform a name_create to get an id
     *  - if an id is given but display_name is undefined, call web_read to get the display_name
     *  - if both id and display_name are given, return the value as is
     *  - in any other cases, return false
     *
     * @param {{ id?: number; display_name?: string }} value
     * @param {string} fieldName
     * @param {string} resModel
     * @returns {Promise<false | { id: number; display_name: string; }>} the completed record { id, display_name } or false
     */
    async _completeMany2OneValue(value, fieldName, resModel) {
        const resId = value.id;
        const displayName = value.display_name;
        if (!resId && !displayName) {
            return false;
        }
        const context = getFieldContext(this, fieldName);
        if (!resId && displayName !== undefined) {
            const pair = await this.model.orm.call(
                resModel,
                "name_create",
                [displayName],
                {
                    context,
                },
            );
            return pair && { id: pair[0], display_name: pair[1] };
        }
        if (resId && displayName === undefined) {
            const fieldSpec = { display_name: {} };
            if (this.activeFields[fieldName].related) {
                Object.assign(
                    fieldSpec,
                    getFieldsSpec(
                        this.activeFields[fieldName].related.activeFields,
                        this.activeFields[fieldName].related.fields,
                        getBasicEvalContext(this.config),
                    ),
                );
            }
            const kwargs = {
                context,
                specification: fieldSpec,
            };
            const records = await this.model.orm.webRead(resModel, [resId], kwargs);
            return records[0];
        }
        return /** @type {{ id: number, display_name: string }} */ (value);
    }

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
    _createStaticListDatapoint(data, fieldName, { orderBys } = {}) {
        const { related, limit, defaultOrderBy } = this.activeFields[fieldName];
        const relatedActiveFields = (related && related.activeFields) || {};
        const config = {
            resModel: this.fields[fieldName].relation,
            activeFields: relatedActiveFields,
            fields: (related && related.fields) || {},
            relationField: this.fields[fieldName].relation_field || false,
            offset: 0,
            resIds: data.map((r) => r.id),
            orderBy: orderBys?.[fieldName] || defaultOrderBy || [],
            limit:
                limit ||
                (Object.keys(relatedActiveFields).length ? Number.MAX_SAFE_INTEGER : 1),
            context: {}, // will be set afterwards, see "_updateContext" in "_setEvalContext"
        };
        const options = {
            onUpdate: (
                /** @type {{ withoutOnchange?: boolean }} */ { withoutOnchange } = {},
            ) => this._update({ [fieldName]: [] }, { withoutOnchange }),
            parent: this,
        };
        return new this.model.Class.StaticList(
            this.model,
            /** @type {any} */ (config),
            /** @type {any} */ (data),
            options,
        );
    }

    _discard() {
        for (const fieldName in this._changes) {
            if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                this._changes[fieldName]._discard();
            }
        }
        if (this._savePoint) {
            this.dirty = this._savePoint.dirty;
            this._changes = markRaw({ ...this._savePoint.changes });
            this._textValues = markRaw({ ...this._savePoint.textValues });
        } else {
            this.dirty = false;
            this._changes = markRaw({});
            this._textValues = markRaw({ ...this._initialTextValues });
        }
        this.data = { ...this._values, ...this._changes };
        this._savePoint = undefined;
        this._setEvalContext();
        this._invalidFields.clear();
        if (!this.isNew) {
            this._checkValidity();
        }
        this._closeInvalidFieldsNotification();
        this._closeInvalidFieldsNotification = () => {};
        this._restoreActiveFields();
    }

    _displayInvalidFieldNotification() {
        return this.model.hooks.onDisplayInvalidFields();
    }

    _formatServerValue(fieldType, value) {
        return formatServerValue(fieldType, value);
    }

    /**
     * @param {RecordType<string, unknown>} [changes]
     * @param {FieldSpecifications} [params]
     * @returns {Record<string, any>}
     */
    _getChanges(changes = this._changes, { withReadonly } = {}) {
        if (!this.resId) {
            // Apply the initial changes when the record is new
            changes = { ...this._values, ...changes };
        }
        /** @type {Record<string, any>} */
        const result = {};
        for (const [fieldName, value] of Object.entries(changes)) {
            const field = this.fields[fieldName];
            if (fieldName === "id") {
                continue;
            }
            if (
                !withReadonly &&
                fieldName in this.activeFields &&
                this._isReadonly(fieldName) &&
                !this.activeFields[fieldName].forceSave
            ) {
                continue;
            }
            if (field.relatedPropertyField) {
                continue;
            }
            if (field.type === "one2many" || field.type === "many2many") {
                const commands = /** @type {import("./static_list").StaticList} */ (
                    value
                )._getCommands({ withReadonly });
                if (!this.isNew && !commands.length && !withReadonly) {
                    continue;
                }
                result[fieldName] = commands;
            } else {
                result[fieldName] = this._formatServerValue(field.type, value);
            }
        }
        return result;
    }

    _getDefaultValues(fieldNames = this.fieldNames) {
        return getDefaultValues(fieldNames, this.fields);
    }

    /**
     * @param {RecordType<string, unknown>} values
     */
    _getTextValues(values) {
        return getTextValues(values, this.activeFields, this.fields);
    }

    /**
     * @param {string} fieldName
     */
    _isInvisible(fieldName) {
        return isFieldInvisible(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    /**
     * @param {string} fieldName
     */
    _isReadonly(fieldName) {
        return isFieldReadonly(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    /**
     * @param {string} fieldName
     */
    _isRequired(fieldName) {
        return isFieldRequired(
            this.activeFields[fieldName],
            this.evalContextWithVirtualIds,
        );
    }

    async _load(nextConfig = {}) {
        if ("resId" in nextConfig && this.resId) {
            throw new Error("Cannot change resId of a record");
        }
        await this.model._updateConfig(this.config, nextConfig, {
            commit: (values) => {
                if (this.resId) {
                    this.model._updateSimilarRecords(this, values);
                }
                this._setData(values);
            },
        });
    }

    /**
     * This function extracts all properties and adds them to fields and activeFields.
     *
     * @param {Object[]} properties the list of properties to be extracted
     * @param {string} fieldName name of the field containing the properties
     * @param {any} parent m2o value {id, display_name} or false
     * @param {Object} currentValues current values of the record
     * @returns An object containing as key `${fieldName}.${property.name}` and as value the value of the property
     */
    _processProperties(properties, fieldName, parent, currentValues = {}) {
        const data = {};

        const hasCurrentValues = Object.keys(currentValues).length > 0;
        for (const property of properties) {
            const propertyFieldName = `${fieldName}.${property.name}`;

            // Add Unknown Property Field and ActiveField
            if (hasCurrentValues || !this.fields[propertyFieldName]) {
                this.fields[propertyFieldName] = {
                    ...property,
                    name: propertyFieldName,
                    relatedPropertyField: {
                        name: fieldName,
                    },
                    propertyName: property.name,
                    relation: property.comodel,
                    sortable: !["many2one", "many2many", "tags"].includes(
                        property.type,
                    ),
                };
            }
            if (hasCurrentValues || !this.activeFields[propertyFieldName]) {
                this.activeFields[propertyFieldName] =
                    createPropertyActiveField(property);
            }

            if (!this.activeFields[propertyFieldName].relatedPropertyField) {
                this.activeFields[propertyFieldName].relatedPropertyField =
                    /** @type {any} */ ({
                        name: fieldName,
                        id: parent?.id,
                        displayName: parent?.display_name,
                    });
            }

            // Extract property data
            if (property.type === "many2many") {
                let staticList = currentValues[propertyFieldName];
                if (!staticList) {
                    staticList = this._createStaticListDatapoint(
                        (property.value || []).map((record) => ({
                            id: record[0],
                            display_name: record[1],
                        })),
                        propertyFieldName,
                    );
                }
                data[propertyFieldName] = staticList;
            } else if (property.type === "many2one") {
                data[propertyFieldName] =
                    property.value && property.value.display_name === null
                        ? {
                              id: property.value.id,
                              display_name: _t("No Access"),
                          }
                        : property.value;
            } else {
                data[propertyFieldName] = property.value ?? false;
            }
        }

        return data;
    }

    /**
     * @param {RecordType<string, unknown>} serverValues
     * @param {FieldSpecifications} [params]
     */
    _parseServerValues(serverValues, { currentValues, orderBys } = {}) {
        const parsedValues = {};
        if (!serverValues) {
            return parsedValues;
        }
        for (const fieldName in serverValues) {
            const value = serverValues[fieldName];
            if (!this.activeFields[fieldName]) {
                continue;
            }
            const field = this.fields[fieldName];
            if (field.type === "one2many" || field.type === "many2many") {
                let staticList =
                    /** @type {import("./static_list").StaticList | undefined} */ (
                        currentValues?.[fieldName]
                    );
                const listValue = /** @type {any[]} */ (value);
                // value can be a list of records or a list of commands (new record)
                const valueIsCommandList =
                    listValue.length > 0 && Array.isArray(listValue[0]);
                if (!staticList) {
                    let data = valueIsCommandList ? [] : listValue;
                    if (data.length > 0 && typeof data[0] === "number") {
                        data = data.map((resId) => ({ id: resId }));
                    }
                    staticList = this._createStaticListDatapoint(
                        /** @type {any} */ (data),
                        fieldName,
                        { orderBys },
                    );
                    if (valueIsCommandList) {
                        staticList._applyInitialCommands(listValue);
                    }
                } else if (valueIsCommandList) {
                    staticList._applyCommands(listValue);
                }
                parsedValues[fieldName] = staticList;
            } else {
                parsedValues[fieldName] = parseServerValue(field, value);
                if (field.type === "properties") {
                    const parent = /** @type {any} */ (
                        serverValues[field.definition_record]
                    );
                    Object.assign(
                        parsedValues,
                        this._processProperties(
                            parsedValues[fieldName],
                            fieldName,
                            parent,
                            currentValues,
                        ),
                    );
                }
            }
        }
        return parsedValues;
    }

    async _preprocessMany2oneChanges(changes) {
        const proms = Object.entries(changes)
            .filter(([fieldName]) => this.fields[fieldName].type === "many2one")
            .map(async ([fieldName, value]) => {
                if (!value) {
                    changes[fieldName] = false;
                } else if (!this.activeFields[fieldName]) {
                    changes[fieldName] = value;
                } else {
                    const relation = this.fields[fieldName].relation;
                    return this._completeMany2OneValue(value, fieldName, relation).then(
                        (v) => {
                            changes[fieldName] = v;
                        },
                    );
                }
            });
        return Promise.all(proms);
    }

    async _preprocessMany2OneReferenceChanges(changes) {
        const proms = Object.entries(changes)
            .filter(
                ([fieldName]) => this.fields[fieldName].type === "many2one_reference",
            )
            .map(async ([fieldName, value]) => {
                if (!value) {
                    changes[fieldName] = false;
                } else if (typeof value === "number") {
                    // Many2OneReferenceInteger field only manipulates the id
                    changes[fieldName] = { resId: value };
                } else {
                    const relation = this.data[this.fields[fieldName].model_field];
                    return this._completeMany2OneValue(
                        { id: value.resId, display_name: value.displayName },
                        fieldName,
                        relation,
                    ).then((v) => {
                        const m2o =
                            /** @type {{ id: number, display_name: string }} */ (v);
                        changes[fieldName] = {
                            resId: m2o.id,
                            displayName: m2o.display_name,
                        };
                    });
                }
            });
        return Promise.all(proms);
    }

    async _preprocessReferenceChanges(changes) {
        const proms = Object.entries(changes)
            .filter(([fieldName]) => this.fields[fieldName].type === "reference")
            .map(async ([fieldName, value]) => {
                if (!value) {
                    changes[fieldName] = false;
                } else {
                    return this._completeMany2OneValue(
                        { id: value.resId, display_name: value.displayName },
                        fieldName,
                        value.resModel,
                    ).then((v) => {
                        const m2o =
                            /** @type {{ id: number, display_name: string }} */ (v);
                        changes[fieldName] = {
                            resId: m2o.id,
                            resModel: value.resModel,
                            displayName: m2o.display_name,
                        };
                    });
                }
            });
        return Promise.all(proms);
    }

    async _preprocessX2manyChanges(changes) {
        for (const [fieldName, value] of Object.entries(changes)) {
            if (
                this.fields[fieldName].type !== "one2many" &&
                this.fields[fieldName].type !== "many2many"
            ) {
                continue;
            }
            const list = this.data[fieldName];
            for (const command of value) {
                switch (command[0]) {
                    case x2ManyCommands.SET:
                        await list._replaceWith(command[2]);
                        break;
                    default:
                        await list._applyCommands([command]);
                }
            }
            changes[fieldName] = list;
        }
    }

    _preprocessPropertiesChanges(changes) {
        for (const [fieldName, value] of Object.entries(changes)) {
            const field = this.fields[fieldName];
            if (field.type === "properties") {
                const parent =
                    changes[field.definition_record] ||
                    this.data[field.definition_record];
                Object.assign(
                    changes,
                    this._processProperties(value, fieldName, parent, this.data),
                );
            } else if (field?.relatedPropertyField) {
                const [propertyFieldName, propertyName] = field.name.split(".");
                const propertiesData = this.data[propertyFieldName] || [];
                if (
                    !propertiesData.find((property) => property.name === propertyName)
                ) {
                    // try to change the value of a properties that has a different parent
                    this.model.hooks.onDisplayPropertyWarning(
                        _t(
                            "This record belongs to a different parent so you can not change this property.",
                        ),
                    );
                    return;
                }
                changes[propertyFieldName] = propertiesData.map((property) =>
                    property.name === propertyName ? { ...property, value } : property,
                );
            }
        }
    }

    _preprocessHtmlChanges(changes) {
        for (const [fieldName, value] of Object.entries(changes)) {
            if (this.fields[fieldName].type === "html") {
                changes[fieldName] = value === false ? false : markup(value);
            }
        }
    }

    /**
     * @param {...string} fieldNames
     */
    _removeInvalidFields(...fieldNames) {
        for (const fieldName of fieldNames) {
            this._invalidFields.delete(fieldName);
        }
    }

    _restoreActiveFields() {
        if (!this._activeFieldsToRestore) {
            return;
        }
        this.model._updateConfig(
            this.config,
            {
                activeFields: { ...this._activeFieldsToRestore },
            },
            { reload: false },
        );
        this._activeFieldsToRestore = undefined;
    }

    /** @param {{ reload?: boolean, onError?: (e: Error, actions: { discard: () => void, retry: () => any }) => any, nextId?: number }} [options] */
    async _save({ reload = true, onError, nextId } = {}) {
        if (this.model._closeUrgentSaveNotification) {
            this.model._closeUrgentSaveNotification();
        }
        const creation = !this.resId;
        if (nextId) {
            if (creation) {
                throw new Error("Cannot set nextId on a new record");
            }
            reload = true;
        }
        // before saving, abandon new invalid, untouched records in x2manys
        for (const fieldName in this.activeFields) {
            const field = this.fields[fieldName];
            if (
                ["one2many", "many2many"].includes(field.type) &&
                !field.relatedPropertyField
            ) {
                this.data[fieldName]._abandonRecords();
            }
        }
        if (!this._checkValidity({ displayNotification: true })) {
            return false;
        }
        const changes = this._getChanges();
        delete changes.id; // id never changes, and should not be written
        if (!creation && !Object.keys(changes).length) {
            if (nextId) {
                return this.model.load({ resId: nextId });
            }
            this._changes = markRaw({});
            this.data = { ...this._values };
            this.dirty = false;
            return true;
        }
        if (
            this.model._urgentSave &&
            this.model.useSendBeaconToSaveUrgently &&
            !this.model.env.inDialog
        ) {
            // We are trying to save urgently because the user is closing the page. To
            // ensure that the save succeeds, we can't do a classic rpc, as these requests
            // can be cancelled (payload too heavy, network too slow, computer too fast...).
            // We instead use sendBeacon, which isn't cancellable. However, it has limited
            // payload (typically < 64k). So we try to save with sendBeacon, and if it
            // doesn't work, we will prevent the page from unloading.
            const route = `/web/dataset/call_kw/${this.resModel}/web_save`;
            const params = {
                model: this.resModel,
                method: "web_save",
                args: [this.resId ? [this.resId] : [], changes],
                kwargs: { context: this.context, specification: {} },
            };
            const data = { jsonrpc: "2.0", method: "call", params };
            const blob = new Blob([JSON.stringify(data)], {
                type: "application/json",
            });
            const succeeded = navigator.sendBeacon(route, blob);
            if (succeeded) {
                this._changes = markRaw({});
                this.dirty = false;
            } else {
                this.model._closeUrgentSaveNotification =
                    this.model.hooks.onDisplayUrgentSave(
                        _t(
                            `Heads up! Your recent changes are too large to save automatically. Please click the %(upload_icon)s button now to ensure your work is saved before you exit this tab.`,
                            {
                                upload_icon: markup`<i class="fa fa-cloud-upload fa-fw"></i>`,
                            },
                        ),
                    );
            }
            return succeeded;
        }
        const canProceed = await this.model.hooks.onWillSaveRecord(this, changes);
        if (canProceed === false) {
            return false;
        }
        // keep x2many orderBy if we stay on the same record
        /** @type {Record<string, any>} */
        const orderBys = {};
        if (!nextId) {
            for (const fieldName of this.fieldNames) {
                if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                    orderBys[fieldName] = this.data[fieldName].orderBy;
                }
            }
        }
        let fieldSpec = {};
        if (reload) {
            fieldSpec = getFieldsSpec(
                this.activeFields,
                this.fields,
                getBasicEvalContext(this.config),
                { orderBys },
            );
        }
        const kwargs = {
            context: this.context,
            specification: fieldSpec,
            next_id: nextId,
        };
        /** @type {Record<string, any>[]} */
        let records;
        try {
            records = await this.model.orm.webSave(
                this.resModel,
                this.resId ? [this.resId] : [],
                changes,
                kwargs,
            );
        } catch (e) {
            if (onError) {
                return onError(e, {
                    discard: () => this._discard(),
                    retry: () => this._save(...arguments),
                });
            }
            if (!this.isInEdition) {
                await this._load({});
            }
            throw e;
        }
        if (reload && !records.length) {
            throw new FetchRecordError([/** @type {number} */ (nextId || this.resId)]);
        }
        if (creation) {
            const resId = records[0].id;
            const resIds = [...this.resIds, resId];
            this.model._updateConfig(this.config, { resId, resIds }, { reload: false });
        }
        await this.model.hooks.onRecordSaved(this, changes);
        if (reload) {
            if (this.resId) {
                this.model._updateSimilarRecords(this, records[0]);
            }
            if (nextId) {
                this.model._updateConfig(
                    this.config,
                    { resId: nextId },
                    { reload: false },
                );
            }
            if (this.config.isRoot) {
                this.model.hooks.onWillLoadRoot(this.config);
            }
            this._setData(records[0], { orderBys });
        } else {
            this._values = markRaw({ ...this._values, ...this._changes });
            if ("id" in this.activeFields) {
                this._values.id = records[0].id;
            }
            for (const fieldName in this.activeFields) {
                const field = this.fields[fieldName];
                if (
                    ["one2many", "many2many"].includes(field.type) &&
                    !field.relatedPropertyField
                ) {
                    this._changes[fieldName]?._clearCommands();
                }
            }
            this._changes = markRaw({});
            this.data = { ...this._values };
            this.dirty = false;
        }
        return true;
    }

    /**
     * For owl reactivity, it's better to only update the keys inside the evalContext
     * instead of replacing the evalContext itself, because a lot of components are
     * registered to the evalContext (but not necessarily keys inside it), and would
     * be uselessly re-rendered if we replace it by a brand new object.
     */
    _setEvalContext() {
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
                if (["one2many", "many2many"].includes(this.fields[fieldName].type)) {
                    value._updateContext(getFieldContext(this, fieldName));
                }
            }
        }
    }

    /**
     * @param {string} fieldName
     */
    async _setInvalidField(fieldName) {
        const canProceed = this.model.hooks.onWillSetInvalidField(this, fieldName);
        if (canProceed === false) {
            return;
        }
        if (toRaw(this._invalidFields).has(fieldName)) {
            return;
        }
        this._invalidFields.add(fieldName);
        if (
            this.selected &&
            this.model.multiEdit &&
            this.model.root._recordToDiscard !== this
        ) {
            this._displayInvalidFieldNotification();
            await this.discard();
            this.switchMode("readonly");
        }
    }

    _resetFieldValidity(fieldName) {
        this._invalidFields.delete(fieldName);
    }

    /**
     * @param {Mode} mode
     */
    _switchMode(mode) {
        this.model._updateConfig(this.config, { mode }, { reload: false });
        if (mode === "readonly") {
            this._noUpdateParent = false;
            this._invalidFields.clear();
        }
    }

    /**
     * @param {boolean} state archive the records if true, otherwise unarchive them
     */
    async _toggleArchive(state) {
        const method = state ? "action_archive" : "action_unarchive";
        const action = await this.model.orm.call(
            this.resModel,
            method,
            [[this.resId]],
            {
                context: this.context,
            },
        );
        const reload = () => this._load();
        return this.model.hooks.onDisplayArchiveAction(action, reload);
    }

    _toggleSelection(selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
        if (!this.selected && this.model.root.isDomainSelected) {
            this.model.root._selectDomain(false);
        }
    }

    /**
     * @param {Record<string, any>} changes
     * @returns {Promise<Record<string, any>>}
     */
    async _getOnchangeValues(changes) {
        for (const fieldName in changes) {
            if (changes[fieldName] instanceof Operation) {
                changes[fieldName] = changes[fieldName].compute(this.data[fieldName]);
            }
        }
        const onChangeFields = Object.keys(changes).filter(
            (fieldName) =>
                this.activeFields[fieldName] && this.activeFields[fieldName].onChange,
        );
        if (!onChangeFields.length) {
            return /** @type {Record<string, any>} */ ({});
        }

        const localChanges = this._getChanges(
            { ...this._changes, ...changes },
            { withReadonly: true },
        );
        if (this.config.relationField) {
            const parentRecord = this._parentRecord;
            localChanges[this.config.relationField] = parentRecord._getChanges(
                parentRecord._changes,
                { withReadonly: true },
            );
            if (!this._parentRecord.isNew) {
                localChanges[this.config.relationField].id = this._parentRecord.resId;
            }
        }
        return this.model._onchange(this.config, {
            changes: localChanges,
            fieldNames: onChangeFields,
            evalContext: toRaw(this.evalContext),
            onError: (e) => {
                // We apply changes and revert them after to force a render of the Field components
                const undoChanges = this._applyChanges(changes);
                undoChanges();
                throw e;
            },
        });
    }

    async _update(
        changes,
        /** @type {{ withoutOnchange?: boolean, withoutParentUpdate?: boolean }} */ {
            withoutOnchange,
            withoutParentUpdate,
        } = {},
    ) {
        this.dirty = true;
        const prom = Promise.all([
            this._preprocessMany2oneChanges(changes),
            this._preprocessMany2OneReferenceChanges(changes),
            this._preprocessReferenceChanges(changes),
            this._preprocessX2manyChanges(changes),
            this._preprocessPropertiesChanges(changes),
            this._preprocessHtmlChanges(changes),
        ]);
        if (!this.model._urgentSave) {
            await prom;
        }
        if (this.selected && this.model.multiEdit) {
            return this.model.root._multiSave(this, changes);
        }
        let onchangeServerValues = {};
        if (!this.model._urgentSave && !withoutOnchange) {
            onchangeServerValues = await this._getOnchangeValues(changes);
        }
        // changes inside the record set as value for a many2one field must trigger the onchange,
        // but can't be considered as changes on the parent record, so here we detect if many2one
        // fields really changed, and if not, we delete them from changes
        for (const fieldName in changes) {
            if (this.fields[fieldName].type === "many2one") {
                const curVal = toRaw(this.data[fieldName]);
                const nextVal = changes[fieldName];
                if (
                    curVal &&
                    nextVal &&
                    curVal.id === nextVal.id &&
                    curVal.display_name === nextVal.display_name
                ) {
                    delete changes[fieldName];
                }
            }
        }
        const undoChanges = this._applyChanges(changes, onchangeServerValues);
        if (
            Object.keys(changes).length > 0 ||
            Object.keys(onchangeServerValues).length > 0
        ) {
            try {
                await this._onUpdate({ withoutParentUpdate });
            } catch (e) {
                undoChanges();
                throw e;
            }
            await this.model.hooks.onRecordChanged(this, this._getChanges());
        }
    }
}
