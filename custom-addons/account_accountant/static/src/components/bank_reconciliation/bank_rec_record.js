/** @odoo-module **/

import { Record } from "@web/model/relational_model/record";
import { RelationalModel } from "@web/model/relational_model/relational_model";
import { parseServerValue } from "@web/model/relational_model/utils";
import { getFieldDomain } from "@web/views/fields/field";

export class BankRecRecord extends Record {

    /**
     * override
     * Track the changed field on lines.
     */
    async _update(changes) {
        if(this.resModel === "bank.rec.widget.line"){
            for(const fieldName of Object.keys(changes)){
                this.model.lineIdsChangedField = fieldName;
            }
        }
        return super._update(...arguments);
    }

    async updateToDoCommand(methodName, args, kwargs) {
        this.dirty = true;

        const onChangeFields = ["todo_command"];
        const changes = {
            todo_command: {
                method_name: methodName,
                args: args,
                kwargs: kwargs,
            },
        };

        const localChanges = this._getChanges(
            { ...this._changes, ...changes },
            { withReadonly: true }
        );
        const otherChanges = await this.model._onchange(this.config, {
            changes: localChanges,
            fieldNames: onChangeFields,
            evalContext: this.evalContext,
        });

        const data = { ...this.data, ...changes };
        for (const fieldName in otherChanges) {
            data[fieldName] = parseServerValue(this.fields[fieldName], otherChanges[fieldName]);
        }
        const applyChanges = () => {
            Object.assign(changes, this._parseServerValues(otherChanges, this.data));
            if (Object.keys(changes).length > 0) {
                this._applyChanges(changes);
            }
        };
        return { data, applyChanges };
    }

    /**
     * Bind an action to be called when a field on lines changed.
     * @param {Function} callback: The action to call taking the changed field as parameter.
     */
    bindActionOnLineChanged(callback){
        this._onUpdate = async () => {
            const lineIdsChangedField = this.model.lineIdsChangedField;
            if(lineIdsChangedField){
                this.model.lineIdsChangedField = null;
                await callback(lineIdsChangedField);
            }
        }
    }

    getFieldDomain(fieldName) {
        return getFieldDomain(this, fieldName);
    }

}

export class BankRecRelationalModel extends RelationalModel{
    setup(params, { action, dialog, notification, rpc, user, view, company }) {
        super.setup(...arguments);
        this.lineIdsChangedField = null;
    }

    load({ values }) {
        this.root = this._createRoot(this.config, values);
    }

    getInitialValues() {
        return this.root._getChanges(this.root.data, { withReadonly: true })
    }
}
BankRecRelationalModel.Record = BankRecRecord;
