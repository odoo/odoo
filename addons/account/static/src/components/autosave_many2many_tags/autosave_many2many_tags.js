/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { Many2ManyTagsField, many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

export class AutosaveMany2ManyTagsField extends Many2ManyTagsField {
    setup() {
        super.setup();

        this.lastBalance = this.props.record.data.balance;
        this.lastAccount = this.props.record.data.account_id;
        this.lastPartner = this.props.record.data.partner_id;

        const super_update = this.update;
        this.update = (recordlist) => {
            super_update(recordlist);
            this._saveOnUpdate();
        };
        useRecordObserver(this.onRecordChange.bind(this));
    }

    async deleteTag(id) {
        await super.deleteTag(id);
        await this._saveOnUpdate();
    }

    onRecordChange(record) {
        const line = record.data;
        if (line.tax_ids.records.length > 0) {
            if (line.balance !== this.lastBalance
                || line.account_id[0] !== this.lastAccount[0]
                || line.partner_id[0] !== this.lastPartner[0]) {
                this.lastBalance = line.balance;
                this.lastAccount = line.account_id;
                this.lastPartner = line.partner_id;
                return record.model.root.save();
            }
        }
    }

    async _saveOnUpdate() {
        await this.props.record.model.root.save();
    }
}

export const autosaveMany2ManyTagsField = {
    ...many2ManyTagsField,
    component: AutosaveMany2ManyTagsField,
};

registry.category("fields").add("autosave_many2many_tags", autosaveMany2ManyTagsField);
