import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { parseDate, formatDate, serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class CRMPartnerAssign extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".interested_partner_assign_form, .desinterested_partner_assign_form, .opp-stage-button, .new_opp_form";
    dynamicContent = {
        ".interested_partner_assign_confirm": { "t-on-click.prevent.stop": this.locked(this.onInterestedPartnerConfirmClick) },
        ".desinterested_partner_assign_confirm": { "t-on-click.prevent.stop": this.locked(this.onDesinterestedPartnerConfirmClick) },
        ".opp-stage-button": { "t-on-click.withTarget": this.locked(this.onOppStageButtonClick) },
        ".edit_contact_confirm": { "t-on-click.prevent.stop": this.locked(this.onEditContactClick) },
        ".new_opp_confirm": { "t-on-click.prevent.stop": this.locked(this.onCreateOppClick) },
        ".edit_opp_confirm": { "t-on-click.prevent.stop": this.locked(this.onEditOppClick) },
        ".edit_opp_form .next_activity": { "t-on-change": this.onNextActivityChange },
        ".edit_opp_form .activity_date_deadline": { "t-att-value": () => formatDate(this.dateNextActivity) },
        "#new-opp-dialog .contact_name": { "t-on-change": (ev) => this.contactName = ev.currentTarget.value.trim() },
        ".title": { "t-att-value": (el) => this.contactName && !el.value.trim() ? _t("%s's Opportunity", this.contactName) : "" },
        ".edit_contact_form .country_id": { "t-on-change": (ev) => this.countryID = parseInt(ev.currentTarget.selectedOptions[0].value) },
        ".edit_contact_form .state": {
            "t-att-style": (el) => ({
                "display": el.getAttribute("country") != this.countryID ? "none" : "block",
            }),
        },
        ".interested_partner_assign_form .error_partner_assign_interested": {
            "t-att-style": () => ({
                "display": this.confirmationFailed ? "block" : "",
            }),
        },
    };

    setup() {
        this.newOppFormEl = this.el.querySelector(".new_opp_form");
        this.editOppFormEl = this.el.querySelector(".edit_opp_form");
        this.contactFormEl = this.el.querySelector(".edit_contact_form");
        this.interestedPartnerFormEl = this.el.querySelector(".interested_partner_assign_form");
        this.desinterestedPartnerFormEl = this.el.querySelector(".desinterested_partner_assign_form");
    }

    async confirmInterestedPartner() {
        await this.services.orm.call("crm.lead", "partner_interested", [
            [parseInt(this.interestedPartnerFormEl.querySelector(".assign_lead_id").value)],
            this.interestedPartnerFormEl.querySelector(".comment_interested").value,
        ]);
        window.location.href = "/my/leads";
    }

    async onDesinterestedPartnerConfirmClick() {
        await this.services.orm.call("crm.lead", "partner_desinterested", [
            [parseInt(this.desinterestedPartnerFormEl.querySelector(".assign_lead_id").value)],
            this.desinterestedPartnerFormEl.querySelector(".comment_desinterested").value,
            this.desinterestedPartnerFormEl.querySelector(".contacted_desinterested").checked,
            this.desinterestedPartnerFormEl.querySelector(".customer_mark_spam").checked,
        ]);
        window.location.href = "/my/leads";
    }

    /**
     * @param {number} leadID
     * @param {number} stageID
     */
    async changeOppStage(leadID, stageID) {
        await this.services.orm.write("crm.lead", [leadID], { stage_id: stageID }, {
            context: Object.assign({ website_partner_assign: 1 }),
        });
        window.location.reload();
    }

    async onEditContactClick() {
        await this.services.orm.call("crm.lead", "update_contact_details_from_portal", [
            [parseInt(this.contactFormEl.querySelector(".opportunity_id").value)],
            {
                partner_name: this.contactFormEl.querySelector(".partner_name").value,
                phone: this.contactFormEl.querySelector(".phone").value,
                email_from: this.contactFormEl.querySelector(".email_from").value,
                street: this.contactFormEl.querySelector(".street").value,
                street2: this.contactFormEl.querySelector(".street2").value,
                city: this.contactFormEl.querySelector(".city").value,
                zip: this.contactFormEl.querySelector(".zip").value,
                state_id: parseInt(this.contactFormEl.querySelector(".state_id").selectedOptions[0].value),
                country_id: parseInt(this.contactFormEl.querySelector(".country_id").selectedOptions[0].value),
            },
        ]);
        window.location.reload();
    }

    async onCreateOppClick() {
        const response = await this.services.orm.call("crm.lead", "create_opp_portal", [{
            contact_name: this.newOppFormEl.querySelector(".contact_name").value,
            title: this.newOppFormEl.querySelector(".title").value,
            description: this.newOppFormEl.querySelector(".description").value,
        }]);
        if (response.errors) {
            this.el.querySelector("#new-opp-dialog .alert")?.remove();
            const alertEl = this.el.createElement("div");
            alertEl.classList.add("alert", "alert-danger");
            alertEl.textContent = response.errors;
            const parentEl = this.el.querySelector("#new-opp-dialog");
            this.insert(alertEl, parentEl, "afterbegin");
        } else {
            window.location = `/my/opportunity/${parseInt(response.id)}`;
        }
    }

    async onEditOppClick() {
        const checkAndParseDate = function (value) {
            var date = parseDate(value);
            if (!date.isValid || date.year < 1900) {
                return false;
            }
            return serializeDate(date);
        }

        await this.services.orm.call("crm.lead", "update_lead_portal", [
            [parseInt(this.editOppFormEl.querySelector(".opportunity_id").value)],
            {
                date_deadline: checkAndParseDate(this.editOppFormEl.querySelector(".date_deadline").value),
                expected_revenue: parseFloat(this.editOppFormEl.querySelector(".expected_revenue").value),
                probability: parseFloat(this.editOppFormEl.querySelector(".probability").value),
                activity_type_id: parseInt(this.editOppFormEl.querySelector(".next_activity").selectedOptions[0].getAttribute("data")),
                activity_summary: this.editOppFormEl.querySelector(".activity_summary").value,
                activity_date_deadline: checkAndParseDate(this.editOppFormEl.querySelector(".activity_date_deadline").value),
                priority: this.el.querySelector("input[name='PriorityRadioOptions']:checked").value,
            },
        ]);
        window.location.reload();
    }

    async onInterestedPartnerConfirmClick() {
        const comment = this.interestedPartnerFormEl.querySelector(".comment_interested").value;
        const contacted = this.interestedPartnerFormEl.querySelector(".contacted_interested").checked;
        this.confirmationFailed = !(comment && contacted);
        if (!this.confirmationFailed) {
            await this.confirmInterestedPartner();
        }
    }

    async onOppStageButtonClick(ev, currentTargetEl) {
        await this.changeOppStage(parseInt(currentTargetEl.getAttribute("opp")), parseInt(currentTargetEl.getAttribute("data")));
    }

    onNextActivityChange() {
        const selectedEl = this.editOppFormEl.querySelector(".next_activity").selectedOptions[0];
        if (selectedEl.getAttribute("activity_summary")) {
            this.editOppFormEl.querySelector(".activity_summary").value = selectedEl.getAttribute("activity_summary");
        }
        if (selectedEl.getAttribute("delay_count")) {
            const delayCount = parseInt(selectedEl.getAttribute("delay_count"));
            const delayUnit = selectedEl.getAttribute("delay_unit");
            this.dateNextActivity = DateTime.now().plus({ [delayUnit]: delayCount });
        }
    }
}

registry
    .category("public.interactions")
    .add("website_crm_partner_assign.crm_partner_assign", CRMPartnerAssign);
