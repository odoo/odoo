import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";

export class HrRecruitmentForm extends Interaction {
    static selector = "#hr_recruitment_form";
    dynamicContent = {
        "#apply-btn": { "t-on-click": this.onApplyButtonClick },
        "#recruitment4": {
            "t-on-focusout": this.onLinkedinFocusOut,
            "t-att-required": () => this.isIncomplete,
        },
        "#recruitment6": {
            "t-att-required": () => this.isIncomplete,
        },
    };

    setup() {
        this.linkedinInputEl = this.el.querySelector("#recruitment4");
        this.linkedinMessageEl = document.querySelector("#linkedin-message");
        this.warningMessageEl = document.querySelector("#warning-message");
        this.resumeInputEl = document.querySelector("#recruitment6");
        this.isIncomplete = false;
    }

    /**
    * @param {HTMLElement} targetEl
    * @param {HTMLElement} messageContainerEl
    * @param {string} message
    */
    showWarningMessage(targetEl, messageContainerEl, message) {
        targetEl.classList.add("border-warning");
        messageContainerEl.textContent = message;
        messageContainerEl.classList.remove("d-none");
    }

    /**
    * @param {HTMLElement} targetEl
    * @param {HTMLElement} messageContainerEl
    */
    hideWarningMessage(targetEl, messageContainerEl) {
        targetEl.classList.remove("border-warning");
        messageContainerEl.classList.add("d-none");
    }

    onApplyButtonClick() {
        const isEmptyLinkedin = !this.linkedinInputEl || this.linkedinInputEl.value.trim() === "";
        const isEmptyResume = !this.resumeInputEl || !this.resumeInputEl.files.length;
        this.isIncomplete = isEmptyLinkedin && isEmptyResume;
    }

    onLinkedinFocusOut() {
        const linkedin = this.linkedinInputEl.value;
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        const isLinkedinValid = !linkedin_regex.test(linkedin) && linkedin !== "";
        if (isLinkedinValid) {
            const message = _t("The profile that you gave us doesn't seems like a linkedin profile");
            this.showWarningMessage(this.linkedinInputEl, this.linkedinMessageEl, message);
        } else {
            this.hideWarningMessage(this.linkedinInputEl, this.linkedinMessageEl);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_hr_recruitment.hr_recruitment_form", HrRecruitmentForm);
