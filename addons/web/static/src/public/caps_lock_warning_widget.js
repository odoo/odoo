import PublicWidget from "@web/legacy/js/public/public_widget";

export const CapsLockWarningWidget = PublicWidget.Widget.extend({
    selector: "[data-widget='caps-lock-check']",
    events: {
        "keydown .password-input": "_onInputKeyDown",
    },

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
        const state = ev.originalEvent.getModifierState?.("CapsLock");
        const shouldHideWarning = ev.key === "CapsLock" ? state : !state;

        // FALSE value REMOVES the `invisible` class while TRUE ADDS it.
        document.querySelector(".caps-lock-warning").classList.toggle("invisible", shouldHideWarning);
    },
});

PublicWidget.registry.CapsLockWarningWidget = CapsLockWarningWidget;
