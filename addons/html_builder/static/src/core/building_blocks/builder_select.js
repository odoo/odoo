import { Component, onMounted, useRef, useSubEnv, xml, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { Dropdown } from "@web/core/dropdown/dropdown";
import {
    basicContainerBuilderComponentProps,
    useVisibilityObserver,
    useApplyVisibility,
    useSelectableComponent,
} from "../utils";
import { BuilderComponent } from "./builder_component";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { setElementContent } from "@web/core/utils/html";
import { useDebounced, useThrottleForAnimation } from "@web/core/utils/timing";
import { fuzzyTest } from "@web/core/utils/search";

export class WithIgnoreItem extends Component {
    static template = xml`<t t-slot="default"/>`;
    static props = {
        slots: { type: Object },
    };
    setup() {
        useSubEnv({
            ignoreBuilderItem: true,
        });
    }
}

export class BuilderSelect extends Component {
    static template = "html_builder.BuilderSelect";
    static props = {
        ...basicContainerBuilderComponentProps,
        className: { type: String, optional: true },
        dropdownContainerClass: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: {
            type: Object,
            shape: {
                default: Object, // Content is not optional
                fixedButton: { type: Object, optional: true },
            },
        },
        dropdownClass: { type: String, optional: true },
        searchable: { type: Boolean, optional: true },
    };
    static defaultProps = { dropdownClass: "o-hb-select-dropdown" };
    static components = {
        Dropdown,
        BuilderComponent,
        WithIgnoreItem,
    };

    setup() {
        this.state = useState({
            searchString: "",
        });
        this.inputRef = useRef("inputRef");

        useVisibilityObserver("content", useApplyVisibility("root"));

        this.dropdown = useDropdownState();

        const buttonRef = useRef("button");
        let currentLabel;
        const updateCurrentLabel = () => {
            if (!this.props.slots.fixedButton) {
                const newHtml = currentLabel || _t("None");
                if (buttonRef.el && buttonRef.el.innerHTML !== newHtml) {
                    setElementContent(buttonRef.el, newHtml);
                }
            }
        };
        useSelectableComponent(this.props.id, {
            onItemChange(item) {
                currentLabel = item.getLabel();
                updateCurrentLabel();
            },
        });
        this.debouncedOnSearchInput = useDebounced((ev) => {
            const searchString = ev.target.value;
            this.state.searchString = searchString || "";
        }, 200);
        // Ensure the dropdown content is re-rendered / repositioned correctly
        // when applying a search filter.
        this.throttledDropdownUpdate = useThrottleForAnimation(() => {
            this.inputRef.el?.focus();
            this.inputRef.el?.ownerDocument.dispatchEvent(new Event("scroll"));
        });
        onMounted(updateCurrentLabel);
        useSubEnv({
            onSelectItem: () => {
                this.dropdown.close();
            },
            searchFilterItem: this.searchFilterItem.bind(this),
            throttledDropdownUpdate: this.throttledDropdownUpdate.bind(this),
        });
    }
    /**
     * Determines whether a dropdown item should be visible based on the current
     * search string.
     *
     * @param {String} itemLabel The dropdown option label.
     */
    searchFilterItem(itemLabel) {
        return !this.state.searchString || fuzzyTest(this.state.searchString.trim(), itemLabel);
    }
    /**
     * Adapts the search input when the dropdown is opened / closed.
     *
     * @param {Boolean} open
     */
    onStateChanged(open) {
        if (this.props.searchable) {
            return open ? this.inputRef.el.focus() : (this.state.searchString = "");
        }
    }
}
