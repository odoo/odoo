import { LinkPopover } from "@html_editor/main/link/link_popover";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";
import { useAutofocus, useChildRef } from "@web/core/utils/hooks";
import wUtils from "@website/js/utils";

/**
 * The goal of this patch is to handle the URL autocomplete in the LinkPopover
 * component. The URL autocomplete is used to suggest internal links, anchors.
 * Before, the autocomplete was implemented as another OWL app. Now with this
 * patch, URL autocomplete is implemented as a child component.
 */

/**
 * this class is used to create a new autocomplete component that will be used
 * in the LinkPopover component. Similar with AutoCompleteWithPages but it has
 * two new props:
 * - inputClass: to change the style of the input element in autocomplete
 * - updateValue: to update the URL of the link element
 */
export class AutoCompleteInLinkPopover extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        inputClass: { type: String, optional: true },
        updateValue: { type: Function, optional: true },
    };
    static template = "website.AutoCompleteInLinkPopover";

    // overwrite the div class to avoid breaking the popover style
    get autoCompleteRootClass() {
        return `${super.autoCompleteRootClass} col`;
    }

    // apply classes on the input element in autocomplete
    get inputClass() {
        return this.props.inputClass || "o_input pe-3";
    }

    /**
     * @param option
     * @return {boolean}
     */
    isCategory(option) {
        return !!option?.separator;
    }

    getOption(indices) {
        const [sourceIndex, optionIndex] = indices;
        return this.sources[sourceIndex]?.options[optionIndex];
    }

    /**
     * @override
     */
    onOptionMouseEnter(indices) {
        if (!this.isCategory(this.getOption(indices))) {
            return super.onOptionMouseEnter(...arguments);
        }
    }

    /**
     * @override
     */
    onOptionMouseLeave(indices) {
        if (!this.isCategory(this.getOption(indices))) {
            return super.onOptionMouseLeave(...arguments);
        }
    }

    isActiveSourceOption(indices) {
        if (!this.isCategory(this.getOption(indices))) {
            return super.isActiveSourceOption(...arguments);
        } else {
            return false;
        }
    }

    /**
     * @override
     */
    selectOption(option) {
        if (!this.isCategory(option)) {
            const { value } = Object.getPrototypeOf(option);
            this.targetDropdown.value = value;
            return super.selectOption(...arguments);
        }
    }

    /**
     * @override
     */
    onInput() {
        super.onInput();
        this.props.updateValue(this.targetDropdown.value);
    }
}

patch(LinkPopover, {
    components: { ...LinkPopover.components, AutoCompleteInLinkPopover },
    template: "website.linkPopover",
});

/* patch the LinkPopover component to maintain the option source for the
 * AutoCompleteInLinkPopover component. Also we make sure state.url is updated
 * when the user enters text in the autocomplete and selects an option from the
 * autocomplete.
 */
patch(LinkPopover.prototype, {
    setup() {
        super.setup();
        this.urlRef = useChildRef();
        useAutofocus({
            refName: this.state.isImage || this.state.label !== "" ? this.urlRef.name : "label",
            mobile: true,
        });
    },

    get sources() {
        return [this.optionsSource];
    },

    get optionsSource() {
        return {
            placeholder: _t("Loading..."),
            options: this.loadOptionsSource.bind(this),
            optionTemplate: "website.AutoCompleteItem",
        };
    },

    mapItemToSuggestion(item) {
        return {
            ...item,
            classList: item.separator ? "ui-autocomplete-category" : "ui-autocomplete-item",
        };
    },

    async loadOptionsSource(term) {
        if (term[0] === "#") {
            const anchors = await wUtils.loadAnchors(term, this.props.linkEl.ownerDocument.body);
            return anchors.map((anchor) =>
                this.mapItemToSuggestion({ label: anchor, value: anchor })
            );
        } else if (term.startsWith("http") || term.length === 0) {
            // avoid useless call to /website/get_suggested_links
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
        return choices.map(this.mapItemToSuggestion);
    },

    onSelect(selectedSubjection) {
        const { value } = Object.getPrototypeOf(selectedSubjection);
        this.state.url = value;
    },

    updateValue(val) {
        this.state.url = val;
    },
});
