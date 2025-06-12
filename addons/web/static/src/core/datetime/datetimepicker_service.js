import { markRaw, onPatched, onWillRender, reactive, useEffect, useRef } from "@odoo/owl";
import { areDatesEqual, formatDate, formatDateTime, parseDate, parseDateTime } from "../l10n/dates";
import { makePopover } from "../popover/popover_hook";
import { registry } from "../registry";
import { ensureArray, zip, zipWith } from "../utils/arrays";
import { deepCopy, shallowEqual } from "../utils/objects";
import { DateTimePicker } from "./datetime_picker";
import { DateTimePickerPopover } from "./datetime_picker_popover";

/**
 * @typedef {luxon["DateTime"]["prototype"]} DateTime
 *
 * @typedef {import("./datetime_picker").DateTimePickerProps} DateTimePickerProps
 * @typedef {import("../popover/popover_hook").PopoverHookReturnType} PopoverHookReturnType
 * @typedef {import("../popover/popover_service").PopoverServiceAddOptions} PopoverServiceAddOptions
 * @typedef {import("@odoo/owl").Component} Component
 * @typedef {ReturnType<typeof import("@odoo/owl").useRef>} OwlRef
 *
 * @typedef {{
 *  createPopover?: (component: Component, options: PopoverServiceAddOptions) => PopoverHookReturnType;
 *  ensureVisibility?: () => boolean;
 *  format?: string;
 *  getInputs?: () => HTMLElement[];
 *  onApply?: (value: DateTimePickerProps["value"]) => any;
 *  onChange?: (value: DateTimePickerProps["value"]) => any;
 *  onClose?: () => any;
 *  pickerProps?: DateTimePickerProps;
 *  showSeconds?: boolean;
 *  target: HTMLElement | string;
 *  useOwlHooks?: boolean;
 * }} DateTimePickerServiceParams
 */

/** @type {typeof shallowEqual} */
function arePropsEqual(obj1, obj2) {
    return shallowEqual(obj1, obj2, (a, b) => areDatesEqual(a, b) || shallowEqual(a, b));
}

/**
 * @template {object} T
 * @param {T} obj
 */
function markValuesRaw(obj) {
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
}

const FOCUS_CLASSNAME = "text-primary";

const formatters = {
    date: formatDate,
    datetime: formatDateTime,
};
const listenedElements = new WeakSet();
const parsers = {
    date: parseDate,
    datetime: parseDateTime,
};

