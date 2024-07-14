/** @odoo-module */

import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";

import { useEffect, useRef } from "@odoo/owl";

export function useInputHook(params) {
    const inputRef = params.ref || useRef(params.refName || "input");

    /*
     * A field is dirty if it is no longer sync with the model
     * More specifically, a field is no longer dirty after it has *tried* to update the value in the model.
     * An invalid value will therefore not be dirty even if the model will not actually store the invalid value.
     */
    let isDirty = false;

    /**
     * The last value that has been committed to the model.
     * Not changed in case of invalid field value.
     */
    let lastSetValue = null;

    /**
     * When a user types, we need to set the field as dirty.
     */
    function onInput(ev) {
        isDirty = ev.target.value !== lastSetValue;
        if (params.setDirty) {
            params.setDirty(isDirty);
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
                } catch {
                    if (params.setInvalid) {
                        params.setInvalid();
                    }
                    isInvalid = true;
                }
            }

            if (!isInvalid) {
                params.notifyChange(val);
                lastSetValue = ev.target.value;
            }

            if (params.setDirty) {
                params.setDirty(isDirty);
            }
        }
    }
    function onKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (params.discard && hotkey === "escape") {
            params.discard();
        } else if (params.commitChanges && ["enter", "tab", "shift+tab"].includes(hotkey)) {
            commitChanges();
        }
        if (params.onKeyDown) {
            params.onKeyDown(ev);
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
        const isInvalid = params.isInvalid ? params.isInvalid() : false;
        if (inputRef.el && !isDirty && !isInvalid) {
            inputRef.el.value = params.getValue();
            lastSetValue = inputRef.el.value;
        }
    });

    function isUrgentSaved(urgent) {
        if (params.isUrgentSaved) {
            return params.isUrgentSaved(urgent);
        }
        return urgent;
    }

    /**
     * Roughly the same as onChange, but called at more specific / critical times. (See bus events)
     */
    async function commitChanges(urgent) {
        if (!inputRef.el) {
            return;
        }

        isDirty = inputRef.el.value !== lastSetValue;
        if (isDirty || isUrgentSaved(urgent)) {
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
                        params.setInvalid();
                    }
                }
            }

            if (isInvalid) {
                return;
            }

            const result = params.commitChanges(val); // means change has been committed
            if (result) {
                lastSetValue = inputRef.el.value;
                if (params.setDirty) {
                    params.setDirty(isDirty);
                }
            }
        }
    }

    return inputRef;
}
