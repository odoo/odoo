/** @odoo-module **/

import { Deferred } from "@web/core/utils/concurrency";
import { useForwardRefToParent, useService } from "@web/core/utils/hooks";
import { useDebounced } from "@web/core/utils/timing";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { usePosition } from "@web/core/position_hook";

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";

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

        this.inputRef = useForwardRefToParent("input");
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
        }, this.constructor.timeout);

        useExternalListener(window, "scroll", this.externalClose, true);
        useExternalListener(window, "pointerdown", this.externalClose, true);

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

    get hasOptions() {
        for (const source of this.sources) {
            if (source.isLoading || source.options.length) {
                return true;
            }
        }
        return false;
    }

    open(useInput = false) {
        this.state.open = true;
        return this.loadSources(useInput);
    }

    close() {
        this.state.open = false;
        this.state.activeSourceOption = null;
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

        if (this.props.resetOnSelect) {
            this.inputRef.el.value = "";
        }

        this.forceValFromProp = true;
        this.props.onSelect(option, {
            ...params,
            input: this.inputRef.el,
        });
        const customEvent = new CustomEvent("AutoComplete:OPTION_SELECTED", { bubbles: true });
        this.root.el.dispatchEvent(customEvent);
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
                if (optionIndex < source.options.length) {
                    this.state.activeSourceOption = [sourceIndex, optionIndex];
                }
            }
        }
    }

    onInputBlur() {
        if (this.ignoreBlur) {
            this.ignoreBlur = false;
            return;
        }
        this.props.onBlur({
            inputValue: this.inputRef.el.value,
        });
    }
    onInputClick() {
        if (!this.isOpened) {
            this.open(this.inputRef.el.value.trim() !== this.props.value);
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
        this.pendingPromise = this.pendingPromise || new Deferred();
        this.loadingPromise = this.pendingPromise;
        this.debouncedProcessInput();
    }

    async onInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        const isSelectKey = hotkey === "enter" || hotkey === "tab";

        if (this.loadingPromise && isSelectKey) {
            if (hotkey === "enter") {
                ev.stopPropagation();
                ev.preventDefault();
            }

            await this.loadingPromise;
        }

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
                this.cancel();
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
        this.inputRef.el.focus();
    }

    externalClose(ev) {
        if (this.isOpened && !this.root.el.contains(ev.target)) {
            this.cancel();
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
        resetOnSelect: { type: Boolean, optional: true },
        onCancel: { type: Function, optional: true },
        onInput: { type: Function, optional: true },
        onChange: { type: Function, optional: true },
        onBlur: { type: Function, optional: true },
        input: { type: Function, optional: true },
    },
    defaultProps: {
        placeholder: "",
        autoSelect: false,
        onCancel: () => {},
        onInput: () => {},
        onChange: () => {},
        onBlur: () => {},
    },
    timeout: 250,
});
