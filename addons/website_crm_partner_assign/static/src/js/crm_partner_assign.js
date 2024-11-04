import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { parseDate, formatDate, serializeDate } from "@web/core/l10n/dates";
const { DateTime } = luxon;

publicWidget.registry.crmPartnerAssign = publicWidget.Widget.extend({
    selector: '#wrapwrap',
    selectorHas: '.interested_partner_assign_form, .desinterested_partner_assign_form, .opp-stage-button, .new_opp_form',
    events: {
        'click .interested_partner_assign_confirm': '_onInterestedPartnerAssignConfirm',
        'click .desinterested_partner_assign_confirm': '_onDesinterestedPartnerAssignConfirm',
        'click .opp-stage-button': '_onOppStageButtonClick',
        'change .edit_contact_form .country_id': '_onEditContactFormChange',
        'click .edit_contact_confirm': '_onEditContactConfirm',
        'click .new_opp_confirm': '_onNewOppConfirm',
        'click .edit_opp_confirm': '_onEditOppConfirm',
        'change .edit_opp_form .next_activity': '_onChangeNextActivity',
        'change #new-opp-dialog .contact_name': '_onChangeContactName',
    },

    init() {
        this._super(...arguments);
        this.orm = this.bindService("orm");
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Element} btnEl
     * @param {function} callback
     * @returns {Promise}
     */
    _buttonExec: function (btnEl, callback) {
        // TODO remove once the automatic system which does this lands in master
        btnEl.setAttribute("disabled", true);
        return callback.call(this).catch(function (e) {
            btnEl.removeAttribute("disabled");
            if (e instanceof Error) {
                return Promise.reject(e);
            }
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _confirmInterestedPartner: function () {
        return this.orm.call("crm.lead", "partner_interested", [
            [parseInt(document.querySelector(".interested_partner_assign_form .assign_lead_id").value)],
            document.querySelector(".interested_partner_assign_form .comment_interested").value
        ]).then(function () {
            window.location.href = '/my/leads';
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _confirmDesinterestedPartner: function () {
        return this.orm.call("crm.lead", "partner_desinterested", [
            [parseInt(document.querySelector(".desinterested_partner_assign_form .assign_lead_id").value)],
            document.querySelector(".desinterested_partner_assign_form .comment_desinterested").value,
            document.querySelector(".desinterested_partner_assign_form .contacted_desinterested").checked,
            document.querySelector(".desinterested_partner_assign_form .customer_mark_spam").checked,
        ]).then(function () {
            window.location.href = '/my/leads';
        });
    },
    /**
     * @private
     * @param {}
     * @returns {Promise}
     */
    _changeOppStage: function (leadID, stageID) {
        return this.orm.write("crm.lead", [leadID], { stage_id: stageID }, {
            context: Object.assign({website_partner_assign: 1}),
        }).then(function () {
            window.location.reload();
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _editContact: function () {
        return this.orm.call("crm.lead", "update_contact_details_from_portal", [
            [parseInt(document.querySelector(".edit_contact_form .opportunity_id").value)],
            {
                partner_name: document.querySelector(".edit_contact_form .partner_name").value,
                phone: document.querySelector(".edit_contact_form .phone").value,
                mobile: document.querySelector(".edit_contact_form .mobile").value,
                email_from: document.querySelector(".edit_contact_form .email_from").value,
                street: document.querySelector(".edit_contact_form .street").value,
                street2: document.querySelector(".edit_contact_form .street2").value,
                city: document.querySelector(".edit_contact_form .city").value,
                zip: document.querySelector(".edit_contact_form .zip").value,
                state_id: parseInt(document.querySelector(".edit_contact_form .state_id").selectedOptions[0].value),
                country_id: parseInt(document.querySelector(".edit_contact_form .country_id").selectedOptions[0].value),
            },
        ]).then(function () {
            window.location.reload();
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _createOpportunity: function () {
        return this.orm.call("crm.lead", "create_opp_portal", [{
            contact_name: document.querySelector(".new_opp_form .contact_name").value,
            title: document.querySelector(".new_opp_form .title").value,
            description: document.querySelector(".new_opp_form .description").value,
        }]).then(function (response) {
            if (response.errors) {
                document.querySelector("#new-opp-dialog .alert")?.remove();
                const alertEl = document.createElement("div");
                alertEl.classList.add("alert", "alert-danger");
                alertEl.textContent = response.errors;
                const parentEl = document.querySelector("#new-opp-dialog");
                parentEl.insertBefore(alertEl, parentEl.firstElementChild);
                return Promise.reject(response);
            } else {
                window.location = '/my/opportunity/' + response.id;
            }
        });
    },
    /**
     * @private
     * @returns {Promise}
     */
    _editOpportunity: function () {
        return this.orm.call("crm.lead", "update_lead_portal", [
            [parseInt(document.querySelector(".edit_opp_form .opportunity_id").value)],
            {
                date_deadline: this._parse_date(document.querySelector(".edit_opp_form .date_deadline").value),
                expected_revenue: parseFloat(document.querySelector(".edit_opp_form .expected_revenue").value),
                probability: parseFloat(document.querySelector(".edit_opp_form .probability").value),
                activity_type_id: parseInt(document.querySelector(".edit_opp_form .next_activity").selectedOptions[0].getAttribute("data")),
                activity_summary: document.querySelector(".edit_opp_form .activity_summary").value,
                activity_date_deadline: this._parse_date(document.querySelector(".edit_opp_form .activity_date_deadline").value),
                priority: document.querySelector("input[name='PriorityRadioOptions']:checked").value,
            },
        ]).then(function () {
            window.location.reload();
        });
    },


    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onInterestedPartnerAssignConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        if (document.querySelector(".interested_partner_assign_form .comment_interested").value && document.querySelector(".interested_partner_assign_form .contacted_interested").checked) {
            this._buttonExec(ev.currentTarget, this._confirmInterestedPartner);
        } else {
            document.querySelector(".interested_partner_assign_form .error_partner_assign_interested").style.display = "block";
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDesinterestedPartnerAssignConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec(ev.currentTarget, this._confirmDesinterestedPartner);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onOppStageButtonClick: function (ev) {
        const btnEl = ev.currentTarget;
        this._buttonExec(
            btnEl,
            this._changeOppStage.bind(this, parseInt(btnEl.getAttribute("opp")), parseInt(btnEl.getAttribute("data")))
        );
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditContactFormChange: function (ev) {
        var countryID = document.querySelector(".edit_contact_form .country_id").selectedOptions[0].value;
        document.querySelectorAll(".edit_contact_form .state").forEach(state => {
            state.style.display = state.getAttribute("country") != countryID ? "none" : "block";
        });
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditContactConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec(ev.currentTarget, this._editContact);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onNewOppConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec(ev.currentTarget, this._createOpportunity);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditOppConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec(ev.currentTarget, this._editOpportunity);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeContactName: function (ev) {
        const contactName = ev.currentTarget.value.trim();
        let titleEl = this.el.querySelector('.title');
        if (!titleEl.value.trim()) {
            titleEl.value = contactName ? _t("%s's Opportunity", contactName) : '';
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onChangeNextActivity: function (ev) {
        const selectedEl = document.querySelector(".edit_opp_form .next_activity").selectedOptions[0];
        if (selectedEl.getAttribute("activity_summary")) {
            document.querySelector(".edit_opp_form .activity_summary").value = selectedEl.getAttribute("activity_summary");
        }
        if (selectedEl.getAttribute("delay_count")) {
            const value = +selectedEl.getAttribute("delay_count");
            const unit = selectedEl.getAttribute("delay_unit");
            const date = DateTime.now().plus({ [unit]: value});
            document.querySelector(".edit_opp_form .activity_date_deadline").value = formatDate(date);
        }
    },
    _parse_date: function (value) {
        var date = parseDate(value);
        if (!date.isValid || date.year < 1900) {
            return false;
        }
        return serializeDate(date);
    },
});
