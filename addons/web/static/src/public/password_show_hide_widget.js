import PublicWidget from "@web/legacy/js/public/public_widget";

export const PasswordShowHideWidget = PublicWidget.Widget.extend({
    selector: "[data-widget='password-reveal']",
    events: {
        "click .show-hide-password": "_showHidePassword",
    },

    /**
     * Toggle password visibility
     *
     * @private
     * @param {Event} ev
     */
    _showHidePassword(ev) {
        ev.preventDefault();
        const inputGroup = ev.delegateTarget;
        const inputEl = inputGroup.querySelector("input");
        const iconEl = inputGroup.querySelector("i");

        inputEl.type = inputEl.type === "text" ? "password" : "text";
        iconEl.classList.toggle("fa-eye");
        iconEl.classList.toggle("fa-eye-slash");
    },
});

PublicWidget.registry.PasswordShowHideWidget = PasswordShowHideWidget;
