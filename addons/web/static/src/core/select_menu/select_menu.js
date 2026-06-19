import { useLayoutEffect, useRef } from "@web/owl2/utils";
import { Component, onWillUpdateProps, props, proxy, t } from "@odoo/owl";
import { hasTouch } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { localeCompare, normalize } from "@web/core/l10n/utils";
import { BadgeTag } from "@web/core/tags_list/badge_tag";
import { mergeClasses } from "@web/core/utils/classname";
import { useChildRef } from "@web/core/utils/hooks";
import { highlightText, odoomark } from "@web/core/utils/html";
import { scrollTo } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";

let selectMenuId = 0;

export const DEBOUNCED_DELAY = 250;

class SelectMenuTagsList extends Component {
    static template = "web.SelectMenuTagsList";
    static components = { BadgeTag };
    static props = {
        tags: { type: Array },
    };
}

export const selectMenuProps = {
    choices: t
        .array(
            t.object({
                enabled: t.boolean().optional(),
                value: t.any(),
                label: t.string(),
            })
        )
        .optional([]),
    groups: t
        .array(
            t.object({
                label: t.string().optional(),
                choices: t.array(
                    t.object({
                        value: t.any(),
                        label: t.string(),
                    })
                ),
                section: t.string().optional(),
            })
        )
        .optional([]),
    sections: t
        .array(
            t.object({
                label: t.string(),
                name: t.string(),
            })
        )
        .optional([]),
    id: t.string().optional(""),
    name: t.string().optional(""),
    class: t.string().optional(""),
    menuClass: t.string().optional(""),
    togglerClass: t.string().optional(""),
    required: t.boolean().optional(false),
    searchable: t.boolean().optional(true),
    autoSort: t.boolean().optional(true),
    placeholder: t.string().optional(),
    searchPlaceholder: t.string().optional(""),
    searchClass: t.string().optional(),
    value: t.any().optional(),
    multiSelect: t.boolean().optional(false),
    onInput: t.function().optional(),
    onSelect: t.function().optional(() => () => {}),
    onNavigated: t.function().optional(() => () => {}),
    onOpened: t.function().optional(() => () => {}),
    onClosed: t.function().optional(() => () => {}),
    slots: t.object().optional(),
    disabled: t.boolean().optional(false),
    menuRef: t.function().optional(),
};

export class SelectMenu extends Component {
    static template = "web.SelectMenu";
    static choiceItemTemplate = "web.SelectMenu.ChoiceItem";

    static components = { Dropdown, DropdownItem, TagsList: SelectMenuTagsList };

    props = props(selectMenuProps);

    static SCROLL_SETTINGS = {
        defaultCount: 500,
        increaseAmount: 300,
        distanceBeforeReload: 500,
    };

