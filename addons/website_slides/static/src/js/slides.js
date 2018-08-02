/*global $, _, PDFJS */
odoo.define('website_slides.slides', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');
var local_storage = require('web.local_storage');
var website = require('website.website');

var _t = core._t;
var page_widgets = {};

$(document).ready(function () {

    var widget_parent = $('body');

    website.localeDef.then(function () {
        $("timeago.timeago").each(function (index, el) {
            var datetime = $(el).attr('datetime'),
                datetime_obj = time.str_to_datetime(datetime),
                // if presentation 7 days, 24 hours, 60 min, 60 second, 1000 millis old(one week)
                // then return fix formate string else timeago
                display_str = "";
            if (datetime_obj && new Date().getTime() - datetime_obj.getTime() > 7 * 24 * 60 * 60 * 1000) {
                display_str = moment(datetime_obj).format('ll');
            } else {
                display_str = moment(datetime_obj).fromNow();
            }
            $(el).text(display_str);
        });
    });

    // To prevent showing channel settings alert box once user closed it.
    $('.o_slides_hide_channel_settings').on('click', function(ev) {
        var channel_id = $(this).data("channelId");
        ev.preventDefault();
        document.cookie = "slides_channel_" + channel_id + " = closed";
        return true;
    });

    /*
     * Like/Dislike Buttons Widget
     */
     var LikeButton = Widget.extend({
        setElement: function($el){
            this._super.apply(this, arguments);
            this.$el.on('click', this, _.bind(this.apply_action, this));
        },
        apply_action: function(ev){
            var button = $(ev.currentTarget);
            var slide_id = button.data('slide-id');
            var user_id = button.data('user-id');
            var is_public = button.data('public-user');
            var href = button.data('href');
            if(is_public){
                this.popover_alert(button, _.str.sprintf(_t('Please <a href="/web?redirect=%s">login</a> to vote this slide'), (document.URL)));
            }else{
                var target = button.find('.fa');
                if (local_storage.getItem('slide_vote_' + slide_id) !== user_id.toString()) {
                    ajax.jsonRpc(href, 'call', {slide_id: slide_id}).then(function (data) {
                        target.text(data);
                        local_storage.setItem('slide_vote_' + slide_id, user_id);
                    });
                } else {
                    this.popover_alert(button, _t('You have already voted for this slide'));
                }
            }
        },
        popover_alert: function($el, message){
            $el.popover({
                trigger: 'focus',
                placement: 'bottom',
                container: 'body',
                html: true,
                content: function(){
                    return message;
                }
            }).popover('show');
        },
    });

    page_widgets['likeButton'] = new LikeButton(widget_parent).setElement($('.oe_slide_js_like'));
    page_widgets['dislikeButton'] = new LikeButton(widget_parent).setElement($('.oe_slide_js_unlike'));

    /*
     * Embedded Code Widget
     */
     var SlideSocialEmbed = Widget.extend({
        events: {
            'change input' : 'change_page',
        },
        init: function(parent, max_page){
            this._super(parent);
            this.max_page = max_page || false;
        },
        change_page: function(ev){
            ev.preventDefault();
            var input = this.$('input');
            var page = parseInt(input.val());
            if (this.max_page && !(page > 0 && page <= this.max_page)) {
                page = 1;
            }
            this.update_embedded_code(page);
        },
        update_embedded_code: function(page){
            var embed_input = this.$('.slide_embed_code');
            var new_code = embed_input.val().replace(/(page=).*?([^\d]+)/, '$1' + page + '$2');
            embed_input.val(new_code);
        },
    });

    $('iframe.o_wslides_iframe_viewer').ready(function() {
        // TODO : make it work. For now, once the iframe is loaded, the value of #page_count is
        // still now set (the pdf is still loading)
        var $iframe = $(this);
        var max_page = $iframe.contents().find('#page_count').val();
        new SlideSocialEmbed($iframe, max_page).setElement($('.oe_slide_js_embed_code_widget'));
    });


    /*
     * Send by email Widget
     */
     var ShareMail = Widget.extend({
        events: {
            'click button' : 'send_mail',
        },
        send_mail: function(){
            var self = this;
            var input = this.$('input');
            var slide_id = this.$('button').data('slide-id');
            if(input.val() && input[0].checkValidity()){
                this.$el.removeClass('has-error');
                ajax.jsonRpc('/slides/slide/send_share_email', 'call', {
                    slide_id: slide_id,
                    email: input.val(),
                }).then(function () {
                    self.$el.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
                });
            }else{
                this.$el.addClass('has-error');
                input.focus();
            }
        },
    });

    page_widgets['share_mail'] = new ShareMail(widget_parent).setElement($('.oe_slide_js_share_email'));

    /*
     * Social Sharing Statistics Widget
     */
    if ($('div#statistic').length) {
        var slide_url = $("div#statistic").attr('slide-url');
        var social_urls = {
            'linkedin': 'https://www.linkedin.com/countserv/count/share?url=',
            'twitter': 'https://cdn.api.twitter.com/1/urls/count.json?url=',
            'facebook': 'https://graph.facebook.com/?id=',
            'gplus': 'https://clients6.google.com/rpc'
        }

        var update_statistics = function(social_site, slide_url) {
            if (social_site == 'gplus') {
                $.ajax({
                    url: social_urls['gplus'],
                    type: "POST",
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify([{
                        "method": "pos.plusones.get",
                        "id": "p",
                        "params": {
                            "nolog": true,
                            "id": slide_url,
                            "source": "widget",
                            "userId": "@viewer",
                            "groupId": "@self"
                        },
                        // TDE NOTE: should there be a key here ?
                        "jsonrpc": "2.0",
                        "apiVersion": "v1"
                    }]),
                    success: function(data) {
                        $('#google-badge').text(data[0].result.metadata.globalCounts.count || 0);
                        $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#google-badge').text()));
                    },
                });
            } else {
                $.ajax({
                    url: social_urls[social_site] + slide_url,
                    dataType: 'jsonp',
                    success: function(data) {
                        var shareCount = (social_site === 'facebook' ? data.shares : data.count) || 0;
                        $('#' + social_site + '-badge').text(shareCount);
                        $('#total-share').text(parseInt($('#total-share').text()) + parseInt($('#' + social_site+ '-badge').text()));
                    },
                });
            }
        };

        $.each(social_urls, function(key, value) {
            update_statistics(key, slide_url);
        });

        $("a.o_slides_social_share").on('click', function(ev) {
            ev.preventDefault();
            var key = $(ev.currentTarget).attr('social-key');
            var popUpURL = $(ev.currentTarget).attr('href');
            var popUp = window.open(
                popUpURL,
                'Share Dialog',
                'width=626,height=436');
            $(window).on('focus', function() {
                if (popUp.closed) {
                    update_statistics(key, slide_url);
                    $(window).off('focus');
                }
            });
        });
    }
});

return {
    page_widgets: page_widgets,
};

});
