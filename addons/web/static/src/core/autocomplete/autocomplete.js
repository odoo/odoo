import { onWillRender, useRef } from "@web/owl2/utils";
import { useAutofocus, useForwardRefToParent, useService } from "@web/core/utils/hooks";
import { isScrollableY, scrollTo } from "@web/core/utils/scrolling";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position/position_hook";
import { Component, onWillUpdateProps, props, proxy, t, useListener } from "@odoo/owl";
import { mergeClasses } from "@web/core/utils/classname";

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
    autocomplete: t.string().optional("new-password"),
    autoSelect: t.boolean().optional(false),
    resetOnSelect: t.boolean().optional(),
    onInput: t.function().optional(() => () => {}),
    onCancel: t.function().optional(() => () => {}),
    onChange: t.function().optional(() => () => {}),
    onBlur: t.function().optional(() => () => {}),
    onFocus: t.function().optional(() => () => {}),
    searchOnInputClick: t.boolean().optional(true),
    input: t.function().optional(),
    inputDebounceDelay: t.number().optional(250),
    dropdown: t.boolean().optional(true),
    autofocus: t.boolean().optional(),
    class: t.string().optional(),
    slots: t.object().optional(),
    menuPositionOptions: t.object().optional({}),
    menuCssClass: t.or([t.string(), t.array(), t.object()]).optional({}),
    selectOnBlur: t.boolean().optional(),
};

export class AutoComplete extends Component {
    static template = "web.AutoComplete";
    props = props(autoCompleteProps);

    get timeout() {
        return this.props.inputDebounceDelay;
    }

    setup() {
        this.nextSourceId = 0;
        this.nextOptionId = 0;
        this.sources = [];
        this.inEdition = false;
        this.mouseSelectionActive = false;
        this.isOptionSelected = false;

        this.state = proxy({
            navigationRev: 0,
            optionsRev: 0,
            open: false,
            activeSourceOption: null,
            value: this.props.value,
        });
        onWillRender(() => {
            // FIXME : We should read every part of the state
            // to actually subscribe the component
            // this is roughly equivalent to what owl2 did
            [...Object.entries(this.state)];
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
            } catch (e) {
                currentPromise.reject(e);
            } finally {
                if (currentPromise === this.loadingPromise) {
                    this.loadingPromise = null;
                }
            }
        }, this.timeout);

        useListener(window, "scroll", this.externalClose.bind(this), true);
        useListener(window, "pointerdown", this.externalClose.bind(this), true);
        useListener(window, "mousemove", () => (this.mouseSelectionActive = true), true);

        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value || this.forceValFromProp) {
                this.forceValFromProp = false;
                if (!this.inEdition) {
                    this.state.value = nextProps.value;
                    this.inputRef.el.value = nextProps.value;
                }
            }
        });

        // position and size
        if (this.props.dropdown) {
            usePosition("sourcesList", () => this.targetDropdown, this.dropdownOptions);
        } else {
            this.open(false);
        }
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
            onPositioned: (popperEl, solution) => {
                if (["bottom", "top"].includes(solution.direction)) {
                    popperEl.style.width = getComputedStyle(this.targetDropdown).width;
                }
            },
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
        this.navigate(0);
        this.scroll();
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
        this.isOptionSelected = true;
        this.forceValFromProp = true;
        option.onSelect();
        this.close();
    }

    navigate(direction) {
        const step = Math.sign(direction);
        if (step) {
            this.state.navigationRev++;
        }

        const navigableOptions = [];
        for (let sourceIndex = 0; sourceIndex < this.sources.length; sourceIndex++) {
            const source = this.sources[sourceIndex];
            if (source.isLoading) {
                continue;
            }

            for (let optionIndex = 0; optionIndex < source.options.length; optionIndex++) {
                if (!source.options[optionIndex].unselectable) {
                    navigableOptions.push([sourceIndex, optionIndex]);
                }
            }
        }

        if (!navigableOptions.length) {
            this.state.activeSourceOption = null;
            return;
        }

        const defaultSourceOption =
            step < 0 ? navigableOptions[navigableOptions.length - 1] : navigableOptions[0];

        if (!step || !this.state.activeSourceOption) {
            this.state.activeSourceOption = defaultSourceOption;
            return;
        }

        const [currentSourceIndex, currentOptionIndex] = this.state.activeSourceOption;
        const currentIndex = navigableOptions.findIndex(
            ([sI, oI]) => sI === currentSourceIndex && oI === currentOptionIndex
        );

        if (currentIndex === -1) {
            this.state.activeSourceOption = defaultSourceOption;
            return;
        }

        let nextIndex = currentIndex + step;

        if (nextIndex < 0) {
            nextIndex = navigableOptions.length - 1;
        } else if (nextIndex >= navigableOptions.length) {
            nextIndex = 0;
        }

        this.state.activeSourceOption = navigableOptions[nextIndex];
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
                this.state.activeSourceOption = firstOption.unselectable ? null : [0, 0];
                this.selectOption(this.activeOption);
            }
        }
        this.props.onBlur({
            inputValue: this.inputRef.el.value,
        });
        this.inEdition = false;
        this.isOptionSelected = false;
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
            case "shift+tab":
                if (!this.isOpened || !this.state.activeSourceOption) {
                    return;
                }
                this.selectOption(this.activeOption);
                break;
            case "escape":
                if (!this.isOpened) {
                    return;
                }
                this.cancel();
                break;
            case "arrowup":
                this.navigate(-1);
                if (!this.isOpened) {
                    this.open(true);
                }
                this.scroll();
                break;
            case "arrowdown":
                this.navigate(+1);
                if (!this.isOpened) {
                    this.open(true);
                }
                this.scroll();
                break;
            case "arrowleft":
            case "arrowright":
                if (!this.isOpened || this.inputRef.el.value.length) {
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

    onOptionMouseEnter(indices) {
        if (!this.mouseSelectionActive) {
            return;
        }

        const [sourceIndex, optionIndex] = indices;
        if (this.sources[sourceIndex].options[optionIndex]?.unselectable) {
            this.state.activeSourceOption = null;
        } else {
            this.state.activeSourceOption = indices;
        }
    }
    onOptionMouseLeave() {
        this.state.activeSourceOption = null;
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
            const element = this.listRef.el.querySelector(`#${this.activeSourceOptionId}`);
            if (element) {
                scrollTo(element);
            }
        }
    }
}
