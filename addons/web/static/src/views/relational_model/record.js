/* @odoo-module */

import { markup } from "@odoo/owl";
import { Domain } from "@web/core/domain";
import { serializeDate, serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { evalDomain, isNumeric, isX2Many } from "@web/views/utils";
import { DataPoint } from "./datapoint";

export class Record extends DataPoint {
    setup(params) {
        console.log(params.data);
        this.resId = params.data.id || false;
        this.resIds = params.resIds || (this.resId ? [this.resId] : []);
        // multiple fields: we could loop here on activeFields and generate a
        // StaticList for each (and an entry in data), but we would have more datapoints
        if (this.resId) {
            this._values = this._parseServerValues(params.data);
            this._changes = {};
        } else {
            this._values = {};
            this._changes = this._parseServerValues(
                Object.assign(this._getDefaultValues(), params.data)
            );
        }
        this.data = { ...this._values, ...this._changes };
        this.evalContext = this._computeEvalContext();
        if (params.mode === "readonly") {
            this.isInEdition = false;
        } else {
            this.isInEdition = params.mode === "edit" || !this.resId;
        }
        this.selected = false; // TODO: rename into isSelected?
        this.isDirty = false;
        this._invalidFields = new Set();
    }

    // -------------------------------------------------------------------------
    // Getter
    // -------------------------------------------------------------------------

    get isNew() {
        return !this.resId;
    }

    get isValid() {
        return true;
    }

    // -------------------------------------------------------------------------
    // Public
    // -------------------------------------------------------------------------

    isInvalid(fieldName) {
        return this._invalidFields.has(fieldName);
    }

    // TODO: remove?
    isReadonly(fieldName) {
        return true;
    }

    // TODO: remove?
    isRequired(fieldName) {
        return false;
    }

    // TODO: remove (there's a subtask)
    getFieldContext(fieldName) {
        return {};
    }
    // TODO: remove (there's a subtask)
    getFieldDomain() {
        return new Domain();
    }

    askChanges() {}

    update(changes) {
        this.isDirty = true;
        Object.assign(this._changes, changes);
        Object.assign(this.data, changes);
        this._setEvalContext();
        this._removeInvalidFields(Object.keys(changes));
        // FIXME: should we remove this from model? Only for standalone case
        this.model.bus.trigger("RELATIONAL_MODEL:RECORD_UPDATED", {
            record: this,
            changes: this._getChanges(),
        });
    }

    async delete() {
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
            await this.load(resId);
        } else {
            this.resId = false;
            this.isDirty = false;
            this._changes = this._parseServerValues(this._getDefaultValues());
            this._values = {};
            this.data = { ...this._changes };
            this._setEvalContext();
        }
        this.resIds = resIds;
    }

    discard() {
        this.isDirty = false;
        this._changes = {};
        this.data = { ...this._values };
        this._setEvalContext();
        this._invalidFields.clear();
    }

    async save({ noReload } = {}) {
        // TODO: mutexify
        // TODO: handle errors
        if (!this._checkValidity()) {
            const items = [...this._invalidFields].map((fieldName) => {
                return `<li>${escape(this.fields[fieldName].string || fieldName)}</li>`;
            }, this);
            this.model.notificationService.add(markup(`<ul>${items.join("")}</ul>`), {
                title: _t("Invalid fields: "),
                type: "danger",
            });
            return false;
        }
        const changes = this._getChanges();
        if (!Object.keys(changes).length) {
            return true;
        }
        const kwargs = { context: this.context };
        let resId = this.resId;
        if (!resId) {
            [resId] = await this.model.orm.create(this.resModel, [changes], kwargs);
        } else {
            await this.model.orm.write(this.resModel, [resId], changes, kwargs);
        }
        if (!noReload) {
            await this.load(resId);
        } else {
            this._values = { ...this._values, ...this._changes };
            this._changes = {};
            this.isDirty = false;
        }
        return true;
    }

    async load(resId = this.resId) {
        // TODO: do not duplicate logic with relational_model?
        // TODO: handle concurrency
        // TODO: really not sure about all this
        const params = {
            activeFields: this.activeFields,
            fields: this.fields,
            resModel: this.resModel,
            context: this.context,
        };
        let record;
        if (resId) {
            params.resId = resId;
            record = await this.model.loadRecord(params);
            this._values = this._parseServerValues(record);
            this._changes = {};
        } else {
            record = await this.model.loadNewRecord(params);
            this._values = {};
            this._changes = this._parseServerValues(
                Object.assign(this._getDefaultValues(), record)
            );
        }
        this.isDirty = false;
        this.data = { ...this._values, ...this._changes };
        this.resId = resId;
        this._setEvalContext();
        this._invalidFields.clear();
    }

    async setInvalidField(fieldName) {
        this._invalidFields.add(fieldName);
    }

    toggleSelection(selected) {
        if (typeof selected === "boolean") {
            this.selected = selected;
        } else {
            this.selected = !this.selected;
        }
    }

    // -------------------------------------------------------------------------
    // Protected
    // -------------------------------------------------------------------------

    _checkValidity() {
        for (const fieldName in this.activeFields) {
            const fieldType = this.fields[fieldName].type;
            const activeField = this.activeFields[fieldName];
            if (activeField.alwaysInvisible || !this._isRequired(fieldName)) {
                this._removeInvalidFields([fieldName]);
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
                    if (!this.data[fieldName]) {
                        this.setInvalidField(fieldName);
                    }
            }
        }
        return !this._invalidFields.size;
    }

    _getChanges() {
        const changes = {};
        for (const [fieldName, value] of Object.entries(this._changes)) {
            const type = this.fields[fieldName].type;
            if (type === "date") {
                changes[fieldName] = value ? serializeDate(value) : false;
            } else if (type === "datetime") {
                changes[fieldName] = value ? serializeDateTime(value) : false;
            } else if (type === "many2one") {
                changes[fieldName] = value ? value[0] : false;
            } else {
                changes[fieldName] = value;
            }
        }
        return changes;
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
            if ([null].includes(value)) {
                // simplify that?
                evalContext[fieldName] = false;
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
        // if (this.getParentRecordContext) {
        //     evalContext.parent = this.getParentRecordContext();
        // }
        return evalContext;
    }

    _isRequired(fieldName) {
        const required = this.activeFields[fieldName].required;
        return required ? evalDomain(required, this.evalContext) : false;
    }

    _isX2ManyValid(fieldName) {
        return this.data[fieldName].records.every((r) => r._checkValidity());
    }

    _removeInvalidFields(fieldNames) {
        for (const fieldName of fieldNames) {
            this._invalidFields.delete(fieldName);
        }
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
}
