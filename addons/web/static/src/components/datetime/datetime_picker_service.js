// @ts-check
/** @odoo-module native */

import {
    markRaw,
    onPatched,
    onWillDestroy,
    onWillRender,
    reactive,
    useEffect,
    useRef,
} from "@odoo/owl";
import { DateTimePicker } from "@web/components/datetime/datetime_picker";
import { DateTimePickerPopover } from "@web/components/datetime/datetime_picker_popover";
import { makeLogger } from "@web/core/debug/debug_logger";
import { reportUncaught } from "@web/core/errors/error_utils";
import {
    areDatesEqual,
    ConversionError,
    formatDate,
    formatDateTime,
    parseDate,
    parseDateTime,
} from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { ensureArray, zip, zipWith } from "@web/core/utils/collections/arrays";
import { shallowEqual } from "@web/core/utils/collections/objects";
import { makePopover } from "@web/ui/popover/popover_hook";

const log = makeLogger("web.components.datetime_picker.controller");

/** @typedef {any} DateTime */
/**
 * @typedef {import("@web/components/datetime/datetime_picker").DateTimePickerProps} DateTimePickerProps
 * @typedef {import("@web/ui/popover/popover_hook").PopoverHookReturnType} PopoverHookReturnType
 * @typedef {import("@web/ui/popover/popover_service").PopoverServiceAddOptions} PopoverServiceAddOptions
 * @typedef {import("@odoo/owl").Component} Component
 * @typedef {ReturnType<typeof import("@odoo/owl").useRef>} OwlRef
 * @typedef {{
 * createPopover?: (component: import("@odoo/owl").ComponentConstructor, options: PopoverServiceAddOptions) => PopoverHookReturnType;
 * ensureVisibility?: () => boolean;
 * format?: string;
 * getInputs?: () => HTMLElement[];
 * onApply?: (value: DateTimePickerProps["value"]) => any;
 * onChange?: (value: DateTimePickerProps["value"]) => any;
 * onClose?: () => any;
 * pickerProps?: DateTimePickerProps;
 * showSeconds?: boolean;
 * target?: HTMLElement | string;
 * useOwlHooks?: boolean;
 * }} DateTimePickerServiceParams
 * @typedef {{
 * enable: () => (() => void);
 * unregister: () => boolean;
 * dispose: () => void;
 * isOpen: () => boolean;
 * open: (inputIndex: number) => void;
 * close: () => void;
 * commitInputs: () => Promise<void>;
 * state: DateTimePickerProps;
 * }} DateTimePickerHandle
 */

/**
 * @param {Record<string, any>} obj
 * @returns {Record<string, any>}
 */
function markValuesRaw(obj) {
    /** @type {Record<string, any>} */
    const copy = {};
    for (const [key, value] of Object.entries(obj)) {
        if (value && typeof value === "object") {
            copy[key] = markRaw(value);
        } else {
            copy[key] = value;
        }
    }
    return copy;
}

/** @param {Record<string, any>} props */
function stringifyProps(props) {
    const copy = {};
    for (const [key, value] of Object.entries(props)) {
        copy[key] = JSON.stringify(value);
    }
    return copy;
}

const FOCUS_CLASSNAME = "text-primary";

const formatters = {
    date: formatDate,
    datetime: formatDateTime,
};
const parsers = {
    date: parseDate,
    datetime: parseDateTime,
};

