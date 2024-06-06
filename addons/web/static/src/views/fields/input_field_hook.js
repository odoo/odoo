/** @odoo-module **/

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { useBus } from "@web/core/utils/hooks";

import { useComponent, useEffect, useRef, useEnv } from "@odoo/owl";

/**
 * This hook is meant to be used by field components that use an input or
 * textarea to edit their value. Its purpose is to prevent that value from being
 * erased by an update of the model (typically coming from an onchange) when the
 * user is currently editing it.
 *
 * @param {() => string} getValue a function that returns the value to write in
 *   the input, if the user isn't currently editing it
 * @param {string} [refName="input"] the ref of the input/textarea
 */
export function useInputField(params) {
    const env = useEnv();
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
        if (component.props.setDirty) {
            component.props.setDirty(isDirty);
        }
        if (component.props.record && !component.props.record.isValid) {
            component.props.record.resetFieldValidity(component.props.name);
        }
    }

    /**
     * On blur, we consider the field no longer dirty, even if it were to be invalid.
     * However, if the field is invalid, the new value will not be committed to the model.
     */
    function onChange(ev) {
        if (isDirty) {
            isDirty = false;
            let isInvalid = false;
            let val = ev.target.value;
            if (params.parse) {
                try {
                    val = params.parse(val);
                } catch (_e) {
                    if (component.props.record) {
                        component.props.record.setInvalidField(component.props.name);
                    }
                    isInvalid = true;
                }
            }

            if (!isInvalid) {
                pendingUpdate = true;
                Promise.resolve(component.props.update(val)).then(() => {
                    pendingUpdate = false;
                });
                lastSetValue = ev.target.value;
            }

            if (component.props.setDirty) {
                component.props.setDirty(isDirty);
            }
        }
    }
    function onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (["enter", "tab", "shift+tab"].includes(hotkey)) {
            commitChanges(false);
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
        const isInvalid = component.props.record
            ? component.props.record.isInvalid(component.props.name)
            : false;
        if (inputRef.el && !isDirty && !isInvalid) {
            inputRef.el.value = params.getValue();
            lastSetValue = inputRef.el.value;
        }
    });

    useBus(env.bus, "RELATIONAL_MODEL:WILL_SAVE_URGENTLY", () => commitChanges(true));
    useBus(env.bus, "RELATIONAL_MODEL:NEED_LOCAL_CHANGES", (ev) =>
        ev.detail.proms.push(commitChanges())
    );

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
                } catch (_e) {
                    isInvalid = true;
                    if (urgent) {
                        return;
                    } else if (component.props.record) {
                        component.props.record.setInvalidField(component.props.name);
                    }
                }
            }

            if (isInvalid) {
                return;
            }

            if ((val || false) !== (component.props.value || false)) {
                lastSetValue = inputRef.el.value;
                await component.props.update(val);
                if (component.props.setDirty) {
                    component.props.setDirty(isDirty);
                }
            } else {
                inputRef.el.value = params.getValue();
            }
        }
    }

    return inputRef;
}
