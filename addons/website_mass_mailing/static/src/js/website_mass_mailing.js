odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var ajax = require('web.ajax');
var utils = require('web.utils');
var animation = require('web_editor.snippets.animation');
require('web_editor.base');

animation.registry.subscribe = animation.Class.extend({
    selector: ".js_subscribe",
    start: function (editable_mode) {
        var self = this;

        // set value and display button
        self.$target.find("input").removeClass("hidden");
        ajax.jsonRpc('/website_mass_mailing/is_subscriber', 'call', {
            list_id: this.$target.data('list-id'),
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
        if (!editable_mode) {
            $('.js_subscribe > .alert').addClass("hidden");
            $('.js_subscribe > .input-group-btn.hidden').removeClass("hidden");
            this.$target.find('.js_subscribe_btn').on('click', function (event) {
                event.preventDefault();
                self.on_click();
            });
        }
    },
    on_click: function () {
        var self = this;
        var $email = this.$target.find(".js_subscribe_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('has-error');
            return false;
        }
        this.$target.removeClass('has-error');

        ajax.jsonRpc('/website_mass_mailing/subscribe', 'call', {
            'list_id': this.$target.data('list-id'),
            'email': $email.length ? $email.val() : false,
        }).then(function (subscribe) {
            self.$target.find(".js_subscribe_email, .input-group-btn").addClass("hidden");
            self.$target.find(".alert").removeClass("hidden");
            self.$target.find('input.js_subscribe_email').attr("disabled", subscribe ? "disabled" : false);
            self.$target.attr("data-subscribe", subscribe ? 'on' : 'off');
        });
    },
});

animation.registry.newsletter_popup = animation.Class.extend({
    selector: ".o_newsletter_popup",
    start: function (editable_mode) {
        var self = this;
        var popupcontent = self.$target.find(".o_popup_content_dev").empty();
        if (!self.$target.data('list-id')) return;

        ajax.jsonRpc('/website_mass_mailing/get_content', 'call', {
            newsletter_id: self.$target.data('list-id')
        }).then(function (data) {
            if (data.content) {
                $('<div></div>').append(data.content).appendTo(popupcontent);
            }
            self.$target.find('input.popup_subscribe_email').val(data.email || "");
            self.redirect_url = data.redirect_url;
            if (!editable_mode && !data.is_subscriber) {
                $(document).on('mouseleave', _.bind(self.show_banner, self));

                self.$target.find('.popup_subscribe_btn').on('click', function (event) {
                    event.preventDefault();
                    self.on_click_subscribe();
                });
            } else { $(document).off('mouseleave'); }
        });
    },
    on_click_subscribe: function () {
        var self = this;
        var $email = self.$target.find(".popup_subscribe_email:visible");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            self.$target.addClass('has-error');
            return false;
        }
        self.$target.removeClass('has-error');

        ajax.jsonRpc('/website_mass_mailing/subscribe', 'call', {
            'list_id': self.$target.data('list-id'),
            'email': $email.length ? $email.val() : false
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
    show_banner: function() {
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

odoo.define('mass_mailing.unsubscribe', function (require) {
    var ajax = require('web.ajax');
    require('web_editor.base'); // wait for implicit dependencies to load

    if (!$('.o_unsubscribe_form').length) {
        return $.Deferred().reject("DOM doesn't contain '.o_unsubscribe_form'");
    }

    $('#unsubscribe_form').on('submit', function(e) {
        e.preventDefault();

        var email = $("input[name='email']").val();
        var mailing_id = parseInt($("input[name='mailing_id']").val());

        var checked_ids = [];
        $("input[type='checkbox']:checked").each(function(i){
          checked_ids[i] = parseInt($(this).val());
        });

        var unchecked_ids = [];
        $("input[type='checkbox']:not(:checked)").each(function(i){
          unchecked_ids[i] = parseInt($(this).val());
        });

        ajax.jsonRpc('/mail/mailing/unsubscribe', 'call', {'opt_in_ids': checked_ids, 'opt_out_ids': unchecked_ids, 'email': email, 'mailing_id': mailing_id})
            .then(function(result) {
                $('.alert-info').html('Your changes has been saved.').removeClass('alert-info').addClass('alert-success');
            })
            .fail(function() {
                $('.alert-info').html('You changes has not been saved, try again later.').removeClass('alert-info').addClass('alert-warning');
            });
    });
});
