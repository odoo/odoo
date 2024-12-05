import { LinkPopover } from "@html_editor/main/link/link_popover";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { patch } from "@web/core/utils/patch";
import { useAutofocus, useChildRef } from "@web/core/utils/hooks";
import { loadAnchorsLinkPopover } from "../utils";

export class AutoCompleteInLinkpopover extends AutoComplete {
    static props = {
        ...AutoComplete.props,
        inputClass: { type: String, optional: true },
        updateValue: { type: Function, optional: true },
    };
    static template = "website.AutoCompleteInLinkpopover";

    // overwrite the div class to avoid breaking the popover style
    get autoCompleteRootClass() {
        return `${super.autoCompleteRootClass} col`;
    }
    // apply classes on the input element in autocomplete
    get inputClass() {
        let classList = "o_input pe-3";
        if (this.props.inputClass) {
            classList = this.props.inputClass;
        }
        return classList;
    }
    /**
     *
     * @param indices
     * @return {boolean}
     * @private
     */
    _isCategory(indices) {
        const [sourceIndex, optionIndex] = indices;
        return !!this.sources[sourceIndex]?.options[optionIndex]?.separator;
    }

    /**
     * @override
     */
    onOptionMouseEnter(indices) {
        if (!this._isCategory(indices)) {
            return super.onOptionMouseEnter(...arguments);
        }
    }

    /**
     * @override
     */
    onOptionMouseLeave(indices) {
        if (!this._isCategory(indices)) {
            return super.onOptionMouseLeave(...arguments);
        }
    }
    isActiveSourceOption(indices) {
        if (!this._isCategory(indices)) {
            return super.isActiveSourceOption(...arguments);
        }
    }
    /**
     * @override
     */
    selectOption(indices) {
        if (!this._isCategory(indices)) {
            const [sourceIndex, optionIndex] = indices;
            const { value } = Object.getPrototypeOf(this.sources[sourceIndex].options[optionIndex]);
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
    components: { ...LinkPopover.components, AutoCompleteInLinkpopover },
    template: "website.linkPopover",
});

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
    _mapItemToSuggestion(item) {
        return {
            ...item,
            classList: item.separator ? "ui-autocomplete-category" : "ui-autocomplete-item",
        };
    },
    async loadOptionsSource(term) {
        if (term[0] === "#") {
            const anchors = await loadAnchorsLinkPopover(
                term,
                this.props.linkEl.ownerDocument.body
            );
            return anchors.map((anchor) =>
                this._mapItemToSuggestion({ label: anchor, value: anchor })
            );
        } else if (term.startsWith("http") || term.length === 0) {
            // avoid useless call to /website/get_suggested_links
            return [];
        }
        try {
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
            return choices.map(this._mapItemToSuggestion);
        } catch {
            return [];
        }
    },
    onSelect(selectedSubjection, { input }) {
        this.state.url = input.value;
    },
    updateValue(val) {
        this.state.url = val;
    },
});
