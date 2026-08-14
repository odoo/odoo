import { proxy, signal } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

export class UrlAutoCompleteField extends CharField {
    static template = "website_links.UrlAutoCompleteField";
    static components = {
        ...CharField.components,
        AutoComplete,
    };
    input = signal.ref();

    setup() {
        super.setup();
        this.input = signal.ref();
        this.state = proxy({ value: this.props.record.data[this.props.name] || "" });
        useInputField({
            getValue: () => this.state.value,
            parse: (v) => this.parse(v),
            ref: this.input,
        });
    }

    get sources() {
        return [
            {
                optionSlot: "option",
                options: async (term) => {
                    const makeItem = (item) => ({
                        cssClass: "ui-autocomplete-item",
                        label: item.label,
                        onSelect: this.onSelect.bind(this, item.value),
                    });
                    const res = await rpc("/website/get_suggested_links", {
                        needle: term,
                        limit: 15,
                    });
                    const choices = [];
                    for (const page of res.matching_pages) {
                        choices.push(makeItem(page));
                    }
                    for (const other of res.others) {
                        if (other.values.length) {
                            choices.push({
                                cssClass: "ui-autocomplete-category",
                                data: { separator: true },
                                label: other.title,
                            });
                            for (const page of other.values) {
                                choices.push(makeItem(page));
                            }
                        }
                    }
                    return choices;
                },
            },
        ];
    }

    update(value) {
        this.state.value = value;
        this.props.record.update({ [this.props.name]: value });
    }

    onSelect(value) {
        const val = browser.location.origin + value;
        this.update(val);
    }
    // onInput({ inputValue }) {
    //     if (!this.state.value || this.state.value !== inputValue) {
    //         this.update(inputValue);
    //     }
    // }
    onChange({ inputValue, isOptionSelected }) {
        if (isOptionSelected) {
            this.update(inputValue);
        }
    }
}

export const urlAutoComplete = {
    ...charField,
    component: UrlAutoCompleteField,
};

registry.category("fields").add("url_autocomplete", urlAutoComplete);
