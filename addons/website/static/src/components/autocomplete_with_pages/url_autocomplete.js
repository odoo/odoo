import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { useChildRef } from "@web/core/utils/hooks";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

export class UrlAutoComplete extends Component {
    static props = {
        options: { type: Object },
        loadAnchors: { type: Function },
        targetDropdown: { type: HTMLElement },
    };
    static template = "website.UrlAutoComplete";
    static components = { AutoCompleteWithPages };

    setup() {
        this.inputRef = useChildRef();
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
                optionSlot: "option",
                options: async (term) => {
                    if (term[0] === "#") {
                        const anchors = await this.props.loadAnchors(
                            term,
                            this.props.options && this.props.options.body
                        );
                        return anchors.map((anchor) => ({
                            cssClass: "ui-autocomplete-item",
                            label: anchor,
                            onSelect: () => this.onSelect(anchor),
                        }));
                    } else if (term.startsWith("http") || term.length === 0) {
                        // avoid useless call to /website/get_suggested_links
                        return [];
                    }
                    if (this.props.options.isDestroyed?.()) {
                        return [];
                    }
                    const res = await rpc("/website/get_suggested_links", {
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
                    return choices.map((choice) => ({
                        cssClass: choice.separator ? "ui-autocomplete-category" : "ui-autocomplete-item",
                        data: choice,
                        label: choice.label,
                        onSelect: () => this.onSelect(choice.value),
                    }));
                },
            },
        ];
    }

    onSelect(value) {
        this.inputRef.value = value;
        this.props.targetDropdown.value = value;
        this.props.options.urlChosen?.();
    }

    onInput({ inputValue }) {
        this.props.targetDropdown.value = inputValue;
    }
}
