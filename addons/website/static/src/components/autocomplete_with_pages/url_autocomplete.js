import { Component } from "@odoo/owl";
import { useChildRef, useService } from "@web/core/utils/hooks";
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
        this.urlSource = useService("website_url_source");
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
                optionSlot: "urlOption",
                options: this.urlSource.loadOptionsSource.bind({
                    component: this,
                    targetElement: this.props.options && this.props.options.body,
                    onSelect: this.onSelect,
                }),
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
