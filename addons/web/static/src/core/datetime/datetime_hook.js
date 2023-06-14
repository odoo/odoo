/** @odoo-module **/

import { markRaw, onPatched, onWillRender, reactive, useEffect, useEnv, useRef } from "@odoo/owl";
import { areDatesEqual } from "../l10n/dates";
import { usePopover } from "../popover/popover_hook";
import { registry } from "../registry";
import { ensureArray, zip, zipWith } from "../utils/arrays";
import { deepCopy, shallowEqual } from "../utils/objects";
import { DateTimePicker } from "./datetime_picker";
import { DateTimePickerPopover } from "./datetime_picker_popover";

/**
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef DateTimePickerHookParams
 * @property {string} [format]
 * @property {(value: DateTimePickerProps["value"]) => any} [onChange] callback
 *  invoked every time the hook updates the reactive value, either through the inputs
 *  or the picker.
 * @property {(value: DateTimePickerProps["value"]) => any} [onApply] callback
 *  invoked once the value is committed: this is either when all inputs received
 *  a "change" event or when the datetime picker popover has been closed.
 * @property {DateTimePickerProps} [pickerProps]
 * @property {string | ReturnType<typeof useRef>} [target]
 *
 * @typedef {import("./datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

/**
 * @template {HTMLElement} T
 * @typedef {{ el: T | null }} OwlRef
 */

/** @type {typeof shallowEqual} */
const arePropsEqual = (obj1, obj2) =>
    shallowEqual(obj1, obj2, (a, b) => areDatesEqual(a, b) || shallowEqual(a, b));

const FOCUS_CLASSNAME = "text-primary";

/**
 * @param {DateTimePickerHookParams} hookParams
 */
