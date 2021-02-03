odoo.define('mass_mailing.website_integration', function (require) {
"use strict";

var utils = require('web.utils');
var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.subscribe = sAnimation.Class.extend({
    selector: ".js_subscribe",
    start: function () {
        var self = this;

        // set value and display button
        self.$target.find("input").removeClass('d-none');
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
            self.$target.removeClass('d-none');
            self.$target.find('.js_subscribe_btn').toggleClass('d-none', !!data.is_subscriber);
            self.$target.find('.js_subscribed_btn').toggleClass('d-none', !data.is_subscriber);
        });

        // not if editable mode to allow designer to edit alert field
        if (!this.editableMode) {
            $('.js_subscribe > .alert').addClass('d-none');
            $('.js_subscribe > .input-group-append.d-none').removeClass('d-none');
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
            this.$target.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }
        this.$target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

        this._rpc({
            route: '/website_mass_mailing/subscribe',
            params: {
                'list_id': this.$target.data('list-id'),
                'email': $email.length ? $email.val() : false,
            },
        }).then(function (subscribe) {
            self.$target.find(".js_subscribe_email, .input-group-append").addClass('d-none');
            self.$target.find(".alert").removeClass('d-none');
            self.$target.find('input.js_subscribe_email').attr("disabled", subscribe ? "disabled" : false);
            self.$target.attr("data-subscribe", subscribe ? 'on' : 'off');
        });
    },
});

sAnimation.registry.newsletter_popup = sAnimation.Class.extend({
    selector: ".o_newsletter_popup",
    start: function () {
        var self = this;

        // Compatibility: rebuilding a correct modal from user database
        // content. Since the first version, the modal is saved in databases
        // directly but has never used a correct structure. While it was working
        // with BS3, it is not with BS4.
        // TODO review the newsletter popup creation, save and loading.
        var $modal = this.$('.modal');
        if ($modal.is('.modal-dialog')) {
            $modal.removeClass('modal-md modal-dialog');
            var $modalContent = $modal.find('.modal-content');
            $modalContent.wrapAll($('<div/>', {class: 'modal-dialog'}));
        }

        var popupcontent = self.$target.find(".o_popup_content_dev").empty();
        if (!self.$target.data('list-id')) {
            return;
        }

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
            this.$target.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
            return false;
        }
        this.$target.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');

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
            }).find('.o_popup_bounce_small span.popup_newsletter_input_conserve').each(function () {
                if ($(this).prev('input').length === 0) {
                    $(this).before($('<input>').attr($(this).getAttributes()).removeClass('d-none popup_newsletter_input_conserve'));
                }
            }).remove();
            document.cookie = "newsletter-popup-"+ self.$target.data('list-id') +"=" + true + ";path=/";
        }
    }
});
});
