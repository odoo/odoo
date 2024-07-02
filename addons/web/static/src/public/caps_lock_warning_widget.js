import PublicWidget from "@web/legacy/js/public/public_widget";

export const CapsLockWarningWidget = PublicWidget.Widget.extend({
    selector: ".oe_login_form, .oe_reset_password_form",
    events: {
        'keydown #password': '_onKeyDownEvent',
    },

    /**
     * @override
     */
    start() {
        this.capsLockWarning = document.querySelector("#caps_lock_warning");
        return this._super.apply(this, arguments);
    },

    _onKeyDownEvent(ev) {
        // Returns true when Caps Lock is active (on) and false when it is inactive (off).
        const isCapsLockActive = ev.originalEvent.getModifierState?.("CapsLock");

        // `false` value REMOVES the `d-none` class and makes the warning visible,
        // `true` value ADDS the `d-none` class and makes the warning invisible.
        const toggleDNone = ev.key === "CapsLock" ? isCapsLockActive : !isCapsLockActive;
        this.capsLockWarning.classList.toggle("d-none", toggleDNone);
    },
});

PublicWidget.registry.CapsLockWarningWidget = CapsLockWarningWidget;
