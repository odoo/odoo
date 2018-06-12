//=======================================================
//      Executed before rendering Unsubscribe page
//  applies for all models except Mass Mailing Contacts
//=======================================================
odoo.define('mass_mailing.unsubscribe', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');

    var _t = core._t;

    if (!$('.o_unsubscribe_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_unsubscribe_form'");
    }

    $('#unsubscribe_form').on('submit', function (e) {
        e.preventDefault();

        var email = $("input[name='email']").val();
        var mailing_id = parseInt($("input[name='mailing_id']").val());

        var checked_ids = [];
        $("input[type='checkbox']:checked").each(function (i){
          checked_ids[i] = parseInt($(this).val());
        });

        var unchecked_ids = [];
        $("input[type='checkbox']:not(:checked)").each(function (i){
          unchecked_ids[i] = parseInt($(this).val());
        });

        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'opt_in_ids': checked_ids, 'opt_out_ids': unchecked_ids, 'email': email, 'mailing_id': mailing_id})
            .then(function (result) {
                $('.alert-info').html(_t('Your changes have been saved.')).removeClass('alert-info').addClass('alert-success');
            })
            .fail(function () {
                $('.alert-info').html(_t('Your changes have not been saved, try again later.')).removeClass('alert-info').addClass('alert-warning');
            });
    });
});


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
    check_email(ajax, email);

    //  ==================
    //      Opt-out
    //  ==================
    $('#button_re_subscribe').click(function (e) {
        if ($('#button_re_subscribe').hasClass('clickable')) {
            call_subscribe_contact(ajax, _t, e, email, mailing_id, res_id);
        }
    });

    $('#button_unsubscribe').click(function (e) {
        if ($('#button_unsubscribe').hasClass('clickable')) {
            e.preventDefault();
            ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'mailing_id': mailing_id, 'opt_in_ids': [], 'opt_out_ids': [res_id], 'email': email})
                .then(function (result) {
                    $('#div_unsubscribed').show();
                    $('#div_contact_subscribed').hide();
                    $('#div_subscription_message').html(_t('You have been successfully <strong>unsubscribed</strong>!'))
                     .removeClass('alert-warning').addClass('alert-success');
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
        call_add_to_blacklist(ajax, e, email);
    });

    $('#button_remove_blacklist').click(function (e) {
        call_remove_from_blacklist(ajax, e, email);
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback').click(function (e) {
        var feedback = $("textarea[name='opt_out_feedback']").val();
        send_feedback(ajax, e, mailing_id, email, feedback);
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
    check_email(ajax, email);

    //  ==================
    //       Opt-out
    //  ==================
    $('#button_update_subscription').click(function (e) {
        if ($('#button_update_subscription').hasClass('clickable')) {
            e.preventDefault();

            var checked_ids = [];
            $("input[type='checkbox']:checked").each(function (i){
              checked_ids[i] = parseInt($(this).val());
            });

            var unchecked_ids = [];
            $("input[type='checkbox']:not(:checked)").each(function (i){
              unchecked_ids[i] = parseInt($(this).val());
            });

            ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'opt_in_ids': checked_ids, 'opt_out_ids': unchecked_ids, 'email': email, 'mailing_id': mailing_id})
                .then(function (result) {
                    $('#subscription_info').html(_t('Your changes have been saved successfully.'))
                         .removeClass('alert-warning').removeClass('alert-info')
                         .addClass('alert-success');
                })
                .fail(function () {
                    $('#subscription_info').html(_t('Your changes have not been saved, try again later.')).removeClass('alert-info').addClass('alert-warning');
                });

            check_blacklist_state(ajax, email, function(){
                $('[name="button_subscription"]').attr('disabled',true).removeClass('clickable');
            });
        }
    });

    $(".mail_list_checkbox").click(function (){
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-success').addClass('alert-info');
        $('[name="button_subscription"]').attr('disabled',false).addClass('clickable');
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist_subscription').click(function (e) {
        call_add_to_blacklist(ajax, e, email);
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-success').addClass('alert-info');
    });

    $('#button_remove_blacklist_subscription').click(function (e) {
        call_remove_from_blacklist(ajax, e, email);
        $('#subscription_info').html(_t('Choose your mailing subscriptions.')).removeClass('alert-success').addClass('alert-info');
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback_subscription').click(function (e) {
        var feedback = $("textarea[name='opt_out_feedback_subscription']").val();
        send_feedback(ajax, e, mailing_id, email, feedback);
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
    $('#div_confirm_blacklisted').hide();
    $('#div_found').hide();
    $('#div_error').hide();
    $('#div_not_found').hide();
    $('#div_removed_blacklist').hide();
    $('#div_blacklist_add').hide();
    $('#div_blacklist_remove').hide();
    $('#div_state_blacklist').hide();
}

function call_subscribe_contact(ajax, _t, e, email, mailing_id, res_id) {
    e.preventDefault();
    ajax.jsonRpc('/mail/mailing/subscribe_contact', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id})
        .then(function (result) {
            if (result == 'success') {
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

function call_add_to_blacklist(ajax, e, email) {
    e.preventDefault();

    ajax.jsonRpc('/mail/mailing/blacklist/add', 'call', {'email': email})
        .then(function (result) {
            clear_blacklist_msg();
            if (result == 'success') {
                $('#div_confirm_blacklisted').show();
                toggle_opt_out_section(false);
            }
            else if (result == 'found') {
                $('#div_found').show();
            }
            else {
                $('#div_error').show();
            }
            $('#div_blacklist_remove').show();
        })
        .fail(function () {
            clear_blacklist_msg();
            $('#div_error').show();
        });

}

function call_remove_from_blacklist(ajax, e, email){
    e.preventDefault();

    ajax.jsonRpc('/mail/mailing/blacklist/remove', 'call', {'email': email})
        .then(function (result) {
            clear_blacklist_msg();
            if (result == 'success') {
                $('#div_removed_blacklist').show();
                toggle_opt_out_section(true);
            }
            else if (result == 'not found') {
                $('#div_not_found').show();
            }
            else {
                $('#div_error').show();
            }
            $('#div_blacklist_add').show();
        })
        .fail(function () {
            clear_blacklist_msg();
            $('#div_error').show();
        });
}

function check_blacklist_state(ajax, email, callback){
    ajax.jsonRpc('/mail/mailing/blacklist/check', 'call', {'email': email})
        .then(function (result) {
            if (result == 'found') {
                $('#state_blacklist').html("You are currently <strong>not able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#div_blacklist_add').hide();
                $('#div_blacklist_remove').show();
                toggle_opt_out_section(false);
                if (callback != undefined){ callback(); }
            }
            else if (result == 'not found') {
                $('#state_blacklist').html("You are currently <strong>able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#div_blacklist_remove').hide();
                $('#div_blacklist_add').show();
                toggle_opt_out_section(true);
                if (callback != undefined){ callback(); }
            }
            else {
                $('#div_error').show();
            }
            $('#div_removed_blacklist').hide();
            $('#div_confirm_blacklisted').hide();
        })
        .fail(function () {
            $('#div_error').show();
            $('#div_removed_blacklist').hide();
            $('#div_confirm_blacklisted').hide();
        });
}

function send_feedback(ajax, e, mailing_id, email, feedback){
    e.preventDefault();
    ajax.jsonRpc('/mail/mailing/feedback', 'call', {'mailing_id': mailing_id, 'email': email, 'feedback': feedback})
        .then(function (result) {
             $('#div_feedback_confirmation').show();
             $("#div_feedback").hide();
        })
        .fail(function () {
            $('#div_feedback_confirmation').html(_t('An error occured. Please try again later or contact us.'))
            .removeClass('alert-info').removeClass('alert-success')
            .addClass('alert-warning');
             $('#div_feedback_confirmation').show();
        });
}