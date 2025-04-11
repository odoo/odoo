import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class CapsLockWarning extends Interaction {
    static selector = ".caps-lock-warning";
    dynamicContent = {
        ".password-input": {
            "t-on-keydown": (ev) => this._onInputKeyDown(ev),
        },
    };

    /**
     * Capture keydown events to detect the CAPS LOCK state and toggle the
     * CAPS LOCK warning accordingly
     *
     * @private
     * @param {KeyboardEvent} ev
     */
    _onInputKeyDown(ev) {
        // FALSE when we first hit the CAPS-LOCK
        // at this point, the CAPS-LOCK is yet to TURN ON.
        const state = ev.getModifierState?.("CapsLock");
        const shouldHideWarning = ev.key === "CapsLock" ? state : !state;

        // FALSE value REMOVES the `invisible` class while TRUE ADDS it.
        this.el
            .querySelector(".caps-lock-warning-text")
            .classList.toggle("invisible", shouldHideWarning);
    }
}

registry.category("public.interactions").add("web.caps_lock_warning", CapsLockWarning);
