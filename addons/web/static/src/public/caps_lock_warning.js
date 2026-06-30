import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CapsLockWarning extends Interaction {
    static selector = ".o_caps_lock_warning";
    dynamicContent = {
        ".o_caps_lock_warning_text": {
            "t-att-class": () => ({ "d-none": this.isWarningHidden }),
        },
        ".o_caps_lock_warning input[type='password']": {
            "t-on-keydown": this._onInputKeyDown,
        },
    };

    setup() {
        this.isWarningHidden = true;
        this.renderAt("web.caps_lock_warning");
    }

    /**
     * Captures keydown events to detect the CAPS LOCK state and toggle the
     * CAPS LOCK warning accordingly
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputKeyDown(ev) {
        // FALSE when we first hit the CAPS-LOCK
        // at this point, the CAPS-LOCK is yet to TURN ON.
        const state = ev.getModifierState?.("CapsLock");

        // FALSE value REMOVES the `invisible` class while TRUE ADDS it.
        this.isWarningHidden = ev.key === "CapsLock" ? state : !state;
    }
}

registry.category("public.interactions").add("web.caps_lock_warning", CapsLockWarning);
