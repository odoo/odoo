/*global $, _, PDFJS */
odoo.define('website_slides.slides_like', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    var core = require('web.core');
    var Widget = require('web.Widget');
    var local_storage = require('web.local_storage');
    var slides = require('website_slides.slides');
    
    var _t = core._t;
    
    (function () {
        var widget_parent = $('body');
    
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
    
        slides.page_widgets['likeButton'] = new LikeButton(widget_parent).setElement($('.oe_slide_js_like'));
        slides.page_widgets['dislikeButton'] = new LikeButton(widget_parent).setElement($('.oe_slide_js_unlike'));
    
    })();
    
});
    