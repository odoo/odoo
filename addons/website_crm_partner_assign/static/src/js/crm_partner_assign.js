odoo.define('crm.partner_assign', function (require) {
'use strict';

var Model = require('web.Model');
var website = require('website.website');
/*
 * This file is intended to add interactivity to survey forms rendered by
 * the website engine.
 */

var interested_form = $('.interested_partner_assign_form');
var desinterested_form = $('.desinterested_partner_assign_form');
var opp_stage_buttons = $('.opp-stage-button');
var new_opp_form = $('.new_opp_form');

if(!interested_form.length && !desinterested_form.length && !opp_stage_buttons.length && !new_opp_form.length) {
    return $.Deferred().reject("DOM doesn't contain website_crm_partner_assign elements");
}

$('.interested_partner_assign_confirm').on('click',function(e){
    var $btn = $(this);
    if ($('.interested_partner_assign_form .comment_interested').val() && $('.interested_partner_assign_form .contacted_interested').prop('checked')){
        $btn.prop('disabled', true);
        new Model('crm.lead')
            .call("partner_interested",[[parseInt($('.interested_partner_assign_form .assign_lead_id').val())], $('.interested_partner_assign_form .comment_interested').val()])
            .then(function(){
                window.location.href = '/my/leads';
            })
            .always(function() {
                $btn.prop('disabled', false);
            });
    }else{
        $('.interested_partner_assign_form .error_partner_assign_interested').css('display', 'block');
    }
    return false;
});


$('.desinterested_partner_assign_confirm').on('click',function(){
    var $btn = $(this);
    $btn.prop('disabled', true);
    new Model('crm.lead')
        .call("partner_desinterested",
            [[parseInt($('.desinterested_partner_assign_form .assign_lead_id').val())],
            $('.desinterested_partner_assign_form .comment_desinterested').val(),
            $('.desinterested_partner_assign_form .contacted_desinterested').prop('checked'),
            $('.desinterested_partner_assign_form .customer_mark_spam').prop('checked'),
            ])
        .then(function(){
            window.location.href = '/my/leads';
        }).always(function() {
            $btn.prop('disabled', false);
        });
    return false;
});

opp_stage_buttons.on('click',function(e){
    var $btn = $(this);
    $btn.prop('disabled', true);
    new Model('crm.lead')
        .call("write", [[parseInt(e.currentTarget.getAttribute('opp'))],{
            stage_id: parseInt(e.currentTarget.getAttribute('data')),
        },], {context: {website_partner_assign:1}})
        .fail(function() {
            $btn.prop('disabled', false);
        })
        .done(function () {
            window.location.reload();
        });
});

$('.edit_contact_form .country_id').on('change', function(){
    var country_id = $('.edit_contact_form .country_id').find(":selected").attr('value');
    $(".edit_contact_form .state[country!="+country_id+"]").css('display','none');
    $(".edit_contact_form .state[country="+country_id+"]").css('display','block');
});

$('.edit_contact_confirm').on('click',function(){
    var $btn = $(this);
    $btn.prop('disabled', true);
    new Model('crm.lead')
        .call("write", [[parseInt($('.edit_contact_form .opportunity_id').val())],{
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
        }])
        .fail(function() {
            $btn.prop('disabled', false);
        })
        .done(function(){
            window.location.reload();
        });
    return false;
});

$('.new_opp_confirm').on('click',function(e){
    new Model('crm.lead')
        .call("create_opp_portal", [{
            contact_name: $('.new_opp_form .contact_name').val(),
            title: $('.new_opp_form .title').val(),
            description: $('.new_opp_form .description').val(),
        }])
        .done(function(response){
            if (response.errors) {
                $('#new-opp-dialog .alert').remove();
                $('#new-opp-dialog div:first').prepend("<div class='alert alert-danger'>" + response.errors + "</div>");
            }
            else {
                window.location = '/my/opportunity/' + response.id;
            }
        });
    return false;
});

$('.edit_opp_confirm').on('click',function(){
    var $btn = $(this);
    $btn.prop('disabled', true);
    new Model('crm.lead')
        .call("update_lead_portal", [[parseInt($('.edit_opp_form .opportunity_id').val())],{
            date_deadline: $('.edit_opp_form .date_deadline').val(),
            planned_revenue: parseFloat($('.edit_opp_form .planned_revenue').val()),
            probability: parseFloat($('.edit_opp_form .probability').val()),
            activity_type_id: parseInt($('.edit_opp_form .next_activity').find(":selected").attr('data')),
            activity_summary: $('.edit_opp_form .activity_summary').val(),
            activity_date_deadline: $('.edit_opp_form .activity_date_deadline').val(),
            priority: $('input[name="PriorityRadioOptions"]:checked').val(),
        }])
        .fail(function() {
            $btn.prop('disabled', false);
        })
        .done(function(){
            window.location.reload();
        });
    return false;
});

$('.edit_opp_form .next_activity').on('change', function(){
    var selected = $('.edit_opp_form .next_activity').find(":selected");
    if(selected.attr('activity_summary')){
        $('.edit_opp_form .activity_summary').val(selected.attr('activity_summary'));
    }
    if(selected.attr('days')){
        var date_now = moment();
        var days = parseInt(selected.attr('days'));
        var date = date_now.add(days, 'days');
        $('.edit_opp_form .activity_date_deadline').val(date.format('YYYY-MM-DD'));
    }
});

$("div.input-group span.fa-calendar").on('click', function(e) {
    $(e.currentTarget).closest("div.date").datetimepicker({
        icons : {
            time: 'fa fa-clock-o',
            date: 'fa fa-calendar',
            up: 'fa fa-chevron-up',
            down: 'fa fa-chevron-down'
        },
    });
});
});