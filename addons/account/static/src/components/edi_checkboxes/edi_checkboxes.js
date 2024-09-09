import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {debounce} from "@web/core/utils/timing";


export class EdiCheckboxes extends Component {
    static template = "account.EdiCheckboxes";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        super.setup();
        this.checkboxes = useState(this.props.record.data[this.props.name]);
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 100);
    }

    commitChanges() {
        this.props.record.update({ [this.props.name]: this.checkboxes });
    }

    onChange(key, checked) {
        this.checkboxes[key]['checked'] = checked;
        this.debouncedCommitChanges();
    }

}

export const ediCheckboxes = {
    component: EdiCheckboxes,
    supportedTypes: ["jsonb"],
}

registry.category("fields").add("account_edi_checkboxes", ediCheckboxes);
