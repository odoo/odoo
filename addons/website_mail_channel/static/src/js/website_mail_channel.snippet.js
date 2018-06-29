odoo.define('website_mail_channel.snippet', function (require) {
'use strict';

var sAnimation = require('website.content.snippets.animation');

sAnimation.registry.follow_alias = sAnimation.Class.extend({
    selector: ".js_follow_alias",
    start: function () {
        var self = this;
        this.is_user = false;
        var unsubscribePage = window.location.search.slice(1).split('&').indexOf("unsubscribe") >= 0;
        this._rpc({
            route: '/groups/is_member',
            params: {
                model: this.$target.data('object'),
                channel_id: this.$target.data('id'),
                get_alias_info: true,
            },
        }).always(function (data) {
            self.is_user = data.is_user;
            self.email = data.email;
            self.$target.find('.js_mg_link').attr('href', '/groups/' + self.$target.data('id'));
            if (unsubscribePage && self.is_user) {
                self.$target.find(".js_mg_follow_form").remove();
            }
            self.toggle_subscription(data.is_member ? 'on' : 'off', data.email);
            self.$target.removeClass("hidden");
        });

        // not if editable mode to allow designer to edit alert field
        if (!this.editableMode) {
            this.$('> .alert').addClass("hidden");
            this.$('> .input-group-btn.hidden').removeClass("hidden");
            this.$('.js_follow_btn, .js_unfollow_btn').on('click', function (event) {
                event.preventDefault();
                self._onClick();
            });

            this.$('.js_follow_btn').on('click', function (ev) {
                if ($(ev.currentTarget).closest('.js_mg_follow_form').length) {
                    self.$('.js_follow_email').val($(ev.currentTarget).closest('.js_mg_follow_form').find('.js_follow_email').val());
                }
            });
        }
        return this._super.apply(this, arguments);
    },
    _onClick: function () {
        var self = this;
        var $email = this.$target.find(".js_follow_email");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('has-error');
            return false;
        }
        this.$target.removeClass('has-error');

        var subscription_action = this.$target.attr("data-follow") || "off";
        if (window.location.search.slice(1).split('&').indexOf("unsubscribe") >= 0) {
            // force unsubscribe mode via URI /groups?unsubscribe
            subscription_action = 'on';
        }
        this._rpc({
            route: '/groups/subscription',
            params: {
                'channel_id': +this.$target.data('id'),
                'object':  this.$target.data('object'),
                'subscription': subscription_action,
                'email': $email.length ? $email.val() : false,
            },
        }).then(function (follow) {
            self.toggle_subscription(follow, self.email);
        });
    },
    toggle_subscription: function (follow, email) {
        // .js_mg_follow_form contains subscribe form
        // .js_mg_details contains send/archives/unsubscribe links
        // .js_mg_confirmation contains message warning has been sent
        var alias_done = this.get_alias_info();
        if (follow === "on") {
            // user is connected and can unsubscribe
            this.$target.find(".js_mg_follow_form").addClass("hidden");
            this.$target.find(".js_mg_details").removeClass("hidden");
            this.$target.find(".js_mg_confirmation").addClass("hidden");
        } else if (follow === "off") {
            // user is connected and can subscribe
            this.$target.find(".js_mg_follow_form").removeClass("hidden");
            this.$target.find(".js_mg_details").addClass("hidden");
            this.$target.find(".js_mg_confirmation").addClass("hidden");
        } else if (follow === "email") {
            // a confirmation email has been sent
            this.$target.find(".js_mg_follow_form").addClass("hidden");
            this.$target.find(".js_mg_details").addClass("hidden");
            this.$target.find(".js_mg_confirmation").removeClass("hidden");
        } else {
            console.error("Unknown subscription action", follow);
        }
        this.$target.find('input.js_follow_email')
            .val(email ? email : "")
            .attr("disabled", follow === "on" || (email.length && this.is_user) ? "disabled" : false);
        this.$target.attr("data-follow", follow);
        return $.when(alias_done);
    },
    get_alias_info: function () {
        var self = this;
        if (! this.$target.data('id')) {
            return $.Deferred().resolve();
        }
        return this._rpc({route: '/groups/' + this.$target.data('id') + '/get_alias_info'}).then(function (data) {
            if (data.alias_name) {
                self.$target.find('.js_mg_email').attr('href', 'mailto:' + data.alias_name);
                self.$target.find('.js_mg_email').removeClass('hidden');
            }
            else {
                self.$target.find('.js_mg_email').addClass('hidden');
            }
        });
    }
});
});
