/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import publicWidget from "@web/legacy/js/public/public_widget";
import { parseDate, formatDate, serializeDate } from "@web/core/l10n/dates";
const { DateTime } = luxon;

publicWidget.registry.crmPartnerAssign = publicWidget.Widget.extend({
    selector: '#wrapwrap:has(.interested_partner_assign_form, .desinterested_partner_assign_form, .opp-stage-button, .new_opp_form)',
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
     * @param {jQuery} $btn
     * @param {function} callback
     * @returns {Promise}
     */
    _buttonExec: function ($btn, callback) {
        // TODO remove once the automatic system which does this lands in master
        $btn.prop('disabled', true);
        return callback.call(this).catch(function (e) {
            $btn.prop('disabled', false);
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
            [parseInt($('.interested_partner_assign_form .assign_lead_id').val())],
            $('.interested_partner_assign_form .comment_interested').val()
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
            [parseInt($('.desinterested_partner_assign_form .assign_lead_id').val())],
            $('.desinterested_partner_assign_form .comment_desinterested').val(),
            $('.desinterested_partner_assign_form .contacted_desinterested').prop('checked'),
            $('.desinterested_partner_assign_form .customer_mark_spam').prop('checked'),
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
            [parseInt($('.edit_contact_form .opportunity_id').val())],
            {
                partner_name: $('.edit_contact_form .partner_name').val(),
                phone: $('.edit_contact_form .phone').val(),
                mobile: $('.edit_contact_form .mobile').val(),
                email_from: $('.edit_contact_form .email_from').val(),
                street: $('.edit_contact_form .street').val(),
                street2: $('.edit_contact_form .street2').val(),
                city: $('.edit_contact_form .city').val(),
                zip: $('.edit_contact_form .zip').val(),
                state_id: parseInt($('.edit_contact_form .state_id').find(':selected').attr('value')),
                country_id: parseInt($('.edit_contact_form .country_id').find(':selected').attr('value')),
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
            contact_name: $('.new_opp_form .contact_name').val(),
            title: $('.new_opp_form .title').val(),
            description: $('.new_opp_form .description').val(),
        }]).then(function (response) {
            if (response.errors) {
                $('#new-opp-dialog .alert').remove();
                $('#new-opp-dialog div:first').prepend('<div class="alert alert-danger">' + response.errors + '</div>');
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
            [parseInt($('.edit_opp_form .opportunity_id').val())],
            {
                date_deadline: this._parse_date($('.edit_opp_form .date_deadline').val()),
                expected_revenue: parseFloat($('.edit_opp_form .expected_revenue').val()),
                probability: parseFloat($('.edit_opp_form .probability').val()),
                activity_type_id: parseInt($('.edit_opp_form .next_activity').find(':selected').attr('data')),
                activity_summary: $('.edit_opp_form .activity_summary').val(),
                activity_date_deadline: this._parse_date($('.edit_opp_form .activity_date_deadline').val()),
                priority: $('input[name="PriorityRadioOptions"]:checked').val(),
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
        if ($('.interested_partner_assign_form .comment_interested').val() && $('.interested_partner_assign_form .contacted_interested').prop('checked')) {
            this._buttonExec($(ev.currentTarget), this._confirmInterestedPartner);
        } else {
            $('.interested_partner_assign_form .error_partner_assign_interested').css('display', 'block');
        }
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onDesinterestedPartnerAssignConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec($(ev.currentTarget), this._confirmDesinterestedPartner);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onOppStageButtonClick: function (ev) {
        var $btn = $(ev.currentTarget);
        this._buttonExec(
            $btn,
            this._changeOppStage.bind(this, parseInt($btn.attr('opp')), parseInt($btn.attr('data')))
        );
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditContactFormChange: function (ev) {
        var countryID = $('.edit_contact_form .country_id').find(':selected').attr('value');
        $('.edit_contact_form .state[country!=' + countryID + ']').css('display', 'none');
        $('.edit_contact_form .state[country=' + countryID + ']').css('display', 'block');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditContactConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec($(ev.currentTarget), this._editContact);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onNewOppConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec($(ev.currentTarget), this._createOpportunity);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onEditOppConfirm: function (ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this._buttonExec($(ev.currentTarget), this._editOpportunity);
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
        var $selected = $('.edit_opp_form .next_activity').find(':selected');
        if ($selected.attr('activity_summary')) {
            $('.edit_opp_form .activity_summary').val($selected.attr('activity_summary'));
        }
        if ($selected.attr('delay_count')) {
            const value = +$selected.attr('delay_count');
            const unit = $selected.attr('delay_unit');
            const date = DateTime.now().plus({ [unit]: value});
            $('.edit_opp_form .activity_date_deadline').val( formatDate(date) );
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
