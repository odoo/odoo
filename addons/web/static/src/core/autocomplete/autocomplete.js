import { useAutofocus } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { Component, onWillUpdateProps, proxy, signal, t, useProps } from "@odoo/owl";
import { Dropdown, dropdownProps } from "@web/core/dropdown/dropdown";
import { useNavigation } from "@web/core/navigation/navigation";
import { mergeClasses } from "@web/core/utils/classname";
import { uniqueId } from "@web/core/utils/functions";

/**
 * Dropdown anchored on the autocomplete input, which lives outside of it.
 */
class AutoCompleteDropdown extends Dropdown {
    props = useProps({
        ...dropdownProps,
        target: t.function(),
    });

    get target() {
        return this.isMounted ? this.props.target() : null;
    }

    get hasParent() {
        return false;
    }

    /** The listbox is the list inside the menu. */
    get menuRole() {
        return undefined;
    }

    onOpened() {
        super.onOpened();
        this.target?.classList.remove("show");
    }

    onPositioned(el, solution) {
        super.onPositioned(el, solution);
        if (this.target) {
            const isVertical = ["bottom", "top"].includes(solution.direction);
            el.style.minWidth = isVertical ? getComputedStyle(this.target).width : "";
        }
    }
}

export const autoCompleteProps = {
    value: t.string().optional(""),
    id: t.string().optional(),
    sources: t.array(
        t.object({
            placeholder: t.string().optional(),
            options: t.or([t.array(), t.function()]),
            optionSlot: t.string().optional(),
        })
    ),
    placeholder: t.string().optional(""),
    title: t.string().optional(""),
    autocomplete: t.string().optional("off"),
    autoSelect: t.boolean().optional(false),
    resetOnSelect: t.boolean().optional(),
    onInput: t.function().optional(() => () => {}),
    onCancel: t.function().optional(() => () => {}),
    onChange: t.function().optional(() => () => {}),
    onBlur: t.function().optional(() => () => {}),
    onFocus: t.function().optional(() => () => {}),
    searchOnInputClick: t.boolean().optional(true),
    inputDebounceDelay: t.number().optional(250),
    dropdown: t.boolean().optional(true),
    autofocus: t.boolean().optional(),
    class: t.string().optional(),
    menuPosition: t.string().optional(),
    menuCssClass: t.or([t.string(), t.array(), t.object()]).optional({}),
    selectOnBlur: t.boolean().optional(),
};

export class AutoComplete extends Component {
    static template = "web.AutoComplete";
    static listTemplate = "web.AutoComplete.list";
    static components = { AutoCompleteDropdown };
    props = useProps(autoCompleteProps);

    menuRef = signal.ref();
    listRef = signal.ref();
    root = signal.ref();
    // Ref on the input element, either owned by the parent (`input` prop) or local.
    inputRef = useProps.static(
        "input",
        t.signal(t.ref()).optional(() => signal.ref())
    );

    get timeout() {
        return this.props.inputDebounceDelay;
    }