export class DateTimePickerController {
    /**
     * @param {Partial<DateTimePickerServiceParams>} params
     * @param {any} env
     * @param {any} popoverService
     * @param {Set<DateTimePickerHandle>} dateTimePickerList
     */
    constructor(params, env, popoverService, dateTimePickerList) {
        this.params = params;
        this.env = env;
        this.popoverService = popoverService;
        this.dateTimePickerList = dateTimePickerList;

        /** @type {boolean[]} */
        this.inputsChanged = [];
        this.destroyed = false;
        /** @type {(() => void) | null} */
        this.disableListeners = null;
        this.propsValueRevision = 0;
        this.closing = false;
        /** @type {{ value: string, promise: Promise<any>, revision: number } | null} */
        this.pendingApply = null;
        /** @type {(() => void) | null} */
        this.restoreTargetMargin = null;
        this.shouldFocus = false;
        /** @type {Record<string, any>} */
        this.stringProps = {};
        /** @type {OwlRef | null} */
        this.targetRef = null;
        /** @type {string | undefined} */
        this.formatKey = undefined;

        this.createPopover =
            params.createPopover ||
            /** @type {(...args: any[]) => PopoverHookReturnType} */ (
                (/** @type {any} */ component, /** @type {any} */ options) =>
                    makePopover(
                        (/** @type {any[]} */ ...args) =>
                            /** @type {any} */ (popoverService).add(...args),
                        component,
                        options,
                    )
            );
        this.ensureVisibility = params.ensureVisibility || (() => this.env.isSmall);
        this.getInputs = params.getInputs || (() => [this.getTarget(), null]);

        /** @type {any} */
        const rawPickerProps = {
            ...DateTimePicker.defaultProps,
            onReset: () => {
                this.updateValue(
                    ensureArray(this.pickerProps.value).length === 2
                        ? [false, false]
                        : false,
                    "date",
                    "picker",
                );
                this.saveAndClose();
            },
            onSelect: (/** @type {any} */ value, /** @type {any} */ unit) => {
                value &&= markRaw(value);
                this.updateValue(value, unit, "picker");
                if (!this.pickerProps.range && this.pickerProps.type === "date") {
                    this.saveAndClose();
                }
            },
            ...markValuesRaw(params.pickerProps || {}),
        };
        this.pickerProps = reactive(rawPickerProps, () => this.onPickerPropsUpdated());
        this.popover = this.createPopover(/** @type {any} */ (DateTimePickerPopover), {
            onClose: () => {
                // Dismiss the calendar while onchange runs. Field flushing awaits
                // the same save through commitInputs, independently of the overlay.
                this.onPopoverClose().catch(reportUncaught);
            },
        });

        /** @type {DateTimePickerHandle} */
        this.picker = {
            enable: this.enable,
            unregister: () => this.dateTimePickerList.delete(this.picker),
            dispose: this.dispose,
            isOpen: this.isOpen,
            open: this.open,
            close: () => this.popover.close(),
            commitInputs: this.commitInputs,
            state: this.pickerProps,
        };
        this.dateTimePickerList.add(this.picker);
    }

    onPickerPropsUpdated = () => {
        this.updateInputs();

        if (!this.isOpen()) {
            this.apply();
        }

        this.shouldFocus = true;
    };

    releaseTargetMargin = () => {
        this.restoreTargetMargin?.();
        this.restoreTargetMargin = null;
    };

    onPopoverClose = async () => {
        this.releaseTargetMargin();
        if (this.destroyed) {
            return;
        }
        this.updateValueFromInputs();
        this.setFocusClass(null);
        this.closing = true;
        try {
            await this.apply();
        } finally {
            this.closing = false;
        }
        if (!this.destroyed) {
            this.params.onClose?.();
        }
    };

    apply = async () => {
        if (this.destroyed) {
            return;
        }
        const { value } = this.pickerProps;
        const stringValue = JSON.stringify(value);
        if (stringValue === this.pendingApply?.value) {
            return this.pendingApply.promise;
        }
        if (!this.pendingApply && stringValue === this.stringProps.value) {
            log.logic("apply skipped", () => ({ value: stringValue }));
            return;
        }
        log.logic("apply", () => ({ value: stringValue }));
        this.inputsChanged = ensureArray(value).map(() => false);

        const completion = Promise.withResolvers();
        const operation = {
            value: stringValue,
            promise: completion.promise,
            revision: this.propsValueRevision,
        };
        this.pendingApply = operation;
        // Install ownership before invoking a callback which may synchronously
        // render or flush the field again. Keep that invocation synchronous.
        try {
            completion.resolve(this.params.onApply?.(value));
        } catch (error) {
            completion.reject(error);
        }
        try {
            await operation.promise;
            if (
                this.pendingApply === operation &&
                operation.revision === this.propsValueRevision &&
                !this.destroyed
            ) {
                this.stringProps.value = stringValue;
            } else {
                log.logic("apply completion superseded");
            }
        } catch (error) {
            log.logic("apply failed");
            throw error;
        } finally {
            if (this.pendingApply === operation) {
                this.pendingApply = null;
            }
        }
    };

    commitInputs = async () => {
        if (this.destroyed) {
            return;
        }
        this.updateValueFromInputs();
        await this.apply();
    };

