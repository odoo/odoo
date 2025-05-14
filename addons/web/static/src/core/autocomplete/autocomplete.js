import { useAutofocus, useChildRef, useForwardRefToParent } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Component, onWillUpdateProps, useExternalListener, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useSourceLoader } from "@web/core/autocomplete/autocomplete_utils";
import { AutoCompleteItem } from "@web/core/autocomplete/autocomplete_item";

function getFirstSelectable(sources) {
    for (const source of sources) {
        for (const option of source.options) {
            if (!option.unselectable) {
                return option;
            }
        }
    }
    return null;
}

export class AutoComplete extends Component {
    static components = { Dropdown, DropdownItem, AutoCompleteItem };
    static template = "web.AutoComplete";
    static props = {
        value: { type: String, optional: true },
        id: { type: String, optional: true },
        sources: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    placeholder: { type: String, optional: true },
                    options: [Array, Function],
                    optionSlot: { type: String, optional: true },
                },
            },
        },
        placeholder: { type: String, optional: true },
        autocomplete: { type: String, optional: true },
        autoSelect: { type: Boolean, optional: true },
        resetOnSelect: { type: Boolean, optional: true },
        onInput: { type: Function, optional: true },
        onCancel: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        onFocus: { type: Function, optional: true },
        searchOnInputClick: { type: Boolean, optional: true },
        // Input ChildRef
        input: { type: Function, optional: true },
        inputDebounceDelay: { type: Number, optional: true },
        dropdown: { type: Boolean, optional: true },
        autofocus: { type: Boolean, optional: true },
        class: { type: String, optional: true },
        menuClass: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        value: "",
        placeholder: "",
        autocomplete: "new-password",
        autoSelect: false,
        dropdown: true,
        onInput: () => {},
        onCancel: () => {},
        onChange: () => {},
        onBlur: () => {},
        onFocus: () => {},
        searchOnInputClick: true,
        inputDebounceDelay: 250,
        menuClass: "",
    };

    get timeout() {
        return this.props.inputDebounceDelay;
    }

    setup() {
        this.inEdition = false;
        this.didNavigate = false;

        this.root = useRef("root");
        this.inputRef = useForwardRefToParent("input");
        this.menuRef = useChildRef();
        this.dropdown = useDropdownState();
        this.navigationOptions = this.getNavigationOptions();

        this.state = useState({
            value: this.props.value,
        });

        onWillUpdateProps((nextProps) => this.updateProps(nextProps));

        if (this.props.autofocus) {
            useAutofocus({ refName: "input" });
        }

        useExternalListener(window, "scroll", this.externalClose, true);
        useExternalListener(window, "pointerdown", this.externalClose, true);
        useExternalListener(window, "mousemove", () => (this.mouseSelectionActive = true), true);

        this.sourceLoader = useSourceLoader({
            sources: this.props.sources,
            onSourcesLoaded: () => {
                if (!this.sourceLoader.hasOptions) {
                    this.dropdown.close();
                }
            },
        });

        this.debounceLoad = useDebounced(() => {
            this.sourceLoader.load(this.inputRef.el.value.trim());
            this.props.onInput({
                inputValue: this.inputRef.el.value,
            });
            this.open();
        }, this.timeout);
    }

    updateProps(nextProps) {
        if (this.props.value !== nextProps.value || this.forceValFromProp) {
            this.forceValFromProp = false;
            if (!this.inEdition) {
                this.state.value = nextProps.value;
                this.inputRef.el.value = nextProps.value;
            }
            this.close();
        }
    }

    get sources() {
        return this.sourceLoader.sources;
    }

    get dropdownClass() {
        const classList = [
            "o-autocomplete--dropdown-menu",
            "dropdown-menu",
            "ui-autocomplete",
            "ui-widget",
            "show",
            "mt-0",
        ];
        if (this.props.menuClass) {
            classList.push(this.props.menuClass);
        }
        return classList.join(" ");
    }

    getOptionId(sourceIndex, optionIndex = "loading") {
        if (sourceIndex === -1 || optionIndex === -1) {
            return null;
        }
        return `${this.props.id || "autocomplete"}_${sourceIndex}_${optionIndex}`;
    }

    open() {
        this.dropdown.open();
    }

    close() {
        this.dropdown.close();
        this.sourceLoader.clear();
    }

    cancel() {
        if (this.inputRef.el && this.inputRef.el.value.length && this.props.autoSelect) {
            this.inputRef.el.value = this.props.value;
            this.props.onCancel();
        }
    }

    selectOption(option) {
        this.inEdition = false;

        if (this.props.resetOnSelect) {
            this.inputRef.el.value = "";
        }

        this.forceValFromProp = true;
        option.onSelect();
        this.close();
    }

    onInputBlur() {
        if (this.ignoreBlur) {
            this.ignoreBlur = false;
            return;
        }
        this.props.onBlur({
            inputValue: this.inputRef.el.value,
        });
        this.inEdition = false;
    }

    onInputClick() {
        if (!this.dropdown.isOpen && this.props.searchOnInputClick) {
            const useInput = this.inputRef.el.value.trim() !== this.props.value.trim();
            const request = useInput ? this.inputRef.el.value.trim() : "";
            this.sourceLoader.load(request);
            this.open();
        } else {
            this.close();
        }
    }

    onInputFocus(ev) {
        this.inputRef.el.setSelectionRange(0, this.inputRef.el.value.length);
        this.props.onFocus(ev);
    }

    onInputChange(ev) {
        if (this.ignoreBlur) {
            ev.stopImmediatePropagation();
        }
        this.props.onChange({
            inputValue: this.inputRef.el.value,
        });
    }

    onInput() {
        this.inEdition = true;
        this.sourceLoader.isLoading = true;
        this.debounceLoad();
    }

    async ensureOptionsLoaded() {
        this.render();
        await new Promise((resolve) => requestAnimationFrame(resolve));
    }

    /**
     * @param {KeyboardEvent} event
     */
    async onKeydown(event) {
        const hotkey = getActiveHotkey(event);
        if (hotkey === "enter") {
            if (this.sourceLoader.isLoading || this.dropdown.isOpen) {
                event.stopPropagation();
                event.preventDefault();
                await this.sourceLoader.waitUntilLoaded();
                this.navigator?.activeItem?.select();
            } else {
                this.close();
            }
        }
    }

    getNavigationOptions() {
        const onArrow = () => {
            if (!this.dropdown.isOpen) {
                this.sourceLoader.load(this.inputRef.el.value.trim());
                this.open();
            } else {
                this.didNavigate = true;
            }
        };

        return {
            virtualFocus: true,
            isActive: (navigator, target) => target === this.inputRef.el,
            getItems: () => {
                const items = [];
                if (this.inputRef.el) {
                    items.push(this.inputRef.el);
                }
                if (this.dropdown.isOpen && this.menuRef.el) {
                    items.push(
                        ...this.menuRef.el.querySelectorAll(
                            ":scope .o-autocomplete--dropdown-item.o-navigable"
                        )
                    );
                }
                return items;
            },
            onUpdated: (navigator) => {
                this.navigator = navigator;
            },
            onNavigate: (item) => {
                this.state.activeElId = item?.el.id ?? "";
                this.navigationRev += 1;
            },
            hotkeys: {
                arrowup: {
                    callback: async (navigator) => {
                        onArrow();
                        if (this.dropdown.isOpen) {
                            navigator.previous();
                        }
                    },
                },
                arrowdown: {
                    callback: async (navigator) => {
                        onArrow();
                        if (this.dropdown.isOpen) {
                            navigator.next();
                        }
                    },
                },
                tab: {
                    callback: async (navigator) => {
                        if (this.sourceLoader.isLoading) {
                            await this.sourceLoader.waitUntilLoaded();
                            await this.ensureOptionsLoaded();
                        }
                        if (
                            this.props.autoSelect &&
                            this.dropdown.isOpen &&
                            (this.didNavigate || this.inputRef.el.value.length > 0)
                        ) {
                            if (navigator.activeItem && navigator.activeItem.el.isConnected) {
                                navigator.activeItem.select();
                            } else {
                                const option = getFirstSelectable(this.sources);
                                if (option) {
                                    this.selectOption(option);
                                }
                            }
                        }
                        this.close();
                    },
                },
                "shift+tab": {
                    callback: () => this.close(),
                },
                enter: {
                    callback: () => {},
                },
                escape: () => {
                    this.close();
                    this.cancel();
                },
            },
        };
    }

    onOpened() {
        if (this.navigator) {
            this.navigator.items[1]?.setActive();
        }
    }

    onOptionClick(option) {
        this.selectOption(option);
        this.inputRef.el.focus();
    }

    externalClose(event) {
        if (
            !this.root.el.contains(event.target) &&
            (!this.menuRef.el || !this.menuRef.el.contains(event.target))
        ) {
            this.cancel();
            this.close();
        }
    }
}
