import { Component, proxy, t, useEffect, useProps } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class JsonCheckboxes extends Component {
    static template = "account.JsonCheckboxes";
    static components = { CheckBox };
    props = useProps({
        ...standardFieldProps,
        stacked: t.boolean().optional(),
    });

    setup() {
        this.checkboxes = proxy(this.props.record.data[this.props.name]);
        this.debouncedCommitChanges = debounce(this.commitChanges.bind(this), 100);

        useEffect(() => {
            Object.assign(this.checkboxes, this.props.record.data[this.props.name]);
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
