odoo.define('crm.partner_assign', function (require) {
'use strict';

var sAnimations = require('website.content.snippets.animation');

/*
 * This file is intended to add interactivity to survey forms rendered by
 * the website engine.
 */

sAnimations.registry.crmPartnerAssign = sAnimations.Class.extend({
    selector: "#portal_my_lead:has(.interested_partner_assign_form,.desinterested_partner_assign_form,.opp-stage-button,.new_opp_form')",
    read_events: {
        'click .interested_partner_assign_confirm': '_onInterestedPartnerAssignConfirm',
        'click .desinterested_partner_assign_confirm': '_onDesinterestedPartnerAssignConfirm',
        'click .opp-stage-button': '_onOppStageButtons',
        'change .edit_contact_form .country_id': '_onEditContactForm',
        'click .edit_contact_confirm': '_onEditContactConfirm',
        'click .new_opp_confirm': '_onNewOppConfirm',
        'click .edit_opp_confirm': '_onEditOppConfirm',
        'change .edit_opp_form .next_activity': '_onEditOppConfirm',
        'click div.input-group span.fa-calendar': '_onCalendarIcon'
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @override
     * @param {Object} ev
     */
    _onInterestedPartnerAssignConfirm: function (ev) {
        var $btn = $(ev.currentTarget);
        if ($('.interested_partner_assign_form .comment_interested').val() && $('.interested_partner_assign_form .contacted_interested').prop('checked')){
            $btn.prop('disabled', true);
            this._rpc({
                    model: 'crm.lead',
                    method: "partner_interested",
                    args: [
                        [parseInt($('.interested_partner_assign_form .assign_lead_id').val())],
                        $('.interested_partner_assign_form .comment_interested').val()
                    ],
                })
                .then(function (){
                    window.location.href = '/my/leads';
                })
                .always(function () {
                    $btn.prop('disabled', false);
                });
        } else {
            $('.interested_partner_assign_form .error_partner_assign_interested').css('display', 'block');
        }
        return false;
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onDesinterestedPartnerAssignConfirm: function (ev) {
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        this._rpc({
                model: 'crm.lead',
                method: 'partner_desinterested',
                args: [
                    [parseInt($('.desinterested_partner_assign_form .assign_lead_id').val())],
                    $('.desinterested_partner_assign_form .comment_desinterested').val(),
                    $('.desinterested_partner_assign_form .contacted_desinterested').prop('checked'),
                    $('.desinterested_partner_assign_form .customer_mark_spam').prop('checked'),
                ],
            })
            .then(function (){
                window.location.href = '/my/leads';
            }).always(function () {
                $btn.prop('disabled', false);
            });
        return false;
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onOppStageButtons: function (ev) {
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        this._rpc({
                model: 'crm.lead',
                method: 'write',
                args: [[parseInt(ev.currentTarget.getAttribute('opp'))],{
                    stage_id: parseInt(ev.currentTarget.getAttribute('data')),
                },],
                context: _.extend({website_partner_assign:1}),
            })
            .fail(function () {
                $btn.prop('disabled', false);
            })
            .done(function () {
                window.location.reload();
            });
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onEditContactForm: function (ev) {
        var country_id = $('.edit_contact_form .country_id').find(":selected").attr('value');
        $(".edit_contact_form .state[country!="+country_id+"]").css('display','none');
        $(".edit_contact_form .state[country="+country_id+"]").css('display','block');
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onEditContactConfirm: function (ev) {
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        this._rpc({
                model: 'crm.lead',
                method: "write",
                args: [[parseInt($('.edit_contact_form .opportunity_id').val())],{
                    partner_name: $('.edit_contact_form .partner_name').val(),
                    phone: $('.edit_contact_form .phone').val(),
                    mobile: $('.edit_contact_form .mobile').val(),
                    email_from: $('.edit_contact_form .email_from').val(),
                    street: $('.edit_contact_form .street').val(),
                    street2: $('.edit_contact_form .street2').val(),
                    city: $('.edit_contact_form .city').val(),
                    zip: $('.edit_contact_form .zip').val(),
                    state_id: parseInt($('.edit_contact_form .state_id').find(":selected").attr('value')),
                    country_id: parseInt($('.edit_contact_form .country_id').find(":selected").attr('value')),
                }],
            })
            .fail(function () {
                $btn.prop('disabled', false);
            })
            .done(function (){
                window.location.reload();
            });
        return false;
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onNewOppConfirm: function (ev) {
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        this._rpc({
                model: 'crm.lead',
                method: 'create_opp_portal',
                args: [{
                    contact_name: $('.new_opp_form .contact_name').val(),
                    title: $('.new_opp_form .title').val(),
                    description: $('.new_opp_form .description').val(),
                }],
            })
            .done(function (response){
                if (response.errors) {
                    $('#new-opp-dialog .alert').remove();
                    $('#new-opp-dialog div:first').prepend("<div class='alert alert-danger'>" + response.errors + "</div>");
                    $btn.prop('disabled', false);

                }
                else {
                    window.location = '/my/opportunity/' + response.id;
                }
            })
            .fail(function () {
                $btn.prop('disabled', false);
            });
        return false;
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onEditOppConfirm: function (ev) {
        var $btn = $(ev.currentTarget);
        $btn.prop('disabled', true);
        this._rpc({
                model: 'crm.lead',
                method: 'update_lead_portal',
                args: [[parseInt($('.edit_opp_form .opportunity_id').val())],{
                    date_deadline: $('.edit_opp_form .date_deadline').val(),
                    planned_revenue: parseFloat($('.edit_opp_form .planned_revenue').val()),
                    probability: parseFloat($('.edit_opp_form .probability').val()),
                    activity_type_id: parseInt($('.edit_opp_form .next_activity').find(":selected").attr('data')),
                    activity_summary: $('.edit_opp_form .activity_summary').val(),
                    activity_date_deadline: $('.edit_opp_form .activity_date_deadline').val(),
                    priority: $('input[name="PriorityRadioOptions"]:checked').val(),
                }],
            })
            .fail(function () {
                $btn.prop('disabled', false);
            })
            .done(function (){
                window.location.reload();
            });
        return false;
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onEditOppForm: function (ev) {
        var selected = $('.edit_opp_form .next_activity').find(":selected");
        if (selected.attr('activity_summary')){
            $('.edit_opp_form .activity_summary').val(selected.attr('activity_summary'));
        }
        if (selected.attr('days')){
            var date_now = moment();
            var days = parseInt(selected.attr('days'));
            var date = date_now.add(days, 'days');
            $('.edit_opp_form .activity_date_deadline').val(date.format('YYYY-MM-DD'));
        }
    },
    /**
     * @override
     * @param {Object} ev
     */
    _onCalendarIcon: function (ev) {
        $(ev.currentTarget).closest("div.date").datetimepicker({
            icons : {
                time: 'fa fa-clock-o',
                date: 'fa fa-calendar',
                up: 'fa fa-chevron-up',
                down: 'fa fa-chevron-down'
            },
        });
    },

});

});
