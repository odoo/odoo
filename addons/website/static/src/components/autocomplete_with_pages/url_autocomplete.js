/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

export class UrlAutoComplete extends Component {
    static template = "website.UrlAutoComplete";
    static components = { AutoCompleteWithPages };

    setup() {
        super.setup();
        this.rpc = useService("rpc");
    }

    _mapItemToSuggestion(item) {
        return {
            ...item,
            classList: item.separator ? "ui-autocomplete-category" : "ui-autocomplete-item",
        };
    }

    get dropdownClass() {
        const classList = [];
        for (const key in this.props.options?.classes) {
            classList.push(key, this.props.options.classes[key]);
        }
        return classList.join(" ")
    }

    get dropdownOptions() {
        const options = {};
        if (this.props.options?.position) {
            options.position = this.props.options?.position;
        }
        return options;
    }

    get sources() {
        return [
            {
                optionTemplate: "website.AutoCompleteWithPagesItem",
                options: async (term) => {
                    if (term[0] === "#") {
                        const anchors = await this.props.loadAnchors(
                            term,
                            this.props.options && this.props.options.body
                        );
                        return anchors.map((anchor) =>
                            this._mapItemToSuggestion({ label: anchor, value: anchor })
                        );
                    } else if (term.startsWith("http") || term.length === 0) {
                        // avoid useless call to /website/get_suggested_links
                        return [];
                    }
                    if (this.props.options.isDestroyed?.()) {
                        return [];
                    }
                    const res = await this.rpc("/website/get_suggested_links", {
                        needle: term,
                        limit: 15,
                    });
                    let choices = res.matching_pages;
                    res.others.forEach((other) => {
                        if (other.values.length) {
                            choices = choices.concat(
                                [{ separator: other.title, label: other.title }],
                                other.values
                            );
                        }
                    });
                    return choices.map(this._mapItemToSuggestion);
                },
            },
        ];
    }

    onSelect(selectedSubjection, { input }) {
        const { value } = Object.getPrototypeOf(selectedSubjection);
        input.value = value;
        this.props.targetDropdown.value = value;
        this.props.options.urlChosen?.();
    }

    onInput({ inputValue }) {
        this.props.targetDropdown.value = inputValue;
        this.props.options.urlChosen?.();
    }
}

UrlAutoComplete.props = {
    options: { type: Object },
    loadAnchors: { type: Function },
    targetDropdown: { type: HTMLElement },
};
