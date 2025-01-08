import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

import { parseDate, formatDate, serializeDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

const { DateTime } = luxon;

export class CRMPartnerAssign extends Interaction {
    static selector = "#wrapwrap";
    static selectorHas = ".interested_partner_assign_form, .desinterested_partner_assign_form, .opp-stage-button, .new_opp_form";
    dynamicContent = {
        ".interested_partner_assign_confirm": { "t-on-click.prevent.stop": this.locked(this.onInterestedPartnerConfirm) },
        ".desinterested_partner_assign_confirm": { "t-on-click.prevent.stop": this.locked(this.onDesinterestedPartnerConfirm) },
        ".opp-stage-button": { "t-on-click.withTarget": this.locked(this.onOppStageButtonClick) },
        ".edit_contact_confirm": { "t-on-click.prevent.stop": this.locked(this.editContact) },
        ".new_opp_confirm": { "t-on-click.prevent.stop": this.locked(this.createOpportunity) },
        ".edit_opp_confirm": { "t-on-click.prevent.stop": this.locked(this.editOpportunity) },
        ".edit_opp_form .next_activity": { "t-on-change": this.onChangeNextActivity },
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
                "display": this.confirmationFailed ? "block" : undefined,
            }),
        },
    };

    async confirmInterestedPartner() {
        await this.services.orm.call("crm.lead", "partner_interested", [
            [parseInt(this.el.querySelector(".interested_partner_assign_form .assign_lead_id").value)],
            this.el.querySelector(".interested_partner_assign_form .comment_interested").value,
        ]);
        window.location.href = "/my/leads";
    }

    async onDesinterestedPartnerConfirm() {
        await this.services.orm.call("crm.lead", "partner_desinterested", [
            [parseInt(this.el.querySelector(".desinterested_partner_assign_form .assign_lead_id").value)],
            this.el.querySelector(".desinterested_partner_assign_form .comment_desinterested").value,
            this.el.querySelector(".desinterested_partner_assign_form .contacted_desinterested").checked,
            this.el.querySelector(".desinterested_partner_assign_form .customer_mark_spam").checked,
        ]);
        window.location.href = "/my/leads";
    }

    async changeOppStage(leadID, stageID) {
        await this.services.orm.write("crm.lead", [leadID], { stage_id: stageID }, {
            context: Object.assign({ website_partner_assign: 1 }),
        });
        window.location.reload();
    }

    async editContact() {
        await this.services.orm.call("crm.lead", "update_contact_details_from_portal", [
            [parseInt(this.el.querySelector(".edit_contact_form .opportunity_id").value)],
            {
                partner_name: this.el.querySelector(".edit_contact_form .partner_name").value,
                phone: this.el.querySelector(".edit_contact_form .phone").value,
                mobile: this.el.querySelector(".edit_contact_form .mobile").value,
                email_from: this.el.querySelector(".edit_contact_form .email_from").value,
                street: this.el.querySelector(".edit_contact_form .street").value,
                street2: this.el.querySelector(".edit_contact_form .street2").value,
                city: this.el.querySelector(".edit_contact_form .city").value,
                zip: this.el.querySelector(".edit_contact_form .zip").value,
                state_id: parseInt(this.el.querySelector(".edit_contact_form .state_id").selectedOptions[0].value),
                country_id: parseInt(this.el.querySelector(".edit_contact_form .country_id").selectedOptions[0].value),
            },
        ]);
        window.location.reload();
    }

    async createOpportunity() {
        const response = await this.services.orm.call("crm.lead", "create_opp_portal", [{
            contact_name: this.el.querySelector(".new_opp_form .contact_name").value,
            title: this.el.querySelector(".new_opp_form .title").value,
            description: this.el.querySelector(".new_opp_form .description").value,
        }]);
        if (response.errors) {
            this.el.querySelector("#new-opp-dialog .alert")?.remove();
            const alertEl = this.el.createElement("div");
            alertEl.classList.add("alert", "alert-danger");
            alertEl.textContent = response.errors;
            const parentEl = this.el.querySelector("#new-opp-dialog");
            this.insert(alertEl, parentEl, "afterbegin");
        } else {
            window.location = "/my/opportunity/" + response.id;
        }
    }

    async editOpportunity() {
        const checkAndParseDate = function (value) {
            var date = parseDate(value);
            if (!date.isValid || date.year < 1900) {
                return false;
            }
            return serializeDate(date);
        }

        await this.services.orm.call("crm.lead", "update_lead_portal", [
            [parseInt(this.el.querySelector(".edit_opp_form .opportunity_id").value)],
            {
                date_deadline: checkAndParseDate(this.el.querySelector(".edit_opp_form .date_deadline").value),
                expected_revenue: parseFloat(this.el.querySelector(".edit_opp_form .expected_revenue").value),
                probability: parseFloat(this.el.querySelector(".edit_opp_form .probability").value),
                activity_type_id: parseInt(this.el.querySelector(".edit_opp_form .next_activity").selectedOptions[0].getAttribute("data")),
                activity_summary: this.el.querySelector(".edit_opp_form .activity_summary").value,
                activity_date_deadline: checkAndParseDate(this.el.querySelector(".edit_opp_form .activity_date_deadline").value),
                priority: this.el.querySelector("input[name='PriorityRadioOptions']:checked").value,
            },
        ]);
        window.location.reload();
    }

    async onInterestedPartnerConfirm() {
        const comment = this.el.querySelector(".interested_partner_assign_form .comment_interested").value;
        const contacted = this.el.querySelector(".interested_partner_assign_form .contacted_interested").checked;
        this.confirmationFailed = !(comment && contacted);
        if (!this.confirmationFailed) {
            await this.confirmInterestedPartner();
        }
    }

    async onOppStageButtonClick(ev, currentTargetEl) {
        await this.changeOppStage(parseInt(currentTargetEl.getAttribute("opp")), parseInt(currentTargetEl.getAttribute("data")));
    }

    onChangeNextActivity() {
        const selectedEl = this.el.querySelector(".edit_opp_form .next_activity").selectedOptions[0];
        if (selectedEl.getAttribute("activity_summary")) {
            this.el.querySelector(".edit_opp_form .activity_summary").value = selectedEl.getAttribute("activity_summary");
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
