import { usePlugin } from "@odoo/owl";
import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { Interaction } from "@web/public/interaction";
import { BootstrapInstance } from "@web/core/utils/bootstrap_plugin";

export class ModalRegistration extends Interaction {
    static selector = "#modal_attendees_registration,.o_wevent_modal_slot_ticket_registration";
    dynamicContent = {
        "form": {
            "t-on-submit": this.onSubmit,
        },
        ".js_goto_event, .btn-close": {
            "t-on-click": this.onClick,
        },
    };

    setup() {
        this.bootstrap = usePlugin(BootstrapInstance);
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
    }

    start() {
        const formModal = this.bootstrap.getOrCreateInstance(window.Modal, this.el, {
            backdrop: "static",
            keyboard: false,
        });

        const form = this.el.querySelector("form#attendee_registration");
        // the turnstile container needs to be already appended to the dom before rendering
        // see modal.js for events
        this.addListener(this.el, "shown.bs.modal", () => {
            this._addTurnstile(form);
        });

        formModal.show();
        // Note: this listener is intentionally added with a raw addEventListener
        // instead of this.addListener, as it is only ever wired up here, while
        // the interaction is already being destroyed (formModal.hide() only
        // triggers "hidden.bs.modal" asynchronously, once the CSS transition
        // ends).
        this.registerCleanup(() => {
            this.el.addEventListener(
                "hidden.bs.modal",
                () => this.bootstrap.disposeBootstrapInstance(formModal),
                { once: true }
            );
            formModal.hide();
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
        this.services["public.interactions"].stopInteractions(this.el);
    }

    /**
     * @param {SubmitEvent} ev
     */
    async onSubmit(ev) {
        ev.preventDefault();

        const form = ev.currentTarget;
        this.recaptchaToken = await this.recaptcha.getToken("website_event_registration");
        if (this.recaptchaToken.error) {
            this.services.notification.add(this.recaptchaToken.error, {
                type: "danger",
                sticky: true,
            });
            this.enableRegistrationFormSubmit();

            this.el.remove();
            this.services["public.interactions"].stopInteractions(this.el);
            return;
        }
        if (this.recaptchaToken.token) {
            const tokenInput = document.createElement("input");
            tokenInput.setAttribute("name", "recaptcha_token_response");
            tokenInput.setAttribute("type", "hidden");
            tokenInput.setAttribute("value", this.recaptchaToken.token);
            this.insert(tokenInput, form);
        }
        form.submit();
    }
}

registry
    .category("public.interactions")
    .add("website_event.modal_registration", ModalRegistration);