    setup() {
        this.listId = uniqueId("o-autocomplete-list-");
        this.nextSourceId = 0;
        this.nextOptionId = 0;
        this.inEdition = false;
        this.isOptionSelected = false;

        this.state = proxy({
            open: false,
            sources: [],
            value: this.props.value,
        });

        // The input keeps the focus and handles the keys itself, so that it
        // can stop their propagation (e.g. Enter in an editable list): the
        // navigation hotkeys are never available.
        this.navigationOptions = {
            virtualFocus: true,
            shouldFocusFirstItem: true,
            isNavigationAvailable: ({ navigator, target }) => navigator.contains(target),
            onUpdated: (navigator) => {
                this.navigator = navigator;
                if (!navigator.activeItem) {
                    this.targetDropdown.removeAttribute("aria-activedescendant");
                }
            },
            onItemActivated: (el) => {
                this.lastActiveItemEl = el;
                this.targetDropdown.setAttribute("aria-activedescendant", el.id);
            },
        };

        const isMenuVisible = () => this.isOpened && this.hasOptions;
        this.dropdownState = {
            get isOpen() {
                return isMenuVisible();
            },
            open: () => this.open(),
            // Also called when the menu is removed programmatically: only an
            // external close (click away, other dropdown opened...) cancels.
            close: () => {
                if (isMenuVisible()) {
                    this.cancel();
                }
            },
        };

        if (this.props.autofocus) {
            useAutofocus({ ref: this.inputRef });
        }

        this.debouncedProcessInput = useDebounced(async () => {
            const currentPromise = this.pendingPromise;
            this.pendingPromise = null;
            this.props.onInput({
                inputValue: this.inputRef().value,
            });
            try {
                await this.open(true);
                currentPromise.resolve();
            } catch (e) {
                currentPromise.reject(e);
            } finally {
                if (currentPromise === this.loadingPromise) {
                    this.loadingPromise = null;
                }
            }
        }, this.timeout);

        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value || this.forceValFromProp) {
                this.forceValFromProp = false;
                if (!this.inEdition) {
                    this.state.value = nextProps.value;
                    this.inputRef().value = nextProps.value;
                }
            }
        });

        if (!this.props.dropdown) {
            this.navigator = useNavigation(this.listRef, {
                ...this.navigationOptions,
                shouldRegisterHotkeys: false,
            });
            this.open(false);
        }
    }

    get targetDropdown() {
        return this.inputRef();
    }

    get sources() {
        return this.state.sources;
    }

    get isOpened() {
        return this.state.open;
    }

    get hasOptions() {
        for (const source of this.sources) {
            if (source.isLoading || source.options.length) {
                return true;
            }
        }
        return false;
    }

    /**
     * The rendered items may still be the ones of a previous search (e.g. Enter
     * pressed right after typing): the first selectable option is then active.
     * Option ids are never reused (`nextOptionId`), so the items are known to be
     * stale when none of them carries the id of the current first option.
     */
    get activeOption() {
        const options = this.sources
            .flatMap((source) => (source.isLoading ? [] : source.options))
            .filter((option) => !option.unselectable);
        const getOptionId = (item) => Number(item?.el.dataset.optionId);
        const items = this.navigator?.items || [];
        if (!items.some((item) => getOptionId(item) === options[0]?.id)) {
            return options[0];
        }
        return options.find((option) => option.id === getOptionId(this.navigator.activeItem));
    }

    open(useInput = false) {
        this.state.open = true;
        return this.loadSources(useInput);
    }

    close() {
        this.state.open = false;
    }

    discardPendingInput() {
        this.debouncedProcessInput.cancel();
        this.pendingPromise?.resolve();
        if (this.loadingPromise === this.pendingPromise) {
            this.loadingPromise = null;
        }
        this.pendingPromise = null;
    }

    cancel() {
        if (this.inputRef().value.length) {
            if (this.props.autoSelect) {
                this.inputRef().value = this.props.value;
                this.props.onCancel();
            }
        }
        this.close();
    }

    async loadSources(useInput) {
        const sources = [];
        const proms = [];
        for (const pSource of this.props.sources) {
            const source = this.makeSource(pSource);
            sources.push(source);

            const options = this.loadOptions(
                pSource.options,
                useInput ? this.inputRef().value.trim() : ""
            );
            if (options instanceof Promise) {
                source.isLoading = true;
                const prom = options.then((options) => {
                    source.options = options.map((option) => this.makeOption(option));
                    source.isLoading = false;
                });
                proms.push(prom);
            } else {
                source.options = options.map((option) => this.makeOption(option));
            }
        }
        this.state.sources = sources;

        await Promise.all(proms);
    }
    get displayOptions() {
        return !this.props.dropdown || this.dropdownState.isOpen;
    }
    loadOptions(options, request) {
        if (typeof options === "function") {
            return options(request);
        } else {
            return options;
        }
    }
    makeOption(option) {
        return {
            cssClass: "",
            data: {},
            ...option,
            id: ++this.nextOptionId,
            unselectable: !option.onSelect,
        };
    }
    makeSource(source) {
        return proxy({
            id: ++this.nextSourceId,
            options: [],
            isLoading: false,
            placeholder: source.placeholder,
            optionSlot: source.optionSlot,
        });
    }

    selectOption(option) {
        this.inEdition = false;
        this.discardPendingInput();
        if (option.unselectable) {
            return;
        }

        if (this.props.resetOnSelect) {
            this.inputRef().value = "";
        }
        this.isOptionSelected = true;
        this.forceValFromProp = true;
        option.onSelect();
        this.close();
    }

    onInputBlur() {
        if (this.ignoreBlur) {
            this.ignoreBlur = false;
            return;
        }
        // If selectOnBlur is true, we select the first element
        // of the autocomplete suggestions list, if this element exists
        if (this.props.selectOnBlur && !this.isOptionSelected && this.sources[0]) {
            const firstOption = this.sources[0].options[0];
            if (firstOption) {
                this.selectOption(firstOption);
            }
        }
        this.props.onBlur({
            inputValue: this.inputRef().value,
        });
        this.inEdition = false;
        this.isOptionSelected = false;
    }
    onInputClick() {
        if (!this.dropdownState.isOpen && this.props.searchOnInputClick) {
            this.open(this.inputRef().value.trim() !== this.props.value.trim());
        } else {
            this.close();
        }
    }
    onInputChange(ev) {
        if (this.ignoreBlur) {
            ev.stopImmediatePropagation();
        }
        this.props.onChange({
            inputValue: this.inputRef().value,
            isOptionSelected: this.ignoreBlur,
        });
    }
    async onInput() {
        this.inEdition = true;
        this.pendingPromise = this.pendingPromise || Promise.withResolvers();
        this.loadingPromise = this.pendingPromise;
        this.debouncedProcessInput();
    }

    onInputFocus(ev) {
        this.restoreActiveItem();
        this.inputRef().setSelectionRange(0, this.inputRef().value.length);
        this.props.onFocus(ev);
    }

    /**
     * The navigation deactivates its item when the focus lands outside of its
     * items, which is always the case here: it happens when the input gets the
     * focus back while the menu is open (e.g. after switching windows).
     */
    restoreActiveItem() {
        if (this.navigator && !this.navigator.activeItem) {
            this.navigator.items.find((item) => item.el === this.lastActiveItemEl)?.setActive();
        }
    }

    get autoCompleteRootClass() {
        let classList = "";
        if (this.props.class) {
            classList += this.props.class;
        }
        if (this.props.dropdown) {
            classList += " dropdown";
        }
        return classList;
    }

    get menuClass() {
        return mergeClasses(
            "o-autocomplete--dropdown-menu ui-widget ui-autocomplete",
            this.props.menuCssClass
        );
    }

    get ulDropdownClass() {
        if (this.props.dropdown) {
            return "list-unstyled m-0";
        }
        return mergeClasses("o-autocomplete--dropdown-menu list-group", this.props.menuCssClass);
    }

    async onInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        const isSelectKey = hotkey === "enter" || hotkey === "tab";

        if (this.loadingPromise && isSelectKey) {
            if (hotkey === "enter") {
                ev.stopPropagation();
                ev.preventDefault();
            }

            await this.loadingPromise.promise;
        }

        switch (hotkey) {
            case "enter":
            case "tab":
            case "shift+tab": {
                const option = this.isOpened && this.activeOption;
                if (!option) {
                    return;
                }
                this.selectOption(option);
                break;
            }
            case "escape":
                if (!this.isOpened) {
                    return;
                }
                this.cancel();
                break;
            case "arrowup":
            case "arrowdown":
                if (!this.isOpened) {
                    this.open(true);
                } else if (hotkey === "arrowup") {
                    this.navigator?.previous();
                } else {
                    this.navigator?.next();
                }
                break;
            case "arrowleft":
            case "arrowright":
                if (!this.isOpened || this.inputRef().value.length) {
                    return;
                }
                this.cancel();
                // Let ArrowLeft/ArrowRight propagate to ensure focus transition
                // from the options dropdown to the neighbor element
                return;
            default:
                return;
        }

        ev.stopPropagation();
        ev.preventDefault();
    }

    onOptionSelected(option) {
        this.selectOption(option);
        this.inputRef().focus();
    }

    onListPointerDown(ev) {
        if (ev.target.closest(".o-autocomplete--dropdown-item")?.querySelector(".o-navigable")) {
            this.ignoreBlur = true;
        }
    }

    /**
     * Cancelling pointerdown does not prevent the focus change, only
     * cancelling mousedown does.
     */
    onListMouseDown(ev) {
        const item = ev.target.closest(".o-autocomplete--dropdown-item");
        if (item && !item.querySelector(".o-navigable")) {
            ev.preventDefault();
        }
    }
}
