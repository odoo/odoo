/** @odoo-module **/

import { Component, useState, useRef, reactive } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _lt } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { useChildRef } from "../utils/hooks";
import { useDropdown } from "../dropdown/dropdown_hook";

export const SCROLL_SETTINGS = {
    defaultCount: 500,
    increaseAmount: 300,
    distanceBeforeReload: 500,
};

export class SelectMenu extends Component {
    setup() {
        this.state = useState({
            options: [],
            displayedOptions: [],
            direction: undefined,
        });

        this.menuRef = useChildRef();
        this.inputRef = useRef("inputRef");
        this.debouncedOnInput = useDebounced(
            () => this.filterOptions(this.inputRef.el ? this.inputRef.el.value.trim() : ""),
            250
        );

        reactive(this.props.options, () => this.debouncedOnInput());

        this.dropdown = useDropdown({
            menuRefName: "dropdownRef",
            togglerRefName: "togglerRef",
            position: "bottom-fit",
            beforeOpen: () => this.filterOptions(),
            onOpened: () => this.onOpened(),
            onPositioned: ({ direction }) => (this.state.direction = direction),
        });
    }

    onOpened() {
        // Using useAutofocus inside the dropdown does not
        // work properly so we set the focus manually.
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }

        if (this.dropdown.menuRef.el) {
            const selectedElement = this.dropdown.menuRef.el.querySelector(".o_select_active");
            if (selectedElement) {
                scrollTo(selectedElement);
            }
        }
    }

    onPositioned({ direction }) {
        this.state.direction = direction;
    }

    isOptionSelected(option) {
        return this.props.value === option.value;
    }

    getItemClass(option) {
        if (this.isOptionSelected(option)) {
            return "o_select_menu_item mb-1 o_select_active bg-primary text-light fw-bolder fst-italic";
        } else {
            return "o_select_menu_item mb-1";
        }
    }

    canClear() {
        return this.props.value != null;
    }

    // ==========================================================================================
    // #                                         Search                                         #
    // ==========================================================================================

    /**
     * Filters the options based on the searchString and
     * slice the result to display a reasonable amount to
     * try to prevent any delay when opening the select.
     *
     * @param {String} searchString
     */
    filterOptions(searchString = "") {
        const groups = [{ options: this.props.options }, ...this.props.groups];

        this.state.options = [];

        for (const group of groups) {
            const filteredOptions = searchString
                ? fuzzyLookup(searchString, group.options, (option) => option.label)
                : group.options;

            if (filteredOptions.length === 0) {
                continue;
            }

            filteredOptions.sort((optionA, optionB) => optionA.label.localeCompare(optionB.label));

            if (group.label) {
                this.state.options.push({ ...group, isGroup: true });
            }
            this.state.options.push(...filteredOptions);
        }

        this.sliceDisplayedOptions();
    }

    /**
     * Sorts the options while keeping the groups separation
     * @param {[]} options
     */
    sortGroups(options) {
        const groupsIndex = this.getGroupsIndex(options);
        for (let i = 0; i < groupsIndex.length; i++) {
            const startIndex = options[groupsIndex[i]].isGroup
                ? groupsIndex[i] + 1
                : groupsIndex[i];
            const lastIndex = i === groupsIndex.length - 1 ? options.length : groupsIndex[i + 1];
            const groupSlice = options.slice(startIndex, lastIndex);
            groupSlice.sort((optionA, optionB) => optionA.label.localeCompare(optionB.label));
            options.splice(startIndex, lastIndex - startIndex, ...groupSlice);
        }
    }

    /**
     * Returns each group starting index.
     * @param {[]} options
     * @returns {[]}
     */
    getGroupsIndex(options) {
        if (options.length === 0) {
            return [];
        }
        return options.flatMap((option, index) => (index === 0 ? 0 : option.isGroup ? index : []));
    }

    // ==========================================================================================
    // #                                         Scroll                                         #
    // ==========================================================================================

    /**
     * If the user scrolls to the end of the dropdown,
     * more options are loaded.
     *
     * @param {*} event
     */
    onScroll(event) {
        const el = event.target;
        const hasReachMax = this.state.displayedOptions.length >= this.state.options.length;
        const remainingDistance = el.scrollHeight - el.scrollTop;
        const distanceToReload = el.clientHeight + SCROLL_SETTINGS.distanceBeforeReload;

        if (!hasReachMax && remainingDistance < distanceToReload) {
            const displayCount =
                this.state.displayedOptions.length + SCROLL_SETTINGS.increaseAmount;

            this.state.displayedOptions = this.state.options.slice(0, displayCount);
        }
    }

    /**
     * Finds the selected option and set [displayOptions] to at
     * least show the selected option and [defaultCount] more
     * or show at least the [defaultDisplayCount].
     */
    sliceDisplayedOptions() {
        const selectedIndex = this.getSelectedOptionIndex();
        const defaultCount = SCROLL_SETTINGS.defaultCount;

        if (selectedIndex === -1) {
            this.state.displayedOptions = this.state.options.slice(0, defaultCount);
        } else {
            const endIndex = Math.max(selectedIndex + SCROLL_SETTINGS.increaseAmount, defaultCount);
            this.state.displayedOptions = this.state.options.slice(0, endIndex);
        }
    }

    getSelectedOptionIndex() {
        let selectedIndex = -1;
        for (let i = 0; i < this.state.options.length; i++) {
            if (this.isOptionSelected(this.state.options[i])) {
                selectedIndex = i;
            }
        }
        return selectedIndex;
    }
}

SelectMenu.template = "web.SelectMenu";
SelectMenu.components = { Dropdown, DropdownItem };
SelectMenu.defaultProps = {
    value: undefined,
    class: "",
    togglerClass: "",
    onSelect: () => {},
    searchPlaceholder: _lt("Search..."),
    options: [],
    groups: [],
};
SelectMenu.props = {
    options: {
        type: Array,
        optional: true,
        element: {
            type: Object,
            shape: {
                value: true,
                label: { type: String },
            },
        },
    },
    groups: {
        type: Array,
        optional: true,
        element: {
            type: Object,
            shape: {
                label: { type: String, optional: true },
                options: {
                    type: Array,
                    element: {
                        type: Object,
                        shape: {
                            value: true,
                            label: { type: String },
                        },
                    },
                },
            },
        },
    },
    class: { type: String, optional: true },
    togglerClass: { type: String, optional: true },
    searchPlaceholder: { type: String, optional: true },
    value: { optional: true },
    onSelect: { type: Function, optional: true },
    slots: { type: Object, optional: true },
};