export const datetimePickerService = {
    dependencies: ["popover"],
    start(env, { popover: popoverService }) {
        return {
            /**
             * @param {DateTimePickerServiceParams} [params]
             */
            create(params = {}) {
                /**
                 * Wrapper method on the "onApply" callback to only call it when the
                 * value has changed, and set other internal variables accordingly.
                 */
                function apply() {
                    const valueCopy = deepCopy(pickerProps.value);
                    if (areDatesEqual(lastAppliedValue, valueCopy)) {
                        return;
                    }

                    inputsChanged = ensureArray(pickerProps.value).map(() => false);

                    params.onApply?.(pickerProps.value);
                    lastAppliedValue = valueCopy;
                }

                function enable() {
                    let editableInputs = 0;
                    for (const [el, value] of zip(
                        getInputs(),
                        ensureArray(pickerProps.value),
                        true
                    )) {
                        updateInput(el, value);
                        if (el && !el.disabled && !el.readOnly && !listenedElements.has(el)) {
                            listenedElements.add(el);
                            el.addEventListener("change", onInputChange);
                            el.addEventListener("click", onInputClick);
                            el.addEventListener("focus", onInputFocus);
                            el.addEventListener("keydown", onInputKeydown);
                            editableInputs++;
                        }
                    }
                    const calendarIconGroupEl = getInput(0)?.parentElement.querySelector(
                        ".o_input_group_date_icon"
                    );
                    if (calendarIconGroupEl) {
                        calendarIconGroupEl.classList.add("cursor-pointer");
                        calendarIconGroupEl.addEventListener("click", () => open(0));
                    }
                    if (!editableInputs && isOpen()) {
                        saveAndClose();
                    }
                    return () => {};
                }

                /**
                 * Ensures the current focused input (indicated by `pickerProps.focusedDateIndex`)
                 * is actually focused.
                 */
                function focusActiveInput() {
                    const inputEl = getInput(pickerProps.focusedDateIndex);
                    if (!inputEl) {
                        shouldFocus = true;
                        return;
                    }

                    const { activeElement } = inputEl.ownerDocument;
                    if (activeElement !== inputEl) {
                        inputEl.focus();
                    }
                    setInputFocus(inputEl);
                }

                /**
                 * @param {number} valueIndex
                 * @returns {HTMLInputElement | null}
                 */
                function getInput(valueIndex) {
                    const el = getInputs()[valueIndex];
                    if (el?.isConnected) {
                        return el;
                    }
                    return null;
                }

                /**
                 * Returns the appropriate root element to attach the popover:
                 * - if the value is a range: the closest common parent of the two inputs
                 * - if not: the first input
                 */
                function getPopoverTarget() {
                    const target = getTarget();
                    if (target) {
                        return target;
                    }
                    if (pickerProps.range) {
                        let parentElement = getInput(0).parentElement;
                        const inputEls = getInputs();
                        while (
                            parentElement &&
                            !inputEls.every((inputEl) => parentElement.contains(inputEl))
                        ) {
                            parentElement = parentElement.parentElement;
                        }
                        return parentElement || getInput(0);
                    } else {
                        return getInput(0);
                    }
                }

                function getTarget() {
                    return targetRef ? targetRef.el : params.target;
                }

                function isOpen() {
                    return popover.isOpen;
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
                function onInputChange(ev) {
                    updateValueFromInputs();
                    inputsChanged[ev.target === getInput(1) ? 1 : 0] = true;
                    if (!isOpen() || inputsChanged.every(Boolean)) {
                        saveAndClose();
                    }
                }

                /**
                 * @param {PointerEvent} ev
                 */
                function onInputClick({ target }) {
                    open(target === getInput(1) ? 1 : 0);
                }

                /**
                 * @param {FocusEvent} ev
                 */
                function onInputFocus({ target }) {
                    pickerProps.focusedDateIndex = target === getInput(1) ? 1 : 0;
                    setInputFocus(target);
                }

                /**
                 * @param {KeyboardEvent} ev
                 */
                function onInputKeydown(ev) {
                    if (ev.key == "Enter" && ev.ctrlKey) {
                        ev.preventDefault();
                        updateValueFromInputs();
                        return open(ev.target === getInput(1) ? 1 : 0);
                    }
                    switch (ev.key) {
                        case "Enter":
                        case "Escape": {
                            return saveAndClose();
                        }
                        case "Tab": {
                            if (
                                !getInput(0) ||
                                !getInput(1) ||
                                ev.target !== getInput(ev.shiftKey ? 1 : 0)
                            ) {
                                return saveAndClose();
                            }
                        }
                    }
                }

                /**
                 * @param {number} inputIndex Input from which to open the picker
                 */
                function open(inputIndex) {
                    pickerProps.focusedDateIndex = inputIndex;

                    if (!isOpen()) {
                        const popoverTarget = getPopoverTarget();
                        if (ensureVisibility()) {
                            const { marginBottom } = popoverTarget.style;
                            // Adds enough space for the popover to be displayed below the target
                            // even on small screens.
                            popoverTarget.style.marginBottom = `100vh`;
                            popoverTarget.scrollIntoView(true);
                            restoreTargetMargin = async () => {
                                popoverTarget.style.marginBottom = marginBottom;
                            };
                        }
                        popover.open(popoverTarget, { pickerProps });
                    }

                    focusActiveInput();
                }

                /**
                 * @template {"format" | "parse"} T
                 * @param {T} operation
                 * @param {T extends "format" ? DateTime : string} value
                 * @returns {[T extends "format" ? string : DateTime, null] | [null, Error]}
                 */
                function safeConvert(operation, value) {
                    const { type } = pickerProps;
                    const convertFn = (operation === "format" ? formatters : parsers)[type];
                    const options = { tz: pickerProps.tz, format: params.format };
                    if (operation === "format") {
                        options.showSeconds = params.showSeconds ?? true;
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
                function saveAndClose() {
                    if (isOpen()) {
                        // apply will be done in the "onClose" callback
                        popover.close();
                    } else {
                        apply();
                    }
                }

                /**
                 * Updates class names on given inputs according to the currently selected input.
                 *
                 * @param {HTMLInputElement | null} input
                 */
                function setFocusClass(input) {
                    for (const el of getInputs()) {
                        if (el) {
                            el.classList.toggle(FOCUS_CLASSNAME, isOpen() && el === input);
                        }
                    }
                }

                /**
                 * Applies class names to all inputs according to whether they are focused or not.
                 *
                 * @param {HTMLInputElement} inputEl
                 */
                function setInputFocus(inputEl) {
                    inputEl.selectionStart = 0;
                    inputEl.selectionEnd = inputEl.value.length;

                    setFocusClass(inputEl);

                    shouldFocus = false;
                }

                /**
                 * Synchronizes the given input with the given value.
                 *
                 * @param {HTMLInputElement} el
                 * @param {DateTime} value
                 */
                function updateInput(el, value) {
                    if (!el) {
                        return;
                    }
                    const [formattedValue] = safeConvert("format", value);
                    el.value = formattedValue || "";
                }

                /**
                 * @param {DateTimePickerProps["value"]} value
                 * @param {"date" | "time"} unit
                 * @param {"input" | "picker"} source
                 */
                function updateValue(value, unit, source) {
                    const previousValue = pickerProps.value;
                    pickerProps.value = value;

                    if (source === "input" && areDatesEqual(previousValue, pickerProps.value)) {
                        return;
                    }

                    if (unit !== "time") {
                        if (pickerProps.range && source === "picker") {
                            if (!value[0]) {
                                pickerProps.focusedDateIndex = 0;
                            } else if (
                                pickerProps.focusedDateIndex === 0 ||
                                (value[0] && value[1] && value[1] < value[0])
                            ) {
                                // If selecting either:
                                // - the first value
                                // - OR a second value before the first:
                                // Then:
                                // - Set the DATE (year + month + day) of all values
                                // to the one that has been selected.
                                const { year, month, day } = value[pickerProps.focusedDateIndex];
                                for (let i = 0; i < value.length; i++) {
                                    value[i] = value[i] && value[i].set({ year, month, day });
                                }
                                pickerProps.focusedDateIndex = 1;
                            } else {
                                // If selecting the second value after the first:
                                // - simply toggle the focus index
                                pickerProps.focusedDateIndex =
                                    pickerProps.focusedDateIndex === 1 ? 0 : 1;
                            }
                        }
                    }

                    params.onChange?.(value);
                }

                function updateValueFromInputs() {
                    const values = zipWith(
                        getInputs(),
                        ensureArray(pickerProps.value),
                        (el, currentValue) => {
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
                    updateValue(values.length === 2 ? values : values[0], "date", "input");
                }

                const createPopover =
                    params.createPopover ||
                    function defaultCreatePopover(...args) {
                        return makePopover(popoverService.add, ...args);
                    };
                const ensureVisibility =
                    params.ensureVisibility ||
                    function defaultEnsureVisibility() {
                        return env.isSmall;
                    };
                const getInputs =
                    params.getInputs ||
                    function defaultGetInputs() {
                        return [getTarget(), null];
                    };

                // Hook variables

                /** @type {DateTimePickerProps} */
                const rawPickerProps = {
                    ...DateTimePicker.defaultProps,
                    onSelect: (value, unit) => {
                        value &&= markRaw(value);
                        updateValue(value, unit, "picker");
                        if (!pickerProps.range && pickerProps.type === "date") {
                            saveAndClose();
                        }
                    },
                    ...markValuesRaw(params.pickerProps),
                };
                const pickerProps = reactive(rawPickerProps, () => {
                    // Resets the popover position when switching from single date to a range
                    // or vice-versa
                    const currentIsRange = pickerProps.range;
                    if (isOpen() && lastIsRange !== currentIsRange) {
                        allowOnClose = false;
                        popover.open(getPopoverTarget(), { pickerProps });
                        allowOnClose = true;
                    }
                    lastIsRange = currentIsRange;

                    // Update inputs
                    for (const [el, value] of zip(
                        getInputs(),
                        ensureArray(pickerProps.value),
                        true
                    )) {
                        if (el) {
                            updateInput(el, value);
                            // Apply changes immediately if the popover is already closed.
                            // Otherwise ´apply()´ will be called later on close.
                            if (!isOpen()) {
                                apply();
                            }
                        }
                    }

                    shouldFocus = true;
                });
                const popover = createPopover(DateTimePickerPopover, {
                    onClose() {
                        if (!allowOnClose) {
                            return;
                        }
                        updateValueFromInputs();
                        apply();
                        setFocusClass(null);
                        if (restoreTargetMargin) {
                            restoreTargetMargin();
                            restoreTargetMargin = null;
                        }
                        params.onClose?.();
                    },
                });

                /** Decides whether the popover 'onClose' callback can be called */
                let allowOnClose = true;
                /** @type {boolean[]} */
                let inputsChanged = [];
                /** @type {DateTimePickerProps | null} */
                let lastInitialProps = null;
                /** @type {DateTimePickerProps["value"] | null}*/
                let lastAppliedValue = null;
                let lastIsRange = pickerProps.range;
                /** @type {(() => void) | null} */
                let restoreTargetMargin = null;
                let shouldFocus = false;
                /** @type {OwlRef | null} */
                let targetRef = null;

                if (params.useOwlHooks) {
                    if (typeof params.target === "string") {
                        targetRef = useRef(params.target);
                    }

                    onWillRender(function computeBasePickerProps() {
                        const nextInitialProps = markValuesRaw(params.pickerProps);
                        const propsCopy = deepCopy(nextInitialProps);

                        if (lastInitialProps && arePropsEqual(lastInitialProps, propsCopy)) {
                            return;
                        }

                        lastInitialProps = propsCopy;
                        lastAppliedValue = propsCopy.value;
                        inputsChanged = ensureArray(lastInitialProps.value).map(() => false);

                        for (const [key, value] of Object.entries(nextInitialProps)) {
                            if (
                                pickerProps[key] !== value &&
                                !areDatesEqual(pickerProps[key], value)
                            ) {
                                pickerProps[key] = value;
                            }
                        }
                    });

                    useEffect(enable, getInputs);

                    // Note: this `onPatched` callback must be called after the `useEffect` since
                    // the effect may change input values that will be selected by the patch callback.
                    onPatched(function focusIfNeeded() {
                        if (isOpen() && shouldFocus) {
                            focusActiveInput();
                        }
                    });
                } else if (typeof params.target === "string") {
                    throw new Error(
                        `datetime picker service error: cannot use target as ref name when not using Owl hooks`
                    );
                }

                return { enable, isOpen, open, state: pickerProps };
            },
        };
    },
};

registry.category("services").add("datetime_picker", datetimePickerService);
