import { markRaw, reactive } from "@odoo/owl";
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
 * @typedef DateTimePickerHookParams
 * @property {string} [format]
 * @property {(value: DateTimePickerProps["value"]) => any} [onChange] callback
 *  invoked every time the hook updates the reactive value, either through the inputs
 *  or the picker.
 * @property {(value: DateTimePickerProps["value"]) => any} [onApply] callback
 *  invoked once the value is committed: this is either when all inputs received
 *  a "change" event or when the datetime picker popover has been closed.
 * @property {DateTimePickerProps} pickerProps
 * @property {string | ReturnType<typeof import("@odoo/owl").useRef>} [target]
 * @property {(component, options) => import("../popover/popover_hook").PopoverHookReturnType} [createPopover]
 * @property {() => boolean} [ensureVisibility=() => env.isSmall]
 * @property {boolean} [showSeconds]
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
             * @param {DateTimePickerHookParams} hookParams
             */
            create: (hookParams, getInputs = () => [hookParams.target, null]) => {
                const createPopover =
                    hookParams.createPopover ??
                    ((...args) => makePopover(popoverService.add, ...args));
                const ensureVisibility = hookParams.ensureVisibility ?? (() => env.isSmall);
                const popover = createPopover(DateTimePickerPopover, {
                    onClose: () => {
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
                    },
                });
                // Hook methods

                /**
                 * Wrapper method on the "onApply" callback to only call it when the
                 * value has changed, and set other internal variables accordingly.
                 */
                const apply = () => {
                    const valueCopy = deepCopy(pickerProps.value);
                    if (areDatesEqual(lastAppliedValue, valueCopy)) {
                        return;
                    }

                    inputsChanged = ensureArray(pickerProps.value).map(() => false);

                    hookParams.onApply?.(pickerProps.value);
                    lastAppliedValue = valueCopy;
                };

                const computeBasePickerProps = () => {
                    const nextInitialProps = markValuesRaw(hookParams.pickerProps);
                    const propsCopy = deepCopy(nextInitialProps);

                    if (lastInitialProps && arePropsEqual(lastInitialProps, propsCopy)) {
                        return;
                    }

                    lastInitialProps = propsCopy;
                    lastAppliedValue = propsCopy.value;
                    inputsChanged = ensureArray(lastInitialProps.value).map(() => false);

                    for (const [key, value] of Object.entries(nextInitialProps)) {
                        if (pickerProps[key] !== value && !areDatesEqual(pickerProps[key], value)) {
                            pickerProps[key] = value;
                        }
                    }
                };

                /**
                 * Ensures the current focused input (indicated by `pickerProps.focusedDateIndex`)
                 * is actually focused.
                 */
                const focusActiveInput = () => {
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
                };

                /**
                 * @param {number} valueIndex
                 * @returns {HTMLInputElement | null}
                 */
                const getInput = (valueIndex) => {
                    const el = getInputs()[valueIndex];
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
                    if (hookParams.target) {
                        return hookParams.target;
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
                    if (ev.key == "Enter" && ev.ctrlKey) {
                        ev.preventDefault();
                        updateValueFromInputs();
                        return openPicker(ev.target === getInput(1) ? 1 : 0);
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
                };

                /**
                 * @param {number} inputIndex Input from which to open the picker
                 */
                const openPicker = (inputIndex) => {
                    pickerProps.focusedDateIndex = inputIndex;

                    if (!popover.isOpen) {
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
                };

                /**
                 * @template {"format" | "parse"} T
                 * @param {T} operation
                 * @param {T extends "format" ? DateTime : string} value
                 * @returns {[T extends "format" ? string : DateTime, null] | [null, Error]}
                 */
                const safeConvert = (operation, value) => {
                    const { type } = pickerProps;
                    const convertFn = (operation === "format" ? formatters : parsers)[type];
                    const options = { tz: pickerProps.tz, format: hookParams.format };
                    if (operation === "format") {
                        options.showSeconds = hookParams.showSeconds ?? true;
                        options.condensed = hookParams.condensed || false;
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
                    for (const el of getInputs()) {
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

                    shouldFocus = false;
                };

                /**
                 * Synchronizes the given input with the given value.
                 *
                 * @param {HTMLInputElement} el
                 * @param {DateTime} value
                 */
                const updateInput = (el, value) => {
                    if (!el) {
                        return;
                    }
                    const [formattedValue] = safeConvert("format", value);
                    el.value = formattedValue || "";
                };

                /**
                 * @param {DateTimePickerProps["value"]} value
                 * @param {"date" | "time"} unit
                 * @param {"input" | "picker"} source
                 */
                const updateValue = (value, unit, source) => {
                    const previousValue = pickerProps.value;
                    pickerProps.value = value;

                    if (areDatesEqual(previousValue, pickerProps.value)) {
                        return;
                    }

                    if (unit !== "time") {
                        if (pickerProps.range && source === "picker") {
                            if (
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

                    hookParams.onChange?.(value);
                };

                const updateValueFromInputs = () => {
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
                    for (const [el, value] of zip(
                        getInputs(),
                        ensureArray(pickerProps.value),
                        true
                    )) {
                        if (el) {
                            updateInput(el, value);
                        }
                    }

                    shouldFocus = true;
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

                return {
                    state: pickerProps,
                    open: openPicker,
                    computeBasePickerProps,
                    focusIfNeeded() {
                        if (popover.isOpen && shouldFocus) {
                            focusActiveInput();
                        }
                    },
                    enable() {
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
                            calendarIconGroupEl.addEventListener("click", () => openPicker(0));
                        }
                        if (!editableInputs && popover.isOpen) {
                            saveAndClose();
                        }
                        return () => {};
                    },
                    get isOpen() {
                        return popover.isOpen;
                    },
                };
            },
        };
    },
};

registry.category("services").add("datetime_picker", datetimePickerService);
