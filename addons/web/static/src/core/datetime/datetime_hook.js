/** @odoo-module **/

import {
    onPatched,
    onWillStart,
    onWillUpdateProps,
    reactive,
    useComponent,
    useEffect,
    useEnv,
    useRef,
} from "@odoo/owl";
import { areDatesEqual } from "../l10n/dates";
import { usePopover } from "../popover/popover_hook";
import { registry } from "../registry";
import { ensureArray, zip, zipWith } from "../utils/arrays";
import { DateTimePicker } from "./datetime_picker";
import { DateTimePickerPopover } from "./datetime_picker_popover";

/**
 * @typedef {luxon.DateTime} DateTime
 *
 * @typedef DateTimePickerHookParams
 * @property {string} [format]
 * @property {(value: DateTimePickerProps["value"]) => any} [onChange]
 * @property {(value: DateTimePickerProps["value"]) => any} [onApply]
 * @property {DateTimePickerProps | (props: Record<string, any>) => PromiseLike<DateTimePickerProps>} [pickerProps]
 * @property {string | ReturnType<typeof useRef>} [target]
 *
 * @typedef {import("./datetime_picker").DateTimePickerProps} DateTimePickerProps
 */

/**
 * @template {HTMLElement} T
 * @typedef {{ el: T | null }} OwlRef
 */

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
    const checkAndApply = () => {
        if (areDatesEqual(pickerProps.value, lastAppliedDate)) {
            return;
        }
        lastAppliedDate = pickerProps.value;
        inputsChanged = ensureArray(pickerProps.value).map(() => false);
        onApply?.(pickerProps.value);
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
        if (isRange(pickerProps.value)) {
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
     * @param {unknown} [value]
     * @returns {boolean}
     */
    const isRange = (value) => Array.isArray(value);

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
                updateValueFromInputs();
                if (!getInput(0) || !getInput(1) || ev.target !== getInput(ev.shiftKey ? 1 : 0)) {
                    return saveAndClose();
                }
            }
        }
    };

    /**
     * @param {DateTimePickerProps} nextProps
     */
    const onPropsUpdated = (nextProps) => {
        const { pickerProps: getPickerProps } = hookParams;
        const nextPickerProps =
            typeof getPickerProps === "function"
                ? getPickerProps(nextProps || comp.props)
                : getPickerProps;

        canNotify = false;
        Object.assign(pickerProps, nextPickerProps);
        canNotify = true;

        lastChangedDate = lastAppliedDate = pickerProps.value;
        inputsChanged = ensureArray(pickerProps.value).map(() => false);
    };

    /**
     * @param {HTMLInputElement} inputEl
     */
    const openFromInput = (inputEl) => {
        pickerProps.focusedDateIndex = inputEl === getInput(1) ? 1 : 0;

        if (!popover.isOpen) {
            if (inputEl && env.isSmall) {
                inputEl.scrollIntoView(true);
            }

            popover.open(getPopoverTarget(), { pickerProps });
        }

        focusInput(inputEl);
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
     * - or by directly calling "checkAndApply", without updating the values.
     */
    const saveAndClose = () => {
        if (popover.isOpen) {
            // check & apply will be done in the "onClose" callback
            popover.close();
        } else {
            checkAndApply();
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
     * Reads every key of the reactive picker props to subscribe to their changes.
     */
    const subscribeToPickerProps = () =>
        Object.keys(pickerProps).forEach((key) => pickerProps[key]);

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
        if (isRange(pickerProps.value)) {
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
        pickerProps.value = value;
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
        updateValue(isRange(pickerProps.value) ? values : values[0]);
    };

    // Hook variables

    const { format, onChange, onApply, target } = hookParams;
    /** @type {ReturnType<typeof useRef<HTMLInputElement>>[]} */
    const targetRef = typeof target === "string" ? useRef(target) : target;
    const inputRefs = [useRef("start-date"), useRef("end-date")];
    const env = useEnv();
    const comp = useComponent();
    const popover = usePopover(DateTimePickerPopover, {
        onClose: () => {
            updateValueFromInputs();
            checkAndApply();
            setFocusClass(null);
        },
    });
    const rawPickerProps = {
        ...DateTimePicker.defaultProps,
        onSelect: (value) => {
            updateValue(value);
            if (!isRange(value) && pickerProps.type === "date") {
                saveAndClose();
            }
        },
    };
    const pickerProps = reactive(rawPickerProps, () => {
        subscribeToPickerProps();

        // Update inputs
        for (const [{ el }, value] of zip(inputRefs, ensureArray(pickerProps.value), true)) {
            if (el) {
                updateInput(el, value);
            }
        }

        // Will focus input on next patch
        shouldFocus = true;
        setFocusClass(getInput(pickerProps.focusedDateIndex));

        if (!canNotify || areDatesEqual(lastChangedDate, pickerProps.value)) {
            return;
        }

        lastChangedDate = pickerProps.value;
        onChange?.(pickerProps.value);
    });

    let canNotify = false;
    let inputsChanged = [];
    let lastAppliedDate;
    let lastChangedDate;
    let shouldFocus = false;

    subscribeToPickerProps();

    onWillStart(onPropsUpdated);
    onWillUpdateProps(onPropsUpdated);

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
                addListener(el, "focus", (ev) => openFromInput(ev.target));
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
