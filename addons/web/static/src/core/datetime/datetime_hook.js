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
 * @property {(value: DateTimePickerProps["value"]) => any} [onChange] callback
 *  invoked every time the hook updates the reactive value, either through the inputs
 *  or the picker.
 * @property {(value: DateTimePickerProps["value"]) => any} [onApply] callback
 *  invoked once the value is committed: this is either when all inputs received
 *  a "change" event or when the datetime picker popover has been closed.
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
     * Ensures the current focused input (indicated by `pickerProps.focusedDateIndex`)
     * is actually focused.
     */
    const focusActiveInput = () => {
        const inputEl = getInput(pickerProps.focusedDateIndex);
        if (!inputEl) {
            shouldFocusOnPatched = true;
            return;
        }

        const { activeElement } = inputEl.ownerDocument;
        if (activeElement !== inputEl) {
            inputEl.focus();
        }

        setInputFocus(inputEl);
    };

    /**
     * @param {number} valueIndex
     * @returns {HTMLInputElement | null}
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
     * @param {PointerEvent} ev
     */
    const onInputClick = ({ target }) => {
        openPicker(target === getInput(1) ? 1 : 0);
    };

    /**
     * @param {FocusEvent} ev
     */
    const onInputFocus = ({ target }) => {
        pickerProps.focusedDateIndex = target === getInput(1) ? 1 : 0;
        setInputFocus(target);
    };

    /**
     * @param {KeyboardEvent} ev
     */
    const onInputKeydown = (ev) => {
        switch (ev.key) {
            case "Enter":
            case "Escape": {
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
     * @param {DateTimePickerProps} nextProps
     */
    const onPropsUpdated = (nextProps) => {
        const { pickerProps: getPickerProps } = hookParams;
        const nextPickerProps =
            typeof getPickerProps === "function"
                ? getPickerProps(nextProps || comp.props)
                : getPickerProps;

        Object.assign(pickerProps, nextPickerProps);

        lastAppliedDate = pickerProps.value;
        inputsChanged = ensureArray(pickerProps.value).map(() => false);
    };

    /**
     * @param {number} inputIndex Input from which to open the picker
     */
    const openPicker = (inputIndex) => {
        pickerProps.focusedDateIndex = inputIndex;

        if (!popover.isOpen) {
            const popoverTarget = getPopoverTarget();
            if (env.isSmall) {
                popoverTarget.scrollIntoView(true);
            }
            popover.open(popoverTarget, { pickerProps });
        }

        focusActiveInput();
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
     * Applies class names to all inputs according to whether they are focused or not.
     *
     * @param {HTMLInputElement} inputEl
     */
    const setInputFocus = (inputEl) => {
        inputEl.selectionStart = 0;
        inputEl.selectionEnd = inputEl.value.length;

        setFocusClass(inputEl);

        shouldFocusOnPatched = false;
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
        const previousValue = pickerProps.value;
        pickerProps.value = value;

        if (areDatesEqual(previousValue, pickerProps.value)) {
            return;
        }

        if (isRange(previousValue)) {
            // When in range: compare each individual value
            const [prevStart, prevEnd] = ensureArray(previousValue);
            const [nextStart, nextEnd] = ensureArray(pickerProps.value);
            if (
                (pickerProps.focusedDateIndex === 0 && areDatesEqual(prevEnd, nextEnd)) ||
                (pickerProps.focusedDateIndex === 1 && areDatesEqual(prevStart, nextStart))
            ) {
                pickerProps.focusedDateIndex = pickerProps.focusedDateIndex === 1 ? 0 : 1;
            }
        }

        onChange?.(pickerProps.value);
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
    /** @type {ReturnType<typeof useRef<HTMLInputElement>>} */
    const targetRef = typeof target === "string" ? useRef(target) : target;
    const inputRefs = [useRef("start-date"), useRef("end-date")];
    const env = useEnv();
    const comp = useComponent();
    const popover = usePopover(DateTimePickerPopover, {
        onClose: () => {
            if (!allowOnClose) {
                return;
            }
            updateValueFromInputs();
            checkAndApply();
            setFocusClass(null);
        },
    });
    /** @type {DateTimePickerProps} */
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

        // Resets the popover position when switching from single date to a range
        // or vice-versa
        const currentIsRange = isRange(pickerProps.value);
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

        shouldFocusOnPatched = true;
    });

    /** Decides whether the popover 'onClose' callback can be called */
    let allowOnClose = true;
    let inputsChanged = [];
    let lastAppliedDate;
    let lastIsRange = isRange(pickerProps.value);
    let shouldFocusOnPatched = false;

    subscribeToPickerProps();

    onWillStart(onPropsUpdated);
    onWillUpdateProps(onPropsUpdated);

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

    // Note: this `onPatched` callback must be called after the `useEffect` since
    // the effect may change input values that will be selected by the patch callback.
    onPatched(() => {
        if (popover.isOpen && shouldFocusOnPatched) {
            focusActiveInput();
        }
    });

    return { state: pickerProps, open: openPicker };
};
