import {
    getDefault,
    getScope,
    immediateEffect,
    markRaw,
    onMounted,
    onPatched,
    onWillDestroy,
    Plugin,
    proxy,
    signal,
    untrack,
    usePlugin,
    useScope,
} from "@odoo/owl";
import { BottomSheetPlugin } from "@web/core/bottom_sheet/bottom_sheet_plugin";
import { hasTouch } from "@web/core/browser/feature_detection";
import { PopoverPlugin } from "@web/core/popover/popover_plugin";
import { services } from "@web/core/services";
import { UIPlugin } from "@web/core/ui/ui_plugin";
import { onWillRender } from "@web/owl2/utils";
import { areDatesEqual, formatDate, formatDateTime, parseDate, parseDateTime } from "../l10n/dates";
import { makePopover } from "../popover/popover_hook";
import { registry } from "../registry";
import { ensureArray, zip } from "../utils/arrays";
import { shallowEqual } from "../utils/objects";
import { dateTimePickerProps } from "./datetime_picker";
import { DateTimePickerPopover } from "./datetime_picker_popover";

/**
 * @typedef {luxon["DateTime"]["prototype"]} DateTime
 *
 * @typedef {import("./datetime_picker").DateTimePickerProps} DateTimePickerProps
 * @typedef {import("../popover/popover_hook").PopoverHookReturnType} PopoverHookReturnType
 * @typedef {import("../popover/popover_plugin").PopoverOptionSchema} PopoverServiceAddOptions
 * @typedef {import("@odoo/owl").Component} Component
 *
 * @typedef {{
 *  createPopover?: (component: Component, options: PopoverServiceAddOptions) => PopoverHookReturnType;
 *  format?: string;
 *  getInputs?: () => HTMLElement[];
 *  onApply?: (value: DateTimePickerProps["value"]) => any;
 *  onChange?: (value: DateTimePickerProps["value"]) => any;
 *  onClose?: () => any;
 *  pickerProps?: DateTimePickerProps;
 *  showSeconds?: boolean;
 *  target: HTMLElement | (() => HTMLElement | null) | { el?: HTMLElement };
 *  showResetButton?: boolean;
 * }} DateTimePickerServiceParams
 */

/**
 * @param {Record<string, any>} props
 */
function stringifyProps(props) {
    const copy = {};
    for (const [key, value] of Object.entries(props)) {
        copy[key] = JSON.stringify(value);
    }
    return copy;
}

/**
 * Derives the default values of the date time picker props from its schema.
 *
 * @returns {Partial<DateTimePickerProps>}
 */
function getPickerDefaults() {
    const defaults = {};
    for (const [key, type] of Object.entries(dateTimePickerProps)) {
        const factory = getDefault(type);
        if (factory) {
            defaults[key] = factory();
        }
    }
    return defaults;
}

const FOCUS_CLASSNAME = "text-primary";

const dateTimeManagerList = new Set();
const formatters = {
    date: formatDate,
    datetime: formatDateTime,
};
const listenedElements = new WeakSet();
const parsers = {
    date: parseDate,
    datetime: parseDateTime,
};

export class DateTimePickerManager {
    #bottomSheetPlugin = usePlugin(BottomSheetPlugin);
    #popoverPlugin = usePlugin(PopoverPlugin);
    #uiPlugin = usePlugin(UIPlugin);
    /** @type {DateTimePickerServiceParams} */
    #params;
    /** @type {DateTimePickerProps} */
    #pickerProps;
    /** @type {PopoverHookReturnType} */
    #popover;
    #disposeEffect = () => {};

    /** @type {import("@odoo/owl").Signal<boolean[]>} */
    #inputsChanged = signal.Array([]);
    #lastAppliedStringValue = signal("");
    /** @type {import("@odoo/owl").Signal<HTMLElement[] | null>} */
    #previousInputs = signal(null);
    #shouldFocus = signal(false);
    #strPickerProps = signal("");
    /** @type {import("@odoo/owl").Signal<Partial<Record<keyof DateTimePickerProps, string>>>} */
    #stringProps = signal({});

