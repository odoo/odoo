import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class Security extends Interaction {
    static selector = ".o_portal_security_body";
    dynamicSelectors = {
        ...this.dynamicSelectors,
        _modal: () => this.modalEl,
    };
    dynamicContent = {
        _modal: {
            "t-on-hide.bs.modal": this.onHideModal,
        },
    };

    setup() {
        this.modalEl = document.querySelector(".modal#portal_deactivate_account_modal");
        if (this.modalEl.classList.contains("show")) {
            this.modalEl.classList.remove("d-block");
            this.modalEl.style.display = "";
        }
    }

    onHideModal() {
        // Remove the error messages when we close the modal,
        // so when we re-open it again we get a fresh new form
        const alertEls = this.modalEl.querySelectorAll(".alert");
        const invalidFeedbackEls = this.modalEl.querySelectorAll(".invalid-feedback");
        const invalidEls = this.modalEl.querySelectorAll(".is-invalid");
        for (const alertEl of alertEls) {
            alertEl.remove();
        }
        for (const invalidFeedbackEl of invalidFeedbackEls) {
            invalidFeedbackEl.remove();
        }
        for (const invalidEl of invalidEls) {
            invalidEl.classList.remove("is-invalid");
        }
    }
}

registry
    .category("public.interactions")
    .add("portal.security", Security);
