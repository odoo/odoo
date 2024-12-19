import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

export class HrRecruitmentForm extends Interaction {
    static selector = "#hr_recruitment_form";
    dynamicContent = {
        "#apply-btn": { "t-on-click": this.onClickApplyButton },
        "#recruitment1": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "name", "#warning-message") },
        "#recruitment2": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "email", "#warning-message") },
        "#recruitment3": { "t-on-focusout": (ev) => this.checkRedundant(ev.currentTarget, "phone", "#warning-message") },
        "#recruitment4": { "t-on-focusout": this.onFocusOutLinkedin },
    };

    /**
    * @param {HTMLElement} targetEl
    * @param {string} messageContainerId
    */
    showWarningMessage(targetEl, messageContainerId) {
        targetEl.classList.add("border-warning");
        document.querySelector(messageContainerId).textContent = message;
        document.querySelector(messageContainerId).classList.remove("d-none");
    }

    /**
    * @param {HTMLElement} targetEl
    * @param {string} messageContainerId
    */
    hideWarningMessage(targetEl, messageContainerId) {
        targetEl.classList.remove("border-warning");
        document.querySelector(messageContainerId).classList.add("d-none");
    }

    async checkRedundant(targetEl, field, messageContainerId, keepPreviousWarningMessage = false) {
        const value = targetEl.value;
        if (!value) {
            this.hideWarningMessage(targetEl, messageContainerId);
            return;
        }
        const job_id = document.querySelector("#recruitment7").value;
        const data = await this.waitFor(rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        }));

        if (data.message) {
            this.showWarningMessage(targetEl, messageContainerId, data.message);
        } else if (!keepPreviousWarningMessage) {
            this.hideWarningMessage(targetEl, messageContainerId);
        }
    }

    onClickApplyButton() {
        const linkedinProfileEl = document.querySelector("#recruitment4");
        const resumeEl = document.querySelector("#recruitment6");

        const isLinkedinEmpty = !linkedinProfileEl || linkedinProfileEl.value.trim() === "";
        const isResumeEmpty = !resumeEl || !resumeEl.files.length;
        if (isLinkedinEmpty && isResumeEmpty) {
            linkedinProfileEl?.setAttribute("required", true);
            resumeEl?.setAttribute("required", true);
        } else {
            linkedinProfileEl?.removeAttribute("required");
            resumeEl?.removeAttribute("required");
        }
    }

    onFocusOutLinkedin(ev) {
        const targetEl = ev.currentTarget;
        const linkedin = targetEl.value;
        const field = "linkedin";
        const messageContainerId = "#linkedin-message";
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        if (!linkedin_regex.test(linkedin) && linkedin !== "") {
            const message = _t("The profile that you gave us doesn't seems like a linkedin profile")
            this.showWarningMessage(targetEl, messageContainerId, message);
            this.checkRedundant(targetEl, field, messageContainerId, true);
        } else {
            this.hideWarningMessage(targetEl, messageContainerId);
            this.checkRedundant(targetEl, field, messageContainerId, false);
        }
    }
}

registry
    .category("public.interactions")
    .add("website_hr_recruitment.hr_recruitment_form", HrRecruitmentForm);
