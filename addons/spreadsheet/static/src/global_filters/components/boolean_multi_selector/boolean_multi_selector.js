import { Component, useEffect } from "@odoo/owl";
import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { _t } from "@web/core/l10n/translation";
import { useChildRef } from "@web/core/utils/hooks";

function toBoolean(value) {
    return value === "true";
}

const OPTIONS = [
    { value: "true", label: _t("Is set") },
    { value: "false", label: _t("Is not set") },
];

export class BooleanMultiSelector extends Component {
    static template = "spreadsheet.BooleanMultiSelector";
    static components = {
        TagsList,
        AutoComplete,
    };

    static props = {
        selectedValues: Array,
        update: Function,
    };

    setup() {
        this.inputRef = useChildRef();
        useEffect(
            () => {
                // Prevent the user from typing free-text by setting the maxlength to 0
                this.inputRef.el?.setAttribute("maxlength", 0);
            },
            () => [this.inputRef.el]
        );
    }

    get tags() {
        return this.props.selectedValues.map((value) => ({
            id: `${value}`,
            text: OPTIONS.find((option) => option.value === `${value}`).label,
            onDelete: () => {
                this.props.update(this.props.selectedValues.filter((v) => v !== value));
            },
        }));
    }

    get sources() {
        return [
            {
                options: OPTIONS.filter(
                    (option) => !this.props.selectedValues.includes(toBoolean(option.value))
                ).map((option) => ({
                    label: option.label,
                    onSelect: () =>
                        this.props.update([...this.props.selectedValues, toBoolean(option.value)]),
                })),
            },
        ];
    }
}
