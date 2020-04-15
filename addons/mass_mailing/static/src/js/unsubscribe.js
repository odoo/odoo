odoo.define('mass_mailing.unsubscribe', function (require) {
    'use strict';

    var session = require('web.session');
    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');

    var _t = core._t;

    var email = $("input[name='email']").val();
    var mailing_id = parseInt($("input[name='mailing_id']").val());
    var res_id = parseInt($("input[name='res_id']").val());
    var token = (location.search.split('token' + '=')[1] || '').split('&')[0];
    var demo_mode = $("input[name='demo_mode']").val();
    var show_blacklist_button = $("input[name='show_blacklist_button']").val();

    if (!$('.o_unsubscribe_form').length) {
        return Promise.reject("DOM doesn't contain '.o_unsubscribe_form'");
    }

    session.load_translations().then(function () {
        if (email != '' && email != undefined){
            ajax.jsonRpc('/mailing/blacklist/check', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#button_add_blacklist').hide();
                        $('#button_remove_blacklist').hide();
                    }
                    else if (result == true) {
                        $('#button_remove_blacklist').show();
                        toggle_opt_out_section(false);
                    }
                    else if (result == false) {
                        $('#button_add_blacklist').show();
                        toggle_opt_out_section(true);
                    }
                    else {
                        $('#subscription_info h2').html(_t('An error occured. Please try again later or contact us.'));
                    }
                })
                .guardedCatch(function () {
                    $('#subscription_info h2').html(_t('An error occured. Please try again later or contact us.'));
                });
        }
        else {
            if(demo_mode && show_blacklist_button){
                $('#button_add_blacklist').show();
                toggle_opt_out_section(false);
            }
            $('#div_blacklist').hide();
        }

        var unsubscribed_list = $("input[name='unsubscribed_list']").val();
        if (unsubscribed_list){
            $('#subscription_info h2').html(_.str.sprintf(
                _t("You're no long part of the %s Mailing List."),
                unsubscribed_list
            ));
        }
        else{
            $('#subscription_info h2').html(_t("You're no longer part of this Mailing List."));
        }
    });

    $('#unsubscribe_form').on('submit', function (e) {
        e.preventDefault();

        var checked_ids = [];
        $("input[type='checkbox']:checked").each(function (i){
          checked_ids[i] = parseInt($(this).val());
        });

        var unchecked_ids = [];
        $("input[type='checkbox']:not(:checked)").each(function (i){
          unchecked_ids[i] = parseInt($(this).val());
        });

        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'opt_in_ids': checked_ids, 'opt_out_ids': unchecked_ids, 'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    $('#unsubscribe_form_status').html(_t(' You are not authorized to do this!'));
                    $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                }
                else if (result == true) {
                    $('#unsubscribe_form_status').html(_t(' Your changes have been saved.'));
                    $('#unsubscribe_form_status').removeClass('text-danger').removeClass('fa-times').addClass('text-success').addClass('fa-check');
                }
                else {
                    $('#unsubscribe_form_status').html(_t(' An error occurred. Your changes have not been saved, try again later.'));
                    $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                }
            })
            .guardedCatch(function () {
                $('#unsubscribe_form_status').html(_t(' An error occurred. Your changes have not been saved, try again later.'));
                $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
            });
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist').click(function (e) {
        e.preventDefault();
        if(!$('#button_add_blacklist').hasClass('disabled')){
            ajax.jsonRpc('/mailing/blacklist/add', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#unsubscribe_form_status').html(_t(' You are not authorized to do this!'));
                        $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                    }
                    else
                    {
                        if (result) {
                            $('#unsubscribe_form_status').html(_t(' Email address added to our blacklist.'));
                            $('#unsubscribe_form_status').removeClass('text-danger').removeClass('fa-times').addClass('text-success').addClass('fa-check');
                            toggle_opt_out_section(false);
                        }
                        else {
                            $('#unsubscribe_form_status').html(_t(' An error occured. Please try again later or contact us.'));
                            $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                        }
                        $('#button_add_blacklist').hide();
                        $('#button_remove_blacklist').show();
                    }
                })
                .guardedCatch(function () {
                    $('#unsubscribe_form_status').html(_t(' An error occured. Please try again later or contact us.'));
                    $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                });
        }
    });

    $('#button_remove_blacklist').click(function (e) {
        e.preventDefault();
        if(!$('#button_remove_blacklist').hasClass('disabled')){
            ajax.jsonRpc('/mailing/blacklist/remove', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#unsubscribe_form_status').html(_t(' You are not authorized to do this!'));
                        $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                    }
                    else
                    {
                        if (result) {
                            $('#unsubscribe_form_status').html(_t(" Email address removed from our blacklist."));
                            $('#unsubscribe_form_status').removeClass('text-danger').removeClass('fa-times').addClass('text-success').addClass('fa-check');
                            toggle_opt_out_section(true);
                        }
                        else {
                            $('#unsubscribe_form_status').html(_t(' An error occured. Please try again later or contact us.'));
                            $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                        }
                        $('#button_add_blacklist').show();
                        $('#button_remove_blacklist').hide();
                    }
                })
                .guardedCatch(function () {
                    $('#unsubscribe_form_status').html(_t(' An error occured. Please try again later or contact us.'));
                    $('#unsubscribe_form_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                });
        }
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback').click(function (e) {
        e.preventDefault();
        if(!$('#button_feedback').hasClass('disabled')){
            var key = $('#opt_out_reason').attr('key');
            var reason = key !== "other" ? $('#opt_out_reason')["0"].innerText : $("textarea[name='opt_out_feedback']").val();
            var feedback = {key: key, reason: reason};
            ajax.jsonRpc('/mailing/feedback', 'call', {'mailing_id': mailing_id, 'res_id': res_id, 'email': email, 'feedback': feedback, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#feedback_status').html(_t(' You are not authorized to do this!'));
                        $('#feedback_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                    }
                    else if (result == 'notImplemented') {
                        $('#feedback_status').html(_t(" Feedback can't be sent for this type of model "));
                        $('#feedback_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                    }
                    else if (result == true){
                        $('#feedback_status').html(_t(' Thank you! Your feedback has been sent successfully!'));
                        $('#feedback_status').removeClass('text-danger').removeClass('fa-times').addClass('text-success').addClass('fa-check');
                        $('#button_feedback').addClass('disabled');
                    }
                    else if (result == false){
                        $('#feedback_status').html(_t(" You are still part of this mailing list. You can't provide feedback!"));
                        $('#feedback_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');

                    }
                    else {
                        $('#feedback_status').html(_t(' An error occured. Please try again later or contact us.'));
                        $('#feedback_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                    }
                })
                .guardedCatch(function () {
                    $('#feedback_status').html(_t( 'An error occured. Please try again later or contact us.'));
                    $('#feedback_status').removeClass('text-success').removeClass('fa-check').addClass('text-danger').addClass('fa-times');
                });
        }
    });

    $("input.unsubscribe_reason").click(function(e){
        $('#opt_out_reason').html(_.str.sprintf(_t("%s"), e.currentTarget.value)).attr("key", e.currentTarget.id);
        $("textarea[name='opt_out_feedback']").toggleClass('d-none', e.currentTarget.id !== 'other');
    });
});

function toggle_opt_out_section(value) {
    var result = !value;
    $("#div_opt_out").find('*').attr('disabled',result);
    $("#button_add_blacklist").attr('disabled', false);
    $("#button_remove_blacklist").attr('disabled', false);
    if (value) { $('[name="button_subscription"]').addClass('clickable');  }
    else { $('[name="button_subscription"]').removeClass('clickable'); }
}
