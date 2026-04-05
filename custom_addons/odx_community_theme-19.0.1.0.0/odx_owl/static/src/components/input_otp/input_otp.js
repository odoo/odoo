/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

function compileMatcher(pattern, inputMode) {
    if (pattern) {
        return new RegExp(pattern);
    }
    if (inputMode === "numeric") {
        return /[0-9]/;
    }
    return /[A-Za-z0-9]/;
}

function normalizeChars(value, length, matcher) {
    const chars = Array.from({ length }, () => "");
    for (const char of String(value || "")) {
        if (!matcher.test(char)) {
            continue;
        }
        const nextIndex = chars.findIndex((entry) => !entry);
        if (nextIndex === -1) {
            break;
        }
        chars[nextIndex] = char;
    }
    return chars;
}

function stringFromChars(chars) {
    return chars.join("");
}

export class InputOTPGroup extends Component {
    static template = "odx_owl.InputOTPGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-input-otp__group", this.props.className);
    }
}

export class InputOTPSeparator extends Component {
    static template = "odx_owl.InputOTPSeparator";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-input-otp__separator", this.props.className);
    }
}

export class InputOTPSlot extends Component {
    static template = "odx_owl.InputOTPSlot";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        index: { type: Number },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "",
        className: "",
        disabled: false,
        placeholder: "",
    };

    get ariaLabel() {
        return (
            this.props.ariaLabel ||
            `One-time password character ${this.props.index + 1} of ${this.env.odxInputOTP.length}`
        );
    }

    get charValue() {
        return this.env.odxInputOTP.getChar(this.props.index);
    }

    get classes() {
        return cn(
            "odx-input-otp__slot",
            {
                "odx-input-otp__slot--active": this.isActive,
                "odx-input-otp__slot--filled": Boolean(this.charValue),
            },
            this.props.className
        );
    }

    get inputAttrs() {
        return this.env.odxInputOTP.getSlotAttrs(this.props.index);
    }

    get isActive() {
        return this.env.odxInputOTP.activeIndex === this.props.index;
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxInputOTP.disabled;
    }

    get placeholder() {
        return this.props.placeholder || this.env.odxInputOTP.placeholderChar;
    }

    get tabIndex() {
        return this.env.odxInputOTP.getTabIndex(this.props.index);
    }

    onClick() {
        this.env.odxInputOTP.setActiveIndex(this.props.index);
    }

    onFocus(ev) {
        this.env.odxInputOTP.setActiveIndex(this.props.index);
        ev.target.select?.();
    }

    onInput(ev) {
        this.env.odxInputOTP.handleInput(this.props.index, ev.target.value);
    }

    onKeydown(ev) {
        this.env.odxInputOTP.handleKeydown(this.props.index, ev);
    }

    onPaste(ev) {
        this.env.odxInputOTP.handlePaste(this.props.index, ev);
    }
}

