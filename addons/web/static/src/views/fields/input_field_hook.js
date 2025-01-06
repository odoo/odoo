/** @odoo-module **/

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useBus } from "@web/core/utils/hooks";

import { useComponent, useEffect, useRef } from "@odoo/owl";

/**
 * This hook is meant to be used by field components that use an input or
 * textarea to edit their value. Its purpose is to prevent that value from being
 * erased by an update of the model (typically coming from an onchange) when the
 * user is currently editing it.
 *
 * @param {() => string} getValue a function that returns the value to write in
 *   the input, if the user isn't currently editing it
 * @param {string} [refName="input"] the ref of the input/textarea
 * @param {boolean} preventLineBreaks Prevent line breaks in input when set
 */
export function useInputField(params) {
    const inputRef = params.ref || useRef(params.refName || "input");
    const component = useComponent();

    /*
     * A field is dirty if it is no longer sync with the model
     * More specifically, a field is no longer dirty after it has *tried* to update the value in the model.
     * An invalid value will thefore not be dirty even if the model will not actually store the invalid value.
     */
    let isDirty = false;

    /**
     * The last value that has been commited to the model.
     * Not changed in case of invalid field value.
     */
    let lastSetValue = null;

    /**
     * Track the fact that there is a change sent to the model that hasn't been acknowledged yet
     * (e.g. because the onchange is still pending). This is necessary if we must do an urgent save,
     * as we have to re-send that change for the write that will be done directly.
     * FIXME: this could/should be handled by the model itself, when it will be rewritten
     */
    let pendingUpdate = false;

    /**
     * When a user types, we need to set the field as dirty.
     */
    function onInput(ev) {
        isDirty = ev.target.value !== lastSetValue;
        if (params.preventLineBreaks && ev.inputType === "insertFromPaste") {
            ev.target.value = ev.target.value.replace(/[\r\n]+/g, " ");
        }
        component.props.record.model.bus.trigger("FIELD_IS_DIRTY", isDirty);
        if (!component.props.record.isValid) {
            component.props.record.resetFieldValidity(component.props.name);
        }
    }

    /**
     * On blur, we consider the field no longer dirty, even if it were to be invalid.
     * However, if the field is invalid, the new value will not be committed to the model.
     */
    async function onChange(ev) {
        if (isDirty) {
            isDirty = false;
            let isInvalid = false;
            let val = ev.target.value;
            if (params.parse) {
                try {
                    val = params.parse(val);
                } catch {
                    component.props.record.setInvalidField(component.props.name);
                    isInvalid = true;
                }
            }

            if (!isInvalid) {
                if (val !== component.props.record.data[component.props.name]) {
                    lastSetValue = inputRef.el.value;
                    pendingUpdate = true;
                    await component.props.record.update({ [component.props.name]: val });
                    pendingUpdate = false;
                    component.props.record.model.bus.trigger("FIELD_IS_DIRTY", isDirty);
                } else {
                    inputRef.el.value = params.getValue();
                }
            }
        }
    }
    function onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "tab", "shift+tab"].includes(hotkey)) {
            commitChanges(false);
        }
        if (params.preventLineBreaks && ["enter", "shift+enter"].includes(hotkey)) {
            ev.preventDefault();
        }
    }

    useEffect(
        (inputEl) => {
            if (inputEl) {
                inputEl.addEventListener("input", onInput);
                inputEl.addEventListener("change", onChange);
                inputEl.addEventListener("keydown", onKeydown);
                return () => {
                    inputEl.removeEventListener("input", onInput);
                    inputEl.removeEventListener("change", onChange);
                    inputEl.removeEventListener("keydown", onKeydown);
                };
            }
        },
        () => [inputRef.el]
    );

    /**
     * Sometimes, a patch can happen with possible a new value for the field
     * If the user was typing a new value (isDirty) or the field is still invalid,
     * we need to do nothing.
     * If it is not such a case, we update the field with the new value.
     */
    useEffect(() => {
        // We need to call getValue before the condition to always observe
        // the corresponding value in the record. Otherwise, in some cases,
        // if the value in the record change the useEffect isn't triggered.
        const value = params.getValue();
        if (
            inputRef.el &&
            !isDirty &&
            !component.props.record.isFieldInvalid(component.props.name)
        ) {
            inputRef.el.value = value;
            lastSetValue = inputRef.el.value;
        }
    });

    const { model } = component.props.record;
    useBus(model.bus, "WILL_SAVE_URGENTLY", () => commitChanges(true));
    useBus(model.bus, "NEED_LOCAL_CHANGES", (ev) => ev.detail.proms.push(commitChanges()));

    /**
     * Roughly the same as onChange, but called at more specific / critical times. (See bus events)
     */
    async function commitChanges(urgent) {
        if (!inputRef.el) {
            return;
        }

        isDirty = inputRef.el.value !== lastSetValue;
        if (isDirty || (urgent && pendingUpdate)) {
            let isInvalid = false;
            isDirty = false;
            let val = inputRef.el.value;
            if (params.parse) {
                try {
                    val = params.parse(val);
                } catch {
                    isInvalid = true;
                    if (urgent) {
                        return;
                    } else {
                        component.props.record.setInvalidField(component.props.name);
                    }
                }
            }

            if (isInvalid) {
                return;
            }

            if ((val || false) !== (component.props.record.data[component.props.name] || false)) {
                lastSetValue = inputRef.el.value;
                await component.props.record.update({ [component.props.name]: val });
                component.props.record.model.bus.trigger("FIELD_IS_DIRTY", false);
            } else {
                inputRef.el.value = params.getValue();
            }
        }
    }

    return inputRef;
}
