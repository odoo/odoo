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

odoo.define('mass_mailing.unsubscribe', function (require) {
    'use strict';
    var core = require("web.core");
    var animation = require('web_editor.snippets.animation');
    var _t = core._t;

    return animation.registry.mass_mailing_unsubscribe = animation.Class.extend({
        selector: "#unsubscribe_form",
        start: function (editable_mode) {
            this.controller = '/mail/mailing/unsubscribe';
            this.$alert = this.$(".alert");
            this.$email = this.$("input[name='email']");
            this.$contacts = this.$("input[name='contact_ids']");
            this.$mailing_id = this.$("input[name='mailing_id']");
            this.$el.on("submit", $.proxy(this.submit, this));
        },

        /**
         * Helper to get list ids, to use in this.$lists.map()
         */
        int_val: function (index, element) {
            return parseInt($(element).val());
        },

        /**
         * Get a filtered array of integer IDs of matching lists
         */
        contact_ids: function (checked) {
            var filter = checked ? ":checked" : ":not(:checked)";
            return this.$contacts.filter(filter).map(this.int_val).get();
        },

        /**
         * Get values to send
         */
        values: function () {
            return {
                email: this.$email.val(),
                mailing_id: parseInt(this.$mailing_id.val()),
                checked_ids: this.contact_ids(true),
                unchecked_ids: this.contact_ids(false),
            };
        },

        /**
         * Submit by ajax
         */
        submit: function (event) {
            event.preventDefault();
            return this._rpc({route: this.controller, params: this.values()})
            .then($.proxy(this.success, this), $.proxy(this.failure, this));
        },

        /**
         * When you successfully saved the new subscriptions status
         */
        success: function () {
            this.$alert
            .html(_t('Your changes have been saved.'))
            .removeClass("alert-info alert-warning")
            .addClass("alert-success");
        },

        /**
         * When you fail to save the new subscriptions status
         */
        failure: function () {
            this.$alert
            .html(_t('Your changes have not been saved, try again later.'))
            .removeClass("alert-info alert-success")
            .addClass("alert-warning");
        },
    });
});
