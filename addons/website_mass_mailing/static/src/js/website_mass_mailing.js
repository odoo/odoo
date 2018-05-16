odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var utils = require('web.utils');
var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.subscribe = sAnimation.Class.extend({
    selector: ".js_subscribe",
    start: function () {
        var self = this;

        // set value and display button
        self.$target.find("input").removeClass("hidden");
        this._rpc({
            route: '/website_mass_mailing/is_subscriber',
            params: {
                list_id: this.$target.data('list-id'),
            },
        }).always(function (data) {
            self.$target.find('input.js_subscribe_email')
                .val(data.email ? data.email : "")
                .attr("disabled", data.is_subscriber && data.email.length ? "disabled" : false);
            self.$target.attr("data-subscribe", data.is_subscriber ? 'on' : 'off');
            self.$target.find('a.js_subscribe_btn')
                .attr("disabled", data.is_subscriber && data.email.length ? "disabled" : false);
            self.$target.removeClass("hidden");
            self.$target.find('.js_subscribe_btn').toggleClass('hidden', !!data.is_subscriber);
            self.$target.find('.js_subscribed_btn').toggleClass('hidden', !data.is_subscriber);
        });

        // not if editable mode to allow designer to edit alert field
        if (!this.editableMode) {
            $('.js_subscribe > .alert').addClass("hidden");
            $('.js_subscribe > .input-group-btn.hidden').removeClass("hidden");
            this.$target.find('.js_subscribe_btn').on('click', function (event) {
                event.preventDefault();
                self._onClick();
            });
        }
    },
    _onClick: function () {
        var self = this;
        var $email = this.$target.find(".js_subscribe_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('has-error');
            return false;
        }
        this.$target.removeClass('has-error');

        this._rpc({
            route: '/website_mass_mailing/subscribe',
            params: {
                'list_id': this.$target.data('list-id'),
                'email': $email.length ? $email.val() : false,
            },
        }).then(function (subscribe) {
            self.$target.find(".js_subscribe_email, .input-group-btn").addClass("hidden");
            self.$target.find(".alert").removeClass("hidden");
            self.$target.find('input.js_subscribe_email').attr("disabled", subscribe ? "disabled" : false);
            self.$target.attr("data-subscribe", subscribe ? 'on' : 'off');
        });
    },
});

sAnimation.registry.newsletter_popup = sAnimation.Class.extend({
    selector: ".o_newsletter_popup",
    start: function () {
        var self = this;
        var popupcontent = self.$target.find(".o_popup_content_dev").empty();
        if (!self.$target.data('list-id')) return;

        this._rpc({
            route: '/website_mass_mailing/get_content',
            params: {
                newsletter_id: self.$target.data('list-id'),
            },
        }).then(function (data) {
            if (data.content) {
                $('<div></div>').append(data.content).appendTo(popupcontent);
            }
            self.$target.find('input.popup_subscribe_email').val(data.email || "");
            self.redirect_url = data.redirect_url;
            if (!self.editableMode && !data.is_subscriber) {
                $(document).on('mouseleave', _.bind(self.show_banner, self));

                self.$target.find('.popup_subscribe_btn').on('click', function (event) {
                    event.preventDefault();
                    self._onClickSubscribe();
                });
            } else { $(document).off('mouseleave'); }
        });
    },
    _onClickSubscribe: function () {
        var self = this;
        var $email = self.$target.find(".popup_subscribe_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('has-error');
            return false;
        }
        this.$target.removeClass('has-error');

        this._rpc({
            route: '/website_mass_mailing/subscribe',
            params: {
                'list_id': self.$target.data('list-id'),
                'email': $email.length ? $email.val() : false,
            },
        }).then(function (subscribe) {
            self.$target.find('#o_newsletter_popup').modal('hide');
            $(document).off('mouseleave');
            if (self.redirect_url) {
                if (_.contains(self.redirect_url.split('/'), window.location.host) || self.redirect_url.indexOf('/') === 0) {
                    window.location.href = self.redirect_url;
                } else {
                    window.open(self.redirect_url, '_blank');
                }
            }
        });
    },
    show_banner: function () {
        var self = this;
        if (!utils.get_cookie("newsletter-popup-"+ self.$target.data('list-id')) && self.$target) {
           $('#o_newsletter_popup:first').modal('show').css({
                'margin-top': '70px',
                'position': 'fixed'
            });
             document.cookie = "newsletter-popup-"+ self.$target.data('list-id') +"=" + true + ";path=/";
        }
    }
});
});