    enable = () => {
        /** @type {Array<[Element, string, (ev: any) => void]>} */
        const addedListeners = [];
        /**
         * @param {Element} el
         * @param {string} event
         * @param {(ev: any) => void} handler
         */
        const listen = (el, event, handler) => {
            el.addEventListener(event, handler);
            addedListeners.push([el, event, handler]);
        };
        this.disableListeners?.();
        for (const [el, value] of zip(
            this.getInputs(),
            ensureArray(this.pickerProps.value),
            true,
        )) {
            const inputEl = /** @type {HTMLInputElement} */ (el);
            this.updateInput(inputEl, value);
            if (inputEl && !inputEl.disabled && !inputEl.readOnly) {
                listen(inputEl, "change", this.onInputChange);
                listen(inputEl, "click", this.onInputClick);
                listen(inputEl, "focus", this.onInputFocus);
                listen(inputEl, "keydown", this.onInputKeydown);
            }
        }
        const calendarIconGroupEl = this.getInput(0)?.parentElement?.querySelector(
            ".o_input_group_date_icon",
        );
        if (calendarIconGroupEl) {
            calendarIconGroupEl.classList.add("cursor-pointer");
            listen(calendarIconGroupEl, "click", () => this.open(0));
        }
        const removeListeners = () => {
            if (this.disableListeners === removeListeners) {
                this.disableListeners = null;
            }
            for (const [el, event, handler] of addedListeners.splice(0)) {
                el.removeEventListener(event, handler);
            }
        };
        this.disableListeners = removeListeners;
        return removeListeners;
    };

    focusActiveInput = () => {
        const inputEl = this.getInput(this.pickerProps.focusedDateIndex);
        if (!inputEl) {
            this.shouldFocus = true;
            return;
        }

        const { activeElement } = inputEl.ownerDocument;
        if (activeElement !== inputEl) {
            inputEl.focus();
        }
        this.setInputFocus(inputEl);
    };

    /**
     * @param {EventTarget | null} el
     * @returns {0 | 1}
     */
    indexOfInput = (el) => (el === this.getInput(1) ? 1 : 0);

    /**
     * @param {number} valueIndex
     * @returns {HTMLInputElement | null}
     */
    getInput = (valueIndex) => {
        const el = /** @type {HTMLInputElement} */ (this.getInputs()[valueIndex]);
        if (el?.isConnected) {
            return el;
        }
        return null;
    };

    getPopoverTarget = () => {
        const target = this.getTarget();
        if (target) {
            return target;
        }
        if (this.pickerProps.range) {
            const firstInput = this.getInput(0);
            if (!firstInput) {
                return this.getInput(1) ?? this.getTarget();
            }
            let parentElement = firstInput.parentElement;
            const inputEls = this.getInputs().filter(Boolean);
            while (parentElement) {
                const candidate = parentElement;
                if (inputEls.every((inputEl) => candidate.contains(inputEl))) {
                    break;
                }
                parentElement = parentElement.parentElement;
            }
            return parentElement || firstInput;
        } else {
            return this.getInput(0);
        }
    };

    /** @returns {HTMLElement | null} */
    getTarget = () =>
        this.targetRef
            ? /** @type {HTMLElement | null} */ (this.targetRef.el)
            : /** @type {HTMLElement} */ (this.params.target);

    isOpen = () => this.popover.isOpen;

    /** @param {Event} ev */
    onInputChange = (ev) => {
        this.updateValueFromInputs();
        this.inputsChanged[this.indexOfInput(ev.target)] = true;
        if (!this.isOpen() || this.inputsChanged.every(Boolean)) {
            this.saveAndClose();
        }
    };

    /** @param {Event} ev */
    onInputClick = (ev) => {
        this.open(this.indexOfInput(ev.target));
    };

    /** @param {FocusEvent} ev */
    onInputFocus = (ev) => {
        const target = /** @type {HTMLInputElement} */ (ev.target);
        this.pickerProps.focusedDateIndex = this.indexOfInput(target);
        this.setInputFocus(target);
    };