export const useDateTimePicker = (hookParams) => {
    // Hook methods

    /**
     * @param {HTMLElement} el
     * @param {string} type
     * @param {(ev: Event) => any} listener
     */
    const addListener = (el, type, listener) => {
        el.addEventListener(type, listener);
        cleanups.push(() => el.removeEventListener(type, listener));
    };

    /**
     * Wrapper method on the "onApply" callback to only call it when the
     * value has changed, and set other internal variables accordingly.
     */
    const apply = () => {
        const serializedValue = JSON.stringify(pickerProps.value);
        if (areDatesEqual(lastInitialProps?.value, serializedValue)) {
            return;
        }

        lastInitialProps = null; // Next pickerProps are considered final
        inputsChanged = ensureArray(pickerProps.value).map(() => false);

        onApply?.(pickerProps.value);
    };

    const computeBasePickerProps = () => {
        const nextInitialProps = markValuesRaw(hookParams.pickerProps);
        const serializedProps = deepCopy(nextInitialProps);

        if (lastInitialProps && arePropsEqual(lastInitialProps, serializedProps)) {
            return;
        }

        lastInitialProps = serializedProps;
        inputsChanged = ensureArray(lastInitialProps.value).map(() => false);

        for (const [key, value] of Object.entries(nextInitialProps)) {
            if (pickerProps[key] !== value && !areDatesEqual(pickerProps[key], value)) {
                pickerProps[key] = value;
            }
        }
    };

    /**
     * Ensures the given input has the focus and applies the class names on all
     * inputs accordingly.
     *
     * @param {HTMLInputElement} inputEl
     */
    const focusInput = (inputEl) => {
        const { activeElement } = inputEl.ownerDocument;
        if (activeElement !== inputEl) {
            inputEl.focus();
        }
        inputEl.selectionStart = 0;
        inputEl.selectionEnd = inputEl.value.length;
        setFocusClass(inputEl);
    };

    /**
     * @param {number} valueIndex
     * @returns
     */
    const getInput = (valueIndex) => {
        const el = inputRefs[valueIndex]?.el;
        if (el && document.body.contains(el)) {
            return el;
        }
        return null;
    };

    /**
     * Returns the appropriate root element to attach the popover:
     * - if the value is a range: the closest common parent of the two inputs
     * - if not: the first input
     */
    const getPopoverTarget = () => {
        if (targetRef?.el) {
            return targetRef.el;
        }
        if (pickerProps.range) {
            let parentElement = getInput(0).parentElement;
            const inputEls = inputRefs.map((ref) => ref.el);
            while (parentElement && !inputEls.every((inputEl) => parentElement.contains(inputEl))) {
                parentElement = parentElement.parentElement;
            }
            return parentElement || getInput(0);
        } else {
            return getInput(0);
        }
    };

    /**
     * @template {object} T
     * @param {T} obj
     */
    const markValuesRaw = (obj) => {
        /** @type {T} */
        const copy = {};
        for (const [key, value] of Object.entries(obj)) {
            if (value && typeof value === "object") {
                copy[key] = markRaw(value);
            } else {
                copy[key] = value;
            }
        }
        return copy;
    };

    /**
     * Inputs "change" event handler. This will trigger an "onApply" callback if
     * one of the following is true:
     * - there is only one input;
     * - the popover is closed;
     * - the other input has also changed.
     *
     * @param {Event} ev
     */
    const onInputChange = (ev) => {
        updateValueFromInputs();
        inputsChanged[ev.target === getInput(1) ? 1 : 0] = true;
        if (!popover.isOpen || inputsChanged.every(Boolean)) {
            saveAndClose();
        }
    };

    /**
     * @param {PointerEvent} ev
     */
    const onInputClick = ({ target }) => {
        pickerProps.focusedDateIndex = target === getInput(1) ? 1 : 0;

        if (!popover.isOpen) {
            if (target && env.isSmall) {
                target.scrollIntoView(true);
            }

            popover.open(getPopoverTarget(), { pickerProps });
        }

        focusInput(target);
    };

    /**
     * @param {FocusEvent} ev
     */
    const onInputFocus = ({ target }) => {
        pickerProps.focusedDateIndex = target === getInput(1) ? 1 : 0;
        focusInput(target);
    };

    /**
     * @param {KeyboardEvent} ev
     */
    const onInputKeydown = (ev) => {
        switch (ev.key) {
            case "Enter":
            case "Escape": {
                ev.preventDefault();
                return saveAndClose();
            }
            case "Tab": {
                if (!getInput(0) || !getInput(1) || ev.target !== getInput(ev.shiftKey ? 1 : 0)) {
                    return saveAndClose();
                }
            }
        }
    };

    /**
     * @template {"format" | "parse"} T
     * @param {T} operation
     * @param {T extends "format" ? DateTime : string} value
     * @returns {[T extends "format" ? string : DateTime, null] | [null, Error]}
     */
    const safeConvert = (operation, value) => {
        const { type } = pickerProps;
        const convertFn = registry
            .category(operation === "format" ? "formatters" : "parsers")
            .get(type);
        try {
            return [convertFn(value, { format }), null];
        } catch (error) {
            if (error?.name === "ConversionError") {
                return [null, error];
            } else {
                throw error;
            }
        }
    };

    /**
     * Wrapper method to ensure the "onApply" callback is called, either:
     * - by closing the popover (if any);
     * - or by directly calling "apply", without updating the values.
     */
    const saveAndClose = () => {
        if (popover.isOpen) {
            // apply will be done in the "onClose" callback
            popover.close();
        } else {
            apply();
        }
    };

    /**
     * Updates class names on given inputs according to the currently selected input.
     *
     * @param {HTMLInputElement | null} input
     */
    const setFocusClass = (input) => {
        for (const { el } of inputRefs) {
            if (el) {
                el.classList.toggle(FOCUS_CLASSNAME, popover.isOpen && el === input);
            }
        }
    };

    /**
     * Synchronizes the given input with the given value.
     *
     * @param {HTMLInputElement} el
     * @param {DateTime} value
     */
    const updateInput = (el, value) => {
        const [formattedValue] = safeConvert("format", value);
        el.value = formattedValue || "";
    };

    /**
     * @param {DateTimePickerProps["value"]} value
     */
    const updateValue = (value) => {
        if (pickerProps.range) {
            // When in range: compare each individual value
            const [currentStart, currentEnd] = ensureArray(pickerProps.value);
            const [nextStart, nextEnd] = ensureArray(value);
            const areStartDatesEqual = areDatesEqual(currentStart, nextStart);
            const areEndDatesEqual = areDatesEqual(currentEnd, nextEnd);
            if (
                (pickerProps.focusedDateIndex === 0 && areEndDatesEqual) ||
                (pickerProps.focusedDateIndex === 1 && areStartDatesEqual)
            ) {
                pickerProps.focusedDateIndex = pickerProps.focusedDateIndex === 1 ? 0 : 1;
            }
        }

        const previousValue = pickerProps.value;
        pickerProps.value = value;

        if (!areDatesEqual(previousValue, pickerProps.value)) {
            onChange?.(pickerProps.value);
        }
    };

    const updateValueFromInputs = () => {
        const values = zipWith(
            inputRefs,
            ensureArray(pickerProps.value),
            ({ el }, currentValue) => {
                if (!el) {
                    return currentValue;
                }
                const [parsedValue, error] = safeConvert("parse", el.value);
                if (error) {
                    updateInput(el, currentValue);
                    return currentValue;
                } else {
                    return parsedValue;
                }
            }
        );
        updateValue(values.length === 2 ? values : values[0]);
    };

    // Hook variables

    const { format, onApply, onChange, target } = hookParams;
    /** @type {ReturnType<typeof useRef<HTMLInputElement>>[]} */
    const targetRef = typeof target === "string" ? useRef(target) : target;
    const inputRefs = [useRef("start-date"), useRef("end-date")];
    const env = useEnv();
    const popover = usePopover(DateTimePickerPopover, {
        onClose: () => {
            if (!allowOnClose) {
                return;
            }
            updateValueFromInputs();
            apply();
            setFocusClass(null);
        },
    });

    /** @type {DateTimePickerProps} */
    const rawPickerProps = {
        ...DateTimePicker.defaultProps,
        onSelect: (value) => {
            value &&= markRaw(value);
            updateValue(value);
            if (!pickerProps.range && pickerProps.type === "date") {
                saveAndClose();
            }
        },
        ...markValuesRaw(hookParams.pickerProps),
    };
    const pickerProps = reactive(rawPickerProps, () => {
        // Resets the popover position when switching from single date to a range
        // or vice-versa
        const currentIsRange = pickerProps.range;
        if (popover.isOpen && lastIsRange !== currentIsRange) {
            allowOnClose = false;
            popover.open(getPopoverTarget(), { pickerProps });
            allowOnClose = true;
        }
        lastIsRange = currentIsRange;

        // Update inputs
        for (const [{ el }, value] of zip(inputRefs, ensureArray(pickerProps.value), true)) {
            if (el) {
                updateInput(el, value);
            }
        }

        // Will focus input on next patch
        shouldFocus = true;
        setFocusClass(getInput(pickerProps.focusedDateIndex));
    });

    /** Decides whether the popover 'onClose' callback can be called */
    let allowOnClose = true;
    /** @type {boolean[]} */
    let inputsChanged = [];
    let lastIsRange = pickerProps.range;
    /** @type {DateTimePickerProps | null} */
    let lastInitialProps = null;
    let shouldFocus = false;

    onWillRender(computeBasePickerProps);

    onPatched(() => {
        if (!shouldFocus || !popover.isOpen) {
            return;
        }
        const input = getInput(pickerProps.focusedDateIndex);
        if (input) {
            shouldFocus = false;
            focusInput(input);
        }
    });

    const cleanups = [];
    useEffect(() => {
        let editableInputs = 0;
        for (const [{ el }, value] of zip(inputRefs, ensureArray(pickerProps.value), true)) {
            if (el && !el.disabled && !el.readOnly) {
                addListener(el, "change", onInputChange);
                addListener(el, "click", onInputClick);
                addListener(el, "focus", onInputFocus);
                addListener(el, "keydown", onInputKeydown);

                updateInput(el, value);
                editableInputs++;
            }
        }
        if (!editableInputs) {
            saveAndClose();
        }
        return () => {
            while (cleanups.length) {
                cleanups.pop()();
            }
        };
    });

    return pickerProps;
};