export class InputOTP extends Component {
    static template = "odx_owl.InputOTP";
    static components = {
        InputOTPGroup,
        InputOTPSlot,
    };
    static props = {
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        containerClassName: { type: String, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        dir: { type: String, optional: true },
        inputMode: { type: String, optional: true },
        length: { type: Number, optional: true },
        name: { type: String, optional: true },
        onComplete: { type: Function, optional: true },
        onValueChange: { type: Function, optional: true },
        pattern: { type: String, optional: true },
        placeholderChar: { type: String, optional: true },
        required: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        ariaLabel: "One-time password",
        attrs: {},
        className: "",
        containerClassName: "",
        disabled: false,
        inputMode: "numeric",
        length: 6,
        placeholderChar: "",
        required: false,
    };

    setup() {
        const self = this;
        this.state = useState({
            activeIndex: 0,
            baseId: nextId("odx-input-otp"),
            value: "",
        });
        this.state.value = stringFromChars(this.currentChars);

        useChildSubEnv({
            odxInputOTP: {
                get activeIndex() {
                    return self.state.activeIndex;
                },
                get disabled() {
                    return self.isDisabled;
                },
                get dir() {
                    return self.direction;
                },
                get length() {
                    return self.props.length;
                },
                get placeholderChar() {
                    return self.props.placeholderChar;
                },
                getChar(index) {
                    return self.currentChars[index] || "";
                },
                getSlotAttrs(index) {
                    return self.getSlotAttrs(index);
                },
                getTabIndex(index) {
                    return self.getTabIndex(index);
                },
                handleInput(index, text) {
                    self.handleInput(index, text);
                },
                handleKeydown(index, ev) {
                    self.handleKeydown(index, ev);
                },
                handlePaste(index, ev) {
                    self.handlePaste(index, ev);
                },
                setActiveIndex(index) {
                    self.setActiveIndex(index);
                },
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.value !== undefined) {
                const nextChars = normalizeChars(
                    nextProps.value,
                    nextProps.length ?? this.props.length,
                    compileMatcher(nextProps.pattern, nextProps.inputMode ?? this.props.inputMode)
                );
                this.state.value = stringFromChars(nextChars);
                if (!nextChars[this.state.activeIndex]) {
                    this.state.activeIndex = Math.min(
                        nextChars.findIndex((char) => !char) === -1
                            ? (nextProps.length ?? this.props.length) - 1
                            : nextChars.findIndex((char) => !char),
                        (nextProps.length ?? this.props.length) - 1
                    );
                }
            }
        });
    }

    get classes() {
        return cn("odx-input-otp", this.props.className);
    }

    get containerClasses() {
        return cn("odx-input-otp__container", this.props.containerClassName);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get currentChars() {
        return normalizeChars(
            this.props.value ?? this.state.value,
            this.props.length,
            compileMatcher(this.props.pattern, this.props.inputMode)
        );
    }

    get currentValue() {
        return stringFromChars(this.currentChars);
    }

    get hasCustomSlots() {
        return Boolean(this.props.slots && this.props.slots.default);
    }

    get hiddenInputName() {
        return this.props.name || this.props.attrs.name;
    }

    get isComplete() {
        return this.currentChars.every(Boolean);
    }

    get isDisabled() {
        return this.props.disabled || Boolean(this.props.attrs.disabled);
    }

    get slotIndexes() {
        return Array.from({ length: this.props.length }, (_, index) => index);
    }

    commitChars(chars, focusIndex = null) {
        const nextValue = stringFromChars(chars);
        if (this.props.value === undefined) {
            this.state.value = nextValue;
        }
        const nextActiveIndex = focusIndex ?? Math.min(
            chars.findIndex((char) => !char) === -1
                ? this.props.length - 1
                : chars.findIndex((char) => !char),
            this.props.length - 1
        );
        this.state.activeIndex = nextActiveIndex;
        this.props.onValueChange?.(nextValue);
        if (chars.every(Boolean)) {
            this.props.onComplete?.(nextValue);
        }
        this.focusSlot(nextActiveIndex);
    }

    filterChars(text) {
        const matcher = compileMatcher(this.props.pattern, this.props.inputMode);
        return Array.from(String(text || "")).filter((char) => matcher.test(char));
    }

    focusSlot(index) {
        browser.requestAnimationFrame(() => {
            const target = document.querySelector(
                `[data-odx-input-otp-root="${this.state.baseId}"] [data-odx-input-otp-slot="${index}"]`
            );
            target?.focus();
            target?.select?.();
        });
    }

    getSlotAttrs(index) {
        return {
            "aria-describedby": this.props.attrs["aria-describedby"],
            "aria-invalid": this.props.attrs["aria-invalid"],
            autocomplete: index === 0 ? "one-time-code" : undefined,
            inputmode: this.props.inputMode,
            pattern: this.props.pattern,
            required: this.props.required || this.props.attrs.required ? true : undefined,
        };
    }

    getTabIndex(index) {
        return this.state.activeIndex === index ? 0 : -1;
    }

    handleInput(index, text) {
        const chars = this.filterChars(text);
        if (!chars.length) {
            const nextChars = [...this.currentChars];
            nextChars[index] = "";
            this.commitChars(nextChars, index);
            return;
        }
        const nextChars = [...this.currentChars];
        let cursor = index;
        for (const char of chars) {
            if (cursor >= this.props.length) {
                break;
            }
            nextChars[cursor] = char;
            cursor += 1;
        }
        this.commitChars(nextChars, Math.min(cursor, this.props.length - 1));
    }

    handleKeydown(index, ev) {
        if (this.isDisabled) {
            return;
        }
        const currentChars = [...this.currentChars];
        const isRtl = isRtlDirection(this.direction);
        if (ev.key === "ArrowLeft") {
            ev.preventDefault();
            this.setActiveIndex(
                Math.min(Math.max(index + (isRtl ? 1 : -1), 0), this.props.length - 1),
                true
            );
            return;
        }
        if (ev.key === "ArrowRight") {
            ev.preventDefault();
            this.setActiveIndex(
                Math.max(Math.min(index + (isRtl ? -1 : 1), this.props.length - 1), 0),
                true
            );
            return;
        }
        if (ev.key === "Home") {
            ev.preventDefault();
            this.setActiveIndex(0, true);
            return;
        }
        if (ev.key === "End") {
            ev.preventDefault();
            this.setActiveIndex(this.props.length - 1, true);
            return;
        }
        if (ev.key === "Backspace") {
            ev.preventDefault();
            if (currentChars[index]) {
                currentChars[index] = "";
                this.commitChars(currentChars, index);
                return;
            }
            const previousIndex = Math.max(index - 1, 0);
            currentChars[previousIndex] = "";
            this.commitChars(currentChars, previousIndex);
            return;
        }
        if (ev.key === "Delete") {
            ev.preventDefault();
            currentChars[index] = "";
            this.commitChars(currentChars, index);
            return;
        }
        if (ev.key.length === 1 && !ev.metaKey && !ev.ctrlKey && !ev.altKey) {
            ev.preventDefault();
            this.handleInput(index, ev.key);
        }
    }

    handlePaste(index, ev) {
        ev.preventDefault();
        const text = ev.clipboardData?.getData("text") || "";
        this.handleInput(index, text);
    }

    setActiveIndex(index, focus = false) {
        this.state.activeIndex = Math.max(0, Math.min(index, this.props.length - 1));
        if (focus) {
            this.focusSlot(this.state.activeIndex);
        }
    }
}
