import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { TagsList } from "@web/core/tags_list/tags_list";
import { mergeClasses } from "@web/core/utils/classname";
import { useChildRef } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { useDebounced } from "@web/core/utils/timing";
import { hasTouch } from "@web/core/browser/feature_detection";

let selectMenuId = 0;

export const DEBOUNCED_DELAY = 250;

export class SelectMenu extends Component {
    static template = "web.SelectMenu";
    static choiceItemTemplate = "web.SelectMenu.ChoiceItem";

    static components = { Dropdown, DropdownItem, TagsList };

    static defaultProps = {
        value: undefined,
        id: "",
        name: "",
        class: "",
        menuClass: "",
        togglerClass: "",
        multiSelect: false,
        onSelect: () => {},
        onNavigated: () => {},
        onOpened: () => {},
        onClosed: () => {},
        required: false,
        searchable: true,
        autoSort: true,
        searchPlaceholder: "",
        choices: [],
        groups: [],
        sections: [],
        disabled: false,
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
                    "*": true,
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
                                "*": true,
                            },
                        },
                    },
                    section: {
                        type: String,
                        optional: true,
                    },
                },
            },
        },
        sections: {
            type: Array,
            optional: true,
            element: {
                label: { type: String },
                name: { type: String },
            },
        },
        id: { type: String, optional: true },
        name: { type: String, optional: true },
        class: { type: String, optional: true },
        menuClass: { type: String, optional: true },
        togglerClass: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        searchable: { type: Boolean, optional: true },
        autoSort: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        searchPlaceholder: { type: String, optional: true },
        searchClass: { type: String, optional: true },
        value: { optional: true },
        multiSelect: { type: Boolean, optional: true },
        onInput: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
        onNavigated: { type: Function, optional: true },
        onOpened: { type: Function, optional: true },
        onClosed: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        disabled: { type: Boolean, optional: true },
        menuRef: { type: Function, optional: true },
    };

    static SCROLL_SETTINGS = {
        defaultCount: 500,
        increaseAmount: 300,
        distanceBeforeReload: 500,
    };

    setup() {
        this.selectMenuId = selectMenuId++;
        this.state = useState({
            choices: [],
            displayedOptions: [],
            searchValue: null,
            isFocused: false,
        });
        this.inputRef = useRef("inputRef");
        this.menuRef = useChildRef();
        this.props.menuRef?.(this.menuRef);
        this.debouncedOnInput = useDebounced((ev) => {
            if (!this.dropdownState.isOpen) {
                this.dropdownState.open();
            }
            const searchString = ev.target.value;
            this.state.searchValue = searchString;
            this.onInput(searchString);
        }, DEBOUNCED_DELAY);
        this.dropdownState = useDropdownState();

        this.selectedChoice = this.getSelectedChoice(this.props);
        onWillUpdateProps((nextProps) => {
            if (this.state.choices !== nextProps.choices) {
                this.state.choices = nextProps.choices;
            }
            if (this.props.value !== nextProps.value) {
                this.selectedChoice = this.getSelectedChoice(nextProps);
            }
        });
        useEffect(
            () => {
                if (this.dropdownState.isOpen) {
                    const groups = [{ choices: this.props.choices }, ...this.props.groups];
                    this.filterOptions(this.state.searchValue, groups);
                }
            },
            () => [this.props.choices, this.props.groups]
        );

        this.navigationOptions = {
            shouldFocusFirstItem: !hasTouch(),
            virtualFocus: this.props.searchable,
            hotkeys: {
                enter: {
                    isAvailable: ({ navigator }) => navigator.items.length > 0,
                    callback: (navigator) => {
                        if (navigator.activeItem) {
                            return navigator.activeItem.select();
                        }
                        if (document.activeElement.value) {
                            navigator.items[0].select();
                        }
                    },
                },
            },
            onItemActivated: (element) => {
                const index = parseInt(element.dataset.choiceIndex);
                if (index >= 0 && this.state.displayedOptions[index]) {
                    this.props.onNavigated(this.state.displayedOptions[index]);
                } else {
                    this.props.onNavigated();
                }
            },
        };
    }

    get displayValue() {
        return this.state.searchValue === null
            ? this.selectedChoice?.label || ""
            : this.state.searchValue;
    }

    get displayInputInToggler() {
        return !this.props.slots || !this.props.slots.default;
    }

    get displayInputInDropdown() {
        return (this.isBottomSheet || !this.displayInputInToggler) && this.props.searchable;
    }

    get isBottomSheet() {
        return this.env.isSmall && hasTouch();
    }

    get canDeselect() {
        return !this.props.required && this.selectedChoice !== undefined;
    }

    get multiSelectChoices() {
        return this.selectedChoice.map((c) => ({
            id: c.value,
            text: c.label,
            onDelete: () => {
                const values = [...this.props.value];
                values.splice(values.indexOf(c.value), 1);
                this.props.onSelect(values);
            },
        }));
    }

    get menuClass() {
        return mergeClasses(
            {
                "my-0": this.displayInputInToggler,
                o_select_menu_menu: true,
                o_select_menu_multi_select: this.props.multiSelect,
            },
            this.props.menuClass
        );
    }

    get placeholderValue() {
        if (this.state.isFocused && this.props.searchPlaceholder) {
            return this.props.searchPlaceholder;
        }
        return this.props.placeholder;
    }

    async onBeforeOpen() {
        this.onInput("");
    }

    onInputFocus(ev) {
        if (!this.props.searchable) {
            return ev.target.blur();
        }
        if (ev.target.classList.contains("o_select_menu_input")) {
            this.state.isFocused = true;
            ev.target.select();
        }
    }

    onInputBlur(ev) {
        this.state.isFocused = false;
        if (ev.target.value === "" && this.canDeselect && !this.props.multiSelect) {
            this.onInputClear();
        }
    }

    onInputClick(ev) {
        if (!ev.target.classList.contains("o_select_menu_toggler")) {
            ev.stopPropagation();
        }
    }

    onInputClear() {
        this.props.onSelect(null);
        this.dropdownState.close();
    }

    onStateChanged(open) {
        if (open) {
            if (this.isBottomSheet) {
                // the toggler input must not be focused
                document.activeElement.blur();
            }
            if (this.displayInputInDropdown && !this.isBottomSheet) {
                this.inputRef.el.focus();
            }
            this.menuRef.el?.addEventListener("scroll", (ev) => this.onScroll(ev));
            const selectedElement = this.menuRef.el?.querySelectorAll(".active")[0];
            if (selectedElement) {
                scrollTo(selectedElement);
            }
            this.props.onOpened();
        } else {
            this.state.searchValue = null;
            this.props.onClosed();
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
            return "o_select_menu_item fw-bolder active";
        } else {
            return "o_select_menu_item";
        }
    }

    async onInput(searchString) {
        this.filterOptions(searchString);
        if (this.props.onInput) {
            await this.props.onInput(searchString);
        }
    }

    getSelectedChoice(props) {
        const choices = [...props.choices, ...props.groups.flatMap((g) => g.choices || [])];
        if (!this.props.multiSelect) {
            return choices.find((c) => c.value === props.value);
        }

        const valueSet = new Set(props.value);
        // Combine previously selected choices + newly selected choice from
        // the searched choices and then filter the choices based on
        // props.value i.e. valueSet.
        return [...(this.selectedChoice || []), ...choices].filter(
            (c, index, self) =>
                valueSet.has(c.value) && self.findIndex((t) => t.value === c.value) === index
        );
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
        this.state.searchValue = null;
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
        const groupsList = groups || [
            { choices: this.props.choices, section: "" },
            ...this.props.groups,
        ];

        const _choices = [];
        const _sections = new Set();
        groupsList.sort((a, b) => (a.section || "").localeCompare(b.section || ""));

        for (const group of groupsList) {
            let filteredOptions = group.choices || [];

            if (searchString) {
                filteredOptions = fuzzyLookup(
                    searchString.trim(),
                    filteredOptions,
                    (choice) => choice.label
                );
            } else {
                if (this.props.autoSort) {
                    filteredOptions.sort((optionA, optionB) =>
                        optionA.label.localeCompare(optionB.label)
                    );
                }
            }

            if (filteredOptions.length === 0) {
                continue;
            }
            if (group.section) {
                const section = this.props.sections.find((e) => e.name === group.section);
                if (!_sections.has(section)) {
                    _sections.add(section);
                    _choices.push({ ...section, isGroup: true });
                }
            }
            if (group.label) {
                _choices.push({ ...group, isGroup: true });
            }
            _choices.push(...filteredOptions);
        }

        this.state.choices = _choices;
        this.sliceDisplayedOptions();
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