    /** @param {KeyboardEvent} ev */
    onInputKeydown = (ev) => {
        const inputTarget = /** @type {HTMLInputElement} */ (ev.target);
        if (ev.key === "Enter" && ev.ctrlKey) {
            ev.preventDefault();
            this.updateValueFromInputs();
            return this.open(this.indexOfInput(ev.target));
        }
        switch (ev.key) {
            case "Enter":
            case "Escape": {
                return this.saveAndClose();
            }
            case "Tab": {
                if (
                    !this.getInput(0) ||
                    !this.getInput(1) ||
                    inputTarget !== this.getInput(ev.shiftKey ? 1 : 0)
                ) {
                    return this.saveAndClose();
                }
                break;
            }
        }
    };

    /** @param {number} inputIndex */
    open = (inputIndex) => {
        if (this.closing) {
            // The owner re-renders while the value it closed with is saved, and may
            // ask to reopen before onClose tells it the picker is closed.
            log.logic("open refused while closing", () => ({ inputIndex }));
            return;
        }
        log.logic("open", () => ({ inputIndex, wasOpen: this.isOpen() }));
        this.pickerProps.focusedDateIndex = inputIndex;

        if (!this.isOpen()) {
            const popoverTarget = this.getPopoverTarget();
            if (!popoverTarget) {
                return;
            }
            if (this.ensureVisibility()) {
                const { marginBottom } = popoverTarget.style;
                popoverTarget.style.marginBottom = `100vh`;
                popoverTarget.scrollIntoView(true);
                this.restoreTargetMargin = () => {
                    popoverTarget.style.marginBottom = marginBottom;
                };
            }
            for (const picker of this.dateTimePickerList) {
                picker.close();
            }
            this.popover.open(popoverTarget, { pickerProps: this.pickerProps });
        }

        this.focusActiveInput();
    };

    /**
     * @template {"format" | "parse"} T
     * @param {T} operation
     * @param {T extends "format" ? DateTime : string} value
     * @returns {[T extends "format" ? string : DateTime, null] | [null, Error]}
     */
    safeConvert = (operation, value) => {
        const { type } = this.pickerProps;
        const convertFn = (operation === "format" ? formatters : parsers)[type];
        /** @type {any} */
        const options = {
            format: this.params.format,
            tz: this.pickerProps.tz,
        };
        if (operation === "format") {
            options.showSeconds = this.params.showSeconds ?? true;
        }
        try {
            return [/** @type {any} */ (convertFn)(value, options), null];
        } catch (error) {
            if (error instanceof ConversionError) {
                return [null, error];
            } else {
                throw error;
            }
        }
    };

    saveAndClose = () => {
        if (this.isOpen()) {
            this.popover.close();
        } else {
            this.apply();
        }
    };

    /** @param {HTMLInputElement | null} input */
    setFocusClass = (input) => {
        for (const el of this.getInputs()) {
            if (el) {
                el.classList.toggle(FOCUS_CLASSNAME, this.isOpen() && el === input);
            }
        }
    };

    /** @param {HTMLInputElement} inputEl */
    setInputFocus = (inputEl) => {
        inputEl.selectionStart = 0;
        inputEl.selectionEnd = inputEl.value.length;

        this.setFocusClass(inputEl);

        this.shouldFocus = false;
    };

    /**
     * @param {HTMLInputElement} el
     * @param {DateTime} value
     */
    updateInput = (el, value) => {
        if (!el) {
            return;
        }
        const [formattedValue] = this.safeConvert("format", value);
        el.value = formattedValue || "";
    };

    /**
     * @param {DateTimePickerProps["value"]} value
     * @param {"date" | "time"} unit
     * @param {"input" | "picker"} source
     */
    updateValue = (value, unit, source) => {
        if (source === "input" && areDatesEqual(this.pickerProps.value, value)) {
            return;
        }
        log.logic("updateValue", () => ({
            unit,
            source,
            value: JSON.stringify(value),
        }));

        let nextFocusedDateIndex = this.pickerProps.focusedDateIndex;
        if (
            this.pickerProps.range &&
            Array.isArray(value) &&
            unit !== "time" &&
            source === "picker"
        ) {
            if (!value[0]) {
                nextFocusedDateIndex = 0;
            } else if (
                this.pickerProps.focusedDateIndex === 0 ||
                (value[1] && value[1] < value[0])
            ) {
                const focused = value[this.pickerProps.focusedDateIndex];
                if (focused) {
                    const { year, month, day } = focused;
                    value = /** @type {any} */ (
                        value.map((bound) => bound && bound.set({ year, month, day }))
                    );
                }
                nextFocusedDateIndex = 1;
            } else {
                nextFocusedDateIndex = this.pickerProps.focusedDateIndex === 1 ? 0 : 1;
            }
        }

        this.pickerProps.value = value;
        this.pickerProps.focusedDateIndex = nextFocusedDateIndex;

        this.params.onChange?.(value);
    };

