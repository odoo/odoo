/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position_hook";

const { Component, useExternalListener, useRef, useState } = owl;

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
            value: this.props.value,
        });

        this.inputRef = useRef("input");
        this.root = useRef("root");
        this.debouncedOnInput = useDebounced(this.onInput, this.constructor.timeout);
        useExternalListener(window, "scroll", this.onWindowScroll, true);

        this.hotkey = useService("hotkey");
        this.hotkeysToRemove = [];

        owl.onWillUpdateProps((nextProps) => {
            if (this.props.value !== nextProps.value || this.forceValFromProp) {
                this.forceValFromProp = false;
                this.state.value = nextProps.value;
                this.inputRef.el.value = nextProps.value;
                this.close();
            }
        });

        // position and size
        usePosition(() => this.inputRef.el, {
            popper: "sourcesList",
            position: "bottom-start",
        });
    }

    get isOpened() {
        return this.state.open;
    }

    open(useInput = false) {
        this.state.open = true;
        this.loadSources(useInput);
    }

    close() {
        this.state.open = false;
        this.state.activeSourceOption = null;
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
        const option = this.sources[indices[0]].options[indices[1]];
        if (option.unselectable) {
            this.inputRef.el.value = "";
            this.close();
            return;
        }

        this.forceValFromProp = true;
        this.props.onSelect(option, {
            ...params,
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

    onInputBlur() {
        const value = this.inputRef.el.value;
        if (
            this.props.autoSelect &&
            this.state.activeSourceOption &&
            value.length > 0 &&
            value !== this.props.value
        ) {
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

    onInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        switch (hotkey) {
            case "enter":
                if (!this.isOpened || !this.state.activeSourceOption) {
                    return;
                }
                this.selectOption(this.state.activeSourceOption);
                break;
            case "escape":
                if (!this.isOpened) {
                    return;
                }
                this.close();
                break;
            case "tab":
                if (!this.isOpened) {
                    return;
                }
                if (
                    this.props.autoSelect &&
                    this.state.activeSourceOption &&
                    (this.state.navigationRev > 0 || this.inputRef.el.value.length > 0)
                ) {
                    this.selectOption(this.state.activeSourceOption);
                }
                this.close();
                return;
            case "arrowup":
                this.navigate(-1);
                if (!this.isOpened) {
                    this.open(true);
                }
                break;
            case "arrowdown":
                this.navigate(+1);
                if (!this.isOpened) {
                    this.open(true);
                }
                break;
            default:
                return;
        }

        ev.stopPropagation();
        ev.preventDefault();
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
