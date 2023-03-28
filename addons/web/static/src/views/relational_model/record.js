/* @odoo-module */

import { markup } from "@odoo/owl";
import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { evalDomain, isNumeric, isX2Many } from "@web/views/utils";
import { DataPoint } from "./datapoint";
import { getOnChangeSpec } from "./utils";

export class Record extends DataPoint {
    setup(params) {
        this._parentRecord = params.parentRecord;
        this._onWillSaveRecord = params.onWillSaveRecord || (() => {});
        this._onRecordSaved = params.onRecordSaved || (() => {});
        this._onChange = params.onChange || (() => {});

        this.resId = params.data.id || false;
        this.resIds = params.resIds || [];
        if (params.mode === "readonly") {
            this.isInEdition = false;
        } else {
            this.isInEdition = params.mode === "edit" || !this.resId;
        }

        if (this.resId) {
            this._values = this._applyServerValues(params.data);
            this._changes = {};
        } else {
            this._values = {};
            this._changes = this._applyServerValues({
                ...this._getDefaultValues(),
                ...params.data,
            });
        }
        this.data = { ...this._values, ...this._changes };
        const parentRecord = this._parentRecord;
        if (parentRecord) {
            this.evalContext = {
                get parent() {
                    return parentRecord.evalContext;
                },
            };
        } else {
            this.evalContext = {};
        }
        this._setEvalContext();

        this.selected = false; // TODO: rename into isSelected?
        this.isDirty = false; // TODO: turn private? askChanges must be called beforehand to ensure the value is correct
        this._invalidFields = new Set();
        this._closeInvalidFieldsNotification = () => {};
        this._urgentSave = false;
    }

    // -------------------------------------------------------------------------
    // Getter
    // -------------------------------------------------------------------------

    get isActive() {
        if ("active" in this.activeFields) {
            return this.data.active;
        } else if ("x_active" in this.activeFields) {
            return this.data.x_active;
        }
        return true;
    }

    get isNew() {
        return !this.resId;
    }