    updateValueFromInputs = () => {
        const values = zipWith(
            this.getInputs(),
            ensureArray(this.pickerProps.value),
            (el, currentValue) => {
                if (!el || el.tagName?.toLowerCase() !== "input") {
                    return currentValue;
                }
                const inputEl = /** @type {HTMLInputElement} */ (el);
                const [parsedValue, error] = this.safeConvert("parse", inputEl.value);
                if (error) {
                    this.updateInput(inputEl, currentValue);
                    return currentValue;
                } else {
                    return parsedValue;
                }
            },
        );
        this.updateValue(values.length === 2 ? values : values[0], "date", "input");
    };

    dispose = () => {
        this.destroyed = true;
        /** @type {any} */
        let firstError;
        for (const step of [
            () => this.popover.close(),
            () => this.releaseTargetMargin(),
            () => this.disableListeners?.(),
            () => this.dateTimePickerList.delete(this.picker),
        ]) {
            try {
                step();
            } catch (error) {
                firstError ??= error;
            }
        }
        if (firstError) {
            throw firstError;
        }
    };

    computeBasePickerProps = () => {
        const nextProps = markValuesRaw(this.params.pickerProps || {});
        const oldStringProps = this.stringProps;
        const oldFormat = this.formatKey;

        this.stringProps = stringifyProps(nextProps);
        if (oldStringProps.value !== this.stringProps.value) {
            this.propsValueRevision++;
        }
        this.formatKey = `${this.params.format}\x00${this.params.showSeconds}`;

        if (shallowEqual(oldStringProps, this.stringProps)) {
            if (oldFormat !== undefined && oldFormat !== this.formatKey) {
                log.logic("format changed", () => ({ format: this.formatKey }));
                this.updateInputs();
            }
            return;
        }
        log.logic("computeBasePickerProps changed", () => ({
            keys: Object.keys(nextProps).filter(
                (key) => oldStringProps[key] !== this.stringProps[key],
            ),
        }));

        this.inputsChanged = ensureArray(nextProps.value).map(() => false);

        for (const [key, value] of Object.entries(nextProps)) {
            if (!areDatesEqual(this.pickerProps[key], value)) {
                this.pickerProps[key] = value;
            }
        }
    };

    updateInputs = () => {
        for (const [el, value] of zip(
            this.getInputs(),
            ensureArray(this.pickerProps.value),
            true,
        )) {
            if (el) {
                this.updateInput(/** @type {HTMLInputElement} */ (el), value);
            }
        }
    };

    focusIfNeeded = () => {
        if (this.isOpen() && this.shouldFocus) {
            this.focusActiveInput();
        }
    };
}

export class DateTimePickerService {
    /**
     * @param {any} env
     * @param {any} popoverService
     */
    constructor(env, popoverService) {
        this.env = env;
        this.popoverService = popoverService;
        /** @type {Set<DateTimePickerHandle>} */
        this.dateTimePickerList = new Set();
    }

    /**
     * @param {Partial<DateTimePickerServiceParams>} [params]
     * @returns {DateTimePickerHandle}
     */
    create(params = {}) {
        const controller = new DateTimePickerController(
            params,
            this.env,
            this.popoverService,
            this.dateTimePickerList,
        );

        if (params.useOwlHooks) {
            onWillDestroy(() => controller.dispose());

            if (typeof params.target === "string") {
                controller.targetRef = useRef(params.target);
            }

            onWillRender(controller.computeBasePickerProps);

            useEffect(controller.enable, controller.getInputs);

            onPatched(controller.focusIfNeeded);
        } else if (typeof params.target === "string") {
            throw new Error(
                `datetime picker service error: cannot use target as ref name when not using Owl hooks`,
            );
        }

        return controller.picker;
    }
}

export const datetimePickerService = {
    dependencies: ["popover"],
    start(env, { popover: popoverService }) {
        return new DateTimePickerService(env, popoverService);
    },
};

registry.category("services").add("datetime_picker", datetimePickerService);
