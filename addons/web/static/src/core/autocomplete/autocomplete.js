/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { debounce } from "@web/core/utils/timing";
import { usePosition } from "@web/core/position_hook";
import { useHotkey } from "../hotkeys/hotkey_hook";

const { Component, onWillUnmount, useExternalListener, useRef, useState, useEffect } = owl;

export class AutoComplete extends Component {
    setup() {
        this.nextSourceId = 0;
        this.nextOptionId = 0;
        this.sources = [];

        this.state = useState({
            navigationRev: 0,
            optionsRev: 0,
            open: false,
            activeSourceOption: null,
        });

        this.inputRef = useRef("input");
        this.root = useRef("root");
        this.debouncedOnInput = debounce(this.onInput.bind(this), this.constructor.timeout);
        useExternalListener(window, "scroll", this.onWindowScroll, true);

        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        onWillUnmount(() => this.debouncedOnInput.cancel());

        // position and size
        const sourcesListRef = useRef("sourcesList");
        useEffect(
            () => {
                if (sourcesListRef.el) {
                    sourcesListRef.el.style.width =
                        this.inputRef.el.getBoundingClientRect().width + "px";
                }
            },
            () => [sourcesListRef.el]
        );
        usePosition(() => this.inputRef.el, {
            popper: "sourcesList",
        });
        useHotkey("ArrowUp", this.onArrowUpPress.bind(this), {
            area: () => this.inputRef.el,
            allowRepeat: true,
            bypassEditableProtection: true,
        });
        useHotkey("ArrowDown", this.onArrowDownPress.bind(this), {
            area: () => this.inputRef.el,
            allowRepeat: true,
            bypassEditableProtection: true,
        });
    }

    get isOpened() {
        return this.state.open;
    }

    open(useInput = false) {
        this.state.open = true;
        this.loadSources(useInput);
        this.registerOtherHotkeys();
    }

    close() {
        this.state.open = false;
        this.state.activeSourceOption = null;
        this.unregisterOtherHotkeys();
    }

    loadSources(useInput) {
        const sources = [];
        const proms = [];
        for (const pSource of this.props.sources) {
            const source = this.makeSource(pSource);
            sources.push(source);

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
        this.sources = sources;
        Promise.all(proms).then(() => {
            this.navigate(0);
        });
    }
    loadOptions(options, request) {
        if (typeof options === "function") {
            return options(request);
        } else {
            return options;
        }
    }
    makeOption(option) {
        return Object.assign(Object.create(option), {
            id: ++this.nextOptionId,
        });
    }
    makeSource(source) {
        return {
            id: ++this.nextSourceId,
            options: [],
            isLoading: false,
            placeholder: source.placeholder,
            optionTemplate: source.optionTemplate,
        };
    }

    isActiveSourceOption([sourceIndex, optionIndex]) {
        return (
            this.state.activeSourceOption &&
            this.state.activeSourceOption[0] === sourceIndex &&
            this.state.activeSourceOption[1] === optionIndex
        );
    }
    selectOption(indices, params = {}) {
        this.inputRef.el.value = "";

        const option = this.sources[indices[0]].options[indices[1]];
        if (option.unselectable) {
            return;
        }

        this.props.onSelect(option, {
            ...params,
            inputValue: this.inputRef.el.value.trim(),
            input: this.inputRef.el,
        });
        this.close();
    }

    navigate(direction) {
        let step = Math.sign(direction);
        if (!step) {
            this.state.activeSourceOption = null;
            step = 1;
        } else {
            this.state.navigationRev++;
        }

        if (this.state.activeSourceOption) {
            let [sourceIndex, optionIndex] = this.state.activeSourceOption;
            let source = this.sources[sourceIndex];

            optionIndex += step;
            if (0 > optionIndex || optionIndex >= source.options.length) {
                sourceIndex += step;
                source = this.sources[sourceIndex];

                while (source && source.isLoading) {
                    sourceIndex += step;
                    source = this.sources[sourceIndex];
                }

                if (source) {
                    optionIndex = step < 0 ? source.options.length - 1 : 0;
                }
            }

            this.state.activeSourceOption = source ? [sourceIndex, optionIndex] : null;
        } else {
            let sourceIndex = step < 0 ? this.sources.length - 1 : 0;
            let source = this.sources[sourceIndex];

            while (source && source.isLoading) {
                sourceIndex += step;
                source = this.sources[sourceIndex];
            }

            if (source) {
                const optionIndex = step < 0 ? source.options.length - 1 : 0;
                this.state.activeSourceOption = [sourceIndex, optionIndex];
            }
        }
    }

    registerOtherHotkeys() {
        // These other hotkeys should only get registered when the autocomplete is opened.
        const hotkeys = {
            escape: this.onEscapePress.bind(this),
            enter: this.onEnterPress.bind(this),
            tab: this.onTabPress.bind(this),
        };
        for (const [hotkey, callback] of Object.entries(hotkeys)) {
            const remove = this.hotkey.add(hotkey, callback, {
                area: () => this.inputRef.el,
                bypassEditableProtection: true,
            });
            this.hotkeysToRemove.push(remove);
        }
    }

    unregisterOtherHotkeys() {
        for (const removeHotkey of this.hotkeysToRemove) {
            removeHotkey();
        }
        this.hotkeysToRemove = [];
    }

    onInputBlur() {
        const value = this.inputRef.el.value;

        if (this.props.autoSelect && this.state.activeSourceOption && value.length > 0) {
            this.selectOption(this.state.activeSourceOption, { triggeredOnBlur: true });
        } else {
            this.props.onBlur({
                inputValue: value,
            });
            this.close();
        }
    }
    onInputClick() {
        if (!this.isOpened) {
            this.open(this.inputRef.el.value.trim() !== this.props.value);
        } else {
            this.close();
        }
    }
    onInputChange() {
        this.props.onChange({
            inputValue: this.inputRef.el.value,
        });
    }
    onInput() {
        this.props.onInput({
            inputValue: this.inputRef.el.value,
        });
        this.open(true);
    }

    onOptionMouseEnter(indices) {
        this.state.activeSourceOption = indices;
    }
    onOptionMouseLeave() {
        this.state.activeSourceOption = null;
    }
    onOptionClick(indices) {
        this.selectOption(indices);
    }

    onEscapePress() {
        this.close();
    }
    onEnterPress() {
        if (this.isOpened && this.state.activeSourceOption) {
            this.selectOption(this.state.activeSourceOption);
        }
    }
    onTabPress() {
        const value = this.inputRef.el.value;

        if (
            this.props.autoSelect &&
            this.state.activeSourceOption &&
            (this.state.navigationRev > 0 || value.length > 0)
        ) {
            this.selectOption(this.state.activeSourceOption);
        }
        this.close();
    }
    onArrowUpPress() {
        this.navigate(-1);
        if (!this.isOpened) {
            this.open(true);
        }
    }
    onArrowDownPress() {
        this.navigate(+1);
        if (!this.isOpened) {
            this.open(true);
        }
    }

    onWindowScroll(ev) {
        if (this.isOpened && !this.root.el.contains(ev.target)) {
            this.close();
        }
    }
}
Object.assign(AutoComplete, {
    template: "web.AutoComplete",
    props: {
        value: { type: String },
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
                },
            },
        },
        placeholder: { type: String, optional: true },
        autoSelect: { type: Boolean, optional: true },
        onInput: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
    },
    defaultProps: {
        placeholder: "",
        autoSelect: false,
        onInput: () => {},
        onChange: () => {},
        onBlur: () => {},
    },
    timeout: 250,
});
