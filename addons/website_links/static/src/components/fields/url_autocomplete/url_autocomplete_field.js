import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import { useChildRef } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { CharField, charField } from "@web/views/fields/char/char_field";
import { useInputField } from "@web/views/fields/input_field_hook";

export class UrlAutoCompleteField extends CharField {
    static template = "web.UrlAutoCompleteField";
    static components = {
        ...CharField.components,
        AutoComplete,
    };

    setup() {
        super.setup();
        this.inputRef = useChildRef();
        useInputField({
            getValue: () => this.props.record.data[this.props.name] || "",
            parse: (v) => this.parse(v),
            ref: this.inputRef,
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

    onSelect(value) {
        this.props.record.update({ [this.props.name]: browser.location.origin + value });
    }
}

export const urlAutoComplete = {
    ...charField,
    component: UrlAutoCompleteField,
};

registry.category("fields").add("url_autocomplete", urlAutoComplete);
