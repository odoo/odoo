/*global $, _, PDFJS */
odoo.define('website_slides.slides', function (require) {
"use strict";

var ajax = require('web.ajax');
var core = require('web.core');
var time = require('web.time');
var Widget = require('web.Widget');
var local_storage = require('web.local_storage');
require('root.widget');

var _t = core._t;
var page_widgets = {};

(function () {
    var widget_parent = $('body');


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
                var target = button.find('.o_wslides_like_dislike_count');
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
                this.$el.removeClass('o_has_error').find('.form-control, .custom-select').removeClass('is-invalid');
                ajax.jsonRpc('/slides/slide/send_share_email', 'call', {
                    slide_id: slide_id,
                    email: input.val(),
                }).then(function () {
                    self.$el.html($('<div class="alert alert-info" role="alert"><strong>Thank you!</strong> Mail has been sent.</div>'));
                });
            }else{
                this.$el.addClass('o_has_error').find('.form-control, .custom-select').addClass('is-invalid');
                input.focus();
            }
        },
    });

    page_widgets['share_mail'] = new ShareMail(widget_parent).setElement($('.oe_slide_js_share_email'));

    /*
     * Social Sharing Statistics Widget
     */
    if ($('div#statistic').length) {
        $("a.o_slides_social_share").on('click', function(ev) {
            ev.preventDefault();
            var popUpURL = $(ev.currentTarget).attr('href');
            window.open(
                popUpURL,
                'Share Dialog',
                'width=626,height=436');
        });
    }
})();

return {
    page_widgets: page_widgets,
};

});
