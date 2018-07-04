//=============================================================
// Unsubscribe page for all models except mass Mailing contacts
//=============================================================
odoo.define('mass_mailing.unsubscribed', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');
    var _t = core._t;

    var email = $("input[name='email']").val();
    var mailing_id = parseInt($("input[name='mailing_id']").val());
    var res_id = parseInt($("input[name='res_id']").val());
    var token = (location.search.split('token' + '=')[1] || '').split('&')[0];
    check_email(ajax, email);

    //  ==================
    //      Opt-out
    //  ==================
    $('#button_re_subscribe').click(function (e) {
        if ($('#button_re_subscribe').hasClass('clickable')) {
            call_subscribe_contact(ajax, _t, e, email, mailing_id, res_id, token);
        }
    });

    $('#button_unsubscribe').click(function (e) {
        if ($('#button_unsubscribe').hasClass('clickable')) {
            e.preventDefault();
            ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'mailing_id': mailing_id, 'opt_in_ids': [], 'opt_out_ids': [res_id], 'email': email, 'res_id': res_id, 'token': token})
                .then(function (result) {
                    if (result == 'unauthorized'){
                        $('#subscription_info').html(_t('You are not authorized to do this!'))
                         .removeClass('alert-success').removeClass('alert-info')
                         .addClass('alert-warning');
                    }
                    else {
                        $('#div_unsubscribed').show();
                        $('#div_contact_subscribed').hide();
                        $('#div_subscription_message').html(_t('You have been successfully <strong>unsubscribed</strong>!'))
                         .removeClass('alert-warning').addClass('alert-success');
                    }
                })
                .fail(function () {
                    $('#div_subscription_message').html(_t('An error occured. Please try again later or contact us.'))
                    .removeClass('alert-success').addClass('alert-warning');
                });
        }
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist').click(function (e) {
        call_add_to_blacklist(ajax, e, _t, mailing_id, res_id, email, token);
    });

    $('#button_remove_blacklist').click(function (e) {
        call_remove_from_blacklist(ajax, e, _t, mailing_id, res_id, email, token);
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback').click(function (e) {
        var feedback = $("textarea[name='opt_out_feedback']").val();
        send_feedback(ajax, e, _t, mailing_id, res_id, email, feedback, token);
    });
});


//===========================================================================
//          Unsubscribe page for mass Mailing contacts model
// the user is able to select which mailing list he wants to be subscribed to
//===========================================================================
odoo.define('mass_mailing.mailing_list_subcription', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');
    var _t = core._t;

    var email = $("input[name='email']").val();
    var mailing_id = parseInt($("input[name='mailing_id']").val());
    var res_id = parseInt($("input[name='res_id']").val());
    var token = (location.search.split('token' + '=')[1] || '').split('&')[0];
    check_email(ajax, email);

    //  ==================
    //       Opt-out
    //  ==================
    $('#button_update_subscription').click(function (e) {
        if ($('#button_update_subscription').hasClass('clickable')) {
            e.preventDefault();

            check_blacklist_state(ajax, email, function(ret){
                if (ret){
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
                                $('#subscription_info').html(_t('You are not authorized to do this!'))
                                 .removeClass('alert-success').removeClass('alert-info')
                                 .addClass('alert-warning');
                            }
                            else {
                                $('#subscription_info').html(_t('Your changes have been saved successfully.'))
                                     .removeClass('alert-warning').removeClass('alert-info')
                                     .addClass('alert-success');
                            }
                        })
                        .fail(function () {
                            $('#subscription_info').html(_t('Your changes have not been saved, try again later.')).removeClass('alert-warning').removeClass('alert-info').addClass('alert-warning');
                        });

                    $('[name="button_subscription"]').attr('disabled',true).removeClass('clickable');
                }
                else{
                    $('#subscription_info').html(_t('You cannot update your preference as you are not able to be contacted by our services.'))
                    .removeClass('alert-info').removeClass('alert-success')
                    .addClass('alert-warning');
                }
            });
        }
    });

    $(".mail_list_checkbox").click(function (){
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-warning').removeClass('alert-success').addClass('alert-info');
        $('[name="button_subscription"]').attr('disabled',false).addClass('clickable');
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist_subscription').click(function (e) {
        call_add_to_blacklist(ajax, e, _t, mailing_id, res_id, email, token);
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-warning').removeClass('alert-success').addClass('alert-info');
    });

    $('#button_remove_blacklist_subscription').click(function (e) {
        call_remove_from_blacklist(ajax, e, _t, mailing_id, res_id, email, token);
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-warning').removeClass('alert-success').addClass('alert-info');
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback_subscription').click(function (e) {
        var feedback = $("textarea[name='opt_out_feedback_subscription']").val();
        send_feedback(ajax, e, _t, mailing_id, res_id, email, feedback, token);
    });
});

//=============================================
// functions common for both subscription pages
//=============================================

function toggle_opt_out_section(value) {
    var result = !value;
    $("#div_opt_out").find('*').attr('disabled',result);
    if (value) { $('[name="button_subscription"]').addClass('clickable');  }
    else { $('[name="button_subscription"]').removeClass('clickable'); }
}

function check_email(ajax, email) {
    // To avoid crash in test_whishlist --> Why this test leads to this page ???
    if (email != '' && email != undefined){
        check_blacklist_state(ajax, email);
    }
    else {
        $('#div_blacklist').hide();
    }
}

function clear_blacklist_msg() {
    $('#div_blacklist_add').hide();
    $('#div_blacklist_remove').hide();
    $('#div_state_blacklist').hide();
}

