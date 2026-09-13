// @ts-check
/** @odoo-module native */

import { Component, onWillRender, toRaw, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/components/dropdown/dropdown";
import { useDropdownState } from "@web/components/dropdown/dropdown_hook";
import { DropdownItem } from "@web/components/dropdown/dropdown_item";
import { TagsList } from "@web/components/tags_list/tags_list";
import { hasTouch } from "@web/core/browser/feature_detection";
import { makeLogger } from "@web/core/debug/debug_logger";
import { useLifecycleLog } from "@web/core/debug/logger_hooks";
import { KeepLast, SupersededError } from "@web/core/utils/concurrency";
import { mergeClasses } from "@web/core/utils/dom/classname";
import { scrollTo } from "@web/core/utils/dom/scrolling";
import { uniqueId } from "@web/core/utils/functions";
import { useChildRef } from "@web/core/utils/hooks";
import { fuzzyLookup } from "@web/core/utils/search";
import { INPUT_DEBOUNCE_DELAY, useDebounced } from "@web/core/utils/timing";
import { utils } from "@web/ui/viewport";

const log = makeLogger("web.components.select_menu");

const collator = new Intl.Collator();

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
                type: Object,
                shape: {
                    label: { type: String },
                    name: { type: String },
                },
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

    /** @type {ReturnType<typeof useDropdownState>} */
    dropdownState;

    /**
     * @type {{
     *     appliedSearch: string,
     *     isFocused: boolean,
     *     displayedRevision: number,
     * }}
     */
    state;
    /**
     * What the user has typed, or null while the input shows the selection.
     * Not reactive: the input owns its text between renders, and a render per
     * keystroke re-rendered every option of the open menu before the debounced
     * search had run. Held on an object for the same reason as `filtered`.
     * @type {{ value: string | null }}
     */
    search = { value: null };
    /**
     * The lists the open menu renders. A plain object with one identity for
     * the component's life: the content slot captures instance fields by
     * value when it is created, so a list reassigned on `this` would stay
     * stale inside the popover, while a list reassigned on this holder is
     * read live through it.
     * @type {{ choices: any[], displayed: any[] }}
     */
    filtered = { choices: [], displayed: [] };
    displayedCount = 0;

    setup() {
        useLifecycleLog(log);
        this.selectMenuId = uniqueId("o_select_menu_");
        this.menuId = `${this.selectMenuId}_menu`;
        this.listboxId = `${this.selectMenuId}_listbox`;
        this.state = useState({
            appliedSearch: "",
            isFocused: false,
            displayedRevision: 0,
        });
        this.inputRef = useRef("inputRef");
        this.menuRef = useChildRef();
        this.dropdownState = useDropdownState();
        this.onInputKeepLast = new KeepLast({ rejectSuperseded: true });
        this.loadMoreSentinel = useRef("loadMoreSentinel");
        /** @type {IntersectionObserver | null} */
        this.loadMoreObserver = null;
        this.props.menuRef?.(this.menuRef);
        this.debouncedOnInput = useDebounced((searchString) => {
            if (!this.dropdownState.isOpen) {
                this.dropdownState.open();
            }
            this.onInput(searchString);
        }, INPUT_DEBOUNCE_DELAY);

        /** @type {Map<any, any>} */
        this._choiceMemory = new Map();
        /** @type {any[]} */
        this._choiceSignature = [];
        this.choicesRevision = 0;
        /** @type {any | any[] | undefined} */
        this.selectedChoice = undefined;
        /** @type {WeakMap<any[], { revision: number, sorted: any[] }>} */
        this._sortedChoicesCache = new WeakMap();
        /** @type {{ revision: number, byValue: Map<any, any> } | null} */
        this._choiceIndex = null;
        /** @type {string | null} */
        this._derivedKey = null;
        /** @type {Set<any> | null} */
        this._selectedValueSet = null;

        onWillRender(() => {
            this._selectedValueSet = null;
            this.syncChoicesRevision();
            this.selectedChoice = this.getSelectedChoice(this.props);
            if (this.dropdownState.isOpen && this._derivedKey !== this.derivationKey) {
                this.filterOptions(this.state.appliedSearch);
            }
            this.filtered.displayed = this.filtered.choices.slice(
                0,
                this.displayedCount,
            );
        });

        const self = this;
        this.navigationOptions = {
            shouldFocusFirstItem: !hasTouch(),
            get virtualFocus() {
                return self.props.searchable;
            },
            hotkeys: {
                enter: {
                    isAvailable: ({ navigator }) => navigator.items.length,
                    callback: (navigator) => {
                        if (navigator.activeItem) {
                            return navigator.activeItem.select();
                        }
                        if (
                            /** @type {HTMLInputElement} */ (document.activeElement)
                                .value
                        ) {
                            navigator.items[0].select();
                        }
                    },
                },
            },
            onItemActivated: (element) => {
                const index = Number.parseInt(element.dataset.choiceIndex, 10);
                if (index >= 0 && this.filtered.displayed[index]) {
                    this.props.onNavigated(this.filtered.displayed[index]);
                } else {
                    this.props.onNavigated();
                }
            },
        };
    }

    /** @returns {any[]} */
    get selectedValues() {
        return this.props.value ?? [];
    }

    /** @returns {boolean} */
    get hasSelection() {
        if (this.props.multiSelect) {
            return this.selectedValues.length > 0;
        }
        return this.selectedChoice !== undefined;
    }

    get displayValue() {
        return this.search.value === null
            ? this.selectedChoice?.label || ""
            : this.search.value;
    }

    get displayInputInToggler() {
        return !this.props.slots || !this.props.slots.default;
    }

    get displayInputInDropdown() {
        return (
            (this.isBottomSheet || !this.displayInputInToggler) && this.props.searchable
        );
    }

    get isBottomSheet() {
        return utils.isSmall() && hasTouch();
    }

    get canDeselect() {
        return !this.props.required && this.hasSelection;
    }

    get multiSelectChoices() {
        return this.selectedChoice.map((c) => ({
            id: c.value,
            text: c.label,
            onDelete: () => {
                const values = [...this.selectedValues];
                const index = values.indexOf(c.value);
                if (index !== -1) {
                    values.splice(index, 1);
                    this.props.onSelect(values);
                }
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
            this.props.menuClass,
        );
    }

    get placeholderValue() {
        if (this.state.isFocused && this.props.searchPlaceholder) {
            return this.props.searchPlaceholder;
        }
        return this.props.placeholder;
    }

    onBeforeOpen() {
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
        const menuEl = /** @type {any} */ (this.menuRef).el;
        const related = /** @type {Node | null} */ (ev.relatedTarget);
        if (this.dropdownState.isOpen && related && menuEl?.contains(related)) {
            return;
        }
        if (ev.target.value === "" && !this.props.multiSelect) {
            if (this.canDeselect) {
                this.onInputClear();
            } else {
                this.search.value = null;
            }
        }
    }

    onInputClick(ev) {
        if (!ev.target.classList.contains("o_select_menu_toggler")) {
            ev.stopPropagation();
        }
    }

    onSearchInput(ev) {
        this.search.value = ev.target.value;
        this.debouncedOnInput(this.search.value);
    }

    onInputClear() {
        this.props.onSelect(this.props.multiSelect ? [] : null);
        this.dropdownState.close();
    }

    onStateChanged(open) {
        log.logic("onStateChanged", () => ({ open, bottomSheet: this.isBottomSheet }));
        if (open) {
            if (this.isBottomSheet) {
                /** @type {HTMLElement} */ (document.activeElement).blur();
            }
            if (this.displayInputInDropdown && !this.isBottomSheet) {
                this.inputRef.el.focus();
            }
            this.observeLoadMore();
            const selectedElement = /** @type {any} */ (
                this.menuRef
            ).el?.querySelectorAll(".selected")[0];
            if (selectedElement) {
                scrollTo(selectedElement);
            }
            this.props.onOpened();
        } else {
            this.debouncedOnInput.cancel();
            this.loadMoreObserver?.disconnect();
            this.loadMoreObserver = null;
            this.search.value = null;
            this.state.appliedSearch = "";
            this.filtered.choices = [];
            this.filtered.displayed = [];
            this.displayedCount = 0;
            this._derivedKey = null;
            this.props.onClosed();
        }
    }

    /** @returns {{ searchValue: string | null, appliedSearch: string, choices: any[], displayedOptions: any[], isFocused: boolean }} */
    get slotData() {
        return {
            searchValue: this.search.value,
            appliedSearch: this.state.appliedSearch,
            choices: this.filtered.choices,
            displayedOptions: this.filtered.displayed,
            isFocused: this.state.isFocused,
        };
    }

    /** @returns {Set<any>} */
    get selectedValueSet() {
        this._selectedValueSet ??= new Set(this.selectedValues);
        return this._selectedValueSet;
    }

    isOptionSelected(choice) {
        if (choice.isGroup) {
            return false;
        }
        if (this.props.multiSelect) {
            return this.selectedValueSet.has(choice.value);
        }
        return this.props.value === choice.value;
    }

    /**
     * @param {any} choice
     * @param {number} index
     * @returns {Record<string, any>}
     */
    getItemAttrs(choice, index) {
        const attrs = { "data-choice-index": index };
        if (this.props.multiSelect) {
            attrs["aria-selected"] = this.isOptionSelected(choice) ? "true" : "false";
        }
        return attrs;
    }

    getItemClass(choice) {
        if (this.isOptionSelected(choice)) {
            return "o_select_menu_item fw-bolder selected";
        } else {
            return "o_select_menu_item";
        }
    }

    async onInput(searchString) {
        this.state.appliedSearch = searchString;
        if (this.props.onInput) {
            try {
                await this.onInputKeepLast.add(
                    Promise.resolve(this.props.onInput(searchString)),
                );
            } catch (error) {
                if (!(error instanceof SupersededError)) {
                    throw error;
                }
            }
        }
    }

    syncChoicesRevision() {
        const signature = this._choiceSignature;
        let cursor = 0;
        let changed = false;
        /** @param {any} entry */
        const visit = (entry) => {
            if (cursor >= signature.length || signature[cursor] !== entry) {
                signature[cursor] = entry;
                changed = true;
            }
            cursor++;
        };
        const visitChoice = (choice) => {
            visit(choice);
            visit(choice.label);
            visit(choice.value);
        };
        visit(this.props.autoSort);
        for (const section of this.props.sections) {
            visit(section.name);
            visit(section.label);
        }
        for (const choice of this.props.choices) {
            visitChoice(choice);
        }
        for (const group of this.props.groups) {
            visit(group);
            visit(group.label);
            visit(group.section);
            for (const choice of group.choices || []) {
                visitChoice(choice);
            }
        }
        if (signature.length !== cursor) {
            signature.length = cursor;
            changed = true;
        }
        if (changed) {
            this.choicesRevision++;
        }
    }

    /** @returns {Map<any, any>} */
    get choiceByValue() {
        if (this._choiceIndex?.revision === this.choicesRevision) {
            return this._choiceIndex.byValue;
        }
        const byValue = new Map();
        for (let i = this.props.groups.length - 1; i >= 0; i--) {
            const choices = this.props.groups[i].choices || [];
            for (let j = choices.length - 1; j >= 0; j--) {
                byValue.set(toRaw(choices[j]).value, choices[j]);
            }
        }
        for (let i = this.props.choices.length - 1; i >= 0; i--) {
            const choice = this.props.choices[i];
            byValue.set(toRaw(choice).value, choice);
        }
        this._choiceIndex = { revision: this.choicesRevision, byValue };
        return byValue;
    }

    getSelectedChoice(props) {
        const byValue = this.choiceByValue;
        const values = props.multiSelect
            ? /** @type {any[]} */ (props.value ?? [])
            : [props.value];

        for (const value of values) {
            const choice = byValue.get(value);
            if (choice) {
                this._choiceMemory.set(value, choice);
            }
        }
        const valueSet = new Set(values);
        for (const value of this._choiceMemory.keys()) {
            if (!valueSet.has(value)) {
                this._choiceMemory.delete(value);
            }
        }

        if (props.multiSelect) {
            return values.map((value) => this._choiceMemory.get(value)).filter(Boolean);
        }
        return byValue.get(props.value) ?? this._rememberedChoice(props.value);
    }

    /**
     * @param {any} value
     * @returns {any | undefined}
     */
    _rememberedChoice(value) {
        if (value === false || value === undefined || value === null) {
            return undefined;
        }
        return this._choiceMemory.get(value);
    }

    onItemSelected(value) {
        log.logic("onItemSelected", () => ({
            value,
            multiSelect: this.props.multiSelect,
        }));
        if (this.props.multiSelect) {
            const values = [...this.selectedValues];
            const valueIndex = values.indexOf(value);

            if (valueIndex !== -1) {
                values.splice(valueIndex, 1);
                this.props.onSelect(values);
            } else {
                this.props.onSelect([...this.selectedValues, value]);
            }
        } else if (this.props.value !== value) {
            this.props.onSelect(value);
        }
        this.search.value = null;
    }

    /**
     * @param {string} searchString
     * @returns {string}
     */
    derivationKeyFor(searchString) {
        return `${this.choicesRevision}\x00${searchString}`;
    }

    /** @returns {string} */
    get derivationKey() {
        return this.derivationKeyFor(this.state.appliedSearch);
    }

    /** @param {String} searchString */
    filterOptions(searchString = "") {
        const end = log.perf("filterOptions", () => ({
            searchString,
            revision: this.choicesRevision,
        }));
        this._selectedValueSet = null;
        this._derivedKey = this.derivationKeyFor(searchString);
        const groupsList = [
            { choices: this.props.choices, section: "" },
            ...this.props.groups,
        ];

        const _choices = [];
        const _sections = new Set();
        const sectionByName = new Map(
            this.props.sections.map((section) => [section.name, section]),
        );
        const sectionOrder = new Map(
            this.props.sections.map((section, index) => [section.name, index]),
        );
        const sectionRank = (group) => {
            if (!group.section) {
                return -1;
            }
            return sectionOrder.get(group.section) ?? Infinity;
        };
        groupsList.sort((a, b) => {
            const rankA = sectionRank(a);
            const rankB = sectionRank(b);
            if (rankA !== rankB) {
                return rankA - rankB;
            }
            return collator.compare(a.section || "", b.section || "");
        });

        for (const group of groupsList) {
            let filteredOptions = group.choices || [];

            if (searchString) {
                filteredOptions = fuzzyLookup(
                    searchString.trim(),
                    filteredOptions,
                    (choice) => choice.label,
                );
            } else {
                if (this.props.autoSort) {
                    filteredOptions = this.getSortedChoices(filteredOptions);
                }
            }

            if (!filteredOptions.length) {
                continue;
            }
            if (group.section) {
                const section = sectionByName.get(group.section);
                if (section && !_sections.has(section.name)) {
                    _sections.add(section.name);
                    _choices.push({ ...section, isGroup: true });
                }
            }
            if (group.label) {
                _choices.push({ ...group, isGroup: true });
            }
            _choices.push(...filteredOptions);
        }

        this.filtered.choices = _choices;
        this.displayedCount = this.initialDisplayedCount();
        end({ choices: _choices.length, displayed: this.displayedCount });
    }

    /**
     * @param {any[]} choices
     * @returns {any[]}
     */
    getSortedChoices(choices) {
        const cached = this._sortedChoicesCache.get(choices);
        if (cached && cached.revision === this.choicesRevision) {
            return cached.sorted;
        }
        const sorted = choices.toSorted((a, b) => collator.compare(a.label, b.label));
        this._sortedChoicesCache.set(choices, {
            revision: this.choicesRevision,
            sorted,
        });
        return sorted;
    }

    /** @returns {typeof SelectMenu.SCROLL_SETTINGS} */
    get scrollSettings() {
        return /** @type {typeof SelectMenu} */ (this.constructor).SCROLL_SETTINGS;
    }

    observeLoadMore() {
        this.loadMoreObserver?.disconnect();
        const root = /** @type {any} */ (this.menuRef).el;
        const sentinel = this.loadMoreSentinel.el;
        if (!root || !sentinel) {
            return;
        }
        const { distanceBeforeReload, increaseAmount } = this.scrollSettings;
        this.loadMoreObserver = new IntersectionObserver(
            ([entry]) => {
                if (!entry.isIntersecting) {
                    return;
                }
                if (this.displayedCount >= this.filtered.choices.length) {
                    return;
                }
                this.displayedCount += increaseAmount;
                this.state.displayedRevision++;
            },
            { root, rootMargin: `0px 0px ${distanceBeforeReload}px 0px` },
        );
        this.loadMoreObserver.observe(sentinel);
    }

    /** @returns {number} */
    initialDisplayedCount() {
        const selectedIndex = this.getSelectedOptionIndex();
        const { defaultCount, increaseAmount } = this.scrollSettings;
        if (selectedIndex === -1) {
            return defaultCount;
        }
        return Math.max(selectedIndex + increaseAmount, defaultCount);
    }

    getSelectedOptionIndex() {
        return this.filtered.choices.findIndex((choice) =>
            this.isOptionSelected(choice),
        );
    }
}