    /**
     * @param {DateTimePickerServiceParams} params
     * @param {{ useOwlHooks?: boolean }} [options]
     */
    constructor(params, options) {
        this.#params = params;

        const createPopover = params.createPopover || this.#defaultCreatePopover.bind(this);

        /** @type {DateTimePickerProps} */
        const defaults = {
            ...getPickerDefaults(),
            onReset: () => {
                this.#updateValue(
                    ensureArray(this.#pickerProps.value).length === 2 ? [false, false] : false,
                    "date",
                    "picker"
                );
                this.#saveAndClose();
            },
            onSelect: (value, unit) => {
                value &&= markRaw(value);
                this.#updateValue(value, unit, "picker");
                if (!this.#pickerProps.range && this.#pickerProps.type === "date") {
                    this.#saveAndClose();
                }
            },
        };

        const rawPickerProps = params.pickerProps;
        const initialPickerProps = { ...defaults };
        for (const [key, value] of Object.entries(rawPickerProps)) {
            if (value !== undefined) {
                initialPickerProps[key] = value;
            }
        }
        this.#pickerProps = proxy(initialPickerProps);
        this.#popover = createPopover(DateTimePickerPopover, {
            useBottomSheet: this.#useBottomSheet(),
            onClose: async () => {
                const abort = this.#updateValueFromInputs();
                if (abort) {
                    return;
                }
                this.#setFocusClass(null);
                await this.#apply();
                params.onClose?.();
            },
        });
        this.#strPickerProps.set(JSON.stringify(this.#pickerProps));

        if (options?.useOwlHooks) {
            onWillRender(() => this.#computeBasePickerProps());

            onMounted(() => this.#setup());
            onWillDestroy(() => this.destroy());

            // `initInputs` must run after mount and after each patch, but only when the set
            // of input elements returned by `getInputs` actually changes.
            onMounted(() => this.#initInputsIfChanged());
            onPatched(() => this.#initInputsIfChanged());

            onPatched(() => this.#focusIfNeeded());
        } else {
            this.#initInputs(...this.#getInputs());
            this.#setup();
        }
    }

    get state() {
        return this.#pickerProps;
    }

    close() {
        this.#popover.close();
    }

    destroy() {
        dateTimeManagerList.delete(this);
        this.#disposeEffect();
    }

    /** @deprecated use {@link destroy} directly */
    enable() {
        return this.destroy.bind(this);
    }

    isOpen() {
        return this.#popover.isOpen;
    }

    /**
     * @param {number} inputIndex Input from which to open the picker
     */
    open(inputIndex) {
        this.#pickerProps.focusedDateIndex = inputIndex;

        if (!this.isOpen()) {
            for (const manager of dateTimeManagerList) {
                manager.close();
            }
            this.#popover.open(this.#getPopoverTarget(), {
                pickerProps: this.#pickerProps,
                showResetButton: this.#params.showResetButton,
            });
        }

        this.#focusActiveInput();
    }

    /**
     * Wrapper method on the "onApply" callback to only call it when the
     * value has changed, and set other internal variables accordingly.
     */
    async #apply() {
        const { value } = this.#pickerProps;
        const stringValue = JSON.stringify(value);
        if (
            stringValue === this.#lastAppliedStringValue() ||
            stringValue === this.#stringProps().value
        ) {
            return;
        }

        this.#lastAppliedStringValue.set(stringValue);
        this.#inputsChanged.set(ensureArray(value).map(() => false));

        await this.#params.onApply?.(value);
    }

    #computeBasePickerProps() {
        const nextProps = this.#params.pickerProps;
        // Runs during the render: reading the signal it writes would loop
        const oldStringProps = untrack(this.#stringProps);
        const stringProps = stringifyProps(nextProps);

        this.#stringProps.set(stringProps);
        this.#lastAppliedStringValue.set(stringProps.value);

        if (shallowEqual(oldStringProps, stringProps)) {
            return;
        }

        this.#inputsChanged.set(ensureArray(nextProps.value).map(() => false));

        for (const [key, value] of Object.entries(nextProps)) {
            if (value === undefined) {
                continue;
            }
            if (!areDatesEqual(this.#pickerProps[key], value)) {
                this.#pickerProps[key] = value;
            }
        }
    }

    #defaultCreatePopover(...args) {
        const plugin = this.#useBottomSheet() ? this.#bottomSheetPlugin : this.#popoverPlugin;
        return makePopover(plugin.add.bind(plugin), ...args);
    }

    /**
     * Ensures the current focused input (indicated by `pickerProps.focusedDateIndex`)
     * is actually focused.
     */
    #focusActiveInput() {
        const inputEl = this.#getInput(this.#pickerProps.focusedDateIndex);
        if (!inputEl) {
            this.#shouldFocus.set(true);
            return;
        }

        const { activeElement } = inputEl.ownerDocument;
        if (activeElement !== inputEl) {
            inputEl.focus();
        }
        this.#setInputFocus(inputEl);
    }

    #focusIfNeeded() {
        if (this.#shouldFocus() && this.isOpen() && !this.#useBottomSheet()) {
            this.#focusActiveInput();
        }
    }

    /**
     * @param {number} valueIndex
     * @returns {HTMLInputElement | null}
     */
    #getInput(valueIndex) {
        const el = this.#getInputs()[valueIndex];
        if (el?.isConnected) {
            return el;
        }
        return null;
    }

    #getInputs() {
        if (this.#params.getInputs) {
            return this.#params.getInputs();
        }
        return [this.#getTarget(), null];
    }

    /**
     * Returns the appropriate root element to attach the popover:
     * - if the value is a range: the closest common parent of the two inputs
     * - if not: the first input
     */
    #getPopoverTarget() {
        const target = this.#getTarget();
        if (target) {
            return target;
        }
        if (this.#pickerProps.range) {
            let parentElement = this.#getInput(0).parentElement;
            const inputEls = this.#getInputs();
            while (parentElement && !inputEls.every((inputEl) => parentElement.contains(inputEl))) {
                parentElement = parentElement.parentElement;
            }
            return parentElement || this.#getInput(0);
        } else {
            return this.#getInput(0);
        }
    }

    #getTarget() {
        // `params.target` may be a raw HTMLElement or a ref (a
        // callable): resolve refs to their element, pass raw
        // elements through.
        const target = this.#params.target;
        return typeof target === "function" ? untrack(target) : target;
    }

    #initInputs(...inputs) {
        for (const [el, value] of zip(inputs, ensureArray(this.#pickerProps.value), true)) {
            this.#updateInput(el, value);
            if (el && !el.disabled && !el.readOnly && !listenedElements.has(el)) {
                listenedElements.add(el);
                el.addEventListener("change", this.#onInputChange.bind(this));
                el.addEventListener("click", this.#onInputClick.bind(this));
                el.addEventListener("focus", this.#onInputFocus.bind(this));
                el.addEventListener("keydown", this.#onInputKeydown.bind(this));
            }
        }
        const calendarIconGroupEl = this.#getInput(0)?.parentElement.querySelector(
            ".o_input_group_date_icon"
        );
        if (calendarIconGroupEl) {
            calendarIconGroupEl.classList.add("cursor-pointer");
            calendarIconGroupEl.addEventListener("click", () => this.open(0));
        }
    }

    #initInputsIfChanged() {
        const inputs = this.#getInputs();
        const previousInputs = this.#previousInputs();
        if (previousInputs && shallowEqual(previousInputs, inputs)) {
            return;
        }
        this.#previousInputs.set(inputs);
        this.#initInputs(...inputs);
    }

    /**
     * Inputs "change" event handler. This will trigger an "onApply" callback if
     * one of the following is true:
     * - there is only one input;
     * - the popover is closed;
     * - the other input has also changed.
     *
     * @param {Event} ev
     */
    #onInputChange(ev) {
        const abort = this.#updateValueFromInputs();
        if (abort) {
            return;
        }
        this.#inputsChanged()[ev.target === this.#getInput(1) ? 1 : 0] = true;
        if (!this.isOpen() || this.#inputsChanged().every(Boolean)) {
            this.#saveAndClose();
        }
    }

    /**
     * @param {PointerEvent} ev
     */
    #onInputClick({ target }) {
        this.open(target === this.#getInput(1) ? 1 : 0);
    }

    /**
     * @param {FocusEvent} ev
     */
    #onInputFocus({ target }) {
        this.#pickerProps.focusedDateIndex = target === this.#getInput(1) ? 1 : 0;
        this.#setInputFocus(target);
    }

    /**
     * @param {KeyboardEvent} ev
     */
    #onInputKeydown(ev) {
        switch (ev.key) {
            case "Enter": {
                const abort = this.#updateValueFromInputs();
                if (abort) {
                    return;
                }
                return this.#saveAndClose();
            }
            case "Escape": {
                return this.#updateInputsFromValue();
            }
            case "Tab": {
                if (
                    !this.#getInput(0) ||
                    !this.#getInput(1) ||
                    ev.target !== this.#getInput(ev.shiftKey ? 1 : 0)
                ) {
                    return this.#saveAndClose();
                }
            }
        }
    }

    /**
     * @template {"format" | "parse"} T
     * @param {T} operation
     * @param {T extends "format" ? DateTime : string} value
     * @returns {[T extends "format" ? string : DateTime, null] | [null, Error]}
     */
    #safeConvert(operation, value) {
        const { type } = this.#pickerProps;
        const convertFn = (operation === "format" ? formatters : parsers)[type];
        const options = { tz: this.#pickerProps.tz, format: this.#params.format };
        if (operation === "format") {
            options.showSeconds = this.#params.showSeconds ?? true;
        }
        try {
            return [convertFn(value, options), null];
        } catch (error) {
            if (error?.name === "ConversionError") {
                return [null, error];
            } else {
                throw error;
            }
        }
    }

    /**
     * Wrapper method to ensure the "onApply" callback is called, either:
     * - by closing the popover (if any);
     * - or by directly calling "apply", without updating the values.
     */
    #saveAndClose() {
        if (this.isOpen()) {
            // apply will be done in the "onClose" callback
            this.#popover.close();
        } else {
            this.#apply();
        }
    }

    /**
     * Updates class names on given inputs according to the currently selected input.
     *
     * @param {HTMLInputElement | null} input
     */
    #setFocusClass(input) {
        for (const el of this.#getInputs()) {
            if (el) {
                el.classList.toggle(FOCUS_CLASSNAME, this.isOpen() && el === input);
            }
        }
    }

    /**
     * Applies class names to all inputs according to whether they are focused or not.
     *
     * @param {HTMLInputElement} inputEl
     */
    #setInputFocus(inputEl) {
        inputEl.selectionStart = 0;
        inputEl.selectionEnd = inputEl.value.length;

        this.#setFocusClass(inputEl);

        this.#shouldFocus.set(false);
    }

    #setup() {
        dateTimeManagerList.add(this);

        this.#disposeEffect = immediateEffect(() => {
            const nextStrPickerProps = JSON.stringify(this.#pickerProps);
            // Only the picker props are tracked, not what syncing the inputs reads
            untrack(() => {
                if (this.#strPickerProps() !== nextStrPickerProps) {
                    this.#strPickerProps.set(nextStrPickerProps);
                    this.#updateInputsFromValue();
                }
            });
        });
    }

    /**
     * Synchronizes the given input with the given value.
     *
     * @param {HTMLInputElement} el
     * @param {DateTime} value
     */
    #updateInput(el, value) {
        if (!el) {
            return;
        }
        const [formattedValue] = this.#safeConvert("format", value);
        el.value = formattedValue || "";
    }

    #updateInputsFromValue() {
        for (const [el, value] of zip(
            this.#getInputs(),
            ensureArray(this.#pickerProps.value),
            true
        )) {
            if (el) {
                this.#updateInput(el, value);
                // Apply changes immediately if the popover is already closed.
                // Otherwise ´apply()´ will be called later on close.
                if (!this.isOpen()) {
                    this.#apply();
                }
            }
        }

        this.#shouldFocus.set(true);
    }

    /**
     * @param {DateTimePickerProps["value"]} value
     * @param {"date" | "time"} unit
     * @param {"input" | "picker"} source
     */
    #updateValue(value, unit, source) {
        if (source === "input" && areDatesEqual(this.#pickerProps.value, value)) {
            return;
        }

        this.#pickerProps.value = value;

        if (this.#pickerProps.range && unit !== "time" && source === "picker") {
            if (!value[0]) {
                this.#pickerProps.focusedDateIndex = 0;
            } else if (
                this.#pickerProps.focusedDateIndex === 0 ||
                (value[0] && value[1] && value[1] < value[0])
            ) {
                // If selecting either:
                // - the first value
                // - OR a second value before the first:
                // Then:
                // - Set the DATE (year + month + day) of all values
                // to the one that has been selected.
                const { year, month, day } = value[this.#pickerProps.focusedDateIndex];
                for (let i = 0; i < value.length; i++) {
                    value[i] = value[i] && value[i].set({ year, month, day });
                }
                this.#pickerProps.focusedDateIndex = 1;
            } else {
                // If selecting the second value after the first:
                // - simply toggle the focus index
                this.#pickerProps.focusedDateIndex =
                    this.#pickerProps.focusedDateIndex === 1 ? 0 : 1;
            }
        }

        this.#params.onChange?.(value);
    }

    #updateValueFromInputs() {
        const inputs = this.#getInputs();
        const updated = this.#params.onWillParseValues?.(
            inputs.map((input) => input && input.value)
        );
        if (updated) {
            return true;
        }
        // Iterate over the current value slots rather than the inputs:
        // a target-only picker has no input elements, in which case
        // every value must be preserved as-is. Indexing an absent input
        // keeps the current value, so the just-selected value is never
        // wiped.
        const values = ensureArray(this.#pickerProps.value).map((currentValue, i) => {
            const el = inputs[i];
            if (!el || el.tagName?.toLowerCase() !== "input") {
                return currentValue;
            }
            const [parsedValue, error] = this.#safeConvert("parse", el.value);
            if (error) {
                this.#updateInput(el, currentValue);
                return currentValue;
            }
            return parsedValue;
        });
        this.#updateValue(values.length === 2 ? values : values[0], "date", "input");
    }

    #useBottomSheet() {
        return this.#uiPlugin.isSmall() && hasTouch();
    }
}

export class DateTimePickerPlugin extends Plugin {
    #scope = useScope();

    /**
     * @param {DateTimePickerServiceParams} params
     * @param {{ useOwlHooks?: boolean }} [options]
     */
    create(params, options) {
        const scope = getScope() ?? this.#scope;
        return scope.run(() => new DateTimePickerManager(params, options));
    }
}

services.add(DateTimePickerPlugin);

/**
 * -----------------------------------------------------------------------------
 * @todo owl3 migration
 * temporary - to remove when all use of the datetime_picker service are removed
 * -----------------------------------------------------------------------------
 */
export const datetimePickerService = {
    dependencies: ["bottom_sheet", "popover", "ui"],
    start() {
        return usePlugin(DateTimePickerPlugin);
    },
};

registry.category("services").add("datetime_picker", datetimePickerService);
