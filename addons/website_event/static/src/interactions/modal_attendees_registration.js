import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Interaction } from "@web/public/interaction";

export class ModalAttendeesRegistration extends Interaction {
    static selector = "#modal_attendees_registration";
    dynamicContent = {
        "form": {
            "t-on-submit": this.onSubmit,
        },
        ".js_goto_event, .btn-close": {
            "t-on-click.once": this.onClick,
        },
    };

    setup() {
        // dynamic get rather than import as we don't depend on this module
        if (session.turnstile_site_key) {
            const { TurnStile } = odoo.loader.modules.get(
                "@website_cf_turnstile/interactions/turnstile"
            );
            if (TurnStile) {
                this._turnstile = new TurnStile("website_event_registration");
                this._turnstile.turnstileEl.classList.add("float-end");
            }
        }
        this.recaptcha = new ReCaptcha();
    }

    async willStart() {
        await this.recaptcha.loadLibs();
        this.recaptchaToken = await this.recaptcha.getToken("website_event_registration");

        if (this.recaptchaToken.error) {
            this.services.notification.add(this.recaptchaToken.error, {
                type: "danger",
                title: _t("Error"),
                sticky: true,
            });
            this.enableRegistrationFormSubmit();

            this.el.remove();
            this.services["public.interactions"].stopInteractions(this.el);
        }
    }

    start() {
        const formModal = window.Modal.getOrCreateInstance(this.el, {
            backdrop: "static",
            keyboard: false,
        });

        const form = this.el.querySelector("form#attendee_registration");
        // the turnstile container needs to be already appended to the dom before rendering
        // see modal.js for events
        this.el.addEventListener("shown.bs.modal", () => {
            this._addTurnstile(form);
        });

        formModal.show();
        this.registerCleanup(() => {
            formModal.hide();
            formModal.dispose();
        });
    }

    _addTurnstile(form) {
        if (!this._turnstile) {
            return false;
        }

        const modalFooter = form.querySelector("div.modal-footer");
        const formButton = form.querySelector("button[type=submit]");

        this._turnstile.constructor.disableSubmit(formButton);
        modalFooter.appendChild(this._turnstile.turnstileEl);
        this._turnstile.insertScripts(form);
        this._turnstile.render();

        return true;
    }

    enableRegistrationFormSubmit() {
        this.env.bus.trigger("websiteEvent.enableSubmit");
    }

    onClick() {
        this.enableRegistrationFormSubmit();
        this.el.remove();
    }

    /**
     * @param {SubmitEvent} ev
     */
    onSubmit(ev) {
        if (this.recaptchaToken.token) {
            const tokenInput = document.createElement("input");
            tokenInput.setAttribute("name", "recaptcha_token_response");
            tokenInput.setAttribute("type", "hidden");
            tokenInput.setAttribute("value", this.recaptchaToken.token);
            this.insert(tokenInput, ev.currentTarget);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_event.modal_attendees_registration", ModalAttendeesRegistration);
