import { Component } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";

function toBoolean(value) {
    return value === "true";
}

export class BooleanMultiSelector extends Component {
    static template = "spreadsheet.BooleanMultiSelector";
    static components = {
        TagsList,
        AutoComplete,
    };

    static props = {
        selectedValues: Array,
        update: Function,
        placeholder: { type: String, optional: true },
    };

    onSelect({ value }) {
        this.props.update([...this.props.selectedValues, toBoolean(value)]);
    }

    get placeholder() {
        return this.props.selectedValues.length ? "" : this.props.placeholder;
    }

    get tags() {
        return this.props.selectedValues.map((value) => ({
            id: `${value}`,
            text: value ? _t("True") : _t("False"),
            onDelete: () => {
                this.props.update(this.props.selectedValues.filter((v) => v !== value));
            },
        }));
    }

    get sources() {
        const options = [
            { value: "true", label: _t("True") },
            { value: "false", label: _t("False") },
        ];
        return [
            {
                options: options.filter(
                    (option) => !this.props.selectedValues.includes(toBoolean(option.value))
                ),
            },
        ];
    }
}
