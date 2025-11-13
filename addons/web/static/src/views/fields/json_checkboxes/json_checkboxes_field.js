import { _t } from "@web/core/l10n/translation";
import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { debounce } from "@web/core/utils/timing";
import { useRecordObserver } from "@web/model/relational_model/utils";

export class JsonCheckboxes extends Component {
    static template = "account.JsonCheckboxes";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
        stacked: { type: Boolean, optional: true },
    };

    setup() {
        this.checkboxes = useState(this.props.record.data[this.props.name]);
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 100);

        useRecordObserver((record) => {
            Object.assign(this.checkboxes, record.data[this.props.name]);
        });
    }

    commitChanges() {
        this.props.record.update({ [this.props.name]: this.checkboxes });
    }

    onChange(key, checked) {
        this.checkboxes[key].checked = checked;
        this.debouncedCommitChanges();
    }
}

export const jsonCheckboxes = {
    component: JsonCheckboxes,
    supportedOptions: [
        {
            label: _t("Stacked"),
            name: "stacked",
            type: "boolean",
            help: _t(
                "If checked, the checkboxes will be displayed in a column. Otherwise, they will be inlined."
            ),
        },
    ],
    supportedTypes: ["json"],
    extractProps({ options }) {
        const stacked = Boolean(options.stacked);
        return {
            stacked,
        };
    },
};

registry.category("fields").add("json_checkboxes", jsonCheckboxes);
registry.category("fields").add("account_json_checkboxes", jsonCheckboxes); // TODO: remove in saas~19.1