    get isValid() {
        return !this._invalidFields.size;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    async archive() {
        return this.model.mutex.exec(() => this._toggleArchive(true));
    }

    getFieldDomain(fieldName) {
        const { domain } = this.fields[fieldName];
        return domain ? new Domain(domain).toList(this.evalContext) : [];
    }

    isInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    async update(changes) {
        if (this._urgentSave) {
            return this._update(changes);
        }
        return this.model.mutex.exec(() => this._update(changes));
    }

    async delete() {
        return this.model.mutex.exec(async () => {
            const unlinked = await this.model.orm.unlink(this.resModel, [this.resId], {
                context: this.context,
            });
            if (!unlinked) {
                return false;
            }
            const resIds = this.resIds.slice();
            const index = resIds.indexOf(this.resId);
            resIds.splice(index, 1);
            const resId = resIds[Math.min(index, resIds.length - 1)] || false;
            if (resId) {
                await this._load(resId);
            } else {
                this.resId = false;
                this.isDirty = false;
                this._changes = this._applyServerValues(this._getDefaultValues());
                this._values = {};
                this.data = { ...this._changes };
                this._setEvalContext();
            }
            this.resIds = resIds;
        });
    }

    async discard() {
        return this.model.mutex.exec(() => this._discard());
    }

    async duplicate() {
        return this.model.mutex.exec(async () => {
            const kwargs = { context: this.context };
            const index = this.resIds.indexOf(this.resId);
            const resId = await this.model.orm.call(this.resModel, "copy", [this.resId], kwargs);
            await this._load(resId);
            this.isInEdition = true;
            this.resIds.splice(index + 1, 0, this.resId);
        });
    }

    async load(resId = this.resId) {
        return this.model.mutex.exec(() => this._load(resId));
    }

    async save(options) {
        await this._askChanges();
        return this.model.mutex.exec(() => this._save(options));
    }

    async setInvalidField(fieldName) {
        this.isDirty = true;
        this._invalidFields.add(fieldName);
    }

    switchMode(mode) {
        this.isInEdition = mode === "edit";
    }

    toggleSelection(selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
    }

    async unarchive() {
        return this.model.mutex.exec(() => this._toggleArchive(false));
    }

    // FIXME: should this be save({ urgent: true }) ?
    urgentSave() {
        this._urgentSave = true;
        this.model.bus.trigger("WILL_SAVE_URGENTLY");
        this._save({ noReload: true });
        return this.isValid;
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _applyChanges(changes) {
        Object.assign(this._changes, changes);
        Object.assign(this.data, changes);
        this._setEvalContext();
        this._removeInvalidFields(Object.keys(changes));
    }

    _applyServerValues(serverValues, currentValues = {}) {
        const parsedValues = {};
        if (!serverValues) {
            return parsedValues;
        }
        for (const fieldName in serverValues) {
            if (!this.activeFields[fieldName]) {
                continue; // ignore fields not in activeFields
            }
            const value = serverValues[fieldName];
            const field = this.fields[fieldName];
            if (field.type === "one2many" || field.type === "many2many") {
                const related = this.activeFields[fieldName].related;
                let staticList = currentValues[fieldName];
                let valueIsCommandList = true;
                if (!staticList) {
                    // value can be a list of records or a list of commands (new record)
                    valueIsCommandList = value.length > 0 && Array.isArray(value[0]);
                    staticList = new this.model.constructor.StaticList(this.model, {
                        // FIXME: can't do that here, no context... yes, we do, but need to pass rawContext
                        resModel: field.relation,
                        activeFields: (related && related.activeFields) || {},
                        fields: (related && related.fields) || {},
                        data: valueIsCommandList ? [] : value,
                        parent: this,
                        onChange: () => this._changes[fieldName] = staticList, // TODO: execute onchange if any
                    });
                }
                if (valueIsCommandList) {
                    staticList._applyCommands(value);
                }
                parsedValues[fieldName] = staticList;
            } else {
                parsedValues[fieldName] = this._parseServerValue(field, value);
            }
        }
        return parsedValues;
    }

    async _askChanges() {
        const proms = [];
        this.model.bus.trigger("NEED_LOCAL_CHANGES", { proms });
        await Promise.all(proms);
    }

    _checkValidity() {
        for (const fieldName in this.activeFields) {
            const fieldType = this.fields[fieldName].type;
            if (this._isInvisible(fieldName)) {
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
                    if (!this._isX2ManyValid(fieldName)) {
                        this.setInvalidField(fieldName);
                    }
                    break;
                default:
                    if (!this.data[fieldName] && this._isRequired(fieldName)) {
                        this.setInvalidField(fieldName);
                    }
            }
        }
        return !this._invalidFields.size;
    }

    _discard() {
        this.isDirty = false;
        this._changes = {};
        this.data = { ...this._values };
        this._setEvalContext();
        this._invalidFields.clear();
        this._closeInvalidFieldsNotification();
        this._closeInvalidFieldsNotification = () => {};
    }

    _getChanges(changes = this._changes, { withReadonly } = {}) {
        const result = {};
        for (const [fieldName, value] of Object.entries(changes)) {
            const type = this.fields[fieldName].type;
            if (!withReadonly && this._isReadonly(fieldName)) {
                continue;
            }
            if (type === "date") {
                result[fieldName] = value ? serializeDate(value) : false;
            } else if (type === "datetime") {
                result[fieldName] = value ? serializeDateTime(value) : false;
            } else if (type === "char" || type === "text") {
                result[fieldName] = value !== "" ? value : false;
            } else if (type === "many2one") {
                result[fieldName] = value ? value[0] : false;
            } else if (type === "one2many" || type === "many2many") {
                result[fieldName] = value._getCommands();
            } else {
                result[fieldName] = value;
            }
        }
        return result;
    }

    _getDefaultValues() {
        const defaultValues = {};
        for (const fieldName of this.fieldNames) {
            const field = this.fields[fieldName];
            if (isNumeric(field)) {
                defaultValues[fieldName] = 0;
            } else if (isX2Many(field)) {
                defaultValues[fieldName] = [];
            } else {
                defaultValues[fieldName] = false;
            }
        }
        return defaultValues;
    }

    _computeEvalContext() {
        const evalContext = {
            ...this.context,
            active_id: this.resId || false,
            active_ids: this.resId ? [this.resId] : [],
            active_model: this.resModel,
            current_company_id: this.model.company.currentCompany.id,
        };
        for (const fieldName in this.data) {
            const value = this.data[fieldName];
            const field = this.fields[fieldName];
            if (["char", "text"].includes(field.type)) {
                evalContext[fieldName] = value !== "" ? value : false;
            } else if (["one2many", "many2many"].includes(field.type)) {
                evalContext[fieldName] = value.resIds;
            } else if (value && field.type === "date") {
                evalContext[fieldName] = serializeDate(value);
            } else if (value && field.type === "datetime") {
                evalContext[fieldName] = serializeDateTime(value);
            } else if (value && field.type === "many2one") {
                evalContext[fieldName] = value[0];
            } else if (value && field.type === "reference") {
                evalContext[fieldName] = `${value.resModel},${value.resId}`;
            } else {
                evalContext[fieldName] = value;
            }
        }
        evalContext.id = this.resId || false;
        return evalContext;
    }

    _isInvisible(fieldName) {
        const invisible = this.activeFields[fieldName].invisible;
        return invisible ? evalDomain(invisible, this.evalContext) : false;
    }

    _isReadonly(fieldName) {
        const readonly = this.activeFields[fieldName].readonly;
        return readonly ? evalDomain(readonly, this.evalContext) : false;
    }

    _isRequired(fieldName) {
        const required = this.activeFields[fieldName].required;
        return required ? evalDomain(required, this.evalContext) : false;
    }

    _isX2ManyValid(fieldName) {
        return this.data[fieldName].records.every((r) => r._checkValidity());
    }

    async _load(resId) {
        const params = {
            activeFields: this.activeFields,
            fields: this.fields,
            resModel: this.resModel,
            context: this.context,
        };
        let record;
        if (resId) {
            params.resId = resId;
            record = await this.model._loadRecord(params);
            this._values = this._applyServerValues(record);
            this._changes = {};
        } else {
            record = await this.model._loadNewRecord(params);
            this._values = {};
            this._changes = this._applyServerValues({ ...this._getDefaultValues(), ...record });
        }
        this.isDirty = false;
        this.data = { ...this._values, ...this._changes };
        this.resId = resId;
        this._setEvalContext();
        this._invalidFields.clear();
    }

    _removeInvalidFields(fieldNames) {
        for (const fieldName of fieldNames) {
            this._invalidFields.delete(fieldName);
        }
    }

    async _save({ noReload, force, onError } = {}) {
        if (!this.isDirty && !force) {
            return true;
        }
        if (!this._checkValidity()) {
            const items = [...this._invalidFields].map((fieldName) => {
                return `<li>${escape(this.fields[fieldName].string || fieldName)}</li>`;
            }, this);
            this._closeInvalidFieldsNotification = this.model.notification.add(
                markup(`<ul>${items.join("")}</ul>`),
                {
                    title: _t("Invalid fields: "),
                    type: "danger",
                }
            );
            return false;
        }
        const changes = this._getChanges();
        const creation = !this.resId;
        delete changes.id; // id never changes, and should not be written
        if (!creation && !Object.keys(changes).length) {
            return true;
        }
        const canProceed = await this._onWillSaveRecord(this);
        if (canProceed === false) {
            return false;
        }
        const kwargs = { context: this.context };
        let resId = this.resId;
        try {
            if (creation) {
                [resId] = await this.model.orm.create(this.resModel, [changes], kwargs);
            } else {
                await this.model.orm.write(this.resModel, [resId], changes, kwargs);
            }
        } catch (e) {
            if (onError) {
                return onError(e, { discard: () => this._discard() });
            }
            if (!this.isInEdition) {
                await this._load(resId);
            }
            return false;
        }
        if (!noReload) {
            await this._load(resId);
            if (creation) {
                this.resIds.push(resId);
            }
        } else {
            this._values = { ...this._values, ...this._changes };
            this._changes = {};
            this.isDirty = false;
        }
        await this._onRecordSaved(this);
        return true;
    }

    /**
     * For owl reactivity, it's better to only update the keys inside the evalContext
     * instead of replacing the evalContext itself, because a lot of components are
     * registered to the evalContext (but not necessarily keys inside it), and would
     * be uselessly re-rendered if we replace it by a brand new object.
     */
    _setEvalContext() {
        Object.assign(this.evalContext, this._computeEvalContext());
    }

    /**
     * @param {boolean} state archive the records if true, otherwise unarchive them
     */
    async _toggleArchive(state) {
        const method = state ? "action_archive" : "action_unarchive";
        const context = this.context;
        const resId = this.resId;
        const action = await this.model.orm.call(this.resModel, method, [[resId]], { context });
        if (action && Object.keys(action).length) {
            this.model.action.doAction(action, { onClose: () => this._load(resId) });
        } else {
            return this._load(resId);
        }
    }

    async _update(changes) {
        this.isDirty = true;
        const onChangeFields = Object.keys(changes).filter(
            (fieldName) => this.activeFields[fieldName].onChange
        );
        if (onChangeFields.length && !this._urgentSave) {
            let context = this.context;
            if (onChangeFields.length === 1) {
                const fieldContext = this.activeFields[onChangeFields[0]].context;
                context = makeContext([context, fieldContext], this.evalContext);
            }
            const otherChanges = await this.model._onchange({
                resModel: this.resModel,
                resIds: this.resId ? [this.resId] : [],
                changes: this._getChanges({ ...this._changes, ...changes }),
                fieldNames: onChangeFields,
                spec: getOnChangeSpec(this.activeFields),
                context,
            });
            Object.assign(changes, this._applyServerValues(otherChanges, this.data));
        }
        this._applyChanges(changes);
        this._onChange();
        // FIXME: should we remove this from model? Only for standalone case
        this.model.bus.trigger("RELATIONAL_MODEL:RECORD_UPDATED", {
            record: this,
            changes: this._getChanges(),
        });
    }
}
