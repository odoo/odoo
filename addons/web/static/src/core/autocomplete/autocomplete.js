import { Deferred } from "@web/core/utils/concurrency";
import { useAutofocus, useForwardRefToParent, useService } from "@web/core/utils/hooks";
import { isScrollableY, scrollTo } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { usePosition } from "@web/core/position/position_hook";
import {
    Component,
    onWillUpdateProps,
    useEffect,
    useExternalListener,
    useRef,
    useState,
} from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";
import { mergeClasses } from "@web/core/utils/classname";

export class AutoComplete extends Component {
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
        input: { type: Function, optional: true },
        inputDebounceDelay: { type: Number, optional: true },
        dropdown: { type: Boolean, optional: true },
        autofocus: { type: Boolean, optional: true },
        class: { type: String, optional: true },
        slots: { type: Object, optional: true },
        menuPositionOptions: { type: Object, optional: true },
        menuCssClass: { type: [String, Array, Object], optional: true },
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
        menuPositionOptions: {},
        menuCssClass: {},
    };

    get timeout() {
        return this.props.inputDebounceDelay;
    }

    setup() {
        this.nextSourceId = 0;
        this.nextOptionId = 0;
        this.sources = [];
        this.inEdition = false;
        this.mouseSelectionActive = false;

        this.state = useState({
            navigationRev: 0,
            optionsRev: 0,
            open: false,
            activeSourceOption: null,
            value: this.props.value,
        });

        this.inputRef = useForwardRefToParent("input");
        this.listRef = useRef("sourcesList");
        if (this.props.autofocus) {
            useAutofocus({ refName: "input" });
        }
        this.root = useRef("root");

        this.debouncedProcessInput = useDebounced(async () => {
            const currentPromise = this.pendingPromise;
            this.pendingPromise = null;
            this.props.onInput({
                inputValue: this.inputRef.el.value,
            });
            try {
                await this.open(true);
                currentPromise.resolve();
            } catch {
                currentPromise.reject();
            } finally {
                if (currentPromise === this.loadingPromise) {
                    this.loadingPromise = null;
                }
            }
        }, this.timeout);

        useExternalListener(window, "scroll", this.externalClose, true);
        useExternalListener(window, "pointerdown", this.externalClose, true);
        useExternalListener(window, "mousemove", () => (this.mouseSelectionActive = true), true);

        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value || this.forceValFromProp) {
                this.forceValFromProp = false;
                if (!this.inEdition) {
                    this.state.value = nextProps.value;
                    this.inputRef.el.value = nextProps.value;
                }
                this.close();
            }
        });

        // position and size
        if (this.props.dropdown) {
            usePosition("sourcesList", () => this.targetDropdown, this.dropdownOptions);
        } else {
            this.open(false);
        }

        this.setupNavigation();
    }

    get targetDropdown() {
        return this.inputRef.el;
    }

    get activeSourceOptionId() {
        if (!this.isOpened || !this.state.activeSourceOption) {
            return undefined;
        }
        const [sourceIndex, optionIndex] = this.state.activeSourceOption;
        const source = this.sources[sourceIndex];
        return `${this.props.id || "autocomplete"}_${sourceIndex}_${
            source.isLoading ? "loading" : optionIndex
        }`;
    }

    get dropdownOptions() {
        return {
            position: "bottom-start",
            ...this.props.menuPositionOptions,
        };
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

    get activeOption() {
        if (!this.state.activeSourceOption) {
            return null;
        }
        const [sourceIndex, optionIndex] = this.state.activeSourceOption;
        return this.sources[sourceIndex].options[optionIndex];
    }

    open(useInput = false) {
        this.state.open = true;
        return this.loadSources(useInput);
    }

    close() {
        this.state.open = false;
        this.state.activeSourceOption = null;
        this.mouseSelectionActive = false;
    }

    cancel() {
        if (this.inputRef.el.value.length) {
            if (this.props.autoSelect) {
                this.inputRef.el.value = this.props.value;
                this.props.onCancel();
            }
        }
        this.close();
    }

    async loadSources(useInput) {
        this.sources = [];
        this.state.activeSourceOption = null;
        const proms = [];
        for (const pSource of this.props.sources) {
            const source = this.makeSource(pSource);
            this.sources.push(source);

            const options = this.loadOptions(
                pSource.options,
                useInput ? this.inputRef.el.value.trim() : ""
            );
            if (options instanceof Promise) {
                source.isLoading = true;
                const prom = options.then((options) => {
                    source.options = options.map((option) => this.makeOption(option));
                    source.isLoading = false;
                    this.state.optionsRev++;
                });
                proms.push(prom);
            } else {
                source.options = options.map((option) => this.makeOption(option));
            }
        }

        await Promise.all(proms);
        this.navigator.update();

        for (let i = 0; i < this.sources.length; i++) {
            const options = this.sources[i].options;
            for (let j = 0; j < options.length; j++) {
                this.state.activeSourceOption = [i, j];
                return;
            }
        }
    }
    get displayOptions() {
        return !this.props.dropdown || (this.isOpened && this.hasOptions);
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
        return {
            id: ++this.nextSourceId,
            options: [],
            isLoading: false,
            placeholder: source.placeholder,
            optionSlot: source.optionSlot,
        };
    }

    isActiveSourceOption([sourceIndex, optionIndex]) {
        return (
            this.state.activeSourceOption &&
            this.state.activeSourceOption[0] === sourceIndex &&
            this.state.activeSourceOption[1] === optionIndex
        );
    }

    selectOption(option) {
        this.inEdition = false;
        if (option.unselectable) {
            return;
        }

        if (this.props.resetOnSelect) {
            this.inputRef.el.value = "";
        }

        this.forceValFromProp = true;
        option.onSelect();
        this.close();
    }

    setupNavigation() {
        const onArrow = (navigator, action) => {
            this.state.navigationRev++;
            if (this.isOpened) {
                navigator[action]();
            } else {
                this.open(true);
            }
        };

        const onTab = async (navigator, event) => {
            if (this.loadingPromise) {
                await this.loadingPromise;
            }

            if (!this.isOpened) {
                return;
            }

            if (
                this.props.autoSelect &&
                this.activeOption &&
                (this.state.navigationRev > 0 || this.inputRef.el.value.length > 0)
            ) {
                this.selectOption(this.activeOption);
            }
            this.close();
        };

        this.navigator = useNavigation(this.listRef, {
            virtualFocus: true,
            activeClass: "ui-state-active",
            getItems: () => {
                const items = [];
                if (this.inputRef.el) {
                    items.push(this.inputRef.el);
                }
                if (this.listRef.el) {
                    items.push(
                        ...this.listRef.el.querySelectorAll(
                            ":scope .o-autocomplete--dropdown-item a[role=option]"
                        )
                    );
                }
                return items;
            },
            /**
             * @param {import("@web/core/navigation/navigation").Navigator} navigator
             */
            onNavigated: (navigator) => {
                const el = navigator.activeItem && navigator.activeItem.el;
                if (el && el.hasAttributes("data-source") && el.hasAttribute("data-option")) {
                    this.state.activeSourceOption = [
                        parseInt(el.dataset.source),
                        parseInt(el.dataset.option),
                    ];
                    // this.inputRef.el.setAttribute(
                    //     "aria-activedescendant",
                    //     this.activeSourceOptionId
                    // );
                } else {
                    this.state.activeSourceOption = null;
                    // this.inputRef.el.removeAttribute("aria-activedescendant");
                }
            },
            hotkeys: {
                arrowup: {
                    callback: (navigator) => onArrow(navigator, "previous"),
                },
                arrowdown: {
                    callback: (navigator) => onArrow(navigator, "next"),
                },
                escape: {
                    isAvailable: () => this.isOpened,
                    callback: () => this.cancel(),
                },
                "shift+tab": {
                    isAvailable: () => true,
                    callback: onTab,
                },
                tab: {
                    isAvailable: () => true,
                    prevent: false,
                    callback: onTab,
                },
                enter: {
                    isAvailable: () => true,
                    prevent: false,
                    callback: async (navigator, event) => {
                        if (this.loadingPromise) {
                            event.stopPropagation();
                            event.preventDefault();
                            await this.loadingPromise;
                        }

                        if (!this.isOpened) {
                            return;
                        }

                        if (this.activeOption) {
                            this.selectOption(this.activeOption);
                            event.stopPropagation();
                            event.preventDefault();
                        }
                    },
                },
            },
        });

        useEffect(
            (listEl) => {
                if (listEl) {
                    this.navigator?.items[1]?.setActive();
                }
            },
            () => [this.listRef.el]
        );
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
        if (!this.isOpened && this.props.searchOnInputClick) {
            this.open(this.inputRef.el.value.trim() !== this.props.value.trim());
        } else {
            this.close();
        }
    }
    onInputChange(ev) {
        if (this.ignoreBlur) {
            ev.stopImmediatePropagation();
        }
        this.props.onChange({
            inputValue: this.inputRef.el.value,
        });
    }
    async onInput() {
        this.inEdition = true;
        this.pendingPromise = this.pendingPromise || new Deferred();
        this.loadingPromise = this.pendingPromise;
        this.debouncedProcessInput();
    }

    onInputFocus(ev) {
        this.inputRef.el.setSelectionRange(0, this.inputRef.el.value.length);
        this.props.onFocus(ev);
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

    get ulDropdownClass() {
        return mergeClasses(this.props.menuCssClass, {
            "dropdown-menu ui-autocomplete": this.props.dropdown,
            "list-group": !this.props.dropdown,
        });
    }

    onOptionClick(option) {
        this.selectOption(option);
        this.inputRef.el.focus();
    }
    onOptionPointerDown(option, ev) {
        this.ignoreBlur = true;
        if (option.unselectable) {
            ev.preventDefault();
        }
    }

    externalClose(ev) {
        if (this.isOpened && !this.root.el.contains(ev.target)) {
            this.cancel();
        }
    }

    scroll() {
        if (!this.activeSourceOptionId) {
            return;
        }
        if (isScrollableY(this.listRef.el)) {
            scrollTo(this.listRef.el.querySelector(`#${this.activeSourceOptionId}`));
        }
    }

    onMouseLeave() {
        this.state.activeSourceOption = null;
        this.navigator?.activeItem?.setInactive();
    }
}