function call_subscribe_contact(ajax, _t, e, email, mailing_id, res_id, token) {
    e.preventDefault();
    ajax.jsonRpc('/mail/mailing/subscribe_contact', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
        .then(function (result) {
            if (result == 'unauthorized'){
                $('#subscription_info').html(_t('You are not authorized to do this!'))
                 .removeClass('alert-success').removeClass('alert-info')
                 .addClass('alert-warning');
            }
            else if (result == 'success') {
                $('#div_contact_subscribed').show();
                $('#div_unsubscribed').hide();
                $('#div_subscription_message').html(_t('You have been successfully <strong>re-subscribed</strong>!'))
                     .removeClass('alert-warning').addClass('alert-success');
            }
            else {
                $('#div_subscription_message').html(_t('An error occured. Please try again later or contact us.'))
                    .removeClass('alert-success').addClass('alert-warning');;
            }
        })
        .fail(function () {
            $('#div_subscription_message').html(_t('An error occured. Please try again later or contact us.'))
                    removeClass('alert-success').addClass('alert-warning');
        });
}

function call_add_to_blacklist(ajax, e, _t, mailing_id, res_id, email, token) {
    e.preventDefault();

    ajax.jsonRpc('/mail/mailing/blacklist/add', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
        .then(function (result) {
            if (result == 'unauthorized'){
                $('#blacklist_info').html(_t('You are not authorized to do this!'))
                 .removeClass('alert-success').removeClass('alert-info').removeClass('alert-error')
                 .addClass('alert-warning');
            }
            else
            {
                clear_blacklist_msg();
                if (result == 'success') {
                    $('#blacklist_info').html(_t("<p>You have been successfully <strong>removed</strong>"
                           + " from our global mailing subscription!</p>"
                           + "<p>You will not be contacted anymore by our services.</p>"))
                        .removeClass('alert-warning').removeClass('alert-info').removeClass('alert-error')
                        .addClass('alert-success');
                    toggle_opt_out_section(false);
                }
                else if (result == 'found') {
                    $('#blacklist_info').html(_t('<p>You were already blacklisted.</p>'
                            + '<p>If you still received a mail from us, please contact us to report the issue.</p>'))
                        .removeClass('alert-success').removeClass('alert-info').removeClass('alert-error')
                        .addClass('alert-warning');
                    toggle_opt_out_section(false);
                }
                else {
                    $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                        .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                        .addClass('alert-error');
                }
                $('#div_blacklist_remove').show();
            }
            $('#blacklist_info').show();
        })
        .fail(function () {
            clear_blacklist_msg();
            $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                .addClass('alert-error');
        });

}

function call_remove_from_blacklist(ajax, e, _t, mailing_id, res_id, email, token){
    e.preventDefault();

    ajax.jsonRpc('/mail/mailing/blacklist/remove', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
        .then(function (result) {
            if (result == 'unauthorized'){
                $('#blacklist_info').html(_t('You are not authorized to do this!'))
                 .removeClass('alert-success').removeClass('alert-info')
                 .addClass('alert-warning');
            }
            else
            {
                clear_blacklist_msg();
                if (result == 'success') {
                    $('#blacklist_info').html(_t("<p>Welcome back!</p>"
                            + "<p>You are now able to be contacted by our services.</p>"))
                        .removeClass('alert-warning').removeClass('alert-info').removeClass('alert-error')
                        .addClass('alert-success');
                    toggle_opt_out_section(true);
                }
                else if (result == 'not found') {
                    $('#blacklist_info').html(_t('<p>You were not blacklisted.</p>'
                            + '<p>If you still not receive mails from us, please contact us to report the issue.</p>'))
                        .removeClass('alert-success').removeClass('alert-info').removeClass('alert-error')
                        .addClass('alert-warning');
                    toggle_opt_out_section(true);
                }
                else {
                    $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                        .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                        .addClass('alert-error');
                }
                $('#div_blacklist_add').show();
            }
            $('#blacklist_info').show();
        })
        .fail(function () {
            clear_blacklist_msg();
            $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                .addClass('alert-error');
        });
}

function check_blacklist_state(ajax, email, callback){
    ajax.jsonRpc('/mail/mailing/blacklist/check', 'call', {'email': email})
        .then(function (result) {
            clear_blacklist_msg();
            if (result == 'found') {
                $('#state_blacklist').html("You are currently <strong>not able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#blacklist_info').hide();
                $('#div_blacklist_remove').show();
                toggle_opt_out_section(false);
                if (callback != undefined){ callback(false); }
            }
            else if (result == 'not found') {
                $('#state_blacklist').html("You are currently <strong>able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#blacklist_info').hide();
                $('#div_blacklist_add').show();
                toggle_opt_out_section(true);
                if (callback != undefined){ callback(true); }
            }
            else {
                $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                .addClass('alert-error');
            }
        })
        .fail(function () {
            $('#blacklist_info').html(_t('An error occured. Please try again later or contact us.'))
                .removeClass('alert-success').removeClass('alert-info').removeClass('alert-warning')
                .addClass('alert-error');
        });
}

function send_feedback(ajax, e, _t, mailing_id, res_id, email, feedback, token){
    e.preventDefault();
    ajax.jsonRpc('/mail/mailing/feedback', 'call', {'mailing_id': mailing_id, 'res_id': res_id, 'email': email, 'feedback': feedback, 'token': token})
        .then(function (result) {
            if (result == 'unauthorized'){
                $('#subscription_info').html(_t('You are not authorized to do this!'))
                 .removeClass('alert-success').removeClass('alert-info')
                 .addClass('alert-warning');
            }
            else {
                $('#div_feedback_confirmation').show();
                $("#div_feedback").hide();
            }
        })
        .fail(function () {
            $('#div_feedback_confirmation').html(_t('An error occured. Please try again later or contact us.'))
            .removeClass('alert-info').removeClass('alert-success')
            .addClass('alert-warning');
             $('#div_feedback_confirmation').show();
        });
}
