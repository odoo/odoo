import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class HrRecruitmentForm extends Interaction {
    static selector = "#hr_recruitment_form";
    dynamicContent = {
        "#apply-btn": { "t-on-click": this.onApplyButtonClick },
        "#recruitment1": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "name", this.warningMessageEl) },
        "#recruitment2": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "email", this.warningMessageEl) },
        "#recruitment3": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "phone", this.warningMessageEl) },
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

    /**
     * @param {HTMLElement} targetEl
     * @param {string} field
     * @param {HTMLElement} messageContainerEl
     * @param {boolean} [keepPreviousWarningMessage=false]
     */
    async checkRedundant(targetEl, field, messageContainerEl, keepPreviousWarningMessage = false) {
        const value = targetEl.value;
        if (!value) {
            this.hideWarningMessage(targetEl, messageContainerEl);
            return;
        }
        const job_id = document.querySelector("#recruitment7").value;
        const data = await this.waitFor(rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        }));

        if (data.message) {
            this.showWarningMessage(targetEl, messageContainerEl, data.message);
        } else if (!keepPreviousWarningMessage) {
            this.hideWarningMessage(targetEl, messageContainerEl);
        }
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
        this.checkRedundant(this.linkedinInputEl, "linkedin", this.linkedinMessageEl, isLinkedinValid);
    }
}

registry
    .category("public.interactions")
    .add("website_hr_recruitment.hr_recruitment_form", HrRecruitmentForm);
