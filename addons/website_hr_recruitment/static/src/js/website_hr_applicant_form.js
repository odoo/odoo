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
        const linkedin_profile = document.querySelector('#recruitment4');
        const resume = document.querySelector('#recruitment6');

        const is_linkedin_empty = !linkedin_profile || linkedin_profile.value.trim() === '';
        const is_resume_empty = !resume || !resume.files.length;
        if (is_linkedin_empty && is_resume_empty) {
            linkedin_profile.setAttribute('required', true);
            resume.setAttribute('required', true);
        } else {
            linkedin_profile.removeAttribute('required');
            resume.removeAttribute('required');
        }
    },

    async _onFocusOutName(ev) {
        const field = "name"
        const messageContainerId = "#name-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutMail (ev) {
        const field = "email"
        const messageContainerId = "#email-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutPhone (ev) {
        const field = "phone"
        const messageContainerId = "#phone-message";
        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async _onFocusOutLinkedin (ev) {
        const linkedin = ev.currentTarget.value;
        const field = "linkedin";
        const messageContainerId = "#linkedin-message";
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        if (!linkedin_regex.test(linkedin)) {
            document.querySelector('#linkedin-message').classList.remove('alert-warning');
            document.querySelector('#linkedin-message').style.display = 'none';
            ev.currentTarget.classList.add('border-warning');
            document.querySelector('#linkedin-message').textContent = _t("The value entered doesn't seems like a linkedin profile.");
            document.querySelector('#linkedin-message').classList.add('alert-warning');
            document.querySelector('#linkedin-message').style.display = 'block';
        }

        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async checkRedundant(target, field, messageContainerId) {
        const value = target.value;
        if (!value) {
            target.classList.remove("border-warning");
            document.querySelector(messageContainerId).classList.remove("alert-warning");
            document.querySelector(messageContainerId).style.display = 'none';
            return;
        }
        const job_id = document.querySelector('#recruitment7').value;
        const data = await rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        });

        if (data.applied_same_job) {
            document.querySelector(messageContainerId).classList.remove("alert-warning");
            document.querySelector(messageContainerId).style.display = 'none';
            target.classList.add("border-warning");
            document.querySelector(messageContainerId).textContent = _t(data.message);
            document.querySelector(messageContainerId).classList.add("alert-warning");
            document.querySelector(messageContainerId).style.display = 'block';
        } else if (data.applied_other_job) {
            document.querySelector(messageContainerId).classList.remove("alert-warning");
            document.querySelector(messageContainerId).style.display = 'none';
            target.classList.add("border-warning");
            document.querySelector(messageContainerId).textContent = _t("You already applied to another position recently. You can continue if it's not a mistake.");
            document.querySelector(messageContainerId).classList.add("alert-warning");
            document.querySelector(messageContainerId).style.display = 'block';
        } else {
            target.classList.remove("border-warning");
            document.querySelector(messageContainerId).classList.remove("alert-warning");
            document.querySelector(messageContainerId).style.display = 'none';
        }
    },
});
