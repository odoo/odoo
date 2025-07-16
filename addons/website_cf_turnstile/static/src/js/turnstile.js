/** @odoo-module **/

import "@website/snippets/s_website_form/000";  // force deps
import publicWidget from '@web/legacy/js/public/public_widget';
import { renderToElement } from "@web/core/utils/render";
import { session } from "@web/session";

export const turnStile = {
    addTurnstile: function (action) {
        if (!this.isEditable) {
            const mode = new URLSearchParams(window.location.search).get('cf') == 'show' ? 'always' : 'interaction-only';
            const turnstileContainer = renderToElement("website_cf_turnstile.turnstile_container", {
                action: action,
                appearance: mode,
                additionalClasses: "float-end",
                beforeInteractiveGlobalCallback: "turnstileBecomeVisible",
                errorGlobalCallback: "throwTurnstileErrorCode",
                executeGlobalCallback: "turnstileSuccess",
                expiredCallback: "turnstileExpired",
                sitekey: session.turnstile_site_key,
                style: "display: none;",
            });
            let toInsert = $(turnstileContainer);

            // Rethrow the error, or we only will catch a "Script error" without any info
            // because of the script api.js originating from a different domain.
            globalThis.throwTurnstileErrorCode = function (code) {
                const error = new Error("Turnstile Error");
                error.code = code;
                throw error;
            };
            const toggleSpinner = (turnstileContainer, show) => {
                const form = turnstileContainer.parentElement;
                const spinner = form.querySelector("i.turnstile-spinner");
                const button = spinner.parentElement;
                button.disabled = show;
                button.classList.toggle("disabled", show);
                spinner.classList.toggle("d-none", !show);
            };
            // `this` is bound to the turnstile widget calling the callback
            globalThis.turnstileSuccess = function () {
                toggleSpinner(this.wrapper.parentElement, false);
            };
            globalThis.turnstileExpired = function () {
                toggleSpinner(this.wrapper.parentElement, true);
            };
            globalThis.turnstileBecomeVisible = function () {
                const turnstileContainer = this.wrapper.parentElement;
                turnstileContainer.style.display = "";
            };

            // on first load of the remote script, all turnstile containers are rendered
            // if render=explicit is not set in the script url.
            // For subsequent insertion of turnstile containers, we need to call turnstile.render on the container
            // see `renderTurnstile`.
            if (!window.turnstile?.render) {
                const turnstileScript = renderToElement("website_cf_turnstile.turnstile_remote_script");
                toInsert = toInsert.add($(turnstileScript));
            }

            return toInsert;
        }
    },

    /**
     * Remove potential existing loaded script/token
     */
    cleanTurnstile: function () {
        if (this.$(".s_turnstile").length) {
            this.$(".s_turnstile").remove();
        }
    },

    /**
     * @override
     * Discard all library changes to reset the state of the Html.
     */
    destroy: function () {
        this.cleanTurnstile();
        this._super(...arguments);
    },

    /**
     * Take the result of `addTurnstile` and render it if needed
     */
    renderTurnstile: function (turnstileNodes) {
        turnstileNodes = turnstileNodes.toArray();
        const turnstileContainer = turnstileNodes.filter((node) =>
            node.classList.contains("s_turnstile_container")
        )[0];
        const turnstileScript = turnstileNodes.filter(
            (node) => node.id === "s_turnstile_remote_script"
        )[0];
        // there should only be a remote script if it was loaded for the first time
        if (turnstileScript) {
            return;
        }
        if (
            window.turnstile?.render &&
            turnstileContainer &&
            !turnstileContainer.querySelector("iframe")
        ) {
            window.turnstile.render(turnstileContainer);
        }
    },

    _createSpinner() {
        const spinner = document.createElement("i");
        spinner.classList.add("fa", "fa-refresh", "fa-spin", "turnstile-spinner");
        return spinner;
    },

    /**
     * same as addSpinner but does not set innerText
     */
    addSpinnerNoMangle(button) {
        const spinner = this._createSpinner();
        spinner.classList.add("me-1");
        button.disabled = true;
        button.classList.add("disabled");
        button.prepend(spinner);
    },

    addSpinner(button) {
        const spinner = this._createSpinner();
        // avoids double-spacing if the button already contains a space
        button.innerText = " " + button.innerText;
        button.disabled = true;
        button.classList.add("disabled");
        button.prepend(spinner);
    },
};

const signupTurnStile = {
    ...turnStile,

    async willStart() {
        this._super(...arguments);
        if (!session.turnstile_site_key) {
            return;
        }
        const button = this.el.querySelector('button[type="submit"]');
        this.addSpinner(button);
        this.cleanTurnstile();
        const turnstileNodes = this.addTurnstile(this.action);
        turnstileNodes?.insertBefore(button);
        this.renderTurnstile(turnstileNodes);
    },
};

publicWidget.registry.s_website_form.include({
    ...turnStile,

    /**
     * @override
     */
    start: function () {
        const res = this._super(...arguments);
        if (this.$target[0].classList.contains('s_website_form_no_recaptcha')) {
            return res;
        }
        if (session.turnstile_site_key) {
            const button = this.el.querySelector(".s_website_form_send, .o_website_form_send");
            this.addSpinner(button);
            this.cleanTurnstile();
            const turnstileNodes = this.addTurnstile("website_form");
            turnstileNodes?.insertAfter(button);
            this.renderTurnstile(turnstileNodes);
        }
        return res;
    },
});

publicWidget.registry.turnstileCaptchaSignup = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_signup_form",
    action: "signup",
});

publicWidget.registry.turnstileCaptchaPasswordReset = publicWidget.Widget.extend({
    ...signupTurnStile,
    selector: ".oe_reset_password_form",
    action: "password_reset",
});
