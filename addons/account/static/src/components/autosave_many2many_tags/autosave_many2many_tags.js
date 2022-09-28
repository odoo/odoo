/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

const { onWillUpdateProps } = owl;

export class AutosaveMany2ManyTagsField extends Many2ManyTagsField {
    setup() {
        super.setup();

        onWillUpdateProps((nextProps) => this.willUpdateProps(nextProps));

        this.lastBalance = this.props.record.data.balance;

        const super_update = this.update;
        this.update = (recordlist) => {
            super_update(recordlist);
            this._saveOnUpdate();
        };
    }

    deleteTag(id) {
        super.deleteTag(id);
        this._saveOnUpdate();
    }

    willUpdateProps(nextProps) {
        const currentBalance = this.props.record.data.balance;
        const hasTax = this.props.record.data.tax_ids.records.length > 0;
        if (hasTax && currentBalance !== this.lastBalance) {
            this.lastBalance = currentBalance;
            this._saveOnUpdate();
        }
    }

    async _saveOnUpdate() {
        await this.props.record.model.root.save({ stayInEdition: true });
    }
}

registry.category("fields").add("autosave_many2many_tags", AutosaveMany2ManyTagsField);
