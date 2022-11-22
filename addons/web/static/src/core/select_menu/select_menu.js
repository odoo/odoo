/** @odoo-module **/

import { Component, useState, useRef, reactive } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _lt } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyTest } from "@web/core/utils/search";

export class SelectMenu extends Component {
    setup() {
        this.state = useState({
            options: [],
            displayedOptions: [],
            direction: undefined,
        });

        this.dropdownContentRef = useRef("dropdownContentRef");
        this.inputRef = useRef("inputRef");
        this.debouncedOnInput = useDebounced(
            () => this.filterOptions(this.inputRef.el.value.trim()),
            250
        );

        this.scrollSettings = {
            defaultCount: 500,
            increaseAmount: 300,
            distanceBeforeReload: 500,
        };

        this.searchSettings = {
            sort: true,
            fuzzySearch: false,
        };

        reactive(this.props.options, () => this.debouncedOnInput());
    }

    onOpened() {
        // Using useAutofocus inside the dropdown does not
        // work properly so we set the focus manually.
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }

        const selectedElement = this.dropdownContentRef.el.querySelector(".o_select_active");
        if (selectedElement) {
            scrollTo(selectedElement);
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
        let filteredOptions = this.props.options.map((option) => {
            return typeof option === "string" ? { label: option, value: option } : option;
        });

        if (searchString) {
            filteredOptions = filteredOptions.filter((option) => {
                return this.matchOption(option, searchString);
            });

            filteredOptions = filteredOptions.filter((option, index) => {
                return (
                    !option.isGroup ||
                    (index < filteredOptions.length - 1 && !filteredOptions[index + 1].isGroup)
                );
            });
        }

        if (this.searchSettings.sort) {
            this.sortGroups(filteredOptions);
        }
        this.state.options = filteredOptions;

        this.sliceDisplayedOptions();
    }

    matchOption(option, searchString) {
        if (option.isGroup) {
            return true;
        }

        if (this.searchSettings.fuzzySearch) {
            return fuzzyTest(option.label);
        } else {
            return option.label.toUpperCase().includes(searchString.toUpperCase());
        }
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
        const distanceToReload = el.clientHeight + this.scrollSettings.distanceBeforeReload;

        if (!hasReachMax && remainingDistance < distanceToReload) {
            const displayCount =
                this.state.displayedOptions.length + this.scrollSettings.increaseAmount;

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
        const defaultCount = this.scrollSettings.defaultCount;

        if (selectedIndex === -1) {
            this.state.displayedOptions = this.state.options.slice(0, defaultCount);
        } else {
            const endIndex = Math.max(
                selectedIndex + this.scrollSettings.increaseAmount,
                defaultCount
            );
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
};
SelectMenu.props = {
    options: {
        type: Array,
        element: {
            type: [Object, String],
            // shape: {
            //     value: { type: [String, Number, Object], optional: true },
            //     label: { type: String, optional: true },
            //     isGroup: { type: Boolean, optional: true },
            //     template: { type: String, optional: true },
            // },
        },
    },
    value: { optional: true },
    class: { type: String, optional: true },
    togglerClass: { type: String, optional: true },
    onSelect: { type: Function, optional: true },
    searchPlaceholder: { type: String, optional: true },
    slots: { type: Object, optional: true },
};
