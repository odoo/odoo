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
    var show_blacklist_button = $('input[name="show_blacklist_button"]').val();

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
                        $('#subscription_info h2').text(_t('An error occured. Please try again later or contact us.'));
                    }
                })
                .guardedCatch(function () {
                    $('#subscription_info h2').text(_t('An error occured. Please try again later or contact us.'));
                });
        }
        else {
            if (show_blacklist_button) {
                $('#button_add_blacklist').show();
                toggle_opt_out_section(false);
            }
            $('#div_blacklist').hide();
        }

        var unsubscribed_list = $("input[name='unsubscribed_list']").val();
        if (unsubscribed_list){
            $('#subscription_info h2').text(_.str.sprintf(
                _t("You're no longer part of the %s Mailing List."),
                unsubscribed_list
            ));
        }
        else{
            $('#subscription_info h2').text(_t("You're no longer part of this Mailing List."));
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

        var setFormStatus = formStatus($('#unsubscribe_form_status'));
        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'opt_in_ids': checked_ids, 'opt_out_ids': unchecked_ids, 'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    setFormStatus(_t('You are not authorized to do this!'), false);
                }
                else if (result == true) {
                    setFormStatus(_t('Your changes have been saved.'), true);
                    $('#div_opt_out .list-group-item').each((_index, item) => {
                        const $item = $(item);
                        const value = parseInt($item.find('input').val());
                        $item.find('.text-primary').text(checked_ids.includes(value) ?
                            _t('Subscribed') :
                            _t('Not subscribed')
                        );
                    });
                }
                else {
                    setFormStatus(_t('An error occurred. Your changes have not been saved, try again later.'), false);
                }
            })
            .guardedCatch(function () {
                setFormStatus(_t('An error occurred. Your changes have not been saved, try again later.'), false);
            });
    });

    //  ==================
    //      Blacklist
    //  ==================
    $('#button_add_blacklist').click(function (e) {
        e.preventDefault();
        if ($('#button_add_blacklist').hasClass('disabled')) {
            return;
        }
        var setFormStatus = formStatus($('#unsubscribe_form_status'));
        ajax.jsonRpc('/mailing/blacklist/add', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    setFormStatus(_t('You are not authorized to do this!'), false);
                }
                else
                {
                    if (result) {
                        setFormStatus(_t('Email address added to our blacklist.'), true);
                        toggle_opt_out_section(false);
                    }
                    else {
                        setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
                    }
                    $('#button_add_blacklist').hide();
                    $('#button_remove_blacklist').show();
                }
            })
            .guardedCatch(function () {
                setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
            });
    });

    $('#button_remove_blacklist').click(function (e) {
        e.preventDefault();
        if ($('#button_remove_blacklist').hasClass('disabled')) {
            return;
        }
        var setFormStatus = formStatus($('#unsubscribe_form_status'));
        ajax.jsonRpc('/mailing/blacklist/remove', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    setFormStatus(_t('You are not authorized to do this!'), false);
                }
                else
                {
                    if (result) {
                        setFormStatus(_t('Email address removed from our blacklist.'), true);
                        toggle_opt_out_section(true);
                    }
                    else {
                        setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
                    }
                    $('#button_add_blacklist').show();
                    $('#button_remove_blacklist').hide();
                }
            })
            .guardedCatch(function () {
                setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
            });
    });

    // ==================
    //      Feedback
    // ==================
    $('#button_feedback').click(function (e) {
        e.preventDefault();
        if ($('#button_feedback').hasClass('disabled')) {
            return;
        }
        var feedback = {
            key: $('input[name="unsubsribe_reason"]:checked').val()
        };
        if (feedback.key === 'other') {
            feedback.reason = $('textarea[name="opt_out_feedback"]').val();
        }
        var setFormStatus = formStatus($('#feedback_status'));
        ajax.jsonRpc('/mailing/feedback', 'call', {'mailing_id': mailing_id, 'res_id': res_id, 'email': email, 'feedback': feedback, 'token': token})
            .then(function (result) {
                if (result == 'unauthorized'){
                    setFormStatus(_t('You are not authorized to do this!'), false);
                }
                else if (result == 'notImplemented') {
                    setFormStatus(_t("Feedback can't be sent for this type of model"), false);
                }
                else if (result == true){
                    setFormStatus(_t('Thank you! Your feedback has been sent successfully!'), true);
                    $('#button_feedback').addClass('disabled');
                }
                else if (result == false) {
                    setFormStatus(_t("You are still part of this mailing list. You can't provide feedback!"), false);
                }
                else {
                    setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
                }
            })
            .guardedCatch(function () {
                setFormStatus(_t('An error occured. Please try again later or contact us.'), false);
            });
    });

    $('input.unsubscribe_reason').click(e => {
        $('textarea[name="opt_out_feedback"]').toggleClass('d-none', e.target.value !== 'other');
    });
});

function formStatus(container) {
    return (content, success) => {
        container.text(content);
        if (success) {
            container.prepend($('<i class="fa fa-check mr-1" />'));
            container.removeClass('text-danger').addClass('text-success');
        } else {
            container.prepend($('<i class="fa fa-times mr-1" />'));
            container.removeClass('text-success').addClass('text-danger');
        }
    };
}

function toggle_opt_out_section(value) {
    var result = !value;
    $("#div_opt_out").find('*').attr('disabled',result);
    $("#button_add_blacklist").attr('disabled', false);
    $("#button_remove_blacklist").attr('disabled', false);
    if (value) { $('[name="button_subscription"]').addClass('clickable');  }
    else { $('[name="button_subscription"]').removeClass('clickable'); }
}
