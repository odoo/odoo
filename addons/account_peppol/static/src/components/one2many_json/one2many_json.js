import {Component, useState} from "@odoo/owl";
import { CharField } from "@web/views/fields/char/char_field";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { debounce } from "@web/core/utils/timing";
import { useRecordObserver } from "@web/model/relational_model/utils";


export class One2ManyJson extends Component {
    static template = "account.One2ManyJson";
    static components = { CharField };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        super.setup();
        this.sequence_threshold = 199;
        let items = this.props.record.data[this.props.name] || {}
        this.state = useState({items: items});
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 100);

        useRecordObserver((record) => {
            this.state.items = record.data[this.props.name] || {};
        });

    }

    commitChanges() {
        this.props.record.update({ [this.props.name]: this.state.items });
    }

    onChange(key, value) {
        this.state.items[key]['value'] = value;
        this.debouncedCommitChanges();
    }

}

export const one2ManyJson = {
    component: One2ManyJson,
    supportedTypes: ["json"],
}

registry.category("fields").add("one2many_json", one2ManyJson);
