/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.hrRecruitment = publicWidget.Widget.extend({
    selector : '#hr_recruitment_form',
    events: {
        'click #apply-btn': '_onClickApplyButton',
        "focusout #recruitment1" : "_onFocusOutName",
        'focusout #recruitment2' : '_onFocusOutMail',
        "focusout #recruitment3" : "_onFocusOutPhone",
        'focusout #recruitment4' : '_onFocusOutLinkedin',
    },

    _onClickApplyButton (ev) {
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
    },

    hideWarningMessage(targetEl, messageContainerId) {
        targetEl.classList.remove("border-warning");
        document.querySelector(messageContainerId)?.classList.add("d-none");
    },

    showWarningMessage(targetEl, messageContainerId, message) {
        targetEl.classList.add("border-warning");
        document.querySelector(messageContainerId).textContent = message;
        document.querySelector(messageContainerId)?.classList.remove("d-none");
    },

    async _onFocusOutName(ev) {
        const field = "name"
        const messageContainerId = "#warning-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutMail (ev) {
        const field = "email"
        const messageContainerId = "#warning-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutPhone (ev) {
        const field = "phone"
        const messageContainerId = "#warning-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutLinkedin (ev) {
        const targetEl = ev.currentTarget;
        const linkedin = targetEl.value;
        const field = "linkedin";
        const messageContainerId = "#linkedin-message";
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        let hasWarningMessage = false;
        if (!linkedin_regex.test(linkedin) && linkedin !== "") {
            const message = _t("The profile that you gave us doesn't seems like a linkedin profile")
            this.showWarningMessage(targetEl, "#linkedin-message", message);
            hasWarningMessage = true;
        } else {
            this.hideWarningMessage(targetEl, "#linkedin-message");
        }
        await this.checkRedundant(targetEl, field, messageContainerId, hasWarningMessage);
    },

    async checkRedundant(targetEl, field, messageContainerId, keepPreviousWarningMessage = false) {
        const value = targetEl.value;
        if (!value) {
            this.hideWarningMessage(targetEl, messageContainerId);
            return;
        }
        const job_id = document.querySelector("#recruitment7").value;
        const data = await rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        });

        if (data.message) {
            this.showWarningMessage(targetEl, messageContainerId, data.message);
        } else if (!keepPreviousWarningMessage) {
            this.hideWarningMessage(targetEl, messageContainerId);
        }
    },
});
