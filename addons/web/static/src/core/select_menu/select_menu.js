import { Component, onWillUpdateProps, useEffect, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { TagsList } from "@web/core/tags_list/tags_list";
import { mergeClasses } from "@web/core/utils/classname";
import { useAutofocus, useChildRef } from "@web/core/utils/hooks";
import { scrollTo } from "@web/core/utils/scrolling";
import { fuzzyLookup } from "@web/core/utils/search";
import { useDebounced } from "@web/core/utils/timing";

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
                },
            },
        },
        class: { type: String, optional: true },
        menuClass: { type: String, optional: true },
        togglerClass: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        searchable: { type: Boolean, optional: true },
        autoSort: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        searchPlaceholder: { type: String, optional: true },
        value: { optional: true },
        multiSelect: { type: Boolean, optional: true },
        onInput: { type: Function, optional: true },
        onSelect: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        element: { type: HTMLElement, optional: true },
        choiceFetchFunction: { type: Function, optional: true },
        // To allow create option & pre-computation on creation.
        // @return [choices].
        onCreate: { type: Function, optional: true },
        disabled: { type: Boolean, optional: true },
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
        if (this.props.element) {
            this.props.element.value = this.props.value;
            this.props.element.style.display = "none";
        }
        this.buttonRef = useRef("buttonRef");
        this.inputRef = useRef("inputRef");
        this.selectedIds = [];
        this.menuRef = useChildRef();
        this.debouncedOnInput = useDebounced(
            () => this.onInput(this.inputRef.el ? this.inputRef.el.value.trim() : ""),
            250
        );
        this.isOpen = false;

        this.choiceValues = this.getSelectedChoice(this.props);
        this.selectedChoice = this.getSelectedChoice(this.props);
        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value) {
                if (this.props.choiceFetchFunction) {
                    nextProps.choices = this.state.choices;
                }
                this.selectedChoice = this.getSelectedChoice(nextProps);
            }
        });
        useEffect(
            () => this.buttonRef.el.classList.toggle("disabled", !!this.props.disabled),
            () => [this.props.disabled]
        );
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
        return this.choiceValues.map((c) => {
            return {
                id: c.value,
                text: c.label,
                onDelete: () => {
                    const values = [...this.props.value];
                    values.splice(values.indexOf(c.value), 1);
                    this.props.onSelect(values);
                    this.choiceValues.splice(
                        this.choiceValues.findIndex((choice) => choice.id == c.id),
                        1
                    );
                    this.setValues(values);
                },
            };
        });
    }

    get menuClass() {
        return mergeClasses(
            {
                "o_select_menu_menu border bg-light": true,
                "py-0": this.props.searchable,
                o_select_menu_multi_select: this.props.multiSelect,
            },
            this.props.menuClass
        );
    }

    async onBeforeOpen() {
        if (this.state.searchValue.length) {
            this.state.searchValue = "";
            if (this.props.onInput) {
                // This props can be used by the parent to fetch items dynamically depending
                // the search value. It must be called with the empty search value.
                await this.executeOnInput("");
            }
        }
        await this.fetchOptions();
        this.filterOptions();
    }

    onStateChanged(open) {
        this.isOpen = open;
        if (open) {
            this.menuRef.el?.addEventListener("scroll", (ev) => this.onScroll(ev));
            const selectedElement = this.menuRef.el?.querySelectorAll(".o_select_active")[0];
            if (selectedElement) {
                scrollTo(selectedElement);
            }
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
            return "o_select_menu_item p-2 o_select_active bg-primary fw-bolder fst-italic";
        } else {
            return "o_select_menu_item p-2";
        }
    }

    async executeOnInput(searchString) {
        await this.props.onInput(searchString);
    }

    async onInput(searchString) {
        await this.fetchOptions(searchString);
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

    getSelectedChoice(props) {
        const choices = [...props.choices, ...props.groups.flatMap((g) => g.choices)];
        if (this.props.multiSelect) {
            return choices.filter((c) => this.props.value.includes(c.value));
        }
        return choices.find((c) => c.value === props.value);
    }

    async onCreateOption(searchString) {
        let choice = {
            id: `_${searchString.trim()}`,
            label: searchString.trim(),
            value: searchString.trim(),
        };
        if (this.props.onCreate) {
            choice = await this.props.onCreate(choice);
        }
        this.props.choices.push(choice);
        this.state.choices = this.props.choices;
        await this.onItemSelected(choice);
    }
    async onItemSelected(choice) {
        if (this.props.multiSelect) {
            const values = [...this.props.value];
            const valueIndex = values.indexOf(choice.value);

            if (valueIndex !== -1) {
                values.splice(valueIndex, 1);
                this.props.onSelect(values);
                this.choiceValues.splice(
                    this.choiceValues.findIndex((c) => c.id == choice.id),
                    1
                );
                this.setValues(values);
            } else {
                this.props.onSelect([...this.props.value, choice.value]);
                this.choiceValues = [...this.choiceValues, choice];
                this.setValues([...this.props.value, choice.value]);
            }
        } else if (!this.selectedChoice || this.selectedChoice.value !== choice.value) {
            this.props.onSelect(choice.value);
            this.setValues([choice.value]);
        }
    }

    setValues(values) {
        if (this.props.element) {
            const selectedValues = new Set(values);
            this.selectedIds = this.props.choices
                .filter((choice) => selectedValues.has(choice.value))
                .map((choice) => choice.id);
            this.props.element.value = this.selectedIds;
        }
    }

    // ==========================================================================================
    // #                                         Search                                         #
    // ==========================================================================================

    /**
     * Fetches the choices by calling choiceFetchFunction provided in props.
     * After fetchning the choices set the choices in state and props.
     *
     * @param {String} searchString
     */
    async fetchOptions(searchString = "") {
        if (this.props.choiceFetchFunction) {
            const choices = await this.props.choiceFetchFunction(searchString);
            this.state.choices = choices;
            this.props.choices = choices;
        }
    }

    /**
     * Filters the choices based on the searchString and
     * slice the result to display a reasonable amount to
     * try to prevent any delay when opening the select.
     *
     * @param {String} searchString
     */
    async filterOptions(searchString = "", groups) {
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
