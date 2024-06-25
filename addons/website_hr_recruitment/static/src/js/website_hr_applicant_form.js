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
        const $linkedin_profile = $('#recruitment4');
        const $resume = $('#recruitment6');

        const is_linkedin_empty = !$linkedin_profile.length || $linkedin_profile.val().trim() === '';
        const is_resume_empty = !$resume.length || !$resume[0].files.length;
        if (is_linkedin_empty && is_resume_empty) {
            $linkedin_profile.attr('required', true);
            $resume.attr('required', true);
        } else {
            $linkedin_profile.attr('required', false);
            $resume.attr('required', false);
        }
    },

    hideWarningMessage(target, messageContainerId) {
        $(target).removeClass("border-warning");
        $(messageContainerId).hide();
    },

    ShowWarningMessage(target, messageContainerId, message) {
        $(target).addClass("border-warning");
        $(messageContainerId).text(message).show();
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
        const target = $(ev.currentTarget);
        const linkedin = target.val();
        const field = "linkedin";
        const messageContainerId = "#linkedin-message";
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        let hasWarningMessage = false;
        if (!linkedin_regex.test(linkedin) && linkedin !== "") {
            const message = _t("The profile that you gave us doesn't seems like a linkedin profile")
            this.ShowWarningMessage(target, '#linkedin-message', message)
            hasWarningMessage = true;
        } else {
            this.hideWarningMessage(target, '#linkedin-message');
        }
        await this.checkRedundant(target, field, messageContainerId, hasWarningMessage);
    },

    async checkRedundant(target, field, messageContainerId, keepPreviousWarningMessage = false) {
        const value = $(target).val();
        if (!value) {
            this.hideWarningMessage(target, messageContainerId);
            return;
        }
        const job_id = $('#recruitment7').val();
        const data = await rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        });

        if (data.message) {
            this.ShowWarningMessage(target, messageContainerId, data.message);
        }
        else if (!keepPreviousWarningMessage) {
            this.hideWarningMessage(target, messageContainerId);
        }
    },
});
