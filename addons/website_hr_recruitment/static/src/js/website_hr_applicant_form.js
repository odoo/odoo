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
        const linkedin = $(ev.currentTarget).val();
        const field = "linkedin";
        const messageContainerId = "#linkedin-message";
        const linkedin_regex = /^(https?:\/\/)?([\w\.]*)linkedin\.com\/in\/(.*?)(\/.*)?$/;
        if (!linkedin_regex.test(linkedin)) {
            $('#linkedin-message').removeClass('alert-warning').hide();
            $(ev.currentTarget).addClass('border-warning');
            $('#linkedin-message').text(_t("The value entered doesn't seems like a linkedin profile.")).addClass('alert-warning').show();
        }

        await this.checkRedundant(ev.currentTarget, field, messageContainerId);
    },

    async checkRedundant(target, field, messageContainerId) {
        const value = $(target).val();
        if (!value) {
            $(target).removeClass("border-warning");
            $(messageContainerId).removeClass("alert-warning").hide();
            return;
        }
        const job_id = $('#recruitment7').val();
                const data = await rpc("/website_hr_recruitment/check_recent_application", {
            field: field,
            value: value,
            job_id: job_id,
        });

        if (data.applied_same_job) {
            $(messageContainerId).removeClass("alert-warning").hide();
            $(target).addClass("border-warning");
            $(messageContainerId).text(_t(data.message)).addClass("alert-warning").show();
        } else if (data.applied_other_job) {
            $(messageContainerId).removeClass("alert-warning").hide();
            $(target).addClass("border-warning");
            $(messageContainerId)
                .text(
                    _t(
                        "You already applied to another position recently. You can continue if it's not a mistake."
                    )
                )
                .addClass("alert-warning")
                .show();
        } else {
            $(target).removeClass("border-warning");
            $(messageContainerId).removeClass("alert-warning").hide();
        }
    },
});
