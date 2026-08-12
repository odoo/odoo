import { Component, signal } from "@odoo/owl";
import { AutoCompleteWithPages } from "@website/components/autocomplete_with_pages/autocomplete_with_pages";

// TODO: we probably don't need it anymore after merging html_builder
// see: https://github.com/odoo/odoo/pull/187091
export class UrlAutoComplete extends Component {
    static props = {
        options: { type: Object },
        // Injected to avoid a circular dependency with "@website/js/utils".
        loadOptionsSource: { type: Function },
        targetDropdown: { type: HTMLElement },
    };
    static template = "website.UrlAutoComplete";
    static components = { AutoCompleteWithPages };

    setup() {
        this.inputRef = signal.ref();
    }

    get dropdownClass() {
        const classList = [];
        for (const key in this.props.options?.classes) {
            classList.push(key, this.props.options.classes[key]);
        }
        return classList.join(" ");
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
                options: (term) => {
                    if (this.props.options.isDestroyed?.()) {
                        return [];
                    }
                    return this.props.loadOptionsSource(
                        term,
                        this.props.options.body,
                        this.onSelect.bind(this)
                    );
                },
            },
        ];
    }

    onSelect(value) {
        this.inputRef().value = value;
        this.props.targetDropdown.value = value;
        this.props.options.urlChosen?.();
    }

    onInput({ inputValue }) {
        this.props.targetDropdown.value = inputValue;
    }
}
