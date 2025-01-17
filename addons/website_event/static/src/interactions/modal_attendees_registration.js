import { ReCaptcha } from "@google_recaptcha/js/recaptcha";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
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
        formModal.show();
        this.registerCleanup(() => {
            formModal.hide();
            formModal.dispose();
        });
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
        const tokenInput = document.createElement("input");
        tokenInput.setAttribute("name", "recaptcha_token_response");
        tokenInput.setAttribute("type", "hidden");
        tokenInput.setAttribute("value", this.recaptchaToken.token);
        this.insert(tokenInput, ev.currentTarget);
    }
}

registry
    .category("public.interactions")
    .add("website_event.modal_attendees_registration", ModalAttendeesRegistration);
