import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { getFieldDomain } from "@web/model/relational_model/utils";
import { useSpecialData } from "@web/views/fields/relational_utils";
import { hasTouch } from "@web/core/browser/feature_detection";
import { standardFieldProps } from "../standard_field_props";

export class SelectionField extends Component {
    static components = {
        SelectMenu,
    };
    static template = "web.SelectionField";
    static props = {
        ...standardFieldProps,
        placeholder: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        domain: { type: [Array, Function], optional: true },
        autosave: { type: Boolean, optional: true },
    };
    static defaultProps = {
        autosave: false,
    };

    setup() {
        this.type = this.props.record.fields[this.props.name].type;
        if (this.type === "many2one") {
            this.specialData = useSpecialData((orm, props) => {
                const { relation } = props.record.fields[props.name];
                const domain = getFieldDomain(props.record, props.name, props.domain);
                return orm.call(relation, "name_search", ["", domain]);
            });
        }
    }

    get choices() {
        return this.options.map(([value, label]) => ({ value, label }));
    }
    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }
    get options() {
        switch (this.type) {
            case "many2one":
                return [...this.specialData.data];
            case "selection":
                return this.props.record.fields[this.props.name].selection.filter(
                    (option) => option[0] !== false && option[1] !== ""
                );
            default:
                return [];
        }
    }
    get string() {
        switch (this.type) {
            case "many2one":
                return this.props.record.data[this.props.name]
                    ? this.props.record.data[this.props.name].display_name
                    : "";
            case "selection":
                return this.props.record.data[this.props.name] !== false
                    ? this.options.find((o) => o[0] === this.props.record.data[this.props.name])[1]
                    : "";
            default:
                return "";
        }
    }
    get value() {
        const rawValue = this.props.record.data[this.props.name];
        return this.type === "many2one" && rawValue ? rawValue.id : rawValue;
    }

    stringify(value) {
        return JSON.stringify(value);
    }

    onChange(value) {
        switch (this.type) {
            case "many2one":
                if (value === null) {
                    this.props.record.update(
                        { [this.props.name]: false },
                        { save: this.props.autosave }
                    );
                } else {
                    const option = this.options.find((option) => option[0] === value);
                    this.props.record.update(
                        {
                            [this.props.name]: { id: option[0], display_name: option[1] },
                        },
                        { save: this.props.autosave }
                    );
                }
                break;
            case "selection":
                this.props.record.update(
                    { [this.props.name]: value },
                    { save: this.props.autosave }
                );
                break;
        }
    }
}

export const selectionField = {
    component: SelectionField,
    displayName: _t("Selection"),
    supportedOptions: [
        {
            label: _t("Dynamic Placeholder"),
            name: "placeholder_field",
            type: "field",
            availableTypes: ["char"],
        },
    ],
    supportedTypes: ["many2one", "selection"],
    isEmpty: (record, fieldName) => record.data[fieldName] === false,
    extractProps({ viewType, placeholder }, dynamicInfo) {
        const props = {
            autosave: viewType === "kanban",
            placeholder,
            required: dynamicInfo.required,
            domain: dynamicInfo.domain,
        };
        if (viewType === "kanban") {
            props.readonly = dynamicInfo.readonly;
        }
        return props;
    },
};

registry.category("fields").add("selection", selectionField);
