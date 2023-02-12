/** @odoo-module **/

import { Component, useState, useRef } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _lt } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";

export class SelectMenu extends Component {
    static template = "web.SelectMenu";

    static components = { Dropdown, DropdownItem };

    static defaultProps = {
        value: undefined,
        class: "",
        togglerClass: "",
        onSelect: () => {},
        searchPlaceholder: _lt("Search..."),
        choices: [],
        groups: [],
    };

    static props = {
        choices: {
            optional: true,
            type: Array,
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
                    choices: {
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

    static SCROLL_SETTINGS = {
        defaultCount: 500,
        increaseAmount: 300,
        distanceBeforeReload: 500,
    };

    setup() {
        this.state = useState({
            choices: [],
            displayedOptions: [],
        });
        this.inputRef = useRef("inputRef");
        this.inputContainerRef = useRef("inputContainerRef");
        this.debouncedOnInput = useDebounced(
            () => this.onInput(this.inputRef.el ? this.inputRef.el.value.trim() : ""),
            250
        );
    }

    get displayValue() {
        if (this.props.value !== undefined) {
            const choices = [...this.props.choices, ...this.props.groups.flatMap((g) => g.choices)];
            const value = choices.find((c) => c.value === this.props.value);
            return value ? value.label : this.props.value;
        }
    }

    onOpened() {
        // Using useAutofocus inside the dropdown does not
        // work properly so we set the focus manually.
        if (this.inputRef.el) {
            this.inputRef.el.focus();
        }

        const selectedElement = document.querySelector(".o_select_active");
        if (selectedElement) {
            scrollTo(selectedElement);
        }
    }

    isOptionSelected(choice) {
        return this.props.value === choice.value;
    }

    getItemClass(choice) {
        if (this.isOptionSelected(choice)) {
            return "o_select_menu_item mb-1 o_select_active bg-primary text-light fw-bolder fst-italic";
        } else {
            return "o_select_menu_item mb-1";
        }
    }

    canClear() {
        return this.props.value != null;
    }

    onInput(searchString) {
        this.filterOptions(searchString);

        // Get reference to dropdown container and scroll to the top.
        const inputContainer = this.inputContainerRef.el;
        if (inputContainer && inputContainer.parentNode) {
            inputContainer.parentNode.scrollTo(0, 0);
        }
    }

    // ==========================================================================================
    // #                                         Search                                         #
    // ==========================================================================================

    /**
     * Filters the choices based on the searchString and
     * slice the result to display a reasonable amount to
     * try to prevent any delay when opening the select.
     *
     * @param {String} searchString
     */
    filterOptions(searchString = "") {
        const groups = [{ choices: this.props.choices }, ...this.props.groups];

        this.state.choices = [];

        for (const group of groups) {
            let filteredOptions = [];

            if (searchString) {
                filteredOptions = fuzzyLookup(
                    searchString,
                    group.choices,
                    (choice) => choice.label
                );
            } else {
                filteredOptions = group.choices;
                filteredOptions.sort((optionA, optionB) =>
                    optionA.label.localeCompare(optionB.label)
                );
            }

            if (filteredOptions.length === 0) {
                continue;
            }

            if (group.label) {
                this.state.choices.push({ ...group, isGroup: true });
            }
            this.state.choices.push(...filteredOptions);
        }

        this.sliceDisplayedOptions();
    }

    /**
     * Sorts the choices while keeping the groups separation
     * @param {[]} choices
     */
    sortGroups(choices) {
        const groupsIndex = this.getGroupsIndex(choices);
        for (let i = 0; i < groupsIndex.length; i++) {
            const startIndex = choices[groupsIndex[i]].isGroup
                ? groupsIndex[i] + 1
                : groupsIndex[i];
            const lastIndex = i === groupsIndex.length - 1 ? choices.length : groupsIndex[i + 1];
            const groupSlice = choices.slice(startIndex, lastIndex);
            groupSlice.sort((optionA, optionB) => optionA.label.localeCompare(optionB.label));
            choices.splice(startIndex, lastIndex - startIndex, ...groupSlice);
        }
    }

    /**
     * Returns each group starting index.
     * @param {[]} choices
     * @returns {[]}
     */
    getGroupsIndex(choices) {
        if (choices.length === 0) {
            return [];
        }
        return choices.flatMap((choice, index) => (index === 0 ? 0 : choice.isGroup ? index : []));
    }

    // ==========================================================================================
    // #                                         Scroll                                         #
    // ==========================================================================================

    /**
     * If the user scrolls to the end of the dropdown,
     * more choices are loaded.
     *
     * @param {*} event
     */
    onScroll(event) {
        const el = event.target;
        const hasReachMax = this.state.displayedOptions.length >= this.state.choices.length;
        const remainingDistance = el.scrollHeight - el.scrollTop;
        const distanceToReload =
            el.clientHeight + this.constructor.SCROLL_SETTINGS.distanceBeforeReload;

        if (!hasReachMax && remainingDistance < distanceToReload) {
            const displayCount =
                this.state.displayedOptions.length +
                this.constructor.SCROLL_SETTINGS.increaseAmount;

            this.state.displayedOptions = this.state.choices.slice(0, displayCount);
        }
    }

    /**
     * Finds the selected choice and set [displayOptions] to at
     * least show the selected choice and [defaultCount] more
     * or show at least the [defaultDisplayCount].
     */
    sliceDisplayedOptions() {
        const selectedIndex = this.getSelectedOptionIndex();
        const defaultCount = this.constructor.SCROLL_SETTINGS.defaultCount;

        if (selectedIndex === -1) {
            this.state.displayedOptions = this.state.choices.slice(0, defaultCount);
        } else {
            const endIndex = Math.max(
                selectedIndex + this.constructor.SCROLL_SETTINGS.increaseAmount,
                defaultCount
            );
            this.state.displayedOptions = this.state.choices.slice(0, endIndex);
        }
    }

    getSelectedOptionIndex() {
        let selectedIndex = -1;
        for (let i = 0; i < this.state.choices.length; i++) {
            if (this.isOptionSelected(this.state.choices[i])) {
                selectedIndex = i;
            }
        }
        return selectedIndex;
    }
}
