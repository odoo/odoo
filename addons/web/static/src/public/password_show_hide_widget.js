import PublicWidget from "@web/legacy/js/public/public_widget";

export const PasswordShowHideWidget = PublicWidget.Widget.extend({
    selector: "[data-widget='password-reveal']",
    events: {
        "click .password-toggle": "_showHidePassword",
    },

    /**
     * Toggle password visibility
     *
     * @private
     * @param {PointerEvent} ev
     */
    _showHidePassword(ev) {
        ev.preventDefault();
        const inputGroupEl = ev.delegateTarget;
        const inputEl = inputGroupEl.querySelector("input");
        const iconEl = inputGroupEl.querySelector("i");

        inputEl.type = inputEl.type === "text" ? "password" : "text";
        iconEl.classList.toggle("fa-eye");
        iconEl.classList.toggle("fa-eye-slash");
    },
});

PublicWidget.registry.PasswordShowHideWidget = PasswordShowHideWidget;
