/** @ts-check */

import { Component, useEffect } from "@odoo/owl";
import { useChildRef } from "@web/core/utils/hooks";

import { TagsList } from "@web/core/tags_list/tags_list";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class TextFilterValue extends Component {
    static template = "spreadsheet.TextFilterValue";
    static components = {
        TagsList,
        AutoComplete,
    };
    static props = {
        onValueChanged: Function,
        value: { type: Array, optional: true },
        options: {
            type: Array,
            element: {
                type: Object,
                shape: { value: String, formattedValue: String },
                optional: true,
            },
        },
    };
    static defaultProps = {
        value: [],
    };

    setup() {
        this.inputRef = useChildRef();
        useEffect(
            () => {
                if (this.props.options.length && this.inputRef.el) {
                    // if there are options restricting the possible values,
                    // we prevent the user from typing free-text by setting the maxlength to 0
                    this.inputRef.el.setAttribute("maxlength", 0);
                } else {
                    this.inputRef.el.removeAttribute("maxlength");
                }
            },
            () => [this.props.options.length, this.inputRef.el]
        );
    }

    get tags() {
        return this.props.value.map((value) => ({
            id: value,
            text:
                this.props.options.find((option) => option.value === value)?.formattedValue ??
                value,
            onDelete: () => {
                this.props.onValueChanged(this.props.value.filter((v) => v !== value));
            },
        }));
    }

    get sources() {
        const alreadySelected = new Set(this.props.value);
        return [
            {
                options: this.props.options
                    .filter((option) => !alreadySelected.has(option.value))
                    .map((option) => ({
                        label: option.formattedValue,
                        onSelect: () =>
                            this.props.onValueChanged([...this.props.value, option.value]),
                    })),
            },
        ];
    }

    onInputChange({ inputValue }) {
        const value = inputValue.trim();
        if (value) {
            if (!this.props.value?.includes(value)) {
                this.props.onValueChanged([...this.props.value, value]);
            }
            this.inputRef.el.value = "";
        }
    }
}
