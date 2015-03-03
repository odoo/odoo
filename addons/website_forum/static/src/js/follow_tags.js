odoo.define('website_forum.follow_tags', function (require) {
'use strict';

var ajax = require('web.ajax');
var animation = require('website.snippets.animation');

animation.registry.follow_tags = animation.Animation.extend({
    selector: ".tags_follow",
    start: function(editable_mode) {
        var self = this;
        if (editable_mode) {
            self.$target.find(".o_js_forum_tag_follow").unbind('mouseenter mouseleave');
        }
        this.is_user = false;
        ajax.jsonRpc('/website_follow/is_follower', 'follow_tags', {
            ids: this.$target.data('record'),
        }).always(function (data) {
            self.is_user = data.is_user;
            self.email = data.email;
            _.each(_.keys(data.is_follower), function(is_follow) {
                self.$target.find("div[data-ids=" + is_follow + "]").attr('data-follow', data.is_follower[is_follow]);
                self.toggle_subscription(is_follow, data.is_follower[is_follow], data.email);
                self.$target.find('.tag_btn[data-id=' + is_follow + ']').on('click', function(event) {
                    self.on_click_tag($(this).attr('data-id'));
                });
            });
        });
        return;
    },
    on_click_tag: function(data_id) {
        var self = this;
        var $email = this.$target.find(".js_tag_follow_email[data-id=" + data_id + "]");

        if ($email.length && !$email.val().match(/.+@.+/)) {
            this.$target.addClass('has-error');
            return false;
        }

        var email = $email.length ? $email.val() : false;
        if (email || this.is_user) {
            ajax.jsonRpc('/website_mail/follow', 'is_follow', {
                'id': data_id,
                'object': 'forum.tag',
                'message_is_follower': this.$target.find("div[data-ids=" + data_id + "]").attr('data-follow') || "off",
                'email': email,
            }).then(function (follow) {
                self.toggle_subscription(data_id, follow[0], email);
                if (!follow[1]) {
                    location.reload();
                }
            });
        }
    },
    toggle_subscription: function(tag_id, follow, email) {
        if (follow) {
            this.$target.find(".js_tag_follow_btn#" + tag_id).addClass("hidden");
            this.$target.find(".js_tag_unfollow_btn#" + tag_id).removeClass("hidden");
            this.$target.find("a[data-tag-id=" + tag_id + "]").addClass("label-success").removeClass("label-default");
        }
        else {
            this.$target.find(".js_tag_follow_btn#" + tag_id).removeClass("hidden");
            this.$target.find(".js_tag_unfollow_btn#" + tag_id).addClass("hidden");
            this.$target.find("a[data-tag-id=" + tag_id + "]").addClass("label-default").removeClass("label-success");
        }
        this.$target.find('input.js_tag_follow_email[data-id=' + tag_id + ']')
            .val(email || "")
            .attr("disabled", email && (follow || this.is_user) ? "disabled" : false);
        this.$target.find('div[data-ids=' + tag_id + ']').attr("data-follow", follow ? 'on' : 'off');
    },
});

});
