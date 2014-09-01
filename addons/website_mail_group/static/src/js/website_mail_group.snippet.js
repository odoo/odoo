(function () {
    'use strict';

    var website = openerp.website;

    website.snippet.animationRegistry.follow_alias = website.snippet.Animation.extend({
        selector: ".js_follow_alias",
        start: function (editable_mode) {
            var self = this;
            this.is_user = false;

            openerp.jsonRpc('/website_mail/is_follower', 'call', {
                model: this.$target.data('object'),
                id: this.$target.data('id'),
                get_alias_info: true,
            }).always(function (data) {
                self.is_user = data.is_user;
                self.email = data.email;
                self.$target.find('.js_mg_link').attr('href', '/groups/' + self.$target.data('id'));
                self.toggle_subscription(data.is_follower, data.email);
                self.$target.removeClass("hidden");
            });

            // not if editable mode to allow designer to edit alert field
            if (!editable_mode) {
                $('.js_follow_alias > .alert').addClass("hidden");
                $('.js_follow_alias > .input-group-btn.hidden').removeClass("hidden");
                this.$target.find('.js_follow_btn, .js_unfollow_btn').on('click', function (event) {
                    event.preventDefault();
                    self.on_click();
                });
            }
            return;
        },
        on_click: function () {
            var self = this;
            var $email = this.$target.find(".js_follow_email");

            if ($email.length && !$email.val().match(/.+@.+/)) {
                this.$target.addClass('has-error');
                return false;
            }
            this.$target.removeClass('has-error');

            openerp.jsonRpc('/website_mail/follow', 'call', {
                'id': +this.$target.data('id'),
                'object': this.$target.data('object'),
                'message_is_follower': this.$target.attr("data-follow") || "off",
                'email': $email.length ? $email.val() : false,
            }).then(function (follow) {
                self.toggle_subscription(follow, self.email);
            });
        },
        toggle_subscription: function(follow, email) {
            var alias_done = this.get_alias_info();
            if (follow) {
                this.$target.find(".js_mg_follow_form").addClass("hidden");
                this.$target.find(".js_mg_details").removeClass("hidden");
            }
            else {
                this.$target.find(".js_mg_follow_form").removeClass("hidden");
                this.$target.find(".js_mg_details").addClass("hidden");
            }
            this.$target.find('input.js_follow_email')
                .val(email ? email : "")
                .attr("disabled", follow || (email.length && this.is_user) ? "disabled" : false);
            this.$target.attr("data-follow", follow ? 'on' : 'off');
            return $.when(alias_done);
        },
        get_alias_info: function() {
            var self = this;
            if (! this.$target.data('id')) {
                return $.Deferred().resolve();
            }
            return openerp.jsonRpc('/groups/' + this.$target.data('id') + '/get_alias_info', 'call', {}).then(function (data) {
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

    $(document).ready(function () {
        $('.js_follow_btn').on('click', function (ev) {
            var email = $(ev.currentTarget).parents('.js_mg_follow_form').first().find('.js_follow_email').val();
            $(document).find('.js_follow_email').val(email);
        });
    });
})();