    setup() {
        this.selectMenuId = selectMenuId++;
        this.state = proxy({
            choices: [],
            displayedOptions: [],
            isFocused: false,
        });

        this.inputRefs = {
            toggler: useRef("inputRefToggler"),
            menu: useRef("inputRefMenu"),
        };

        this.menuRef = useChildRef();
        this.choicesRef = useRef("choicesRef");
        this.props.menuRef?.(this.menuRef);
        this.debouncedOnInput = useDebounced(() => {
            if (!this.dropdownState.isOpen) {
                this.dropdownState.open();
            }
            this.onInput(this.pendingValue);
        }, DEBOUNCED_DELAY);
        this.dropdownState = useDropdownState();

        this.selectedChoice = this.getSelectedChoice(this.props);
        onWillUpdateProps((nextProps) => {
            const choicesChanged = this.state.choices !== nextProps.choices;
            if (choicesChanged) {
                this.state.choices = nextProps.choices;
            }
            if (choicesChanged || this.props.value !== nextProps.value) {
                this.selectedChoice = this.getSelectedChoice(nextProps);
            }
        });
        useLayoutEffect(
            () => {
                if (this.dropdownState.isOpen) {
                    const groups = [{ choices: this.props.choices }, ...this.props.groups];
                    this.filterOptions(this.pendingValue, groups);
                }
            },
            () => [this.props.choices, this.props.groups]
        );

        useLayoutEffect(
            () => this.updateInputValue(),
            () => [this.selectedChoice]
        );

        const navigationCallback = (navigator) => {
            if (navigator.activeItem) {
                return navigator.activeItem.select();
            }
            if (document.activeElement.value) {
                navigator.items[0].select();
            }
        };

        this.navigationOptions = {
            shouldFocusFirstItem: !hasTouch(),
            virtualFocus: this.props.searchable,
            hotkeys: {
                enter: {
                    isAvailable: ({ navigator }) => navigator.items.length > 0,
                    callback: navigationCallback,
                },
                tab: {
                    isAvailable: ({ navigator }) => navigator.items.length > 0,
                    callback: navigationCallback,
                },
                "shift+tab": {
                    isAvailable: ({ navigator }) => navigator.items.length > 0,
                    callback: navigationCallback,
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

    handleInputDebounced(ev) {
        this.pendingValue = ev.target.value;
        this.debouncedOnInput();
    }

    clearInputValue() {
        delete this.pendingValue;
        this.updateInputValue();
    }

    updateInputValue(value = null) {
        for (const ref of Object.values(this.inputRefs)) {
            if (ref.el) {
                ref.el.value = value || this.pendingValue || this.selectedChoice?.label || "";
            }
        }
    }

    get displayInputInToggler() {
        return !this.props.slots || !this.props.slots.default;
    }

    get displayInputInDropdown() {
        return (this.isBottomSheet || !this.displayInputInToggler) && this.props.searchable;
    }

    get isBottomSheet() {
        return hasTouch();
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
                "p-0": true,
                "overflow-hidden": true,
                "d-flex": true,
                "flex-column": true,
            },
            this.props.menuClass
        );
    }

    get placeholderValue() {
        if (
            (this.state.isFocused || this.dropdownNextOpenState === "open") &&
            this.props.searchPlaceholder
        ) {
            return this.props.searchPlaceholder;
        }
        return this.props.placeholder;
    }

    async onBeforeOpen() {
        this.dropdownNextOpenState = "open";
        this.onInput("");
    }

    onKeyDown(ev) {
        if (ev.key === " " && !this.dropdownState.isOpen) {
            this.dropdownState.open();
            ev.preventDefault();
        }
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
        // if the input is not in the toggler, it is in the dropdown.
        // if the input blurs, it means that something else has gained
        // focus, so that the dropdown will be closing.
        if (this.displayInputInToggler) {
            this.state.isFocused = false;
        }
        if (ev.target.value === "" && !this.props.multiSelect) {
            if (this.canDeselect) {
                this.onInputClear();
            } else {
                this.clearInputValue();
            }
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
        this.dropdownNextOpenState = undefined;
        if (open) {
            if (this.isBottomSheet) {
                // the toggler input must not be focused
                document.activeElement.blur();
            }
            if (this.displayInputInDropdown && !this.isBottomSheet) {
                this.inputRefs.menu.el?.focus();
            }
            this.choicesRef.el?.addEventListener("scroll", (ev) => this.onScroll(ev));
            const selectedElement = this.menuRef.el?.querySelectorAll(".selected")[0];
            if (selectedElement) {
                scrollTo(selectedElement);
            }
            this.updateInputValue();
            this.props.onOpened();
        } else {
            this.clearInputValue();
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
        return mergeClasses("o_select_menu_item text-wrap", {
            "fw-bolder selected": this.isOptionSelected(choice),
            "text-muted": !choice.enabled,
        });
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
            if (this.state.choices && this.state.choices.length) {
                this.updateInputValue(this.state.choices.find((c) => c.value === value).label);
            }
        }
        this.clearInputValue();
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
        groupsList.sort((a, b) => localeCompare(a.section, b.section, { emptyLast: false }));

        for (const group of groupsList) {
            let filteredOptions = group.choices || [];
            const normalizedSearchString = searchString && normalize(searchString);

            if (normalizedSearchString) {
                filteredOptions = filteredOptions.filter((choice) =>
                    normalize(choice.label).includes(normalizedSearchString)
                );
                // Fuzzy filtering commented in case we want it back
                // filteredOptions = fuzzyLookup(
                //     searchString.trim(),
                //     filteredOptions,
                //     (choice) => choice.label
                // );
            } else {
                if (this.props.autoSort) {
                    filteredOptions.sort((optionA, optionB) =>
                        localeCompare(optionA.label, optionB.label)
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
            _choices.push(
                ...filteredOptions.map((choice) => ({
                    ...choice,
                    enabled: choice.enabled ?? true,
                    label: choice.label
                        ? highlightText(
                              searchString,
                              odoomark(choice.label),
                              "text-primary fw-bold"
                          )
                        : choice.value,
                    value: choice.value,
                }))
            );
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