//==============================================================================

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

//=====================================================================================

odoo.define('mass_mailing.unsubscribed', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var core = require('web.core');
    require('web.dom_ready');

    var _t = core._t;

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

    function clear_subscription_msg() {
        $('#div_unsubscribed').hide();
        $('#div_contact_subscribed').hide()
    }

    var email = $("input[name='email']").val();
    var mailing_id = parseInt($("input[name='mailing_id']").val());
    var res_id = parseInt($("input[name='res_id']").val());

    if (email != '' && email != undefined){
        check_blacklist_state(email);
    }
    else {
        $('#div_blacklist').hide();
    }

    var mailing_list_name = $("input[name='mailing_list_name']").val();
    if (mailing_list_name != '' && mailing_list_name != undefined){
        $('.mailing_list_name').html(" from <strong>"+mailing_list_name+"</strong>");
    }

//  ==================
//      Opt-out
//  ==================
    $('#button_re_subscribe').click(function (e) {
        e.preventDefault();

        ajax.jsonRpc('/mail/mailing/subscribe_contact', 'call', {'email': email, 'mailing_id': mailing_id, 'res_id': res_id})
            .then(function (result) {
                clear_subscription_msg();
                if (result == 'success') {
                    $('#div_contact_subscribed').show();
                        if (mailing_list_name != '' && mailing_list_name != undefined){
                            $('.mailing_list_name').html(" to <strong>"+mailing_list_name+"</strong>");
                        }
                }
                else {
                    $('#div_subscription_error').show();
                }
            })
            .fail(function () {
                clear_subscription_msg();
                $('#div_subscription_error').show();
            });
    });

    $('#button_unsubscribe').click(function (e) {
        e.preventDefault();

        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'mailing_id': mailing_id, 'opt_in_ids': [], 'opt_out_ids': [res_id], 'email': email})
            .then(function (result) {
                clear_subscription_msg();
                $('#div_unsubscribed').show();
                    if (mailing_list_name != '' && mailing_list_name != undefined){
                        $('.mailing_list_name').html(" from <strong>"+mailing_list_name+"</strong>");
                    }
            })
            .fail(function () {
                clear_subscription_msg();
                $('#div_subscription_error').show();
            });
    });


//  ==================
//      Blacklist
//  ==================
    $('#button_add_blacklist').click(function (e) {
        e.preventDefault();

        ajax.jsonRpc('/mail/mailing/blacklist/add', 'call', {'email': email})
            .then(function (result) {
                clear_blacklist_msg();
                if (result == 'success') {
                    $('#div_confirm_blacklisted').show();
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
    });

    $('#button_remove_blacklist').click(function (e) {
        e.preventDefault();

        ajax.jsonRpc('/mail/mailing/blacklist/remove', 'call', {'email': email})
            .then(function (result) {
                clear_blacklist_msg();
                if (result == 'success') {
                    $('#div_removed_blacklist').show();
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
    });

    function check_blacklist_state(email){
        ajax.jsonRpc('/mail/mailing/blacklist/check', 'call', {'email': email})
        .then(function (result) {
            if (result == 'found') {
                $('#state_blacklist').html("You are currently <strong>not able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#div_blacklist_add').hide();
                $('#div_blacklist_remove').show();
            }
            else if (result == 'not found') {
                $('#state_blacklist').html("You are currently <strong>able</strong> to be contacted by our services.");
                $('#div_state_blacklist').show();
                $('#div_blacklist_remove').hide();
                $('#div_blacklist_add').show();
            }
            else {
                $('#div_error').show();
            }
        })
        .fail(function () {
            $('#div_error').show();
        });
    }
});