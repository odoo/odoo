import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CapsLockWarning extends Interaction {
    static selector = ".o_caps_lock_warning";
    dynamicContent = {
        _document: {
            "t-on-keyup": this.onInputKeyUp,
        },
        ".o_caps_lock_warning_text": {
            "t-att-class": () => ({ "d-none": !this.passwordFocused || !this.isCapsLockOn }),
        },
        ".o_caps_lock_warning input": {
            // display warning only after password field has been focused
            "t-on-focusin": () => (this.passwordFocused = true),
            "t-on-focusout": () => (this.passwordFocused = false),
        },
    };

    setup() {
        this.isCapsLockOn = null;
        this.renderAt("web.caps_lock_warning");
    }

    /**
     * Captures keydown events to detect the CAPS LOCK state and toggle the
     * CAPS LOCK warning accordingly
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    onInputKeyUp(ev) {
        const reportedState = ev.getModifierState?.("CapsLock");

        if (reportedState === undefined) {
            return;
        }

        if (ev.key === "CapsLock") {
            if (this.isCapsLockOn === null) {
                // This is first CapsLock press, trust the reported state, it's
                // accurate on Windows and MacOs, but not on Linux as
                // getModifierState behaves wrongly in Chrome, on 'keyup' event
                // it always returns true when we press CapsLock no matter if
                // it's on or off, so we assume it is accurate and if not, it
                // will be toggled correctly on the next non-CapsLock keypress
                this.isCapsLockOn = reportedState;
            } else {
                // Subsequent CapsLock press, toggle our tracked state
                this.isCapsLockOn = !this.isCapsLockOn;
            }
        } else {
            // Non-CapsLock key: trust the reported state (it's accurate)
            this.isCapsLockOn = reportedState;
        }
    }
}

registry.category("public.interactions").add("web.caps_lock_warning", CapsLockWarning);
