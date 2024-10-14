import { Deferred } from "@web/core/utils/concurrency";
import { useAutofocus, useChildRef, useForwardRefToParent } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Component, onWillUpdateProps, useExternalListener, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { useSourceLoader } from "@web/core/autocomplete/autocomplete_utils";

/**
 * @typedef Source
 * @param {bool} isLoading
 * @param {string} placeholder
 * @param {string} optionTemplate
 * @param {Array<Option>} options
 */

/**
 * @typedef Option
 * @param {number} id
 * @param {string} label
 * @param {string} classList
 */

function getIndices(optionEl) {
    if (optionEl) {
        const sourceIndex = parseInt(optionEl.dataset.source);
        const optionIndex = parseInt(optionEl.dataset.option);
        return [sourceIndex, optionIndex];
    } else {
        return [-1, -1];
    }
}

export class AutoComplete extends Component {
    static components = { Dropdown, DropdownItem };
    static template = "web.AutoComplete";
    static props = {
        value: { type: String, optional: true },
        id: { type: String, optional: true },
        onSelect: { type: Function },
        sources: {
            type: Array,
            element: {
                type: Object,
                shape: {
                    placeholder: { type: String, optional: true },
                    optionTemplate: { type: String, optional: true },
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
        input: { type: Function, optional: true },
        inputDebounceDelay: { type: Number, optional: true },
        dropdown: { type: Boolean, optional: true },
        autofocus: { type: Boolean, optional: true },
        class: { type: String, optional: true },
        slots: { type: Object, optional: true },
        menuClass: { type: String, optional: true },
    };
    static defaultProps = {
        value: "",
        placeholder: "",
        autocomplete: "new-password",
        autoSelect: false,
        dropdown: true,
        onInput: () => { },
        onCancel: () => { },
        onChange: () => { },
        onBlur: () => { },
        onFocus: () => { },
        searchOnInputClick: true,
        inputDebounceDelay: 250,
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

        this.state = useState({
            optionsRev: 0,
            value: this.props.value,
            activeIndices: [-1, -1],
        });

        onWillUpdateProps((nextProps) => this.updateProps(nextProps));

        if (this.props.autofocus) {
            useAutofocus({ refName: "input" });
        }

        useExternalListener(window, "scroll", this.externalClose, true);
        useExternalListener(window, "pointerdown", this.externalClose, true);

        this.sourceLoader = useSourceLoader({
            sources: this.props.sources,
            inputRef: this.inputRef,
            timeout: this.timeout,
            onSourcesLoaded: () => {
                if (!this.sourceLoader.hasOptions) {
                    this.dropdown.close();
                }
            },
            onProcessInput: () => {
                this.props.onInput({
                    inputValue: this.inputRef.el.value,
                })
                this.open();
            },
        });
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

    get navigationOptions() {
        return {
            virtualFocus: true,
            onEnabled: (navigator) => {
                this.navigator = navigator;
                this.navigator.items[0]?.setActive(true);
            },
            onNavigate: (item) => {
                this.state.activeIndices = getIndices(this.navigator?.activeItem?.el);
            },
            hotkeys: {
                // Remove dropdown default navigation
                tab: { callback: () => {} },
                "shift+tab": { callback: () => {} },
                enter: { callback: () => {} },
                escape: async () => {
                    this.close();
                    this.cancel();
                },
            },
        };
    }

    get sources() {
        return this.sourceLoader.sources;
    }

    get dropdownClass() {
        let classList = "o-autocomplete--dropdown-menu ui-widget show mt-0";
        if (this.props.dropdown) {
            classList += " dropdown-menu ui-autocomplete";
        } else {
            classList += " list-group";
        }
        if (this.props.menuClass) {
            classList += " " + this.props.menuClass;
        }
        return classList;
    }

    get activeOption() {
        const [sourceIndex, optionIndex] = this.state.activeIndices;
        return this.sources[sourceIndex]?.options[optionIndex] ?? null;
    }

    getOptionId(sourceIndex, optionIndex = "loading") {
        return `${this.props.id || 'autocomplete'}_${sourceIndex}_${optionIndex}`;
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

    selectOption(option, params = {}) {
        this.inEdition = false;

        if (this.props.resetOnSelect) {
            this.inputRef.el.value = "";
        }

        this.forceValFromProp = true;
        this.props.onSelect(option, {
            ...params,
            input: this.inputRef.el,
        });
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
            this.sourceLoader.load(this.inputRef.el.value.trim() !== this.props.value.trim());
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
        this.sourceLoader.processInput();
    }

    /**
     * @param {KeyboardEvent} ev
     */
    async onInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);

        const isSelectKey = hotkey === "enter" || hotkey === "tab";
        if (this.sourceLoader.isLoading && isSelectKey) {
            if (hotkey === "enter") {
                ev.stopPropagation();
                ev.preventDefault();
            }
            await this.sourceLoader.waitUntilLoaded();
        }

        if (["arrowup", "arrowdown"].includes(hotkey)) {
            if (!this.dropdown.isOpen) {
                this.sourceLoader.load(true);
                this.open();
            } else {
                this.didNavigate = true;
            }
        }

        const activeOption = this.activeOption || this.sources[0]?.options[0];
        if (hotkey === "tab" || hotkey === "shift+tab") {
            if (
                this.props.autoSelect &&
                activeOption &&
                (this.didNavigate || this.inputRef.el.value.length > 0)
            ) {
                this.selectOption(activeOption);
            }
            this.close();
        } else if (this.dropdown.isOpen && hotkey === "enter" && activeOption) {
            ev.stopPropagation();
            ev.preventDefault();
            this.selectOption(activeOption);
        }
    }

    onOptionClick(option) {
        this.selectOption(option);
        this.inputRef.el.focus();
    }

    externalClose(event) {
        if (!this.root.el.contains(event.target) && (!this.menuRef.el || !this.menuRef.el.contains(event.target))) {
            this.cancel();
            this.close();
        }
    }
}
