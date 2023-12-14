/** @odoo-module **/

import { Component, useState, useRef, onWillUpdateProps, useEffect } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useDebounced } from "@web/core/utils/timing";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { TagsList } from "@web/core/tags_list/tags_list";
import { useAutofocus } from "@web/core/utils/hooks";

export class SelectMenu extends Component {
    static template = "web.SelectMenu";
    static choiceItemTemplate = "web.SelectMenu.ChoiceItem";

    static components = { Dropdown, DropdownItem, TagsList };

    static defaultProps = {
        value: undefined,
        class: "",
        togglerClass: "",
        multiSelect: false,
        onSelect: () => {},
        required: false,
        searchable: true,
        autoSort: true,
        searchPlaceholder: _t("Search..."),
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
        required: { type: Boolean, optional: true },
        searchable: { type: Boolean, optional: true },
        autoSort: { type: Boolean, optional: true },
        searchPlaceholder: { type: String, optional: true },
        value: { optional: true },
        multiSelect: { type: Boolean, optional: true },
        onInput: { type: Function, optional: true },
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
            searchValue: "",
        });
        this.inputRef = useRef("inputRef");
        this.debouncedOnInput = useDebounced(
            () => this.onInput(this.inputRef.el ? this.inputRef.el.value.trim() : ""),
            250
        );
        this.isOpen = false;

        this.selectedChoice = this.getSelectedChoice(this.props);
        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                this.selectedChoice = this.getSelectedChoice(nextProps);
            }
        });
        useEffect(
            () => {
                if (this.isOpen) {
                    const groups = [{ choices: this.props.choices }, ...this.props.groups];
                    this.filterOptions(this.state.searchValue, groups);
                }
            },
            () => [this.props.choices, this.props.groups]
        );
        useAutofocus({ refName: "inputRef" });
    }

    get displayValue() {
        return this.selectedChoice ? this.selectedChoice.label : "";
    }

    get canDeselect() {
        return !this.props.required && this.selectedChoice !== undefined;
    }

    get multiSelectChoices() {
        const choices = [
            ...this.props.choices,
            ...this.props.groups.flatMap((g) => g.choices),
        ].filter((c) => this.props.value.includes(c.value));
        return choices.map((c) => {
            return {
                id: c.value,
                text: c.label,
                onDelete: () => {
                    const values = [...this.props.value];
                    values.splice(values.indexOf(c.value), 1);
                    this.props.onSelect(values);
                },
            };
        });
    }

    onStateChanged({ open }) {
        this.isOpen = open;

        if (!open) {
            this.state.searchValue = "";
            return;
        }

        const selectedElement = document.querySelector(".o_select_active");
        if (selectedElement) {
            scrollTo(selectedElement);
        }
    }

    isOptionSelected(choice) {
        if (this.props.multiSelect) {
            return this.props.value.includes(choice.value);
        }
        return this.props.value === choice.value;
    }

    getItemClass(choice) {
        if (this.isOptionSelected(choice)) {
            return "o_select_menu_item mb-1 o_select_active bg-primary fw-bolder fst-italic";
        } else {
            return "o_select_menu_item mb-1";
        }
    }

    async executeOnInput(searchString) {
        await this.props.onInput(searchString);
    }

    onInput(searchString) {
        this.filterOptions(searchString);
        this.state.searchValue = searchString;

        // Get reference to dropdown container and scroll to the top.
        const inputEl = this.inputRef.el;
        if (inputEl && inputEl.parentNode) {
            inputEl.parentNode.scrollTo(0, 0);
        }
        if (this.props.onInput) {
            this.executeOnInput(searchString);
        }
    }

    onSearchKeydown(ev) {
        if (ev.key === "ArrowDown" || ev.key === "Enter") {
            // Focus the first choice when navigating from the input using the arrow down key
            const target = ev.target.parentElement.querySelector(".o_select_menu_item");
            ev.target.classList.remove("focus");
            target?.classList.add("focus");
            target?.focus();
            ev.preventDefault();
        }
        if (ev.key === "Enter" && this.state.choices.length === 1) {
            // When there is only one displayed option, the enter key selects the value
            ev.target.parentElement.querySelector(".o_select_menu_item").click();
        }
    }

    getSelectedChoice(props) {
        const choices = [...props.choices, ...props.groups.flatMap((g) => g.choices)];
        return choices.find((c) => c.value === props.value);
    }

    onItemSelected(value) {
        if (this.props.multiSelect) {
            const values = [...this.props.value];
            const valueIndex = values.indexOf(value);

            if (valueIndex !== -1) {
                values.splice(valueIndex, 1);
                this.props.onSelect(values);
            } else {
                this.props.onSelect([...this.props.value, value]);
            }
        } else if (!this.selectedChoice || this.selectedChoice.value !== value) {
            this.props.onSelect(value);
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
    filterOptions(searchString = "", groups) {
        const groupsList = groups || [{ choices: this.props.choices }, ...this.props.groups];

        this.state.choices = [];

        for (const group of groupsList) {
            let filteredOptions = [];

            if (searchString) {
                filteredOptions = fuzzyLookup(
                    searchString,
                    group.choices,
                    (choice) => choice.label
                );
            } else {
                filteredOptions = group.choices;
                if (this.props.autoSort) {
                    filteredOptions.sort((optionA, optionB) =>
                        optionA.label.localeCompare(optionB.label)
                    );
                }
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
