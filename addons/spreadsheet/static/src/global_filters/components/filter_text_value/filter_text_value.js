/** @ts-check */

import { useLayoutEffect } from "@web/owl2/utils";
import { Component, props, signal, t } from "@odoo/owl";

import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";

export class TextFilterValue extends Component {
    static template = "spreadsheet.TextFilterValue";
    static components = {
        BadgeTag,
        AutoComplete,
    };
    props = props({
        onValueChanged: t.function(),
        value: t.array().optional([]),
        options: t.array(t.object({ value: t.string(), formattedValue: t.string() }).optional()),
        placeholder: t.string().optional(),
    });

    setup() {
        this.inputRef = signal.ref();
        useLayoutEffect(
            () => {
                if (this.props.options.length && this.inputRef()) {
                    // if there are options restricting the possible values,
                    // we prevent the user from typing free-text by setting the maxlength to 0
                    this.inputRef().setAttribute("maxlength", 0);
                } else {
                    this.inputRef().removeAttribute("maxlength");
                }
            },
            () => [this.props.options.length, this.inputRef()]
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

    get placeholder() {
        return this.tags.length ? "" : this.props.placeholder;
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
            this.inputRef().value = "";
        }
    }
}
