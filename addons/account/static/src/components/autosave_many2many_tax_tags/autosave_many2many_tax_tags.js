import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import {
    Many2ManyTaxTagsField,
    many2ManyTaxTagsField
} from "@account/components/many2x_tax_tags/many2x_tax_tags";

export class AutosaveMany2ManyTaxTagsField extends Many2ManyTaxTagsField {
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
                || line.account_id.id !== this.lastAccount.id
                || line.partner_id.id !== this.lastPartner.id) {
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

export const autosaveMany2ManyTaxTagsField = {
    ...many2ManyTaxTagsField,
    component: AutosaveMany2ManyTaxTagsField,
};

registry.category("fields").add("autosave_many2many_tax_tags", autosaveMany2ManyTaxTagsField);
